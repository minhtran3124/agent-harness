export const meta = {
  name: 'autopilot-run',
  description: 'Ship tickets to one PR: build, verify, review, test, ADRs',
  phases: [
    { title: 'Setup', detail: 'validate args, create the integration branch (multi-ticket only)' },
    { title: 'Tickets', detail: 'intent, plan, implement, verify, finish per ticket; groups in order, tickets of a group in parallel' },
    { title: 'Merge', detail: 'merge a finished group into the integration branch (multi-ticket only)' },
    { title: 'Review', detail: 'code-review the final PR, fix findings, re-review only the fix commits' },
    { title: 'Intent review', detail: 'plan-blind check of the final diff against the original request' },
    { title: 'UAT', detail: 'plan-blind acceptance test of the running app against the original request (FE, BE, FE+BE)' },
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
// Depth L is the difficulty signal: design and plan run on Opus there; every other stage and depth uses MODEL.
function stageModel(stage, depth) {
  return depth === 'L' && (stage === 'design' || stage === 'plan') ? 'opus' : MODEL[stage]
}
const FIX_THRESHOLD = 50   // a review finding scoring at or above this gets one fix agent
const MAX_FIX_ROUNDS = 2   // hard cap on fix rounds in the review loop
const CI_WAIT_MS = 600000  // the ticket gate waits at most this long for CI (one Bash call)
const CI_INTERVAL = 30     // seconds between gh pr checks polls
// Paths whose change makes the review level 'high'.
const RISKY_PATH = /(^|\/)(hooks|migrations?|auth|security|secrets?|\.github\/workflows)(\/|$)|settings\.json$|\.sql$|\.env/i
const LARGE_DIFF_LINES = 800, SMALL_DIFF_LINES = 150, LARGE_DIFF_FILES = 25
// The one wording of the ADR gate, used by the stage rules and the decision schema.
const NEEDS_REVIEW_WHEN = 'affects another ticket, a public contract or interface, stored data, security or cost, or is a trade-off that is costly to reverse, or contradicts the ticket text or an owner-confirmed answer'
const CO_AUTHOR = 'Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>'
const PR_FOOTER = '🤖 Generated with [Claude Code](https://claude.com/claude-code)'

const rulesCommon = repoDir => `Rules (all of them apply):
- No human is in the loop. Never ask anyone anything. On any ambiguity pick the recommended option and return it as a decision in decisions[].
- Never merge into the base branch or main. Never force-push. Never touch secrets. Never weaken a test to make it pass.
- Project rules: before your first edit, read the project's own rules and follow them. The target repo does not auto-load them for you. Read ${repoDir}/CLAUDE.md, ${repoDir}/CLAUDE.local.md if it exists, and every ${repoDir}/.claude/rules/*.md (honor a rule file's paths: scoping against the files you touch). Once you have your own worktree, read the tracked ones (CLAUDE.md, .claude/rules/*.md) from it, at the same relative path; before that, read them from ${repoDir}. Your worktree holds only committed content, so also run git -C ${repoDir} status --porcelain -- CLAUDE.md .claude/rules/; for any file it lists (uncommitted edit, for example just written by setup), read that file from ${repoDir} instead. CLAUDE.local.md is untracked, so read ${repoDir}/CLAUDE.local.md (if present). The hard rules above (never merge into the base branch or main, never force-push, never touch secrets, never weaken a test) cannot be overridden by project rules.
- Work only in your own worktree and on your own branch. Never edit files in the owner's checkout.
- Your session working directory is NOT the target repo. Use absolute paths; run every git command as git -C <path> or after cd <your worktree>.
- needs_review: true ONLY when the decision ${NEEDS_REVIEW_WHEN}. needs_review is the only thing that makes an ADR file, so be strict. A reversible choice inside the ticket (naming, how to handle an edge case the ticket leaves open, which implementation to use) is needs_review: false, even when you are unsure (set confidence low then). It is still recorded as a decision.
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
    needs_review: { type: 'boolean', description: `true ONLY when the decision ${NEEDS_REVIEW_WHEN}. This alone makes an ADR file. A reversible choice inside the ticket (naming, an edge case the ticket leaves open, which implementation) is false, even at low confidence.` },
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
const STEP = { type: 'object', properties: { title: STR, files: strList, done_when: STR,
  covers: { type: 'array', items: STR, description: 'the acceptance criteria this step proves, as AC1, AC2 (the order of acceptance[])' } }, required: ['title', 'done_when'] }
const INTENT_SCHEMA = stageSchema({ goal: STR, acceptance: strList, files: strList, out_of_scope: strList, plan_steps: { type: 'array', items: STEP },
  approach: { type: 'string', description: 'Two to four sentences: the approach you chose and any option you rejected. It becomes design.md for depth S and M.' } }, ['goal'])
const RESEARCH_SCHEMA = stageSchema({ research_md: STR }, ['research_md'])
const DESIGN_SCHEMA = stageSchema({ design_md: STR }, ['design_md'])
const PLAN_SCHEMA = stageSchema({ plan_md: STR, plan_steps: { type: 'array', items: STEP } }, ['plan_md'])
const IMPLEMENT_SCHEMA = stageSchema({
  worktree: STR, branch: STR, files: strList,
  commits: { type: 'array', items: { type: 'object', properties: { sha: STR, subject: STR }, required: ['sha', 'subject'] } },
  verify: { type: 'array', items: { type: 'object', properties: { command: STR, exit: NUM, notes: STR, covers: strList }, required: ['command', 'exit'] } },
}, ['worktree', 'branch'])
// The verify skill reports prose; this schema gives ship.js the facts it decides on. Not IMPLEMENT_SCHEMA.verify.
const VERIFY_SCHEMA = stageSchema({
  passed: { type: 'boolean', description: 'true only when every step and command of the Verify: row passed and the browser console had no errors' },
  kind: { type: 'string', enum: ['BE', 'FE', 'FE+BE', 'docs'], description: 'the ticket type from the Verify: row' },
  configPath: { type: 'string', description: 'absolute path of the verify.config.json you used, or empty when the Verify: row used none' },
  failedStep: STR, consoleErrors: strList, stills: { type: 'array', items: STR, description: 'absolute local paths of the screenshots' }, report: STR,
}, ['passed', 'kind'])
// UAT: status blocked means the run did not happen (no config, app will not start, no credentials); it is never an AC failure.
const UAT_SCHEMA = stageSchema({
  passed_ac: { type: 'boolean', description: 'true only when every browser-checkable AC scenario passed' },
  scenarios: { type: 'array', items: { type: 'object',
    properties: { id: STR, covers: STR, kind: { type: 'string', enum: ['ac', 'negative', 'extra', 'not-browser-checkable'] },
      status: { type: 'string', enum: ['PASS', 'FAIL', 'SKIPPED'] }, assertion: STR, still: STR },
    required: ['id', 'covers', 'kind', 'status'] } },
  non_ac_failures: { type: 'array', items: { type: 'object', properties: { id: STR, detail: STR }, required: ['id', 'detail'] } },
  console_errors: NUM,
}, ['passed_ac', 'scenarios'])
const GIF_SCHEMA = stageSchema({ gif: { type: 'string', description: 'absolute path of the GIF, or empty when none was built' } }, ['gif'])
const FINISH_SCHEMA = stageSchema({ pr: NUM, url: STR, body_file: STR }, ['pr'])
const SETUP_SCHEMA = stageSchema({})
const JOURNAL_SCHEMA = stageSchema({ lines: { type: 'number', description: 'how many lines of the journal file parsed as JSON' } }, [])
const MERGE_SCHEMA = stageSchema({
  merged: { type: 'array', items: NUM },
  failed: { type: 'array', items: { type: 'object', properties: { n: NUM, reason: STR }, required: ['n', 'reason'] } },
}, ['merged', 'failed'])
const FINAL_PR_SCHEMA = stageSchema({ pr: NUM, url: STR }, ['pr'])
// CI: the agent only reports the checks; the script judges them. bucket is the gh pr checks bucket (pass, fail, pending, skipping, cancel).
const CI_SCHEMA = { type: 'object',
  properties: { checks: { type: 'array', items: { type: 'object', properties: { name: STR, bucket: STR }, required: ['name', 'bucket'] } }, headRefOid: STR, branchTip: STR, note: STR },
  required: ['checks'] }
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
    properties: { number: NUM, path: STR, needs_review: BOOL, ticket: STR, title: STR }, required: ['number', 'path', 'needs_review'] } },
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
const RULES = `${rulesCommon(repoDir)}\n- Harness files (skills/, agents/, scripts/) live in the plugin directory ${pluginDir}. Read them there by absolute path.`
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
// Agent label shown in the agents panel: what the agent does, then what it works on, cut to fit the pane.
const lbl = (what, subject) => {
  const sub = String(subject == null ? '' : subject).replace(/\s+/g, ' ').trim()
  const chars = Array.from(sub)   // cut on code points so an emoji is never split
  return sub ? `${what} · ${chars.length > 40 ? `${chars.slice(0, 39).join('')}…` : sub}` : what
}
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
function runBoundaryText(only) {
  const ns = only ? [String(only)].filter(n => boundaries[n]) : Object.keys(boundaries)
  if (!ns.length) return ''
  const body = ns.map(n => `Ticket #${n}\n` + boundaryText('', boundaries[n]).replace(`\n${BOUNDARY_RULE}\n`, '').trim()).join('\n\n')
  return `Boundary (${only ? `ticket #${only}` : 'union over the tickets in this run'}):\n${body}\n` +
    `The file set limits production, test and doc files alike: a test or doc file is in bounds only when the list above names it. ` +
    `A fix that would touch a file outside this set, or contradict an Out of scope line, changes nothing: return fix_status skipped and a decisions[] entry whose title starts with '${BOUNDARY_PREFIX}' and needs_review true.\n`
}

const capSummary = v => { const x = (typeof v === 'string' ? v : '').replace(/\s+/g, ' ').trim(); return x.length > 200 ? `${x.slice(0, 199)}…` : x }

class Blocked extends Error {}

// Run journal: one JSONL file per run. The Workflow sandbox has no fs, process, require, import() or performance
// (measured in the real runtime, #529), so the script cannot write the file itself. It keeps the rows in memory,
// returns them as out.journal, and one cheap agent writes the file at the end (as it does for specs/). A stage that
// never finishes (a crash of the script) leaves no file; the in-memory rows still go out with the result.
// The id becomes part of a file name: keep a safe charset and no leading dot, so it cannot leave the journal dir.
const shortId = v => (v.length > 80 ? `${v.slice(0, 40)}-${v.slice(-39)}` : v)   // keep the tail: it holds the unique time suffix
const safeId = v => shortId(String(v).trim().replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^[.-]+/, ''))
const runIdArg = typeof args.runId === 'string' ? safeId(args.runId) : ''
// The slug is not unique: a missing runId would let a second launch replace the first journal, so it is logged.
const runId = runIdArg || slugOf(slug) || 'run'
if (!runIdArg) log(`journal: args.runId is missing or empty, using "${runId}"; a second run with the same name gets a numbered file name (journal-${runId}-2.jsonl), so look for the newest one`)
// Outside the target repo, next to the worktrees, so git status of the owner's checkout stays clean.
const journalDir = `${parentDir}/.ship-${trimmed.split('/').pop()}/journals`
const journalFile = `${journalDir}/journal-${runId}.jsonl`
const journalRows = []
let journalFlushed = false
let clockLogged = false
// null means "no clock": the real sandbox has no performance, and 0 would read as a real 0 ms.
const nowMs = () => { try { return typeof performance !== 'undefined' && performance && typeof performance.now === 'function' ? performance.now() : null } catch (e) { return null } }
function durationSince(t0) {
  const t1 = nowMs()
  if (t0 === null || t1 === null) {
    if (!clockLogged) { clockLogged = true; log('journal: no clock available, duration_ms is null') }
    return null
  }
  return Math.round(t1 - t0)
}
// There is no clock, so the second cost measure is the output tokens spent (budget.spent() is shared by the whole
// turn, so for stages that overlap in a parallel group it is an upper bound, not an exact figure). null without budget.
const tokensNow = () => { try { const v = typeof budget !== 'undefined' && budget && typeof budget.spent === 'function' ? budget.spent() : null; return Number.isFinite(v) ? v : null } catch (e) { return null } }
const tokensSince = k0 => { const k1 = tokensNow(); return Number.isFinite(k0) && Number.isFinite(k1) ? Math.max(0, Math.round(k1 - k0)) : null }
// What a stage result says about itself. A result that did not throw is not automatically ok.
function statusOf(res) {
  if (res === null || res === undefined) return 'failed'
  if (typeof res !== 'object') return 'ok'
  if (res.status === 'blocked' || res.status === 'not run') return 'blocked'
  if (res.passed === false || res.passed_ac === false) return 'failed'
  if (typeof res.failed === 'number' && res.failed > 0) return 'failed'
  if (Array.isArray(res.failed) && res.failed.length) return 'failed'
  return 'ok'
}
const appendJournal = entry => { journalRows.push({ kind: 'stage', ...entry }) }

// When no agent can write the file (budget spent, abort, refused write), the rows still reach the run log, one line each.
function dumpJournal(why) {
  log(`journal: ${why}`)
  for (const r of journalRows) log(`journal row: ${JSON.stringify(r)}`)
}

// Writes the collected rows to journalFile with one cheap agent. Fail open: a failure is logged and changes nothing.
// The text goes in a quoted heredoc (as writeSpecFiles does) and the agent must report how many lines of the file parse as JSON, which is
// compared with the number of rows: a refused, truncated or altered write is logged, not silent.
async function flushJournal() {
  if (!journalRows.length || journalFlushed) return
  journalFlushed = true
  try {
    const text = journalRows.map(r => JSON.stringify(r)).join('\n') + '\n'
    const res = await call(`Stage: write the run journal. ${notCwd()}\n` +
      `1. Run: mkdir -p ${journalDir}\n` +
      `2. Write the text between the markers below, exactly and with no change, to ${journalFile} (create the file; ${runIdArg ? 'replace it if it exists' : `if it exists, do not replace it: use the first free name journal-${runId}-2.jsonl, -3.jsonl and so on, and say which in summary`}). Use a Bash heredoc with a quoted delimiter (cat > FILE <<'JOURNAL_EOF'), not the file-write tool, which can be refused. Do not include the marker lines.\n` +
      `3. Run: python3 -c "import json,sys; print(sum(1 for l in open(sys.argv[1]) if json.loads(l)))" <the file you wrote in step 2>   and return that number as lines. If the write or the parse failed, return status blocked with blocked_reason.\n` +
      `Edit nothing else.\n\n<<<JOURNAL\n${text}JOURNAL>>>`,
      { label: 'write run journal', phase: 'Decisions', schema: JOURNAL_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
    if (!res || res.status === 'blocked') { dumpJournal(`not written, ${(res && (res.blocked_reason || res.summary)) || 'the writer returned nothing'}`); return }
    if (typeof res.lines === 'number' && res.lines !== journalRows.length) log(`journal: written, but ${res.lines} lines parse and there are ${journalRows.length} rows; check ${journalFile}`)
  } catch (e) { dumpJournal(`not written, ${e && e.message ? e.message : e}`) }
}

async function askAdvisor(t, stage, question, state) {
  const prompt = `${RULES}\n\nTicket #${t.n}: ${t.title} (depth ${t.depth}), stage ${stage}.\n` +
    `${notCwd()}\nQuestion: ${question || '(the stage gave no question; review its work)'}\n` +
    `Stage summary: ${state || '(none)'}\n` +
    `Answer with: Recommendation, Reasons, Risks, Confidence. Read only what the question needs. Do not edit anything.`
  const advice = await call(prompt,
    { label: lbl(`#${t.n} advisor ${stage}`, t.title), phase: 'Tickets', model: advisorModel, effort: EFFORT.advisor, agentType: 'harness:advisor' },
    `${pluginDir}/agents/advisor.md`)
  return typeof advice === 'string' ? advice : ''
}

// Times fn and writes one journal line for it, whatever the outcome. ticket is a number or 'run'.
// The status comes from the result, not from the absence of a throw: judge(res) is the stage's own verdict
// (the same function the pipeline uses), statusOf is the fallback.
async function journaled(ticket, stage, model, fn, j = { retries: 0 }, judge = statusOf) {
  const t0 = nowMs()
  const k0 = tokensNow()
  let status = 'failed'
  try {
    const res = await fn(j)
    try { status = judge(res) } catch (e) { status = statusOf(res) }   // a judge that throws never changes the stage outcome
    return res
  } catch (e) {
    status = e instanceof Blocked ? 'blocked' : 'failed'
    throw e
  } finally {
    appendJournal({ ticket, stage, model, status, retries: j.retries, duration_ms: durationSince(t0), output_tokens: tokensSince(k0) })
  }
}

// One ticket stage: run it; on needs_advisor ask once and re-run once; collect decisions; stop on a block.
function runStage(t, stage, build, schema, { judge, ...opts }) {
  return journaled(t.n, stage, opts.model, j => runStageInner(t, stage, build, schema, opts, j), undefined, judge)
}

async function runStageInner(t, stage, build, schema, opts, j) {
  const { roleFile, ...rest } = opts
  const o = { ...rest, schema, phase: 'Tickets' }
  let res = await call(build(''), { ...o, label: lbl(`#${t.n} ${stage}`, t.title) }, roleFile)
  if (res && res.needs_advisor) {
    j.retries = 1
    const advice = await askAdvisor(t, stage, res.advisor_question, res.summary)
    res = await call(build(`\n\n## Advisor advice (follow it unless it is wrong; record any deviation as a decision)\n${advice}`),
      { ...o, label: lbl(`#${t.n} ${stage} retry`, t.title) }, roleFile)
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
    `and return plan_steps (title, files, covers, done_when) as the plan and approach (the chosen approach in two to four sentences). Copy the ticket's Out of scope lines verbatim into out_of_scope (an empty list when it has none).${t.depth === 'S' ? ' This is the plan for the implement stage.' : ' A later stage writes the full plan.'} ` +
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
    `Stage: design. Return the design as a decision with stage 'design' in decisions[] (a design ADR) and its text as design_md, in the shape of ${pluginDir}/templates/specs/design.md. Write no file.\n` +
    `Intent: ${JSON.stringify(intent)}\nResearch brief:\n${research.research_md}${advice}`, w.dir)
  return runStage(t, 'design', build, DESIGN_SCHEMA, { model: stageModel('design', t.depth), effort: EFFORT.design })
}

function stagePlan(t, intent, extra) {
  const w = newWt(`plan-${t.n}`, null, integRef)
  const build = advice => w.setup + head(t, 'writing-plans',
    `Stage: plan. Write no file; return the full plan text as plan_md, in the shape of ${pluginDir}/templates/specs/plan.md, plus plan_steps (the script saves it as specs/<slug>/plan.md).\n` +
    `Intent: ${JSON.stringify(intent)}\n${extra || ''}${advice}`, w.dir)
  return runStage(t, 'plan', build, PLAN_SCHEMA, { model: stageModel('plan', t.depth), effort: EFFORT.plan })
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
    `Do not fix code, retry, or judge flakiness. Keep the evidence local and uncommitted. Return passed (true only if every step passed and the console had no errors), kind, configPath (the absolute path of the verify.config.json you used, empty when none), failedStep, consoleErrors, stills (absolute paths) and report (the table).${advice}`, dir)
  // verify-base is meant to fail: the test must fail on the base commit. A pass there is the bad outcome.
  const judge = base ? res => (res && !res.passed ? 'ok' : 'failed') : undefined
  return runStage(t, mode, build, VERIFY_SCHEMA, { model: MODEL.verify, effort: EFFORT.verify, judge })
}

// A failed comment must not change the outcome: it is only logged.
async function commentVerify(t, text) {
  if (LOCAL) return
  try {
    await call(`Run: gh issue comment ${t.n} --repo ${repo} --body "<the text below, as one quoted argument>"\n\n${RULES}\n\nText:\n${text}\nPost the comment and return status ok. Edit nothing else.`,
      { label: lbl(`#${t.n} post verify comment`, t.title), phase: 'Tickets', schema: SETUP_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
  } catch (e) { log(`#${t.n} verify comment failed: ${e && e.message}`) }
}

const verifyFacts = r => `failing step: ${r.failedStep || 'unknown'}; console errors: ${(r.consoleErrors || []).join(' | ') || 'none'}\n${r.report || ''}`

// Head run, one retry, then the base check (FE and FE+BE only). Local mode skips the stage.
async function verifyTicket(t, impl) {
  if (LOCAL) return null
  const dir = `${impl.worktree}/.playwright-mcp/${t.n}`
  const blocked = (msg, r, base) => Object.assign(new Blocked(msg), { verify: { result: 'fail', kind: r.kind, base, stills: r.stills || [], dir, gif: null, report: r.report || '' } })
  let r = await stageVerify(t, impl, 'verify')
  let result = 'pass'
  if (!r.passed) {
    r = await stageVerify(t, impl, 'verify-retry')
    if (!r.passed) {
      const msg = `verify failed twice (${verifyFacts(r)})`
      await commentVerify(t, `Verify failed twice for #${t.n}: ${verifyFacts(r)}`)
      throw blocked(msg, r, 'not run')
    }
    result = 'flaky'
  }
  let baseResult = 'not run'
  if (r.kind === 'FE' || r.kind === 'FE+BE') {
    const b = await stageVerify(t, impl, 'verify-base')
    if (b.passed) {
      const msg = 'verify steps also pass on the base commit, so the test does not prove the change (weak test)'
      await commentVerify(t, `Verify for #${t.n}: ${msg}.\n${b.report || ''}`)
      throw blocked(msg, r, 'passed')
    }
    baseResult = 'failed'
  }
  const stills = r.stills || []
  const gif = await buildGif(t, impl, stills)
  // UAT reads this path from the prompt, not the repo root (the Verify: row may name another config).
  return { result, kind: r.kind, base: baseResult, stills, dir, gif, report: r.report || '', configPath: r.configPath || `${impl.worktree}/verify.config.json` }
}

// Stills to one GIF with ffmpeg. Any problem gives null and a log line; it never changes the verify result.
async function buildGif(t, impl, stills) {
  if (!stills.length) { log(`#${t.n} no stills, no GIF`); return null }
  const dir = `${impl.worktree}/.playwright-mcp/${t.n}`
  try {
    const res = await call(
      `Stage: gif. Build one animated GIF from the verify stills of ticket #${t.n}. Stills (in order): ${stills.join(', ')}. They sit in ${dir}.\n` +
      `Use only the stills listed above, in that order; ignore any other file in ${dir}. Write a concat list file ${dir}/stills.txt with one line per still ("file '<absolute path>'" and "duration 1"), then repeat the last still's "file" line once more at the end with no duration (the concat demuxer ignores the duration of the last entry, so without the repeat the final still flashes for one frame), then run: ffmpeg -y -f concat -safe 0 -i ${dir}/stills.txt -vf "scale=800:-2:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" ${dir}/evidence.gif. Do not use a wildcard pattern for the input.\n` +
      `Before the list: compare the stills with sha256sum and drop a still that is identical to the one before it. If fewer than 2 distinct stills remain, run no ffmpeg and return an empty gif (a later step attaches the first still as a PNG).\n` +
      `Rules: palettegen, at most 30 seconds, 800 px wide, under 10 MB (drop frames or lower the frame rate if larger). Write the GIF inside ${dir}. Commit nothing and do not add it to git.\n` +
      `Return gif: the absolute path of the GIF, or an empty string when there are no stills, fewer than 2 distinct stills remain, ffmpeg is missing or the build failed. An empty gif means a later step attaches the first still as a PNG.\n\n${RULES}`,
      { label: lbl(`#${t.n} record GIF`, t.title), phase: 'Tickets', schema: GIF_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
    if (res && res.gif) return res.gif
    log(`#${t.n} no GIF built`)
  } catch (e) { log(`#${t.n} gif build failed: ${e && e.message}`) }
  return null
}

// Separate from stageFinish: runs only for a real PR with evidence (the GIF, else the first still as a PNG) and a pass or flaky result. A failure is only logged.
async function stageAttach(t, fin, verifyResult) {
  if (!(fin && fin.pr > 0) || !verifyResult) return false
  const evidence = verifyResult.gif || (verifyResult.stills || [])[0]
  if (!evidence) return false
  if (verifyResult.result !== 'pass' && verifyResult.result !== 'flaky') return false
  const flaky = verifyResult.result === 'flaky'
  const note = `Verify for #${t.n} was flaky: it failed once and passed on the retry.`
  const cmd = `gh pr comment ${fin.pr} --repo ${repo} --attach ${evidence} --body "Verify evidence for #${t.n}: ${verifyResult.result}"`
  try {
    const res = await call(
      `Stage: attach. Run: ${cmd}\n` +
      `The --attach flag needs gh 2.99.0 or newer. The comment body must not contain an image line: the evidence file is attached with --attach only.\n` +
      (flaky ? `Then add this note to the end of the PR body: read it with gh pr view ${fin.pr} --repo ${repo} --json body -q .body, append "${note}", and write it back with gh pr edit ${fin.pr} --repo ${repo} --body-file <file>.\n` : '') +
      `If the command is denied or fails (old gh, permission denied, any error), do not retry and do not work around it. Return status ok (never blocked) and one decision with needs_review true, titled "Attach the verify GIF by hand for #${t.n}", whose decision field holds this exact command so the owner can paste it as written: ${cmd}\n` +
      `Commit nothing; the evidence file stays uncommitted. Otherwise return status ok.\n\n${RULES}`,
      { label: lbl(`#${t.n} attach evidence`, t.title), phase: 'Tickets', schema: SETUP_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
    takeDecisions(t.n, 'attach', res)
    return !!res && res.status !== 'blocked' && !((res.decisions || []).some(d => d && d.needs_review === true))
  } catch (e) {
    log(`#${t.n} attach failed: ${e && e.message}`)
    addDecision(t.n, 'attach', {
      title: `Attach the verify GIF by hand for #${t.n}`,
      context: `The attach step failed: ${e && e.message}`,
      decision: cmd, why: 'The GIF was not attached to the pull request.',
      consequences: 'The PR has no verify GIF until the owner runs the command.', how_to_reverse: 'n/a',
      needs_review: true,
    })
    return false
  }
}

// ---------------------------------------------------------------------------
// Merge policy block (owner decision F). Every PR the workflow opens carries a "Merge: auto|human" line and a
// readiness checklist between two markers, so a later stage can replace the block in place.
// ---------------------------------------------------------------------------
const MP_OPEN = '<!-- merge-policy -->', MP_CLOSE = '<!-- /merge-policy -->'
const PENDING = { ok: false, text: 'pending' }
function mergeBlock({ mode, ci = PENDING, review = PENDING, intent = PENDING, adrs = PENDING, uat = { ok: false, text: 'n/a' }, why = '' }) {
  const head = mode === 'auto' ? 'Merge: auto' : mode === 'pending' ? 'Merge: auto (pending gates)' : `Merge: human${why ? ` (${why})` : ''}`
  const row = (name, x) => `- [${x && x.ok ? 'x' : ' '}] ${name}: ${(x && x.text) || 'pending'}`
  return [MP_OPEN, head, row('CI', ci), row('Review', review), row('Intent', intent), row('needs_review ADRs', adrs), row('UAT', uat), MP_CLOSE].join('\n')
}

function stageFinish(t, impl, verifyResult) {
  const prBase = single ? base : integBranch
  const fw = newWt(`finish-${t.n}`, null, LOCAL ? impl.branch : `${remote}/${impl.branch}`)
  const dir = impl.worktree || fw.dir
  const where = `Your branch ${impl.branch} is checked out in ${dir}; work there with cd ${dir}. If that path is gone, run: git -C ${repoDir} worktree add ${fw.dir} ${impl.branch}, and work in ${fw.dir} (git fetch ${remote} first).\n`
  const how = LOCAL
    ? `Local mode: do NOT push and do NOT open a pull request. Verify the branch as the skill describes, then write the PR description for base ${prBase} to .ship/pr-${t.n}.md inside the worktree (do not commit it) and return its absolute path as body_file with pr: 0.\n`
    : `Verify, push the branch and open the pull request with base ${prBase}. The body says "Refs #${t.n}" (the final PR carries the Closes lines), contains this merge-policy block exactly once, unchanged, and ends with the footer line. Return the PR number as pr and its url.\n${single ? mergeBlock({ mode: 'human', why: `the PR targets ${base}` }) : mergeBlock({ mode: 'pending' })}\n`
  const ver = verifyResult
    ? `Verify result: ${verifyResult.result}. Local stills: ${verifyResult.stills.join(', ') || 'none'}. Evidence stays uncommitted; a later step attaches the evidence file to the pull request.\n`
    : ''
  const build = advice => head(t, 'finishing-a-development-branch', `Stage: finish. ${where}${ver}${how}Do not run the full suite.${advice}`, dir)
  return runStage(t, 'finish', build, FINISH_SCHEMA, { model: MODEL.implement, effort: EFFORT.implement })
}

// ---------------------------------------------------------------------------
// specs/<slug>/ flow files: local scratch, gitignored. Stages write none. The script renders the files from the
// stage results and a cheap agent writes them into the main checkout, so they outlive the worktrees. Early files
// are written per ticket as each stage ends: intent.md after the intent stage (at depth S also design.md and
// plan.md), design.md, plan.md and research-brief.md after the plan stage. decision.md and summary.md need
// end-of-run data, so they are written at the end, and the end pass rewrites all five files. A failed render or
// write never changes the outcome of the run: it is only logged.
// ---------------------------------------------------------------------------
const specs = {}   // ticket number -> the stage results the flow files are rendered from
const specDir = t => `${trimmed}/specs/${t.n}-${slugOf(t.title)}`
const REQUEST_LINE = '{{REQUEST}}', DATE_TOKEN = '{{DATE}}'   // the writer fills both; the script reads no clock
const bullets = a => (Array.isArray(a) && a.length ? a.map(x => `- ${x}`).join('\n') : '- none')
// Same headings as templates/specs/*.md at every depth; an empty section says none.
const header = (t, kind) => [`# ${kind}: ${t.title}`, `Ticket: ${LOCAL ? t.n : `#${t.n}`} · Depth: ${t.depth} · Date: ${DATE_TOKEN}`, '']
const ownDecisions = t => decisions.filter(d => d.ticket === t.n || (single && d.ticket === 'run'))
const adrOf = (d, run) => { const a = run.adrs.find(x => x.title === d.title && String(x.ticket) === String(d.ticket)); return a ? a.path : 'none' }
const cell = v => String(v).replace(/\|/g, '\\|')

function renderSteps(steps) {
  return (steps || []).map((x, k) => `### ${k + 1}. ${x.title}\n- Files: ${(x.files || []).join(', ') || 'none listed'}\n` +
    `- Covers: ${(x.covers || []).join(', ') || 'none'}\n- Done-when: ${x.done_when}`).join('\n\n') || 'none'
}

function renderDecisionLog(t, run) {
  const own = ownDecisions(t)
  const L = header(t, 'Decisions')
  if (!own.length) L.push('none', '')
  own.forEach((d, k) => L.push(`### D${k + 1} ${d.title}`,
    `- Stage: ${d.stage} · Confidence: ${d.confidence} · needs_review: ${d.needs_review ? 'yes' : 'no'} · owner_confirmed: ${d.owner_confirmed ? 'yes' : 'no'}`,
    `- Context: ${d.context}`, `- Options: ${(d.options || []).join('; ')}`, `- Decision: ${d.decision}`, `- Why: ${d.why}`,
    `- Consequences: ${d.consequences}`, `- Reverse: ${d.how_to_reverse}`, `- ADR: ${adrOf(d, run)}`, ''))
  return L.join('\n')
}

function renderSummary(t, run) {
  const s = specs[t.n] || {}, r = run.byN.get(t.n) || {}, impl = s.impl || {}, fin = s.fin || {}, v = s.verify
  const checks = (impl.verify || []).map(c => `| \`${cell(c.command)}\` | exit ${c.exit}${c.notes ? `: ${cell(c.notes)}` : ''} | ${cell((c.covers || []).join(', ') || '-')} |`)
  if (v) checks.push(`| Verify: row (${v.kind}) | ${cell(v.result)} | - |`)
  const review = [`- code review: ${run.review.status === 'not run' ? `not run (${run.review.reason || 'no ticket was delivered'})` : `${run.review.rounds} fix round(s), ${run.review.fixed.length} fixed, ${run.review.leftover.length} left`}`,
    `- intent-review: ${run.intent.verdict}`, `- full suite: passed ${run.suite.passed}, failed ${run.suite.failed}, skipped ${run.suite.skipped}`]
  const pr = fin.url || (fin.pr ? `#${fin.pr}` : fin.body_file || 'none')
  const finalPr = !single && run.final ? ` · Final PR: ${run.final.url || (run.final.pr ? `#${run.final.pr}` : 'none')}` : ''
  return [...header(t, 'Summary'), '## Shipped', '',
    `Status: ${r.status || 'unknown'}${r.reason ? ` (${r.reason})` : ''} · Branch: ${impl.branch || ticketBranch(t)} · PR: ${pr}${finalPr}`,
    capSummary(impl.summary) || 'none', '', `- Commits: ${(impl.commits || []).map(c => `${c.sha} ${c.subject}`).join(', ') || 'none'}`, '',
    '## Verify', '', '| Command | Result | Covers |', '|---|---|---|', ...(checks.length ? checks : ['| none | - | - |']), '',
    '## Review', '', ...review, '', '## Deviations from plan', '', '- none recorded (decisions made while implementing are in decision.md)', '',
    '## Decisions', '', bullets(ownDecisions(t).map((d, k) => `D${k + 1} ${d.title} → ${adrOf(d, run) === 'none' ? 'local only' : adrOf(d, run)}`)), ''].join('\n')
}

function renderSpecs(t, run) {
  const s = specs[t.n] || {}, i = s.intent || {}
  const files = {}
  files['intent.md'] = [...header(t, 'Intent'), '## Original request', '', LOCAL ? (t.body || t.title) : REQUEST_LINE, '', '## Goal', '', i.goal || 'none', '',
    '## Acceptance criteria', '', bullets((i.acceptance || []).map((a, k) => `AC${k + 1}: ${a}`)), '', '## Out of scope', '', bullets(i.out_of_scope), '',
    '## Verdict', '', `READY — triaged by autopilot before the run; depth ${t.depth}`, '',
    '## Confirmed decisions', '', (t.confirmed && t.confirmed.trim()) || 'none', ''].join('\n')
  files['design.md'] = s.design ? s.design.design_md
    : [...header(t, 'Design'), '## Context', '', i.goal || 'none', '', '## Options', '', '- none weighed by the workflow', '',
      '## Decision', '', i.approach || 'The steps in plan.md are the approach.', '', '## Why', '', 'none', '',
      '## Consequences', '', 'none', '', '## How to reverse', '', 'Revert the ticket commits.', ''].join('\n')
  files['plan.md'] = s.plan ? s.plan.plan_md
    : [...header(t, 'Plan'), '## Goal', '', i.goal || 'none', '', '## Steps', '', renderSteps(i.plan_steps), ''].join('\n')
  if (s.research) files['research-brief.md'] = s.research.research_md
  files['decision.md'] = renderDecisionLog(t, run)
  files['summary.md'] = renderSummary(t, run)
  return files
}

// One agent writes the files of every ticket, skipped ones included. run: { byN, final, review, intent, suite, adrs }.
async function writeSpecs(run) {
  return writeSpecFiles(tickets, run, { label: 'write specs/ flow files', phase: 'Decisions' })
}

// Early write for one ticket: only the named files, rendered from an empty run (no decision.md or summary.md).
// It never throws: a failure is only logged.
async function writeSpecsEarly(t, files) {
  try {
    const stub = { byN: new Map(), adrs: [], final: null, review: { status: 'not run', reason: 'run in progress', rounds: 0, fixed: [], leftover: [] },
      intent: { verdict: 'not run' }, suite: { passed: 0, failed: 0, skipped: 0 } }
    await writeSpecFiles([t], stub, { only: files, label: 'write specs/ early', phase: 'Tickets' })
  } catch (e) {
    log(`#${t.n} early spec files not written: ${e && e.message ? e.message : String(e)}`)
  }
}

async function writeSpecFiles(list, run, { only, label, phase }) {
  const parts = [], reqs = []
  for (const t of list) {
    let files
    try { files = renderSpecs(t, run) } catch (e) { log(`#${t.n} spec files not rendered: ${e && e.message ? e.message : String(e)}`); continue }
    if (only) files = Object.fromEntries(Object.entries(files).filter(([f]) => only.includes(f)))
    const dir = specDir(t)
    if (files['intent.md'] && files['intent.md'].includes(REQUEST_LINE)) reqs.push(`In ${dir}/intent.md, replace the line ${REQUEST_LINE} with the issue body, verbatim, from: gh issue view ${t.n} --repo ${repo} --json body -q .body`)
    parts.push(...Object.entries(files).map(([f, text]) => `=== ${dir}/${f}\n${text}`))
  }
  if (!parts.length) return
  const prompt = `Stage: write the local spec files of this run. Your session working directory is NOT the target repo.\n` +
    `1. Run: git -C ${repoDir} check-ignore -q specs/x. If it exits non-zero, specs/ is not gitignored: write nothing and return status blocked with blocked_reason "specs/ is not gitignored in ${repoDir}".\n` +
    `2. Run: date +%F, and use its output wherever a file below says ${DATE_TOKEN}.\n` +
    `3. Write each file below with one Bash call, by absolute path: mkdir -p its folder, then cat > <path> <<'SPEC_EOF' (quoted delimiter, so nothing expands), the exact text between its === line and the next one, then a line SPEC_EOF. This overwrites a file that exists. Use Bash for every file: a file-write tool call for a summary-style .md file can be refused by a subagent rule, and the stage then reports blocked with a file missing. Check afterwards with ls that all the files exist.\n` +
    `${reqs.length ? `${reqs.join('\n')}\n` : ''}` +
    `${trimmed}/specs/ is gitignored local scratch and the only place in ${repoDir} you may write. Edit nothing else; run no other git command and commit nothing. Return status ok.\n\n${parts.join('\n\n')}`
  try {
    const res = await call(prompt, { label, phase, schema: SETUP_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
    if (!res || res.status === 'blocked') log(`spec files not written: ${(res && (res.blocked_reason || res.summary)) || 'no answer'}`)
  } catch (e) {
    log(`spec files not written: ${e && e.message ? e.message : String(e)}`)
  }
}

// ---------------------------------------------------------------------------
// Per-ticket merge gate (multi-ticket remote runs only). The script judges structured results from the review,
// the intent review and gh pr checks; the merge stage merges only a ticket whose gate passed.
// ---------------------------------------------------------------------------
// ci: the list gh pr checks returned. Fails closed: no checks, a failure, a cancel, a pending check or no head commit all fail.
function judgeCi(res, expectHead) {
  const checks = res && Array.isArray(res.checks) ? res.checks : []
  if (!checks.length) return { ok: false, text: 'no CI checks found (fails closed)' }
  const count = b => checks.filter(c => c && c.bucket === b).length
  const bad = checks.filter(c => !c || !['pass', 'skipping'].includes(c.bucket))
  if (count('pending')) return { ok: false, text: `${count('pending')} check(s) still pending after the wait` }
  if (bad.length) return { ok: false, text: `${bad.map(c => `${c && c.name || '?'}: ${c && c.bucket || '?'}`).join(', ')}` }
  if (!count('pass')) return { ok: false, text: 'every check was skipped (fails closed)' }
  if (!(res && typeof res.headRefOid === 'string' && res.headRefOid.trim())) return { ok: false, text: 'the PR head commit is unknown (fails closed)' }
  // The fix rounds push new commits. CI that ran on an older head is stale: the head must be the pushed branch tip.
  // The branch tip the CI stage read is the reference; the last fix commit is only the fallback when no tip came back.
  expectHead = (res.branchTip && res.branchTip.trim()) || expectHead
  if (expectHead) {
    const h = res.headRefOid.trim()
    if (!(h.startsWith(expectHead) || expectHead.startsWith(h))) return { ok: false, text: `CI ran on ${h.slice(0, 8)} but the branch tip is ${expectHead.slice(0, 8)} (stale)` }
  }
  return { ok: true, text: `${checks.length} check(s) green at ${res.headRefOid.slice(0, 8)}` }
}

function judgeReview(rv) {
  if (!rv || rv.status !== 'ran') return { ok: false, text: `not run${rv && rv.reason ? ` (${rv.reason})` : ''}` }
  const notFixed = (rv.notFixed || []).length, left = (rv.leftover || []).filter(f => f.score >= FIX_THRESHOLD).length
  if (rv.reReviewNotRun) return { ok: false, text: `re-review not run (${rv.reReviewNotRun})` }
  if (rv.unreviewedFix) return { ok: false, text: 'the intent fix commits were not reviewed' }
  if (notFixed || left) return { ok: false, text: `${notFixed} not fixed, ${left} left at score ${FIX_THRESHOLD} or more` }
  return { ok: true, text: `ran, ${(rv.fixed || []).length} fixed, nothing left` }
}

const reviewStatus = rv => (judgeReview(rv).ok ? 'ok' : (rv && rv.status === 'ran' ? 'failed' : 'blocked'))

function stageCi(t, fin, ctx, label) {
  const pr = fin.pr
  const prompt = `${RULES}\n\nStage: ci. Read the CI result of PR ${pr} in ${repo}. Edit nothing. ${notCwd()}\n` +
    `1. Poll until the PR has at least one check for its current head: gh pr checks ${pr} --repo ${repo} --json name,bucket (repeat every ${CI_INTERVAL} s). A push can need a moment before its checks appear.\n` +
    `2. Then run: gh pr checks ${pr} --repo ${repo} --watch --interval ${CI_INTERVAL}\n` +
    `Use a Bash timeout of ${CI_WAIT_MS} ms in total for steps 1 and 2. Exit code 1 (a check failed) and 8 (checks pending) are expected results, not errors: go on to step 3 anyway.\n` +
    `3. Run: gh pr checks ${pr} --repo ${repo} --json name,bucket   and: gh pr view ${pr} --repo ${repo} --json headRefOid -q .headRefOid   and: git ls-remote ${remote} refs/heads/${ctx.branch}  (the first column is the branch tip)\n` +
    `Return checks (one entry per check: name and bucket, copied unchanged), headRefOid and branchTip (the ls-remote commit). If a command fails, return the checks you have (an empty list when none) and say why in note. Do not judge the result yourself.`
  return journaled(t.n, 'ci', MODEL.cheap, () => call(prompt, { label, phase: 'Gate', schema: CI_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap }), undefined, res => (judgeCi(res).ok ? 'ok' : 'failed'))
}

// Rewrites the merge-policy block of the ticket PR body. A failure is only logged.
async function updateMergeBlock(t, fin, ctx, block) {
  try {
    await call(`${RULES}\n\nStage: update the PR body. ${notCwd()}\nRead the body: gh pr view ${fin.pr} --repo ${repo} --json body -q .body\n` +
      `Replace everything from the line ${MP_OPEN} to the line ${MP_CLOSE} (both included) with the block below, change nothing else, write the result to a temp file and run: gh pr edit ${fin.pr} --repo ${repo} --body-file <file>. ` +
      `If the body has no such block, add the block at the top. Return status ok.\n\n${block}`,
      { label: `${ctx.labelPrefix}PR body`, phase: 'Gate', schema: SETUP_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
  } catch (e) {
    log(`#${t.n} merge-policy block not written: ${e && e.message ? e.message : String(e)}`)
  }
}

// The PR body still says Merge: auto from the gate pass; rewrite it to a human merge.
async function humanMergeBlock(n, r) {
  if (LOCAL || !(r && r.pr)) return
  const mt = tickets.find(x => x.n === n) || { n }
  const ci = r.gate && r.gate.ci, rv = r.gate && r.gate.review, it = r.gate && r.gate.intent
  await updateMergeBlock(mt, { pr: r.pr }, { labelPrefix: `#${n} merge failed · ` },
    mergeBlock({ mode: 'human', why: `merge into ${integBranch} failed`, ci: ci || PENDING, review: rv || PENDING, intent: it || PENDING, adrs: { ok: true, text: 'none' } }))
}

async function stageGate(t, fin, impl, branch) {
  const fail = (gates, extra) => ({ pass: false, failed: gates, ...extra })
  if (!(fin && fin.pr > 0)) return fail([{ gate: 'pr', detail: 'no PR number was returned' }])
  const tb = impl.branch || branch
  const ctx = { ticket: t.n, ref: `${remote}/${tb}`, branch: tb, diffBase: integRef, target: String(fin.pr),
    wtPrefix: `g${t.n}-`, labelPrefix: `#${t.n} gate `, boundary: runBoundaryText(t.n) }
  const failed = []
  const review = await journaled(t.n, 'gate-review', MODEL.review, () => reviewLoop(ctx, ctx.target), undefined, reviewStatus)
  let intent = await stageIntentReview([{ n: t.n }], ctx)
  let intentFixTip = ''
  if (intent.fixRound) {
    intentFixTip = (intent.fixRange && intent.fixRange.split('..')[1]) || ''
    // Code the intent fix landed has not been reviewed. Review that range; a second fix round is never reviewed, so it fails the gate.
    if (intent.fixRange) {
      const again = await reviewWithRetry(`${ctx.labelPrefix}code-review · intent fix`, review.level, intent.fixRange,
        `This is a review of the intent-fix commits only, range ${intent.fixRange}. Review that diff and nothing else.\n`, ctx)
      if (again.notRun) review.reReviewNotRun = again.notRun
      else review.leftover = [...review.leftover, ...((again.res && again.res.findings) || []).filter(f => !f.pre_existing && f.score >= FIX_THRESHOLD)]
    } else review.unreviewedFix = true
    intent = await stageIntentReview([{ n: t.n }], ctx)
    if (intent.fixRound) review.unreviewedFix = true
  }
  const reviewG = judgeReview(review)
  const intentG = { ok: intent.verdict === 'match', text: intent.verdict }
  if (!reviewG.ok) failed.push({ gate: 'review', detail: reviewG.text })
  if (!intentG.ok) failed.push({ gate: 'intent', detail: intentG.text })
  let ciG, head = ''
  if (failed.length) ciG = { ok: false, text: 'not checked (an earlier gate failed)' }
  else {
    const res = await stageCi(t, fin, ctx, `${ctx.labelPrefix}CI checks`)
    const lastFix = intentFixTip || ((review.fixed || []).slice(-1)[0] || {}).commit || ''
    ciG = judgeCi(res, lastFix)
    head = ciG.ok ? res.headRefOid.trim() : ''
    if (!ciG.ok) failed.push({ gate: 'ci', detail: ciG.text })
  }
  const nr = decisions.filter(d => d.ticket === t.n && d.needs_review)
  const nrG = { ok: nr.length === 0, text: nr.length ? `${nr.length} (${nr.map(d => d.title).join('; ')})` : 'none' }
  if (!nrG.ok) failed.push({ gate: 'needs_review', detail: nrG.text })
  const pass = failed.length === 0
  const block = mergeBlock({ mode: pass ? 'auto' : 'human', why: pass ? '' : `gate ${failed.map(f => f.gate).join(', ')} failed`, ci: ciG, review: reviewG, intent: intentG, adrs: nrG })
  await updateMergeBlock(t, fin, ctx, block)
  return { pass, failed, ci: ciG, review: reviewG, intent: intentG, head }
}

async function runTicket(t) {
  const branch = ticketBranch(t)
  const spec = specs[t.n] = {}
  try {
    const intent = spec.intent = await stageIntent(t)
    boundaries[t.n] = boundaryOf(intent)
    const boundary = boundaryText(`Boundary for ticket #${t.n}:`, intent)
    await writeSpecsEarly(t, t.depth === 'S' ? ['intent.md', 'design.md', 'plan.md'] : ['intent.md'])
    let planText
    if (t.depth === 'S') {
      planText = `Plan (steps from the intent stage):\n${JSON.stringify(intent.plan_steps || [])}`
    } else if (t.depth === 'M') {
      const plan = await stagePlan(t, intent)
      spec.plan = plan
      await writeSpecsEarly(t, ['design.md', 'plan.md'])
      planText = `Follow this plan:\n${plan.plan_md}`
    } else {
      const research = spec.research = await stageResearch(t, intent)
      const design = spec.design = await stageDesign(t, intent, research)
      const plan = spec.plan = await stagePlan(t, intent, `Design:\n${design.design_md}\n`)
      const advice = await advisePlan(t, design, plan)
      await writeSpecsEarly(t, ['design.md', 'plan.md', 'research-brief.md'])
      planText = `Design:\n${design.design_md}\n\nAdvisor review of design and plan (follow it unless it is wrong; record any deviation as a decision):\n${advice}\n\n` +
        `Follow this plan:\n${plan.plan_md}`
    }
    const impl = spec.impl = await stageImplement(t, branch, planText, boundary)
    const verifyResult = spec.verify = await verifyTicket(t, impl)
    const fin = spec.fin = await stageFinish(t, impl, verifyResult)
    const attached = await stageAttach(t, fin, verifyResult)
    const result = { n: t.n, status: 'done', pr: fin.pr || null, url: fin.url || '', branch: impl.branch || branch, summary: capSummary(impl.summary || fin.summary), reason: '', body_file: fin.body_file, ...(verifyResult ? { verify: { ...verifyResult, attached } } : {}) }
    if (!single && !LOCAL) {
      let gate
      try { gate = await stageGate(t, fin, impl, branch) } catch (e) { gate = { pass: false, failed: [{ gate: 'gate stage', detail: e && e.message ? e.message : String(e) }] } }
      result.gate = gate
      if (!gate.pass) {
        const names = gate.failed.map(f => f.gate).join(', ')
        const cmd = fin.pr ? `gh pr merge ${fin.pr} --repo ${repo} --merge` : `(no PR was opened for #${t.n})`
        result.status = 'blocked'; result.reason = `human merge: gate ${names} failed`
        addDecision(t.n, 'merge', {
          title: `Merge PR ${fin.pr || '?'} by hand for #${t.n}: gate ${names} failed`,
          context: `The merge gate for #${t.n} did not pass. ${gate.failed.map(f => `${f.gate}: ${f.detail}`).join('. ')}.`,
          decision: `The workflow does not merge this PR into ${integBranch}. After you have checked the failed gate${gate.failed.length > 1 ? 's' : ''}, run: ${cmd}`,
          why: 'Only a ticket PR that passes CI, review, intent review and has no open needs_review decision is merged by the workflow.',
          consequences: `Ticket #${t.n} is missing from the final PR and the tickets that depend on it are skipped until the PR is merged.`,
          how_to_reverse: 'Do not run the command; close the PR instead.',
          needs_review: true, confidence: 'high',
        })
        log(`#${t.n} gate failed: ${names}`)
      }
    }
    log(`#${t.n} ${result.status === 'done' ? 'done' : 'ready for a human merge'}: ${fin.url || fin.body_file || impl.branch}`)
    return result
  } catch (e) {
    const reason = e && e.message ? e.message : String(e)
    log(`#${t.n} blocked: ${reason}`)
    return { n: t.n, status: 'blocked', pr: null, url: '', branch, summary: '', reason, ...(e && e.verify ? { verify: e.verify } : {}) }
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
    { label: 'set up integration branch', phase: 'Setup', schema: SETUP_SCHEMA, model: MODEL.merge, effort: EFFORT.merge })
}

// Merge the tickets that passed their gate. The script decides what is merged; the agent only runs the commands.
// There is no conflict path: a conflict or any failure changes nothing and the ticket stays open as a human merge.
async function stageMerge(group, done) {
  const list = done.map(r => `- #${r.n} branch ${r.branch}${r.pr ? ` PR ${r.pr}` : ''}${r.gate && r.gate.head ? ` head ${r.gate.head}` : ''}`).join('\n')
  const how = LOCAL
    ? `Merge each branch below into ${integBranch} with "git merge --no-ff". On a conflict, run "git merge --abort", change nothing for that branch and return its ticket in failed with the reason. Then run: git update-ref refs/heads/${integBranch} HEAD   (local mode: nothing is pushed).`
    : `Merge each ticket PR below into ${integBranch}. Each PR passed its gate at the head commit shown. Run each command as its own Bash call, never joined with &&, ; or a subshell: for example gh pr merge <pr> --repo ${repo} --merge --match-head-commit <head> is one call (the merge guard needs --repo and reads the PR base). These PRs target ${integBranch}, never ${base}. A PR that is already MERGED into ${integBranch} counts as merged: check its state first with gh pr view <pr> --repo ${repo} --json state, and do not merge it again. On a conflict, a head mismatch or any other failure, change nothing: do not merge locally, do not push, do not close the PR, and return that ticket in failed with the reason (a human merges it). If gh pr merge is denied by a permission rule or by the merge guard, do not look for a workaround: return that ticket in failed with a reason that names the denial and the fix (the owner allows gh pr merge into ${integBranch}*), and do not just write denied.`
  const w = newWt(`merge-g${group}`, `scratch/${slug}-merge-g${group}`, integRef)
  const prompt = `${w.setup}${RULES}\n\nStage: merge group ${group} into ${integBranch}.\n${how}\n${list}\n` +
    `Return merged (ticket numbers) and failed ([{n, reason}]). Never merge into ${base}.`
  const res = await call(prompt, { label: `merge ticket branches · group ${group}`, phase: 'Merge', schema: MERGE_SCHEMA, model: MODEL.merge, effort: EFFORT.merge })
  takeDecisions('run', 'merge', res)
  return res
}

// One look at the CI state of the final PR for the readiness checklist. It waits for nothing and is not a gate.
async function stageCiSnapshot(finalPr) {
  if (LOCAL || !(finalPr && finalPr.pr > 0)) return null
  try {
    const res = await call(`${RULES}\n\nStage: ci snapshot. Run once, without --watch: gh pr checks ${finalPr.pr} --repo ${repo} --json name,bucket   and: gh pr view ${finalPr.pr} --repo ${repo} --json headRefOid -q .headRefOid\n` +
      `Exit code 1 and 8 are expected results. Return checks (name and bucket, unchanged) and headRefOid; an empty list when there are none. Edit nothing. ${notCwd()}`,
      { label: 'CI snapshot', phase: 'Decisions', schema: CI_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
    const checks = (res && res.checks) || []
    if (!checks.length) return { ok: false, text: 'no checks reported yet' }
    const n = b => checks.filter(c => c.bucket === b).length
    return { ok: n('pass') + n('skipping') === checks.length && n('pass') > 0, text: `${n('pass')} pass, ${n('fail') + n('cancel')} fail, ${n('pending')} pending (snapshot, not a gate)` }
  } catch (e) {
    log(`CI snapshot failed: ${e && e.message ? e.message : String(e)}`)
    return { ok: false, text: 'unknown (snapshot failed)' }
  }
}

function stageFinalPr(done, bodyTemplate) {
  const prompt = `${RULES}\n\nStage: open the final pull request ${integBranch} -> ${base} in ${repo}.\n` +
    (LOCAL
      ? `Local mode: do not push and do not open a pull request. Return pr: 0.\n`
      : `Write the body below to a temp file and run: gh pr create --repo ${repo} --base ${base} --head ${integBranch} --title "${slug}" --body-file <file>. Return its number and url.\n`) +
    `Body (a later stage replaces it with the final text):\n${bodyTemplate}`
  return call(prompt, { label: 'open final PR', phase: 'Review', schema: FINAL_PR_SCHEMA, model: MODEL.merge, effort: EFFORT.merge })
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

// A stage context says what a review, fix or intent stage works on. The run context is the final branch; the
// per-ticket gate builds one per ticket (ref = the ticket branch, diffBase = the integration branch). ticket is the
// key decisions are recorded under; wtPrefix keeps worktree dirs apart and labelPrefix keeps agent labels apart.
const RUN_CTX = { ticket: 'run', ref: finalRef, branch: finalBranch, diffBase: baseRef, wtPrefix: '', labelPrefix: '', boundary: null }

function reviewAgent(label, level, target, rangeNote, retryNote, ctx = RUN_CTX) {
  const w = newWt(`${ctx.wtPrefix}${label}`, null, ctx.ref)
  const prompt = `${w.setup}${RULES}\n\n` +
    `Stage: review. Use the Skill tool: skill 'code-review', args '${level} ${target}'. Run it from ${w.dir} (${ctx.ref} is checked out there${rangeNote ? '' : `; the diff is ${ctx.diffBase}...${ctx.ref}`}). Never edit files, never post comments.\n` +
    `${RULE_SKILL} Return skill_invoked: true only when the skill ran.\n${retryNote || ''}` +
    `${rangeNote}Return every finding with score 0-100 (how sure you are that it is a real defect worth fixing). ` +
    `Mark pre_existing: true for a finding that is already present on ${ctx.diffBase} and not introduced by this change.`
  return call(prompt, { label, phase: 'Review', schema: REVIEW_SCHEMA, model: MODEL.review, effort: EFFORT.review })
}

// Run code-review; one retry when the skill did not run. Returns {res} or {notRun: reason}.
async function reviewWithRetry(label, level, target, rangeNote, ctx = RUN_CTX) {
  let res = await reviewAgent(label, level, target, rangeNote, '', ctx)
  if (res && res.skill_invoked === true) { takeDecisions(ctx.ticket, 'review', res); return { res } }
  const why = r => (r && typeof r.skill_error === 'string' && r.skill_error.trim()) || (r ? 'the agent did not report running the skill' : 'the review agent returned nothing')
  const first = why(res)
  res = await reviewAgent(`${label} retry`, level, target, rangeNote,
    `The previous attempt did not run code-review. Its error: ${first}\nTry again. ${RULE_SKILL}\n`, ctx)
  if (res && res.skill_invoked === true) { takeDecisions(ctx.ticket, 'review', res); return { res } }
  return { notRun: why(res) }
}

function fixAgent(label, findingText, extra, phaseName, wtKey, ctx = RUN_CTX) {   // wtKey names the worktree; the label is display text
  const w = newWt(`${ctx.wtPrefix}fix-${wtKey || label}`, null, ctx.ref)
  const prompt = `${w.setup}${RULES}\n\n` +
    `Stage: fix. Run "git rev-parse HEAD" first and return it as base_sha. ${findingText}\n${ctx.boundary == null ? runBoundaryText() : ctx.boundary}` +
    `Make one commit ("git add", then "git commit"), include a test that fails without the fix, run only the related tests (${testCmd}) and lint (${lintCmd}). ` +
    `Then land it: ${land(ctx.branch)}. Return the commit sha as commit. ${extra || ''}` +
    `If the finding is wrong or cannot be fixed safely, change nothing and return fix_status skipped or failed with the reason in summary.`
  return call(prompt, { label, phase: phaseName || 'Review', schema: FIX_SCHEMA, model: MODEL.fix, effort: EFFORT.fix })
}

// The final, cross-ticket review: the run context over the final branch.
function stageReview(finalPr) {
  return journaled('run', 'review', MODEL.review, () => reviewLoop(RUN_CTX, finalPr && finalPr.pr ? String(finalPr.pr) : finalBranch), undefined, reviewStatus)
}

async function reviewLoop(ctx, target) {
  const P = ctx.labelPrefix
  const stat = await call(
    `git -C ${repoDir} fetch ${remote}\ngit -C ${repoDir} diff --numstat ${ctx.diffBase}...${ctx.ref}\n\n${notCwd()}\nRun the two commands above. Return one entry per file (path, added, deleted). Do not edit anything.`,
    { label: `${P}measure diff size`, phase: ctx.ticket === 'run' ? 'Review' : 'Gate', schema: DIFFSTAT_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
  const { level, lines, risky } = pickLevel((stat && stat.files) || [])
  log(`review level ${level} (${lines} changed lines${risky.length ? `, risky paths: ${risky.join(', ')}` : ''})${ctx.ticket === 'run' ? '' : ` for #${ctx.ticket}`}`)

  const out = { rounds: 0, fixed: [], notFixed: [], leftover: [], preExisting: [], level, status: 'ran', reason: '' }
  const skipped = (reason, what) => {
    addDecision(ctx.ticket, 'review', { title: `Review skipped: code-review did not run (${reason})`, context: `The review stage must invoke the code-review skill; it did not run${what ? ` for ${what}` : ''}.`,
      decision: 'Continue the pipeline without that review and say so in the PR body.', why: 'A review that did not run must not read as a pass; the owner decides.',
      consequences: 'The change was not reviewed by code-review.', how_to_reverse: 'Run /code-review on the PR.', needs_review: true, confidence: 'high' })
  }
  const first = await reviewWithRetry(`${P}code-review · round 0`, level, target, '', ctx)
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
      const res = await fixAgent(lbl(`${P}fix r${out.rounds}.${k + 1}`, `${f.path ? f.path.split('/').pop() : f.summary}${f.path && f.line ? `:${f.line}` : ''}`), `Finding ${f.id} (score ${f.score}) in ${f.path || 'the diff'}${f.line ? `:${f.line}` : ''}: ${f.summary}`, '', undefined, `r${out.rounds}-${k + 1}`, ctx)
      takeDecisions(ctx.ticket, 'review-fix', res)
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
    const again = await reviewWithRetry(`${P}code-review · round ${out.rounds}`, level, range,
      `This is a re-review of the fix commits only, range ${range}. Review that diff and nothing else; ignore the rest of the branch.\n`, ctx)
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

// Per-ticket request text, cached so the UAT stage reuses it without another agent call.
const requestCache = new Map()   // ticket number -> { body, fetched }
async function requestTexts(done) {
  const parts = await parallel(done.map(r => () => {
    const t = tickets.find(x => x.n === r.n)
    if (LOCAL) return Promise.resolve({ body: t.body || t.title })
    return call(`Run: gh issue view ${t.n} --repo ${repo} --json body -q .body\nReturn its output unchanged in body. Do not summarise or edit it.`,
      { label: lbl(`#${t.n} fetch owner request`, t.title), phase: 'Intent review', schema: REQUEST_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
  }))
  const texts = new Map()
  done.forEach((r, i) => {
    const t = tickets.find(x => x.n === r.n)
    const got = parts[i] && parts[i].body
    const e = { body: got || t.title, fetched: !!got }
    texts.set(t.n, e)
    requestCache.set(t.n, e)
  })
  return texts
}

async function stageIntentReview(done, ctx = RUN_CTX) {
  const texts = await requestTexts(done)
  const request = done.map(r => {
    const t = tickets.find(x => x.n === r.n)
    return `### #${t.n} ${t.title}\n${texts.get(t.n).body}`
  }).join('\n\n')
  // Plan-blind on purpose: the request, the owner's own confirmed decisions (owner words, not agent plan) and the range. No plan, design, ADR or summary.
  const owner = done.map(r => tickets.find(x => x.n === r.n)).filter(t => t && t.confirmed && t.confirmed.trim())
    .map(t => `### #${t.n}\n${t.confirmed.trim()}`).join('\n\n')
  const ownerBlock = owner ? `Owner-confirmed decisions (the owner's own words; a change they name is NOT a gap, drift or excess):\n<<<\n${owner}\n>>>\n\n` : ''
  const w = newWt(`${ctx.wtPrefix}intent-review`, null, ctx.ref)
  const role = `${pluginDir}/agents/intent-reviewer.md`
  const prompt = `${w.setup}Role: read ${role} and act as that role. If it does not exist, use this role: ` +
    `compare the diff with the owner's request and report only gaps (requested but missing), drift (does something other than requested) and excess (unrequested behaviour).\n\n` +
    `Owner's original request, verbatim:\n<<<\n${request}\n>>>\n\n${ownerBlock}Diff range: ${ctx.diffBase}..${ctx.ref}\n\n` +
    `Read the diff with: git -C ${w.dir} diff ${ctx.diffBase}..${ctx.ref}. Read-only: edit nothing. ` +
    `Report only findings of kind gap, drift or excess. Do not report anything else: nothing about tests, about whether tests pass, or about your role file. If there is nothing to report, return no findings.`
  const res = await call(prompt, { label: `${ctx.labelPrefix}intent review · diff vs request`, phase: ctx.ticket === 'run' ? 'Intent review' : 'Gate', schema: INTENT_REVIEW_SCHEMA, effort: EFFORT.review, agentType: 'harness:intent-reviewer' }, role)
  const findings = (res && res.findings) || []
  const fixable = findings.filter(f => f.kind === 'gap' || (f.kind === 'drift' && f.behaviour_changing))
  let fixRange = ''
  if (fixable.length) {
    const text = fixable.map((f, i) => `${i + 1}. [${f.kind}] ${f.clause}: ${f.detail}`).join('\n')
    const fix = await fixAgent(`${ctx.labelPrefix}intent fix · close gaps`, `The intent review found these gaps against the owner's request:\n${text}\nFix each one, one commit per finding.` +
      (owner ? `\nOwner-confirmed decisions (never revert or undo a change they name; skip any finding that conflicts with them and return it as a decision with needs_review: true instead):\n${owner}\n` : ''),
      'Return base_sha and the last commit sha. ', undefined, undefined, ctx)
    takeDecisions(ctx.ticket, 'intent-fix', fix)
    fixRange = fix && fix.fix_status === 'fixed' && fix.base_sha && fix.commit ? `${fix.base_sha}..${fix.commit}` : ''
  }
  return { verdict: res ? res.verdict : 'unknown', gaps: findings, fixRound: fixable.length > 0, fixRange }
}

// Drop each Verify: row and its continuation. Continuation = a line indented deeper than the row (sub-bullets too) or a wrapped plain-prose line at the row's own level. A blank line, a heading, a list bullet or a "Label:" line at the row's level ends the row, so tight AC lines under it stay. A mid-sentence mention stays.
const VERIFY_ROW = /^\s*(?:[-*>]\s*)?(?:\*\*|__)?Verify:/
const NEW_BLOCK = /^\s*(?:[-*+>#]|\d+[.)])\s|^\s*(?:\*\*|__)?[A-Za-z][\w -]{0,24}:/
function stripVerify(text) {
  let skipping = false, count = 0, rowIndent = 0
  const kept = []
  for (const line of String(text || '').split('\n')) {
    const indent = line.match(/^\s*/)[0].length
    if (VERIFY_ROW.test(line)) { skipping = true; rowIndent = indent; count++; continue }
    if (skipping && line.trim() && (indent > rowIndent || !NEW_BLOCK.test(line))) { count++; continue }
    skipping = false
    kept.push(line)
  }
  return { text: kept.join('\n'), count }
}

// One plan-blind UAT agent. No head(): that tells the agent to run gh issue view and would hand it the Verify row.
// The prompt holds the stripped request, the stripped owner block and the config path. No plan, diff or Verify row.
function uatAgent(label, wtName, t, body, owner, configPath) {
  const w = newWt(wtName, null, finalRef)
  const prompt = `${w.setup}${RULES}\n\nTicket #${t.n}: ${t.title}. Repo ${repo}.\n` +
    `Stage: uat. Read ${pluginDir}/skills/uat/SKILL.md and follow it with Mode: auto, only after your worktree exists. Never ask anyone. ` +
    `The recipe file is ${pluginDir}/skills/verify/references/run-app.md. ` +
    `The request text below is your only source: do not run gh issue view, and do not read git log, diffs, docs/adr/, specs/ or any plan. Keep the evidence local and uncommitted; fix nothing.\n\n` +
    `Owner's request (the issue body, verify rows removed by the workflow):\n<<<\n${body}\n>>>\n\n` +
    (owner ? `Owner-confirmed decisions (the owner's own words):\n<<<\n${owner}\n>>>\n\n` : '') +
    `Config: ${configPath} (read-only; use this path, not the repo root; run its startCommand from ${w.dir}). If that file does not exist, use verify.config.json at the root of your own worktree ${w.dir} (verify commits it to the ticket branch); report blocked only when neither exists.\n` +
    `Return passed_ac, scenarios (id, covers, kind, status, assertion, still), non_ac_failures and console_errors. If the run could not happen (no config, app will not start, no credentials), return status blocked with blocked_reason.`
  return call(prompt, { label, phase: 'UAT', schema: UAT_SCHEMA, model: MODEL.verify, effort: EFFORT.verify })
}

const uatStatus = res => (!res ? 'failed' : res.status === 'blocked' ? 'blocked' : uatOk(res) ? 'ok' : 'failed')
async function runUat(label, wtName, t, body, owner, configPath, stage = 'uat') {
  try { return await journaled(t.n, stage, MODEL.verify, () => uatAgent(label, wtName, t, body, owner, configPath), undefined, uatStatus) }
  catch (e) { log(`${label} failed: ${e && e.message}`); return null }   // an infrastructure failure never fails the ticket
}

// The agent's passed_ac is a claim and must be exactly true (a missing value is not a pass): an AC row with FAIL also fails the run. Console errors are reported, never blocking: unrelated noise must not fail a ticket whose ACs pass.
const uatOk = res => res.passed_ac === true &&
  !(res.scenarios || []).some(s => s.kind === 'ac' && s.status === 'FAIL')

const uatNotRun = (n, reason) => addDecision(n, 'uat', {
  title: `UAT not run for #${n}`, context: `The UAT stage could not check the running app: ${reason}`,
  decision: 'Continue without UAT; the ticket stays done and the PR body says UAT did not run.',
  why: 'A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.',
  consequences: 'The running app was not checked against the original request.', how_to_reverse: `Run /harness:uat ${n} by hand.`,
  needs_review: true,
})

// Serial over the tickets: one app, one port. Returns n -> { status, reason, scenarios, fixed } for the PR body.
async function stageUat(delivered) {
  const records = {}
  if (LOCAL) { log('UAT skipped: local mode has no verify result'); return records }
  for (const r of delivered) {
    const t = tickets.find(x => x.n === r.n)
    const kind = r.verify && r.verify.kind
    if (!kind) { log(`UAT #${t.n} skipped: no verify result`); continue }
    if (kind === 'docs') { log(`UAT #${t.n} skipped: docs ticket`); continue }
    const cached = requestCache.get(t.n)
    if (!cached || !cached.fetched) { uatNotRun(t.n, 'the issue body could not be read'); records[t.n] = { status: 'not run', reason: 'issue body unreadable', scenarios: [] }; continue }
    const body = stripVerify(cached.body), owner = stripVerify(t.confirmed ? t.confirmed.trim() : '')
    log(`UAT #${t.n}: stripped ${body.count} line(s) from the body and ${owner.count} from the owner block`)
    const configPath = (r.verify && r.verify.configPath) || `${repoDir}/verify.config.json`
    const rec = { status: 'passed', reason: '', scenarios: [], fixed: false }
    records[t.n] = rec
    let res = await runUat(lbl(`#${t.n} UAT`, t.title), `uat-${t.n}`, t, body.text, owner.text, configPath)
    if (!res || res.status === 'blocked') {
      const why = (res && (res.blocked_reason || res.summary)) || 'the UAT agent returned nothing'
      uatNotRun(t.n, why); rec.status = 'not run'; rec.reason = why
      continue
    }
    takeDecisions(t.n, 'uat', res)
    rec.scenarios = res.scenarios || []
    if (!uatOk(res)) {
      const failing = rec.scenarios.filter(s => s.kind === 'ac' && s.status === 'FAIL')
      const fix = await fixAgent(lbl(`#${t.n} UAT fix`, t.title),
        `UAT on the running app found acceptance criteria of ticket #${t.n} that fail:\n${failing.map(s => `- ${s.covers}: ${s.assertion || s.id}`).join('\n') || '- (see the UAT summary) ' + (res.summary || '')}\nFix the code so the owner's request holds. Console errors are report-only: do not fix them unless a failing AC needs it.`,
        '', 'UAT', `uat-${t.n}`)
      takeDecisions(t.n, 'uat-fix', fix)
      rec.fixed = !!(fix && fix.fix_status === 'fixed')
      // No fix commit landed: a rerun would test the same code, so skip it and let the first result stand.
      const again = rec.fixed ? await runUat(lbl(`#${t.n} UAT rerun`, t.title), `uat-rerun-${t.n}`, t, body.text, owner.text, configPath, 'uat-rerun') : res   // own worktree: it must see the fix
      if (!rec.fixed) log(`UAT #${t.n}: fix ${fix && fix.fix_status || 'returned nothing'}, rerun skipped`)
      if (!again || again.status === 'blocked') {
        const why = (again && (again.blocked_reason || again.summary)) || 'the UAT rerun agent returned nothing'
        uatNotRun(t.n, `rerun: ${why}`); rec.status = 'not run'; rec.reason = `rerun: ${why}`
        continue
      }
      takeDecisions(t.n, 'uat-rerun', again)
      rec.scenarios = again.scenarios || rec.scenarios
      res = again
    }
    if (!uatOk(res)) {
      rec.status = 'failed'; rec.reason = 'UAT AC failed'
      r.status = 'blocked'; r.reason = 'UAT AC failed'   // code stays, the PR still opens, nothing is reverted
      addDecision(t.n, 'uat', {
        title: `UAT AC failed for #${t.n}`, context: 'An acceptance criterion still failed on the running app after one fix round and one rerun.',
        options: ['Mark the ticket blocked, keep the code', 'Revert the code', 'Ignore the failure'], decision: 'Mark the ticket blocked with reason "UAT AC failed" and keep the code.',
        why: 'The owner decided that an AC failure fails the ticket, with no revert.',
        consequences: 'The PR body says Refs instead of Closes for this ticket and the run output shows it blocked.', how_to_reverse: 'Fix the AC, then close the issue by hand.',
        needs_review: true,
      })
    }
    for (const f of res.non_ac_failures || []) addDecision(t.n, 'uat', {
      title: `UAT ${f.id} failed for #${t.n}`, context: `A negative or extra scenario failed on the running app: ${f.detail}`,
      decision: 'Continue the run; the owner decides.', why: 'Only an AC failure fails the ticket; a negative or extra failure is for the owner to review.',
      consequences: 'The behaviour that scenario covers may be wrong.', how_to_reverse: 'Fix the code the scenario exercises.', needs_review: true,
    })
  }
  return records
}

async function stageSuite() {
  const prompt = (label, cmd, only) => `${newWt(`suite-${label}`, null, finalRef).setup}${RULES}\n\n` +
    `Stage: verify. ${only ? `Re-run ONLY these failing tests: ${only.join(', ')} (use the narrowest command the project supports; ${testCmd} is the related-tests template).` : `Run the full suite: ${cmd}`}\n` +
    `Start the command in the background with its output going to a file, then poll that file until the process has exited. Never edit code or tests. ` +
    `Return the real counts of passed, failed and skipped tests from the output, the names of failing tests as failing, the exit code, and the last lines of output as tail.`
  const first = await call(prompt('run', fullTestCmd, null), { label: 'test · run full suite', phase: 'Testing', schema: SUITE_SCHEMA, model: MODEL.test, effort: EFFORT.test })
  if (!first) return { passed: 0, failed: 0, skipped: 0, note: 'the suite agent returned nothing' }
  if (!first.failed) return { passed: first.passed, failed: 0, skipped: first.skipped }
  const fix = await call(`${newWt('fix-suite', null, finalRef).setup}${RULES}\n\nStage: fix the failing tests of the final suite run, with minimal commits ("git add", then "git commit"). Failing: ${first.failing.join(', ')}\nOutput tail:\n${first.tail || ''}\n` +
    `Fix the code, not the test, unless the test itself is wrong. Run only the failing tests. Then land it: ${land(finalBranch)}`,
    { label: 'test · fix failing tests', phase: 'Testing', schema: stageSchema({}), model: MODEL.fix, effort: EFFORT.fix })
  takeDecisions('run', 'suite-fix', fix)
  const again = await call(prompt('rerun', fullTestCmd, first.failing), { label: 'test · rerun failed tests', phase: 'Testing', schema: SUITE_SCHEMA, model: MODEL.test, effort: EFFORT.test })
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
  const res = await call(prompt, { label: 'update run artifact', phase: 'Decisions', schema: ARTIFACT_SCHEMA, model: MODEL.adr, effort: EFFORT.adr })
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
    `Return adrs from .ship/written.json (number, path, needs_review, ticket, title). Do not commit anything under .ship.\n\nBody:\n${bodyTemplate}`
  const res = await call(prompt, { label: 'write ADRs (needs_review)', phase: 'Decisions', schema: ADR_SCHEMA, model: MODEL.adr, effort: EFFORT.adr })
  return res || { adrs: [], status: 'blocked', summary: 'the ADR agent returned nothing' }
}

// The script writes the PR body text; the ADR stage only substitutes {{DECISIONS}} and publishes it.
function buildBody(results, review, intent, suite, uat = {}, ci = null) {
  const done = results.filter(r => r.status === 'done')
  const open = results.filter(r => r.status !== 'done')
  const L = []
  // The final PR targets the base branch, so it is always a human merge (owner decision A). Values are pending until the final call.
  const pend = review.level === 'pending' || intent.verdict === 'pending'
  const nrCount = decisions.filter(d => d.needs_review).length
  const uatRowsAll = Object.values(uat)
  const uatG = !uatRowsAll.length ? { ok: false, text: 'n/a' }
    : { ok: uatRowsAll.every(u => u.status === 'passed' || u.status === 'pass'), text: [...new Set(uatRowsAll.map(u => u.status))].join(', ') }
  L.push('## Merge readiness', '', mergeBlock({ mode: 'human', why: `the PR targets ${base}; a human merges it`,
    ci: LOCAL ? { ok: false, text: 'n/a (local mode)' } : (ci || PENDING),
    review: pend ? PENDING : review.status === 'not run' ? { ok: false, text: `not run (${review.reason})` }
      : { ok: !review.notFixed.length && !review.leftover.some(f => f.score >= FIX_THRESHOLD), text: `${review.rounds} fix round(s), ${review.notFixed.length} not fixed, ${review.leftover.length} left` },
    intent: pend ? PENDING : { ok: intent.verdict === 'match', text: intent.verdict },
    adrs: pend ? PENDING : { ok: nrCount === 0, text: nrCount ? `${nrCount} (see Decisions)` : 'none' },
    uat: uatG }), '')
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
  const withVerify = results.filter(r => r.verify)
  if (withVerify.length) {
    L.push('', '## Verify', '')
    for (const r of withVerify) {
      const v = r.verify
      const baseText = v.base === 'failed' ? 'failed on base as required' : v.base === 'passed' ? 'passed on base (weak test)' : 'not run'
      const gifText = !v.gif ? 'not built' : v.attached ? 'built and attached' : 'built, not attached'
      L.push(`- ${ref(r.n)} ${v.kind}: ${v.result}; base: ${baseText}; stills: ${v.dir}; GIF: ${gifText}`)
    }
  }
  L.push('', '## Intent review', '', `Verdict: ${intent.verdict}${intent.fixRound ? ' (one fix round ran, not re-reviewed)' : ''}`)
  for (const g of intent.gaps) L.push(`- ${g.kind}${g.behaviour_changing ? ' (behaviour-changing)' : ''}: ${g.clause}: ${g.detail}`)
  const uatRows = Object.entries(uat).filter(([, u]) => u.scenarios.length || u.status === 'not run')
  if (uatRows.length) {
    L.push('', '## UAT sign-off', '', 'A human ticks these. Nothing enforces or waits on them.')
    for (const [n, u] of uatRows) {
      L.push(`- ${ref(Number(n))} UAT: ${u.status}${u.fixed ? ' (one fix round ran, not re-reviewed)' : ''}${u.reason ? ` (${u.reason})` : ''}`)
      for (const s of u.scenarios) L.push(`  - [ ] ${s.id} ${s.covers} (${s.kind}): ${s.status}${s.assertion ? `: ${s.assertion}` : ''}`)
    }
    L.push('- [ ] Copy reads right', '- [ ] Layout looks right', '- [ ] The flow feels right')
  }
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

try {
phase('Setup')
// The role files come from the plugin directory. call() falls back silently to the default agent
// when an agent type is missing, which would hide a wrong pluginDir, so check it once, up front.
const pluginCheck = await call(`Run: test -f ${pluginDir}/agents/implementer.md && test -f ${pluginDir}/scripts/write_adrs.py && echo found || echo missing\n\n${notCwd()}\nReturn status ok when the output is found, otherwise status blocked with blocked_reason "pluginDir ${pluginDir} does not hold the harness plugin". Edit nothing.`,
  { label: 'check plugin and tools', phase: 'Setup', schema: SETUP_SCHEMA, model: MODEL.cheap, effort: EFFORT.cheap })
if (!pluginCheck || pluginCheck.status === 'blocked') throw new Error(`ship: ${(pluginCheck && (pluginCheck.blocked_reason || pluginCheck.summary)) || 'the plugin check returned nothing'}`)
log(`ship ${tickets.map(t => `#${t.n}`).join(' ')} -> ${base}: ${tickets.length} ticket(s) in ${groups.length} group(s), ${single ? 'single: the ticket PR is the final PR' : `integration branch ${integBranch}`}${LOCAL ? ', local mode' : ''}`)
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
  // Only a ticket whose gate passed is merged (local mode has no PRs, so no gate). A single-ticket run never merges.
  const ready = done.filter(r => LOCAL || (r.gate && r.gate.pass))
  if (!single && ready.length) {
    phase('Merge')
    const m = await journaled('run', `merge-g${g}`, MODEL.merge, () => stageMerge(g, ready), undefined,
      res => (!res || (res.failed || []).length || !ready.every(r => (res.merged || []).includes(r.n)) ? 'failed' : 'ok'))
    const failed = (m && m.failed) || []
    for (const f of failed) {
      const r = byN.get(f.n)
      if (r) { r.status = 'blocked'; r.reason = `merge into ${integBranch} failed: ${f.reason}` }
      log(`#${f.n} blocked at merge: ${f.reason}`)
      await humanMergeBlock(f.n, r)
      if (!LOCAL && r && r.pr) addDecision(f.n, 'merge', {
        title: `Merge PR ${r.pr} by hand for #${f.n}`,
        context: `The gate passed for #${f.n}, but the merge of PR ${r.pr} into ${integBranch} failed: ${f.reason}`,
        decision: `After the cause above is fixed, run: gh pr merge ${r.pr} --repo ${repo} --merge. If the failure was a denied permission or the merge guard, merge it yourself in a terminal.`,
        why: 'The ship run cannot merge this PR itself. The merge stage never merges locally, pushes or closes the PR, so the PR is still open.',
        consequences: `Ticket #${f.n} stays blocked in this run until the PR is merged.`,
        how_to_reverse: 'Do not run the command; close the PR instead.',
        needs_review: true,
      })
    }
    // No answer, or a ticket the agent neither merged nor failed: the ticket stays open, so the PR body must say human.
    const unmerged = m ? ready.filter(r => !(m.merged || []).includes(r.n) && !failed.some(f => f.n === r.n)) : ready
    for (const r of unmerged) {
      r.status = 'blocked'
      r.reason = m ? `the merge agent did not report #${r.n} as merged or failed` : 'the merge agent returned nothing'
      await humanMergeBlock(r.n, r)
    }
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
  await writeSpecs({ byN, final: null, review: out.review, intent: out.intent, suite: out.suite, adrs: [] })
  out.tickets = ordered().map(publicTicket)
  await flushJournal()
  out.journal = journalRows
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

phase('UAT')
const uat = await stageUat(deliveredAll)
log(`UAT: ${Object.keys(uat).length} ticket(s) checked, ${Object.values(uat).filter(u => u.status === 'failed').length} failed`)

phase('Testing')
const suite = await journaled('run', 'suite', MODEL.test, () => stageSuite(), undefined, res => (!res || /returned nothing/.test(res.note || '') || res.failed > 0 ? 'failed' : 'ok'))
out.suite = suite
log(`full suite: ${suite.passed} passed, ${suite.failed} failed, ${suite.skipped} skipped`)

phase('Decisions')
const artifact = await stageArtifact(ordered())
out.artifact = artifact
const ciSnap = await stageCiSnapshot(finalPr)
const adr = await stageAdr(finalPr, artifact, buildBody(ordered(), review, intent, suite, uat, ciSnap))
takeDecisions('run', 'adr', adr)
out.adrs = (adr.adrs || []).map(a => ({ number: a.number, path: a.path, needsReview: !!a.needs_review }))
log(`decisions: ${decisions.length} recorded, ${out.adrs.length} ADR file(s)`)

await writeSpecs({ byN, final: out.final, review: out.review, intent: out.intent, suite: out.suite, adrs: adr.adrs || [] })

out.tickets = ordered().map(publicTicket)
await flushJournal()
out.journal = journalRows
out.worktrees = [...worktrees]
log(`worktrees created (the script never removes them; remove with git -C ${repoDir} worktree remove <dir>):\n${out.worktrees.join('\n')}`)
return out
} catch (e) {
  // A failed run is when the ledger matters most: write the rows collected so far, then rethrow.
  await flushJournal()
  throw e
}
