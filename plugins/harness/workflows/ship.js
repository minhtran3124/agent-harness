export const meta = {
  name: 'ship',
  description: 'Ship 1..N triaged tickets to one reviewable PR with no human in the loop: per-ticket pipeline, review loop, intent review, full suite once, ADRs.',
  phases: [
    { title: 'Setup', detail: 'validate args, create the integration branch (multi-ticket only)' },
    { title: 'Tickets', detail: 'intent, plan, implement, verify, finish per ticket; groups in order, tickets of a group in parallel' },
    { title: 'Merge', detail: 'merge a finished group into the integration branch (multi-ticket only)' },
    { title: 'Review', detail: 'code-review the final PR, fix findings, re-review only the fix commits' },
    { title: 'Intent review', detail: 'plan-blind check of the final diff against the original request' },
    { title: 'Testing', detail: 'full test suite once, on the final branch' },
    { title: 'Decisions', detail: 'artifact, ADR files, final PR body' },
  ],
}

// ---------------------------------------------------------------------------
// Constants. Models and effort are chosen here, per stage, never inside a stage.
// ---------------------------------------------------------------------------
const MODEL = { intent: 'sonnet', research: 'haiku', design: 'sonnet', plan: 'sonnet', implement: 'sonnet',
  verify: 'sonnet', fix: 'sonnet', merge: 'sonnet', adr: 'sonnet', review: 'sonnet', test: 'haiku', cheap: 'haiku' }
const EFFORT = { intent: 'medium', research: 'low', design: 'medium', plan: 'medium', implement: 'medium',
  verify: 'medium', fix: 'medium', merge: 'low', adr: 'low', review: 'medium', test: 'low', cheap: 'low', advisor: 'high' }
const FIX_THRESHOLD = 50   // a review finding scoring at or above this gets one fix agent
const MAX_FIX_ROUNDS = 2   // hard cap on fix rounds in the review loop
// Paths whose change makes the review level 'high'.
const RISKY_PATH = /(^|\/)(hooks|migrations?|auth|security|secrets?|\.github\/workflows)(\/|$)|settings\.json$|\.sql$|\.env/i
const LARGE_DIFF_LINES = 800, SMALL_DIFF_LINES = 150, LARGE_DIFF_FILES = 25
const CO_AUTHOR = 'Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>'
const PR_FOOTER = '🤖 Generated with [Claude Code](https://claude.com/claude-code)'

const RULES_COMMON = `Rules (all of them apply):
- No human is in the loop. Never ask anyone anything. On any ambiguity pick the recommended option and return it as a decision in decisions[].
- Never merge into the base branch or main. Never force-push. Never touch secrets. Never weaken a test to make it pass.
- Follow the project's CLAUDE.md.
- Work only in your own worktree and on your own branch. Never edit files in the owner's checkout.
- Your session working directory is NOT the target repo. Use absolute paths; run every git command as git -C <path> or after cd <your worktree>.
- needs_review: true ONLY when the decision affects another ticket, a public contract or interface, stored data, security or cost, or contradicts the ticket text or an owner-confirmed answer. A reversible choice inside the ticket (naming, how to handle an edge case the ticket leaves open, which implementation to use) is needs_review: false. It is still recorded as a decision.
- summary is one plain sentence about what changed in the code. Never write about pushes, pull requests, the mode, or test counts in it.
- "Done" needs real command output. Report what you ran and its exit code; never claim a result you did not see.
- Run only the tests related to your change. The full suite is the last stage's job.
- Commit messages end with the line: ${CO_AUTHOR}
- Pull request bodies end with the line: ${PR_FOOTER}
- Run "git add" and "git commit" as separate commands.
- Use --json with "gh issue view" (plain "gh issue view" fails on this repo).
- owner_confirmed: true ONLY when a decision just restates an answer listed under the ticket's owner-confirmed decisions. Such a decision gets no ADR file unless it also has needs_review: true (needs_review wins); the PR table says owner-confirmed. Otherwise leave it out.
- decisions[] holds only real choices between options that change the code or the behaviour. Facts about the environment (which test runner you used, that pytest is missing, that a file was or was not found, that a plan step was already satisfied) are not decisions: leave them out.
- Never write ADR files. Return decisions[] instead; one stage at the end writes them.
- You cannot start other agents. If you are stuck, unsure, or a choice affects another ticket or a public contract, set needs_advisor: true with advisor_question and stop; the script asks the advisor.`

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------
const STR = { type: 'string' }, BOOL = { type: 'boolean' }, NUM = { type: 'number' }
const strList = { type: 'array', items: STR }

const DECISION = {
  type: 'object',
  properties: {
    title: STR, context: STR, options: strList, decision: STR, why: STR, consequences: STR,
    how_to_reverse: STR, confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    needs_review: { type: 'boolean', description: 'true ONLY when the decision affects another ticket, a public contract or interface, stored data, security or cost, or contradicts the ticket text or an owner-confirmed answer. A reversible choice inside the ticket (naming, an edge case the ticket leaves open, which implementation) is false.' },
    stage: STR, contradicts_confirmed: BOOL, dangerous: BOOL,
    owner_confirmed: { type: 'boolean', description: 'true ONLY when the decision just restates an owner-confirmed answer for the ticket (no ADR file is written for it unless needs_review is also true). Leave out otherwise.' },
  },
  required: ['title', 'context', 'options', 'decision', 'why', 'consequences', 'how_to_reverse', 'confidence', 'needs_review'],
}

// Every stage result carries status, decisions and the advisor request (ADR 0001 decision 2).
function stageSchema(extra, required) {
  return {
    type: 'object',
    properties: {
      status: { type: 'string', enum: ['ok', 'blocked'] },
      summary: { type: 'string', description: 'One plain sentence about what changed in the code. Never about pushes, pull requests, mode, or test counts.' }, blocked_reason: STR,
      decisions: { type: 'array', items: DECISION }, needs_advisor: BOOL, advisor_question: STR, ...extra,
    },
    required: ['status', 'summary', ...(required || [])],
  }
}
const STEP = { type: 'object', properties: { title: STR, files: strList, done_when: STR }, required: ['title', 'done_when'] }
const INTENT_SCHEMA = stageSchema({ goal: STR, acceptance: strList, files: strList, out_of_scope: strList, plan_steps: { type: 'array', items: STEP } }, ['goal'])
const RESEARCH_SCHEMA = stageSchema({ research_md: STR }, ['research_md'])
const DESIGN_SCHEMA = stageSchema({ design_md: STR }, ['design_md'])
const PLAN_SCHEMA = stageSchema({ plan_md: STR, plan_steps: { type: 'array', items: STEP } }, ['plan_md'])
const IMPLEMENT_SCHEMA = stageSchema({
  worktree: STR, branch: STR, files: strList,
  commits: { type: 'array', items: { type: 'object', properties: { sha: STR, subject: STR }, required: ['sha', 'subject'] } },
  verify: { type: 'array', items: { type: 'object', properties: { command: STR, exit: NUM, notes: STR }, required: ['command', 'exit'] } },
}, ['worktree', 'branch'])
// The verify skill reports prose; this schema gives ship.js the facts it decides on. Not IMPLEMENT_SCHEMA.verify.
const VERIFY_SCHEMA = stageSchema({
  passed: { type: 'boolean', description: 'true only when every step and command of the Verify: row passed and the browser console had no errors' },
  kind: { type: 'string', enum: ['BE', 'FE', 'FE+BE', 'docs'], description: 'the ticket type from the Verify: row' },
  failedStep: STR, consoleErrors: strList, stills: { type: 'array', items: STR, description: 'absolute local paths of the screenshots' }, report: STR,
}, ['passed', 'kind'])
const GIF_SCHEMA = stageSchema({ gif: { type: 'string', description: 'absolute path of the GIF, or empty when none was built' } }, ['gif'])
const FINISH_SCHEMA = stageSchema({ pr: NUM, url: STR, body_file: STR }, ['pr'])
const SETUP_SCHEMA = stageSchema({})
const MERGE_SCHEMA = stageSchema({
  merged: { type: 'array', items: NUM },
  failed: { type: 'array', items: { type: 'object', properties: { n: NUM, reason: STR }, required: ['n', 'reason'] } },
}, ['merged', 'failed'])
const FINAL_PR_SCHEMA = stageSchema({ pr: NUM, url: STR }, ['pr'])
const DIFFSTAT_SCHEMA = { type: 'object',
  properties: { files: { type: 'array', items: { type: 'object', properties: { path: STR, added: NUM, deleted: NUM }, required: ['path', 'added', 'deleted'] } } },
  required: ['files'] }
const REVIEW_SCHEMA = stageSchema({
  findings: { type: 'array', items: { type: 'object',
    properties: { id: STR, path: STR, line: NUM, summary: STR, score: NUM, pre_existing: BOOL },
    required: ['id', 'summary', 'score'] } },
  skill_invoked: { type: 'boolean', description: 'true only if you invoked the Skill tool with skill code-review and it ran. Reading the diff yourself does not count.' },
  skill_error: { type: 'string', description: 'When skill_invoked is false: the exact error or the reason the skill did not run.' },
}, ['findings', 'skill_invoked'])
const FIX_SCHEMA = stageSchema({
  fix_status: { type: 'string', enum: ['fixed', 'skipped', 'failed'] }, base_sha: STR, commit: STR, test_added: STR,
}, ['fix_status'])
const REQUEST_SCHEMA = { type: 'object', properties: { body: STR }, required: ['body'] }
const INTENT_REVIEW_SCHEMA = { type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['match', 'gaps found'] },
    findings: { type: 'array', items: { type: 'object',
      properties: { kind: { type: 'string', enum: ['gap', 'drift', 'excess'] }, behaviour_changing: BOOL, clause: STR, detail: STR },
      required: ['kind', 'clause', 'detail'] } },
  },
  required: ['verdict', 'findings'] }
const SUITE_SCHEMA = { type: 'object',
  properties: { passed: NUM, failed: NUM, skipped: NUM, failing: strList, exit_code: NUM, tail: STR },
  required: ['passed', 'failed', 'skipped', 'failing'] }
const ARTIFACT_SCHEMA = { type: 'object', properties: { created: BOOL, url: STR, fallback: STR }, required: ['created'] }
const ADR_SCHEMA = stageSchema({
  adrs: { type: 'array', items: { type: 'object',
    properties: { number: NUM, path: STR, needs_review: BOOL }, required: ['number', 'path', 'needs_review'] } },
  body_file: STR,
}, ['adrs'])

// ---------------------------------------------------------------------------
// Args and derived names
// ---------------------------------------------------------------------------
function validateArgs(a) {
  if (!a || typeof a !== 'object') throw new Error('ship: args is required')
  for (const k of ['repo', 'repoDir', 'pluginDir', 'remote', 'base', 'slug', 'testCmd', 'lintCmd', 'fullTestCmd', 'advisorModel']) {
    if (typeof a[k] !== 'string' || !a[k].trim()) throw new Error(`ship: args.${k} is required (non-empty string)`)
  }
  if (!Array.isArray(a.tickets) || a.tickets.length === 0) throw new Error('ship: args.tickets must be a non-empty array')
  const seen = new Set()
  for (const t of a.tickets) {
    if (!t || !Number.isInteger(t.n)) throw new Error('ship: every ticket needs an integer n')
    if (seen.has(t.n)) throw new Error(`ship: duplicate ticket number #${t.n}`)
    seen.add(t.n)
    if (typeof t.title !== 'string' || !t.title) throw new Error(`ship: ticket #${t.n} needs a title`)
    if (!['S', 'M', 'L'].includes(t.depth)) throw new Error(`ship: ticket #${t.n} depth must be S, M or L`)
    if (!Number.isInteger(t.group)) throw new Error(`ship: ticket #${t.n} needs an integer group`)
    if (t.deps !== undefined && !Array.isArray(t.deps)) throw new Error(`ship: ticket #${t.n} deps must be an array`)
  }
}
validateArgs(args)

const { repo, repoDir, pluginDir, remote, base, slug, testCmd, lintCmd, fullTestCmd, advisorModel } = args
// The harness files (skills, agents, scripts) live in the plugin directory, not in the target repo.
const RULES = `${RULES_COMMON}\n- Harness files (skills/, agents/, scripts/) live in the plugin directory ${pluginDir}. Read them there by absolute path.`
const LOCAL = args.local === true
const NO_ASK = args.noAsk === true
const tickets = args.tickets
const single = tickets.length === 1

const slugOf = s => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40)
const baseRef = `${remote}/${base}`
const integBranch = `feat/${slug}`
// Where tickets branch from. In local mode the integration branch only exists locally.
const integRef = single ? baseRef : (LOCAL ? integBranch : `${remote}/${integBranch}`)
const ticketBranch = t => (single ? `feat/${t.n}-${slugOf(t.title)}` : `feat/${slug}-${t.n}`)
const finalBranch = single ? ticketBranch(tickets[0]) : integBranch
const finalRef = single ? (LOCAL ? finalBranch : `${remote}/${finalBranch}`) : integRef

// No agent uses isolation: 'worktree'. That option binds to the session's cwd, which is not the target repo
// (ADR 0002). Each agent creates its own worktree of repoDir, outside the repo, so git status stays clean.
const trimmed = repoDir.replace(/\/+$/, '')
const parentDir = trimmed.split('/').slice(0, -1).join('/')
const wtRoot = `${parentDir}/.ship-${trimmed.split('/').pop()}/${slugOf(slug)}`
const worktrees = new Set()   // every dir the script told an agent to create; the owner removes them
const notCwd = dir => `Your session working directory is NOT the target repo. Run every command with \`git -C <path>\` or after \`cd ${dir || repoDir}\`; never edit ${repoDir} itself.`
// branch: create it; null: detached checkout of `from` (an existing ref).
function newWt(name, branch, from) {
  const dir = `${wtRoot}/${name.replace(/[^a-z0-9]+/gi, '-').replace(/^-+|-+$/g, '')}`
  worktrees.add(dir)
  return { dir, setup:
    `git -C ${repoDir} fetch ${remote}\ngit -C ${repoDir} worktree add ${branch ? `-b ${branch} ` : '--detach '}${dir} ${from}\n\n` +
    `Run the two commands above first, in that order. If ${dir} already exists (an earlier attempt of this stage), do not recreate it: cd into it and continue. Your worktree is ${dir}. ${notCwd(dir)}\n\n` }
}
// Publish the current HEAD to an existing branch (fast-forward only).
const land = branch => (LOCAL
  ? `git update-ref refs/heads/${branch} HEAD   (local mode: nothing is pushed)`
  : `git push ${remote} HEAD:${branch}`)

// ---------------------------------------------------------------------------
// Agent calls
// ---------------------------------------------------------------------------
const clean = o => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined))

// A plugin agent type (harness:<role>) may not resolve; then the default agent reads the role file itself.
async function call(prompt, opts, roleFile) {
  if (!opts.agentType) return agent(prompt, clean(opts))
  try {
    return await agent(prompt, clean(opts))
  } catch (e) {
    log(`agent type '${opts.agentType}' unavailable (${e && e.message}); using the default agent with ${roleFile}`)
    const { agentType, ...rest } = opts
    return agent(`Your role: first read ${roleFile} and act as that role.\n\n${prompt}`, clean(rest))
  }
}

const decisions = []   // the only place decisions live; agents never write ADR files
const str = v => (typeof v === 'string' && v.trim() ? v : 'n/a')
function takeDecisions(ticket, stage, res) {
  for (const d of (res && res.decisions) || []) {
    if (!d || typeof d !== 'object') continue
    const flagged = !!(d.contradicts_confirmed || d.dangerous)
    const title = str(d.title)   // only the agent labels a decision Boundary; a skip for another reason keeps its own title
    decisions.push({
      ticket, stage: d.stage || stage, title, context: str(d.context),
      options: Array.isArray(d.options) && d.options.length ? d.options : ['n/a'],
      decision: str(d.decision), why: str(d.why), consequences: str(d.consequences), how_to_reverse: str(d.how_to_reverse),
      confidence: ['high', 'medium', 'low'].includes(d.confidence) ? d.confidence : 'low',
      needs_review: flagged || title.startsWith(BOUNDARY_PREFIX) || d.needs_review === true,
      owner_confirmed: !flagged && d.owner_confirmed === true,
      boundary: title.startsWith(BOUNDARY_PREFIX),
      decided_by: `claude (ship workflow: ${stage})`,
    })
  }
}

function addDecision(ticket, stage, d) {
  decisions.push({ ticket, stage, options: ['n/a'], confidence: 'high', needs_review: false, decided_by: `claude (ship workflow: ${stage})`, ...d })
}

// The boundary of a ticket: its Out of scope lines and the files it names (intent files plus plan-step files).
const BOUNDARY_PREFIX = 'Boundary: '
const boundaries = {}   // ticket number -> { out_of_scope, files }, filled after each intent stage
const uniq = a => [...new Set(a.filter(x => typeof x === 'string' && x.trim()))]
function boundaryOf(intent) {
  const i = intent || {}
  return {
    out_of_scope: uniq(Array.isArray(i.out_of_scope) ? i.out_of_scope : []),
    files: uniq([...(Array.isArray(i.files) ? i.files : []), ...(Array.isArray(i.plan_steps) ? i.plan_steps : []).flatMap(s => (s && Array.isArray(s.files) ? s.files : []))]),
  }
}
const BOUNDARY_RULE = `A change outside these files, or against an Out of scope line, is NOT made. Return it as a decision whose title starts with '${BOUNDARY_PREFIX}' and needs_review true.`
function boundaryText(label, intent) {
  const b = boundaryOf(intent)
  return `${label}\nOut of scope (the ticket's own lines):\n${b.out_of_scope.length ? b.out_of_scope.map(x => `- ${x}`).join('\n') : '- none listed'}\n` +
    `Files this ticket names (production, test and doc files alike: a test or doc file is in bounds only when it is listed here):\n${b.files.length ? b.files.map(x => `- ${x}`).join('\n') : '- none listed'}\n${BOUNDARY_RULE}\n`
}
// Run-level view for the fix agents: the union over all tickets, labelled by ticket number.
function runBoundaryText() {
  const ns = Object.keys(boundaries)
  if (!ns.length) return ''
  const body = ns.map(n => `Ticket #${n}\n` + boundaryText('', boundaries[n]).replace(`\n${BOUNDARY_RULE}\n`, '').trim()).join('\n\n')
  return `Boundary (union over the tickets in this run):\n${body}\n` +
    `The file set limits production, test and doc files alike: a test or doc file is in bounds only when the list above names it. ` +
    `A fix that would touch a file outside this set, or contradict an Out of scope line, changes nothing: return fix_status skipped and a decisions[] entry whose title starts with '${BOUNDARY_PREFIX}' and needs_review true.\n`
}

const capSummary = v => { const x = (typeof v === 'string' ? v : '').replace(/\s+/g, ' ').trim(); return x.length > 200 ? `${x.slice(0, 199)}…` : x }

class Blocked extends Error {}

async function askAdvisor(t, stage, question, state) {
  const prompt = `${RULES}\n\nTicket #${t.n}: ${t.title} (depth ${t.depth}), stage ${stage}.\n` +
    `${notCwd()}\nQuestion: ${question || '(the stage gave no question; review its work)'}\n` +
    `Stage summary: ${state || '(none)'}\n` +
    `Answer with: Recommendation, Reasons, Risks, Confidence. Read only what the question needs. Do not edit anything.`
  const advice = await call(prompt,
    { label: `advisor:${stage}:${t.n}`, phase: 'Tickets', model: advisorModel, effort: EFFORT.advisor, agentType: 'harness:advisor' },
    `${pluginDir}/agents/advisor.md`)
  return typeof advice === 'string' ? advice : ''
}

// One ticket stage: run it; on needs_advisor ask once and re-run once; collect decisions; stop on a block.
async function runStage(t, stage, build, schema, opts) {
  const { roleFile, ...rest } = opts
  const o = { ...rest, schema, phase: 'Tickets' }
  let res = await call(build(''), { ...o, label: `${stage}:${t.n}` }, roleFile)
  if (res && res.needs_advisor) {
    const advice = await askAdvisor(t, stage, res.advisor_question, res.summary)
    res = await call(build(`\n\n## Advisor advice (follow it unless it is wrong; record any deviation as a decision)\n${advice}`),
      { ...o, label: `${stage}:${t.n}:retry` }, roleFile)
    if (res && res.needs_advisor) log(`#${t.n} ${stage}: asked for a second advisor call; the limit is one per stage, continuing with the retry result`)
  }
  if (!res) throw new Blocked(`${stage}: the agent returned nothing`)
  takeDecisions(t.n, stage, res)
  if (res.status === 'blocked') throw new Blocked(`${stage}: ${res.blocked_reason || res.summary}`)
  const bad = (res.decisions || []).find(d => d.contradicts_confirmed || d.dangerous)
  if (bad) throw new Blocked(`${stage}: question for the owner: ${bad.title} (${bad.contradicts_confirmed ? 'contradicts an owner-confirmed answer' : 'dangerous'})`)
  return res
}

// ---------------------------------------------------------------------------
// Ticket stages (one function per stage)
// ---------------------------------------------------------------------------
function head(t, skill, extra, wt) {
  const confirmed = t.confirmed && t.confirmed.trim()
    ? `Owner-confirmed decisions for this ticket (never contradict them; if you must, mark the decision contradicts_confirmed and stop that part):\n${t.confirmed}\n\n`
    : ''
  const ask = NO_ASK ? 'No owner answers exist for this run: every question you would have asked becomes a decision; set needs_review by the rule above.\n' : ''
  const read = skill ? `Read ${pluginDir}/skills/${skill}/SKILL.md and run it with Mode: auto, only after your worktree exists (it is created by the commands above). Never ask anyone.\n` : ''
  const source = LOCAL ? `Ticket text: ${t.title}\n` : `The ticket is GitHub issue #${t.n} of ${repo}; read it with: gh issue view ${t.n} --repo ${repo} --json body -q .body\n`
  return `${RULES}\n\n${notCwd(wt)}\nTicket #${t.n}: ${t.title} (depth ${t.depth}). Repo ${repo}.\n${source}${confirmed}${ask}${read}${extra || ''}`
}

function stageIntent(t) {
  const build = advice => head(t, null,
    `Stage: intent. Restate what the owner asked for as a goal and checkable acceptance criteria, list the files likely touched, ` +
    `and return plan_steps (title, files, done_when) as the plan. Copy the ticket's Out of scope lines verbatim into out_of_scope (an empty list when it has none).${t.depth === 'S' ? ' This is the plan for the implement stage.' : ' A later stage writes the full plan.'} ` +
    `${single ? `You may read files in ${repoDir} (git -C ${repoDir} ...); never edit them.` : `Plan against the code as it is on ${integRef}, which already holds the finished earlier groups; the checkout in ${repoDir} is NOT that code. Run git -C ${repoDir} fetch ${remote} first, then read files only with git -C ${repoDir} show ${integRef}:<path> or git -C ${repoDir} ls-tree -r ${integRef}. Never edit ${repoDir}.`} Return decisions[] for every real choice you made.${advice}`)
  return runStage(t, 'intent', build, INTENT_SCHEMA, { model: MODEL.intent, effort: EFFORT.intent })
}

function stageResearch(t, intent) {
  const w = newWt(`research-${t.n}`, null, integRef)
  const build = advice => w.setup + head(t, 'xia2',
    `Stage: research for a depth L ticket. Write the research brief and return its full text as research_md.\nIntent: ${JSON.stringify(intent)}${advice}`, w.dir)
  return runStage(t, 'research', build, RESEARCH_SCHEMA, { model: MODEL.research, effort: EFFORT.research })
}

function stageDesign(t, intent, research) {
  const w = newWt(`design-${t.n}`, null, integRef)
  const build = advice => w.setup + head(t, 'brainstorming',
    `Stage: design. Return the design as a decision with stage 'design' in decisions[] (a design ADR) and its text as design_md.\n` +
    `Intent: ${JSON.stringify(intent)}\nResearch brief:\n${research.research_md}${advice}`, w.dir)
  return runStage(t, 'design', build, DESIGN_SCHEMA, { model: MODEL.design, effort: EFFORT.design })
}

function stagePlan(t, intent, extra) {
  const w = newWt(`plan-${t.n}`, null, integRef)
  const build = advice => w.setup + head(t, 'writing-plans',
    `Stage: plan. Write PLAN.md locally (do not commit it) and return its full text as plan_md, plus plan_steps.\n` +
    `Intent: ${JSON.stringify(intent)}\n${extra || ''}${advice}`, w.dir)
  return runStage(t, 'plan', build, PLAN_SCHEMA, { model: MODEL.plan, effort: EFFORT.plan })
}

// A depth-L ticket gets one advisor look at its design and plan before any code is written.
async function advisePlan(t, design, plan) {
  return askAdvisor(t, 'plan-review', 'Is this design and plan sound and complete enough to implement? Name what to change.',
    `Design:\n${design.design_md}\n\nPlan:\n${plan.plan_md}`)
}

function stageImplement(t, branch, planText, boundary) {
  const w = newWt(`t${t.n}`, branch, integRef)
  const build = advice => w.setup + head(t, 'implement',
    `Stage: implement. You cannot start other agents, so act as the implementer yourself (${pluginDir}/agents/implementer.md): take the plan steps one at a time. ` +
    `For each step: do it, run its done_when command, then "git add" and, as a separate command, "git commit". ` +
    `Related tests: ${testCmd} (a template; fill in the files you touched). Lint: ${lintCmd}.\n` +
    `Return ${w.dir} as worktree, and your branch.\n\n${boundary || ''}\n${planText}${advice}`, w.dir)
  return runStage(t, 'implement', build, IMPLEMENT_SCHEMA, { agentType: 'harness:implementer', roleFile: `${pluginDir}/agents/implementer.md`, model: MODEL.implement, effort: EFFORT.implement })
}

// One verify run. mode: 'verify' (head), 'verify-retry' (head again) or 'verify-base' (base commit, a separate worktree).
// The agent only runs the steps and reports; retry, flaky and base decisions stay in verifyTicket.
function stageVerify(t, impl, mode) {
  const base = mode === 'verify-base'
  const w = base ? newWt(`verify-base-${t.n}`, null, integRef) : null
  const dir = base ? w.dir : impl.worktree
  const build = advice => (base ? w.setup : '') + head(t, null,
    `Stage: verify. Read ${pluginDir}/skills/verify/SKILL.md and follow it. Read the Verify: row of the issue body above. ` +
    (base
      ? `Mode: base. Your worktree ${dir} holds the base commit, without the ticket code. Read verify.config.json from ${impl.worktree}/verify.config.json (read-only; copy it into ${dir} without committing it). The steps are expected to FAIL here: report the real result. Commit nothing.\n`
      : `Mode: head. Work in ${impl.worktree} (cd there; it is the ticket branch ${impl.branch}). Commit only verify.config.json, nothing else.${mode === 'verify-retry' ? ' This is a second run after a failure: start the app fresh and run every step again.' : ''}\n`) +
    `Do not fix code, retry, or judge flakiness. Keep the evidence local and uncommitted. Return passed (true only if every step passed and the console had no errors), kind, failedStep, consoleErrors, stills (absolute paths) and report (the table).${advice}`, dir)
  return runStage(t, mode, build, VERIFY_SCHEMA, { model: MODEL.verify, effort: EFFORT.verify })
}

// A failed comment must not change the outcome: it is only logged.
async function commentVerify(t, text) {
  if (LOCAL) return
  try {
    await call(`Run: gh issue comment ${t.n} --repo ${repo} --body "<the text below, as one quoted argument>"\n\n${RULES}\n\nText:\n${text}\nPost the comment and return status ok. Edit nothing else.`,
      { label: `verify-comment:${t.n}`, phase: 'Tickets', schema: SETUP_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
  } catch (e) { log(`#${t.n} verify comment failed: ${e && e.message}`) }
}

const verifyFacts = r => `failing step: ${r.failedStep || 'unknown'}; console errors: ${(r.consoleErrors || []).join(' | ') || 'none'}\n${r.report || ''}`

// Head run, one retry, then the base check (FE and FE+BE only). Local mode skips the stage.
async function verifyTicket(t, impl) {
  if (LOCAL) return null
  let r = await stageVerify(t, impl, 'verify')
  let result = 'pass'
  if (!r.passed) {
    r = await stageVerify(t, impl, 'verify-retry')
    if (!r.passed) {
      const msg = `verify failed twice (${verifyFacts(r)})`
      await commentVerify(t, `Verify failed twice for #${t.n}: ${verifyFacts(r)}`)
      throw new Blocked(msg)
    }
    result = 'flaky'
  }
  if (r.kind === 'FE' || r.kind === 'FE+BE') {
    const b = await stageVerify(t, impl, 'verify-base')
    if (b.passed) {
      const msg = 'verify steps also pass on the base commit, so the test does not prove the change (weak test)'
      await commentVerify(t, `Verify for #${t.n}: ${msg}.\n${b.report || ''}`)
      throw new Blocked(msg)
    }
  }
  const stills = r.stills || []
  const gif = await buildGif(t, impl, stills)
  return { result, stills, gif, report: r.report || '' }
}

// Stills to one GIF with ffmpeg. Any problem gives null and a log line; it never changes the verify result.
async function buildGif(t, impl, stills) {
  if (!stills.length) { log(`#${t.n} no stills, no GIF`); return null }
  const dir = `${impl.worktree}/.playwright-mcp/${t.n}`
  try {
    const res = await call(
      `Stage: gif. Build one animated GIF from the verify stills of ticket #${t.n}. Stills (in order): ${stills.join(', ')}. They sit in ${dir}.\n` +
      `Use ffmpeg, for example: ffmpeg -y -framerate 1 -pattern_type glob -i '${dir}/*.png' -vf "scale=800:-2:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" ${dir}/evidence.gif\n` +
      `Rules: palettegen, at most 30 seconds, 800 px wide, under 10 MB (drop frames or lower the frame rate if larger). Write the GIF inside ${dir}. Commit nothing and do not add it to git.\n` +
      `Return gif: the absolute path of the GIF, or an empty string when there are no stills, ffmpeg is missing or the build failed.\n\n${RULES}`,
      { label: `gif:${t.n}`, phase: 'Tickets', schema: GIF_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
    if (res && res.gif) return res.gif
    log(`#${t.n} no GIF built`)
  } catch (e) { log(`#${t.n} gif build failed: ${e && e.message}`) }
  return null
}

// Separate from stageFinish: runs only for a real PR with a GIF and a pass or flaky result. A failure is only logged.
async function stageAttach(t, fin, verifyResult) {
  if (!(fin && fin.pr > 0) || !verifyResult || !verifyResult.gif) return
  if (verifyResult.result !== 'pass' && verifyResult.result !== 'flaky') return
  const flaky = verifyResult.result === 'flaky'
  const note = `Verify for #${t.n} was flaky: it failed once and passed on the retry.`
  try {
    await call(
      `Stage: attach. Run: gh pr comment ${fin.pr} --repo ${repo} --attach ${verifyResult.gif} --body "Verify evidence for #${t.n}: ${verifyResult.result}"\n` +
      (flaky ? `Then add this note to the end of the PR body: read it with gh pr view ${fin.pr} --repo ${repo} --json body -q .body, append "${note}", and write it back with gh pr edit ${fin.pr} --repo ${repo} --body-file <file>.\n` : '') +
      `Commit nothing; the GIF stays uncommitted. Return status ok.\n\n${RULES}`,
      { label: `attach:${t.n}`, phase: 'Tickets', schema: SETUP_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
  } catch (e) { log(`#${t.n} attach failed: ${e && e.message}`) }
}

function stageFinish(t, impl, verifyResult) {
  const prBase = single ? base : integBranch
  const fw = newWt(`finish-${t.n}`, null, LOCAL ? impl.branch : `${remote}/${impl.branch}`)
  const dir = impl.worktree || fw.dir
  const where = `Your branch ${impl.branch} is checked out in ${dir}; work there with cd ${dir}. If that path is gone, run: git -C ${repoDir} worktree add ${fw.dir} ${impl.branch}, and work in ${fw.dir} (git fetch ${remote} first).\n`
  const how = LOCAL
    ? `Local mode: do NOT push and do NOT open a pull request. Verify the branch as the skill describes, then write the PR description for base ${prBase} to .ship/pr-${t.n}.md inside the worktree (do not commit it) and return its absolute path as body_file with pr: 0.\n`
    : `Verify, push the branch and open the pull request with base ${prBase}. The body says "Refs #${t.n}" (the final PR carries the Closes lines) and ends with the footer line. Return the PR number as pr and its url.\n`
  const ver = verifyResult
    ? `Verify result: ${verifyResult.result}. Local stills: ${verifyResult.stills.join(', ') || 'none'}. Evidence stays uncommitted; a later step attaches the GIF to the pull request.\n`
    : ''
  const build = advice => head(t, 'finishing-a-development-branch', `Stage: finish. ${where}${ver}${how}Do not run the full suite.${advice}`, dir)
  return runStage(t, 'finish', build, FINISH_SCHEMA, { model: MODEL.implement, effort: EFFORT.implement })
}

async function runTicket(t) {
  const branch = ticketBranch(t)
  try {
    const intent = await stageIntent(t)
    boundaries[t.n] = boundaryOf(intent)
    const boundary = boundaryText(`Boundary for ticket #${t.n}:`, intent)
    let planText
    if (t.depth === 'S') {
      planText = `Plan (steps from the intent stage):\n${JSON.stringify(intent.plan_steps || [])}`
    } else if (t.depth === 'M') {
      const plan = await stagePlan(t, intent)
      planText = `Write this to specs/${slug}-${t.n}/PLAN.md in your worktree (local scratch, do not commit it) and follow it:\n${plan.plan_md}`
    } else {
      const research = await stageResearch(t, intent)
      const design = await stageDesign(t, intent, research)
      const plan = await stagePlan(t, intent, `Design:\n${design.design_md}\n`)
      const advice = await advisePlan(t, design, plan)
      planText = `Design:\n${design.design_md}\n\nAdvisor review of design and plan (follow it unless it is wrong; record any deviation as a decision):\n${advice}\n\n` +
        `Write this to specs/${slug}-${t.n}/PLAN.md in your worktree (local scratch, do not commit it) and follow it:\n${plan.plan_md}`
    }
    const impl = await stageImplement(t, branch, planText, boundary)
    const verifyResult = await verifyTicket(t, impl)
    const fin = await stageFinish(t, impl, verifyResult)
    await stageAttach(t, fin, verifyResult)
    log(`#${t.n} done: ${fin.url || fin.body_file || impl.branch}`)
    return { n: t.n, status: 'done', pr: fin.pr || null, url: fin.url || '', branch: impl.branch || branch, summary: capSummary(impl.summary || fin.summary), reason: '', body_file: fin.body_file }
  } catch (e) {
    const reason = e && e.message ? e.message : String(e)
    log(`#${t.n} blocked: ${reason}`)
    return { n: t.n, status: 'blocked', pr: null, url: '', branch, summary: '', reason }
  }
}

// ---------------------------------------------------------------------------
// Run-level stages
// ---------------------------------------------------------------------------
function stageSetupIntegration() {
  // Only refs change; nothing is checked out and no file in repoDir is edited.
  const how = LOCAL
    ? `git -C ${repoDir} fetch ${remote}\ngit -C ${repoDir} branch ${integBranch} ${baseRef}`
    : `git -C ${repoDir} fetch ${remote}\ngit -C ${repoDir} push ${remote} ${baseRef}:refs/heads/${integBranch}`
  return call(`${how}\n\n${RULES}\n\n${notCwd()}\n\nCreate the integration branch ${integBranch} from ${baseRef} using exactly the commands above (only refs change; never check anything out in ${repoDir}). ` +
    `If it already exists, report that in summary and change nothing. Return status ok when ${integBranch} points at ${baseRef} or a descendant of it.`,
    { label: 'setup-integration', phase: 'Setup', schema: SETUP_SCHEMA, model: MODEL.merge, effort: EFFORT.merge })
}

async function stageMerge(group, done) {
  const list = done.map(r => `- #${r.n} branch ${r.branch}${r.pr ? ` PR ${r.pr}` : ''}`).join('\n')
  const how = LOCAL
    ? `Merge each branch below into ${integBranch} with "git merge --no-ff". Then run: git update-ref refs/heads/${integBranch} HEAD   (local mode: nothing is pushed).`
    : `Merge each ticket PR below into ${integBranch}: gh pr merge <pr> --repo ${repo} --merge. On a conflict, merge locally, resolve it, and land it with: git push ${remote} HEAD:${integBranch}, then close that PR with a comment. These PRs target ${integBranch}, never ${base}. A PR that is already MERGED into ${integBranch} counts as merged: check its state first with gh pr view <pr> --repo ${repo} --json state, and do not merge it again. If gh pr merge is denied by a permission rule, do not look for a workaround: return that ticket in failed with a reason that names the missing permission and the fix (the owner allows gh pr merge into ${integBranch}*), and do not just write denied.`
  const w = newWt(`merge-g${group}`, `scratch/${slug}-merge-g${group}`, integRef)
  const prompt = `${w.setup}${RULES}\n\nStage: merge group ${group} into ${integBranch}.\n${how}\n${list}\n` +
    `After any conflict resolution run the related tests (${testCmd}, filled with the conflicted files) and lint (${lintCmd}). ` +
    `Return merged (ticket numbers) and failed ([{n, reason}]). Never merge into ${base}.`
  const res = await call(prompt, { label: `merge:g${group}`, phase: 'Merge', schema: MERGE_SCHEMA, model: MODEL.merge, effort: EFFORT.merge })
  takeDecisions('run', 'merge', res)
  return res
}

function stageFinalPr(done, bodyTemplate) {
  const prompt = `${RULES}\n\nStage: open the final pull request ${integBranch} -> ${base} in ${repo}.\n` +
    (LOCAL
      ? `Local mode: do not push and do not open a pull request. Return pr: 0.\n`
      : `Write the body below to a temp file and run: gh pr create --repo ${repo} --base ${base} --head ${integBranch} --title "${slug}" --body-file <file>. Return its number and url.\n`) +
    `Body (a later stage replaces it with the final text):\n${bodyTemplate}`
  return call(prompt, { label: 'final-pr', phase: 'Review', schema: FINAL_PR_SCHEMA, model: MODEL.merge, effort: EFFORT.merge })
}

function pickLevel(files) {
  const lines = files.reduce((s, f) => s + (f.added || 0) + (f.deleted || 0), 0)
  const risky = files.filter(f => RISKY_PATH.test(f.path)).map(f => f.path)
  let level = 'medium'
  if (risky.length || lines > LARGE_DIFF_LINES || files.length > LARGE_DIFF_FILES) level = 'high'
  else if (lines <= SMALL_DIFF_LINES) level = 'low'
  return { level, lines, risky }
}

const RULE_SKILL = `You MUST invoke the Skill tool with skill 'code-review'. Do not substitute your own review: reading the diff yourself does not count. ` +
  `If the Skill tool or the skill is unavailable or fails, return skill_invoked: false and the exact error in skill_error, and return no findings.`

function reviewAgent(label, level, target, rangeNote, retryNote) {
  const w = newWt(label, null, finalRef)
  const prompt = `${w.setup}${RULES}\n\n` +
    `Stage: review. Use the Skill tool: skill 'code-review', args '${level} ${target}'. Run it from ${w.dir} (the final branch is checked out there${rangeNote ? '' : `; the diff is ${baseRef}...${finalRef}`}). Never edit files, never post comments.\n` +
    `${RULE_SKILL} Return skill_invoked: true only when the skill ran.\n${retryNote || ''}` +
    `${rangeNote}Return every finding with score 0-100 (how sure you are that it is a real defect worth fixing). ` +
    `Mark pre_existing: true for a finding that is already present on ${baseRef} and not introduced by this change.`
  return call(prompt, { label, phase: 'Review', schema: REVIEW_SCHEMA, model: MODEL.review, effort: EFFORT.review })
}

// Run code-review; one retry when the skill did not run. Returns {res} or {notRun: reason}.
async function reviewWithRetry(label, level, target, rangeNote) {
  let res = await reviewAgent(label, level, target, rangeNote, '')
  if (res && res.skill_invoked === true) { takeDecisions('run', 'review', res); return { res } }
  const why = r => (r && typeof r.skill_error === 'string' && r.skill_error.trim()) || (r ? 'the agent did not report running the skill' : 'the review agent returned nothing')
  const first = why(res)
  res = await reviewAgent(`${label}:retry`, level, target, rangeNote,
    `The previous attempt did not run code-review. Its error: ${first}\nTry again. ${RULE_SKILL}\n`)
  if (res && res.skill_invoked === true) { takeDecisions('run', 'review', res); return { res } }
  return { notRun: why(res) }
}

function fixAgent(label, findingText, extra) {
  const w = newWt(`fix-${label}`, null, finalRef)
  const prompt = `${w.setup}${RULES}\n\n` +
    `Stage: fix. Run "git rev-parse HEAD" first and return it as base_sha. ${findingText}\n${runBoundaryText()}` +
    `Make one commit ("git add", then "git commit"), include a test that fails without the fix, run only the related tests (${testCmd}) and lint (${lintCmd}). ` +
    `Then land it: ${land(finalBranch)}. Return the commit sha as commit. ${extra || ''}` +
    `If the finding is wrong or cannot be fixed safely, change nothing and return fix_status skipped or failed with the reason in summary.`
  return call(prompt, { label, phase: 'Review', schema: FIX_SCHEMA, model: MODEL.fix, effort: EFFORT.fix })
}

async function stageReview(finalPr) {
  const stat = await call(
    `git -C ${repoDir} fetch ${remote}\ngit -C ${repoDir} diff --numstat ${baseRef}...${finalRef}\n\n${notCwd()}\nRun the two commands above. Return one entry per file (path, added, deleted). Do not edit anything.`,
    { label: 'diffstat', phase: 'Review', schema: DIFFSTAT_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
  const { level, lines, risky } = pickLevel((stat && stat.files) || [])
  log(`review level ${level} (${lines} changed lines${risky.length ? `, risky paths: ${risky.join(', ')}` : ''})`)
  const target = finalPr && finalPr.pr ? String(finalPr.pr) : finalBranch

  const out = { rounds: 0, fixed: [], notFixed: [], leftover: [], preExisting: [], level, status: 'ran', reason: '' }
  const skipped = (reason, what) => {
    addDecision('run', 'review', { title: `Review skipped: code-review did not run (${reason})`, context: `The review stage must invoke the code-review skill; it did not run${what ? ` for ${what}` : ''}.`,
      decision: 'Continue the pipeline without that review and say so in the PR body.', why: 'A review that did not run must not read as a pass; the owner decides.',
      consequences: 'The change was not reviewed by code-review.', how_to_reverse: 'Run /code-review on the PR.', needs_review: true, confidence: 'high' })
  }
  const first = await reviewWithRetry('review:r0', level, target, '')
  if (first.notRun) {
    out.status = 'not run'; out.reason = first.notRun
    skipped(first.notRun, '')
    log(`review: NOT RUN (${first.notRun})`)
    return out
  }
  let review = first.res
  const note = r => {
    for (const f of (r && r.findings) || []) if (f.pre_existing && !out.preExisting.some(p => p.id === f.id)) out.preExisting.push(f)
  }
  note(review)
  let findings = ((review && review.findings) || []).filter(f => !f.pre_existing)

  while (out.rounds < MAX_FIX_ROUNDS) {
    const todo = findings.filter(f => f.score >= FIX_THRESHOLD)
    if (!todo.length) break
    out.rounds++
    const commits = []
    for (let k = 0; k < todo.length; k++) {   // sequential: each fix lands before the next starts
      const f = todo[k]
      const res = await fixAgent(`fix:r${out.rounds}:${k + 1}`, `Finding ${f.id} (score ${f.score}) in ${f.path || 'the diff'}${f.line ? `:${f.line}` : ''}: ${f.summary}`)
      takeDecisions('run', 'review-fix', res)
      if (res && res.fix_status === 'fixed' && res.commit) { commits.push(res); out.fixed.push({ id: f.id, summary: f.summary, commit: res.commit }) }
      else {
        const bd = res && res.fix_status === 'skipped' && (res.decisions || []).find(d => d && typeof d.title === 'string' && (d.title.startsWith(BOUNDARY_PREFIX) || d.needs_review === true || d.contradicts_confirmed || d.dangerous))
        const reason = bd ? `needs your decision: ${bd.title}` : (res && res.summary) || 'fix agent returned nothing'
        out.notFixed.push({ id: f.id, summary: f.summary, reason })
      }
    }
    if (!commits.length) { findings = []; break }
    // Re-review only what the fix commits changed.
    const range = `${commits[0].base_sha}..${commits[commits.length - 1].commit}`
    const again = await reviewWithRetry(`review:r${out.rounds}`, level, range,
      `This is a re-review of the fix commits only, range ${range}. Review that diff and nothing else; ignore the rest of the branch.\n`)
    if (again.notRun) {
      out.reReviewNotRun = again.notRun
      skipped(again.notRun, `the fix commits ${range}`)
      log(`review: re-review of ${range} NOT RUN (${again.notRun})`)
      findings = []
      break
    }
    review = again.res
    note(review)
    findings = ((review && review.findings) || []).filter(f => !f.pre_existing)
  }
  if (findings.some(f => f.score >= FIX_THRESHOLD)) log(`review: findings at or above ${FIX_THRESHOLD} remain after ${MAX_FIX_ROUNDS} fix rounds; listed in the PR body`)
  out.leftover = findings
  return out
}

async function requestText(done) {
  const parts = await parallel(done.map(r => () => {
    const t = tickets.find(x => x.n === r.n)
    if (LOCAL) return Promise.resolve({ body: t.body || t.title })
    return call(`Run: gh issue view ${t.n} --repo ${repo} --json body -q .body\nReturn its output unchanged in body. Do not summarise or edit it.`,
      { label: `request:${t.n}`, phase: 'Intent review', schema: REQUEST_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
  }))
  return done.map((r, i) => {
    const t = tickets.find(x => x.n === r.n)
    return `### #${t.n} ${t.title}\n${(parts[i] && parts[i].body) || t.title}`
  }).join('\n\n')
}

async function stageIntentReview(done) {
  const request = await requestText(done)
  // Plan-blind on purpose: the request, the owner's own confirmed decisions (owner words, not agent plan) and the range. No plan, design, ADR or summary.
  const owner = done.map(r => tickets.find(x => x.n === r.n)).filter(t => t && t.confirmed && t.confirmed.trim())
    .map(t => `### #${t.n}\n${t.confirmed.trim()}`).join('\n\n')
  const ownerBlock = owner ? `Owner-confirmed decisions (the owner's own words; a change they name is NOT a gap, drift or excess):\n<<<\n${owner}\n>>>\n\n` : ''
  const w = newWt('intent-review', null, finalRef)
  const role = `${pluginDir}/agents/intent-reviewer.md`
  const prompt = `${w.setup}Role: read ${role} and act as that role. If it does not exist, use this role: ` +
    `compare the diff with the owner's request and report only gaps (requested but missing), drift (does something other than requested) and excess (unrequested behaviour).\n\n` +
    `Owner's original request, verbatim:\n<<<\n${request}\n>>>\n\n${ownerBlock}Diff range: ${baseRef}..${finalRef}\n\n` +
    `Read the diff with: git -C ${w.dir} diff ${baseRef}..${finalRef}. Read-only: edit nothing. ` +
    `Report only findings of kind gap, drift or excess. Do not report anything else: nothing about tests, about whether tests pass, or about your role file. If there is nothing to report, return no findings.`
  const res = await call(prompt, { label: 'intent-review', phase: 'Intent review', schema: INTENT_REVIEW_SCHEMA, effort: EFFORT.review, agentType: 'harness:intent-reviewer' }, role)
  const findings = (res && res.findings) || []
  const fixable = findings.filter(f => f.kind === 'gap' || (f.kind === 'drift' && f.behaviour_changing))
  if (fixable.length) {
    const text = fixable.map((f, i) => `${i + 1}. [${f.kind}] ${f.clause}: ${f.detail}`).join('\n')
    const fix = await fixAgent('intent-fix', `The intent review found these gaps against the owner's request:\n${text}\nFix each one, one commit per finding.` +
      (owner ? `\nOwner-confirmed decisions (never revert or undo a change they name; skip any finding that conflicts with them and return it as a decision with needs_review: true instead):\n${owner}\n` : ''),
      'Return base_sha and the last commit sha. ')
    takeDecisions('run', 'intent-fix', fix)
  }
  return { verdict: res ? res.verdict : 'unknown', gaps: findings, fixRound: fixable.length > 0 }
}

async function stageSuite() {
  const prompt = (label, cmd, only) => `${newWt(`suite-${label}`, null, finalRef).setup}${RULES}\n\n` +
    `Stage: verify. ${only ? `Re-run ONLY these failing tests: ${only.join(', ')} (use the narrowest command the project supports; ${testCmd} is the related-tests template).` : `Run the full suite: ${cmd}`}\n` +
    `Start the command in the background with its output going to a file, then poll that file until the process has exited. Never edit code or tests. ` +
    `Return the real counts of passed, failed and skipped tests from the output, the names of failing tests as failing, the exit code, and the last lines of output as tail.`
  const first = await call(prompt('run', fullTestCmd, null), { label: 'suite', phase: 'Testing', schema: SUITE_SCHEMA, model: MODEL.test, effort: EFFORT.test })
  if (!first) return { passed: 0, failed: 0, skipped: 0, note: 'the suite agent returned nothing' }
  if (!first.failed) return { passed: first.passed, failed: 0, skipped: first.skipped }
  const fix = await call(`${newWt('fix-suite', null, finalRef).setup}${RULES}\n\nStage: fix the failing tests of the final suite run, with minimal commits ("git add", then "git commit"). Failing: ${first.failing.join(', ')}\nOutput tail:\n${first.tail || ''}\n` +
    `Fix the code, not the test, unless the test itself is wrong. Run only the failing tests. Then land it: ${land(finalBranch)}`,
    { label: 'suite-fix', phase: 'Testing', schema: stageSchema({}), model: MODEL.fix, effort: EFFORT.fix })
  takeDecisions('run', 'suite-fix', fix)
  const again = await call(prompt('rerun', fullTestCmd, first.failing), { label: 'suite-rerun', phase: 'Testing', schema: SUITE_SCHEMA, model: MODEL.test, effort: EFFORT.test })
  if (!again) return { passed: first.passed, failed: first.failed, skipped: first.skipped, note: 'the re-run agent returned nothing' }
  return { passed: first.passed + again.passed, failed: again.failed, skipped: first.skipped + again.skipped, note: `${first.failed} failed first; re-ran only those` }
}

async function stageArtifact(results) {
  // Local mode publishes nothing outside the machine: no push, no PR, no artifact.
  if (LOCAL) return { fallback: 'docs/adr/' }
  const prompt = `${RULES}\n\nStage: build ONE private artifact for this run. If the 'ink-artifact' skill and the Artifact tool both exist, use the skill to build it: one section per ticket, decisions with needs_review: true first. Keep it private.\n` +
    `If either is missing, build nothing, return created: false and fallback: 'docs/adr/' (the ADR files are the source of truth).\n` +
    `Tickets: ${JSON.stringify(results.map(r => ({ n: r.n, status: r.status, summary: r.summary, reason: r.reason, url: r.url })))}\n` +
    `Decisions: ${JSON.stringify(decisions)}`
  const res = await call(prompt, { label: 'artifact', phase: 'Decisions', schema: ARTIFACT_SCHEMA, model: MODEL.adr, effort: EFFORT.adr })
  return res && res.created && res.url ? { url: res.url } : { fallback: (res && res.fallback) || 'docs/adr/' }
}

async function stageAdr(finalPr, artifact, bodyTemplate) {
  const input = JSON.stringify({ run: slug, decisions })
  const update = LOCAL
    ? `Local mode: save the final body as PR-BODY.md at the worktree root (do not commit it) and return its absolute path as body_file.`
    : `Update the pull request: gh pr edit ${finalPr.pr} --repo ${repo} --body-file .ship/pr-body.md`
  const w = newWt('adr', null, finalRef)
  const prompt = `${w.setup}${RULES}\n\n` +
    `Stage: write the ADRs and the final PR body. First cd ${w.dir}; every relative path below is relative to it. Do these in order:\n` +
    `1. mkdir -p .ship and save this JSON, exactly, to .ship/decisions.json (use a quoted heredoc). It holds ${decisions.length} decisions.\n${input}\n` +
    `2. Run "python3 ${pluginDir}/scripts/write_adrs.py --help" first. ${decisions.length ? `Then run it with --input .ship/decisions.json and save its stdout to .ship/written.json. Add --table-out .ship/decisions-table.md: it writes the Decisions table. The script merges duplicates and writes a file only for a decision that needs a human look, so it may write no file and print []. Exit 2 means bad input: fix the file and re-run.` : 'There are no decisions: save [] to .ship/written.json and skip the next step and write no table.'}\n` +
    `3. "git add docs/adr", then, as a separate command, "git commit" (message ends with ${CO_AUTHOR}); then land it: ${land(finalBranch)}\n` +
    `4. Render the section: python3 ${pluginDir}/scripts/write_adrs.py --render-section .ship/written.json${artifact.url ? ` --artifact ${artifact.url}` : ''}${artifact.url ? '' : `  (no artifact this run; link docs/adr/ in the section)`}\n` +
    `5. Write the body below to .ship/pr-body.md, replacing the line {{DECISIONS}} with the rendered section${decisions.length ? ', then a blank line, then the content of .ship/decisions-table.md unchanged' : ''}. ${update}\n` +
    `Return adrs from .ship/written.json (number, path, needs_review). Do not commit anything under .ship.\n\nBody:\n${bodyTemplate}`
  const res = await call(prompt, { label: 'adr', phase: 'Decisions', schema: ADR_SCHEMA, model: MODEL.adr, effort: EFFORT.adr })
  return res || { adrs: [], status: 'blocked', summary: 'the ADR agent returned nothing' }
}

// The script writes the PR body text; the ADR stage only substitutes {{DECISIONS}} and publishes it.
function buildBody(results, review, intent, suite) {
  const done = results.filter(r => r.status === 'done')
  const open = results.filter(r => r.status !== 'done')
  const L = []
  const excess = ((intent && intent.gaps) || []).filter(g => g.kind === 'excess' && g.behaviour_changing === true)
  const bounded = decisions.filter(d => d.boundary && d.needs_review)
  if (excess.length || bounded.length) {
    L.push('## Needs your decision', '')
    for (const g of excess) L.push(`- excess (behaviour-changing): ${g.clause}: ${g.detail}`)
    for (const d of bounded) L.push(`- ${d.title}: ${d.decision}`)
    L.push('')
  }
  L.push('## Summary', '')
  const ref = n => (LOCAL ? `Ticket ${n}` : `#${n}`)   // in local mode the ticket is not a real issue
  for (const r of results) L.push(`- ${ref(r.n)} ${r.status}${r.summary ? `: ${capSummary(r.summary)}` : ''}${r.reason ? ` (${r.reason})` : ''}`)
  L.push('')
  if (LOCAL) { for (const r of results) L.push(`Ticket ${r.n}`) }
  else { for (const r of done) L.push(`Closes #${r.n}`); for (const r of open) L.push(`Refs #${r.n}`) }
  L.push('', '## Review', '')
  if (review.status === 'not run') L.push(`Review: NOT RUN (${review.reason})`)
  else L.push(`Level ${review.level}; ${review.rounds} fix round(s); ${review.fixed.length} fixed.`)
  if (review.reReviewNotRun) L.push(`Re-review of the fix commits: NOT RUN (${review.reReviewNotRun})`)
  for (const f of review.notFixed) L.push(`- not fixed: ${f.summary} (${f.reason})`)
  for (const f of review.leftover) L.push(`- left: [${f.score}] ${f.summary}`)
  for (const f of review.preExisting) L.push(`- already on ${base}, not fixed: ${f.summary}`)
  L.push('', '## Intent review', '', `Verdict: ${intent.verdict}${intent.fixRound ? ' (one fix round ran, not re-reviewed)' : ''}`)
  for (const g of intent.gaps) L.push(`- ${g.kind}${g.behaviour_changing ? ' (behaviour-changing)' : ''}: ${g.clause}: ${g.detail}`)
  L.push('', '## Final verification', '', `Passed ${suite.passed}, failed ${suite.failed}, skipped ${suite.skipped}.${suite.note ? ` ${suite.note}.` : ''}`)
  L.push('', '{{DECISIONS}}', '', PR_FOOTER)
  return L.join('\n')
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
const results = []   // one entry per ticket, in input order after the run
const byN = new Map()
const groups = [...new Set(tickets.map(t => t.group))].sort((a, b) => a - b)
const ordered = () => tickets.map(t => byN.get(t.n))

phase('Setup')
// The role files come from the plugin directory. call() falls back silently to the default agent
// when an agent type is missing, which would hide a wrong pluginDir, so check it once, up front.
const pluginCheck = await call(`Run: test -f ${pluginDir}/agents/implementer.md && test -f ${pluginDir}/scripts/write_adrs.py && echo found || echo missing\n\n${notCwd()}\nReturn status ok when the output is found, otherwise status blocked with blocked_reason "pluginDir ${pluginDir} does not hold the harness plugin". Edit nothing.`,
  { label: 'plugin-check', phase: 'Setup', schema: SETUP_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
if (!pluginCheck || pluginCheck.status === 'blocked') throw new Error(`ship: ${(pluginCheck && (pluginCheck.blocked_reason || pluginCheck.summary)) || 'the plugin check returned nothing'}`)
log(`ship: ${tickets.length} ticket(s) in ${groups.length} group(s), ${single ? 'single: the ticket PR is the final PR' : `integration branch ${integBranch}`}${LOCAL ? ', local mode' : ''}`)
if (!single) {
  const setup = await stageSetupIntegration()
  takeDecisions('run', 'setup', setup)
  if (!setup || setup.status === 'blocked') throw new Error(`ship: could not create ${integBranch}: ${(setup && (setup.blocked_reason || setup.summary)) || 'no answer'}`)
}

for (const g of groups) {
  phase('Tickets')
  const inGroup = tickets.filter(t => t.group === g)
  const runnable = []
  for (const t of inGroup) {
    const blockedDep = (t.deps || []).map(d => byN.get(d)).find(r => r && r.status !== 'done')
    if (blockedDep) {
      const reason = `dependency #${blockedDep.n} is ${blockedDep.status}`
      byN.set(t.n, { n: t.n, status: 'skipped', pr: null, url: '', branch: ticketBranch(t), summary: '', reason })
      log(`#${t.n} skipped: ${reason}`)
    } else runnable.push(t)
  }
  log(`group ${g}: running ${runnable.map(t => `#${t.n}`).join(', ') || 'nothing'}`)
  const ran = await parallel(runnable.map(t => () => runTicket(t)))
  runnable.forEach((t, i) => byN.set(t.n, ran[i] || { n: t.n, status: 'blocked', pr: null, url: '', branch: ticketBranch(t), summary: '', reason: 'the ticket pipeline threw or was skipped' }))

  const done = runnable.map(t => byN.get(t.n)).filter(r => r.status === 'done')
  if (!single && done.length) {
    phase('Merge')
    const m = await stageMerge(g, done)
    const failed = (m && m.failed) || []
    for (const f of failed) {
      const r = byN.get(f.n)
      if (r) { r.status = 'blocked'; r.reason = `merge into ${integBranch} failed: ${f.reason}` }
      log(`#${f.n} blocked at merge: ${f.reason}`)
    }
    if (!m) for (const r of done) { r.status = 'blocked'; r.reason = 'the merge agent returned nothing' }
  }
}

const deliveredAll = ordered().filter(r => r.status === 'done')
const out = {
  single, final: null, tickets: [], review: { status: 'not run', rounds: 0, fixed: [], notFixed: [], leftover: [] }, worktrees: [],
  intent: { verdict: 'not run', gaps: [] }, suite: { passed: 0, failed: 0, skipped: 0 }, adrs: [], artifact: { fallback: 'docs/adr/' }, decisions,
}
const publicTicket = r => ({ n: r.n, status: r.status, pr: r.pr, summary: r.summary, reason: r.reason })

if (!deliveredAll.length) {
  log('ship: no ticket was delivered; nothing to review, verify or record')
  out.tickets = ordered().map(publicTicket)
  out.worktrees = [...worktrees]
  return out
}

// The final PR must exist before the review, because code-review takes a PR number.
let finalPr
if (single) {
  const r = deliveredAll[0]
  finalPr = { pr: r.pr || 0, url: r.url, branch: finalBranch }
} else {
  phase('Review')
  const prelim = await stageFinalPr(deliveredAll, buildBody(ordered(), { level: 'pending', rounds: 0, fixed: [], notFixed: [], leftover: [], preExisting: [] }, { verdict: 'pending', gaps: [] }, { passed: 0, failed: 0, skipped: 0 }))
  takeDecisions('run', 'final-pr', prelim)
  finalPr = { pr: (prelim && prelim.pr) || 0, url: (prelim && prelim.url) || '', branch: finalBranch }
}
out.final = { pr: finalPr.pr || null, url: finalPr.url, branch: finalBranch }

phase('Review')
const review = await stageReview(finalPr)
out.review = { status: review.status, reason: review.reason, rounds: review.rounds, fixed: review.fixed, notFixed: review.notFixed, leftover: review.leftover, preExisting: review.preExisting }
log(`review: ${review.rounds} fix round(s), ${review.fixed.length} fixed, ${review.notFixed.length} not fixed, ${review.leftover.length} left`)

phase('Intent review')
const intent = await stageIntentReview(deliveredAll)
out.intent = { verdict: intent.verdict, gaps: intent.gaps }
log(`intent review: ${intent.verdict}, ${intent.gaps.length} finding(s)${intent.fixRound ? ', one fix round ran' : ''}`)

phase('Testing')
const suite = await stageSuite()
out.suite = suite
log(`full suite: ${suite.passed} passed, ${suite.failed} failed, ${suite.skipped} skipped`)

phase('Decisions')
const artifact = await stageArtifact(ordered())
out.artifact = artifact
const adr = await stageAdr(finalPr, artifact, buildBody(ordered(), review, intent, suite))
takeDecisions('run', 'adr', adr)
out.adrs = (adr.adrs || []).map(a => ({ number: a.number, path: a.path, needsReview: !!a.needs_review }))
log(`decisions: ${decisions.length} recorded, ${out.adrs.length} ADR file(s)`)

out.tickets = ordered().map(publicTicket)
out.worktrees = [...worktrees]
log(`worktrees created (the script never removes them; remove with git -C ${repoDir} worktree remove <dir>):\n${out.worktrees.join('\n')}`)
return out
