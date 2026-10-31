// Deterministic test harness for workflows/ship.js. No real agents run: agent() is a stub that
// records every call and answers from a scripted table. Output: one line per case,
// "PASS <name>" or "FAIL <name>: <why>"; exit 1 if any case failed.
//   node tests/workflows/harness.js
'use strict'
const fs = require('fs')
const path = require('path')
const assert = require('assert')

const SRC = fs.readFileSync(path.join(__dirname, '..', '..', 'plugins', 'harness', 'workflows', 'ship.js'), 'utf8')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

function metaText() {
  const start = SRC.indexOf('export const meta = ')
  assert(start >= 0, 'script must begin with export const meta')
  assert(SRC.slice(0, start).trim() === '', 'meta must be the first statement')
  let depth = 0, i = SRC.indexOf('{', start), inStr = null
  for (let j = i; j < SRC.length; j++) {
    const c = SRC[j]
    if (inStr) { if (c === '\\') j++; else if (c === inStr) inStr = null; continue }
    if (c === "'" || c === '"' || c === '`') { inStr = c; continue }
    if (c === '{') depth++
    if (c === '}' && --depth === 0) return SRC.slice(i, j + 1)
  }
  throw new Error('unterminated meta')
}

// ship.js labels agents for people to read ("#3 intent · Add the thing"); the scripted answers below
// and the assertions key on the stable role names, so the mock translates a display label back.
const FIXED_LABELS = {
  'write specs/ flow files': 'specs', 'write specs/ early': 'specs-early', 'set up integration branch': 'setup-integration', 'open final PR': 'final-pr',
  'measure diff size': 'diffstat', 'intent review · diff vs request': 'intent-review', 'test · run full suite': 'suite',
  'test · fix failing tests': 'suite-fix', 'test · rerun failed tests': 'suite-rerun', 'update run artifact': 'artifact',
  'CI snapshot': 'ci-snapshot', 'write ADRs (needs_review)': 'adr', 'check plugin and tools': 'plugin-check', 'intent fix · close gaps': 'intent-fix',
}
const TICKET_VERBS = {
  'post verify comment': 'verify-comment', 'record GIF': 'gif', 'attach evidence': 'attach', 'fetch owner request': 'request',
  'UAT fix': 'uat-fix', 'UAT rerun': 'uat-rerun', 'UAT': 'uat',
}
function legacyLabel(l) {
  if (l == null) return l
  let g
  if ((g = l.match(/^#(\d+) gate (.+)$/))) {   // per-ticket merge gate: keyed by role, then ticket
    const [, gn, what] = g
    let m
    if (what === 'measure diff size') return `gdiffstat:${gn}`
    if ((m = what.match(/^code-review · round (\d+)( retry)?$/))) return `greview:${gn}:r${m[1]}${m[2] ? ':retry' : ''}`
    if (what === 'code-review · intent fix') return `greview:${gn}:rif`
    if ((m = what.match(/^fix r(\d+)\.(\d+)/))) return `gfix:${gn}:r${m[1]}:${m[2]}`
    if (what.startsWith('intent review')) return `gintent:${gn}`
    if (what.startsWith('intent fix')) return `gintent-fix:${gn}`
    if (what === 'CI checks') return `gci:${gn}`
    if (what === 'PR body') return `gbody:${gn}`
  }
  const head = l.split(' · ')[0]
  if (FIXED_LABELS[l] || FIXED_LABELS[head]) return FIXED_LABELS[l] || FIXED_LABELS[head]
  let m
  if ((m = head.match(/^merge ticket branches$/))) return `merge:g${l.match(/group (\d+)/)[1]}`
  if ((m = head.match(/^code-review( retry)?$/)) || (m = l.match(/^code-review · round (\d+)( retry)?$/))) {
    const r = l.match(/round (\d+)( retry)?$/); return `review:r${r[1]}${r[2] ? ':retry' : ''}`
  }
  if ((m = head.match(/^fix r(\d+)\.(\d+)$/))) return `fix:r${m[1]}:${m[2]}`
  if ((m = head.match(/^#(\d+) advisor (.+)$/))) return `advisor:${m[2]}:${m[1]}`
  if ((m = head.match(/^#(\d+) (.+?)( retry)?$/))) {
    const verb = TICKET_VERBS[m[2]]
    if (verb) return `${verb}:${m[1]}`
    return `${m[2]}:${m[1]}${m[3] ? ':retry' : ''}`
  }
  return l
}

// ---- default scripted answers, keyed by label -----------------------------------------------
const ok = (extra) => ({ status: 'ok', summary: 'did it', decisions: [], ...extra })
function defaults(c, st) {
  const l = c.label || ''
  const n = (l.match(/:(\d+)(:retry)?$/) || [])[1]
  if (l.startsWith('advisor:')) return 'ADVICE-TEXT'
  if (l === 'setup-integration' || l === 'plugin-check') return ok()
  if (l.startsWith('intent:')) return ok({ goal: 'g', acceptance: [], files: [], plan_steps: [{ title: 'step', files: [], done_when: 'true' }] })
  if (l.startsWith('research:')) return ok({ research_md: 'RESEARCH' })
  if (l.startsWith('design:')) return ok({ design_md: 'DESIGN' })
  if (l.startsWith('plan:')) return ok({ plan_md: 'PLAN-MD', plan_steps: [] })
  if (l.startsWith('implement:')) return ok({ worktree: `/wt/${n}`, branch: `b${n}`, files: [], commits: [], verify: [] })
  if (/^verify(-retry|-base)?:/.test(l)) return ok({ passed: !l.startsWith('verify-base'), kind: 'BE', failedStep: '', consoleErrors: [], stills: [], report: 'VERIFY-REPORT' })
  if (l.startsWith('verify-comment:')) return ok()
  if (/^uat(-rerun)?:/.test(l)) return ok({ passed_ac: true, scenarios: [{ id: 'S1', covers: 'AC1', kind: 'ac', status: 'PASS', assertion: 'ok', still: '' }], non_ac_failures: [], console_errors: 0 })
  if (l.startsWith('uat-fix:')) return ok({ fix_status: 'fixed', base_sha: 'ubase', commit: 'ucommit' })
  if (l.startsWith('gif:')) return ok({ gif: '' })
  if (l.startsWith('attach:')) return ok()
  if (l.startsWith('finish:')) return ok({ pr: args0.local ? 0 : 100 + Number(n), url: `https://x/pull/${100 + Number(n)}` })
  if (l.startsWith('merge:')) return ok({ merged: [...c.prompt.matchAll(/^- #(\d+)/gm)].map(m => Number(m[1])), failed: [] })
  if (l === 'final-pr') return ok({ pr: args0.local ? 0 : 900, url: 'https://x/pull/900' })
  if (l.startsWith('gdiffstat:')) return { files: [{ path: 'src/a.js', added: 10, deleted: 2 }] }
  if (l.startsWith('greview:')) return ok({ findings: [], skill_invoked: true, skill_error: '' })
  if (l.startsWith('gfix:') || l.startsWith('gintent-fix:')) { st.fix++; st.tip = `gc${st.fix}`; return ok({ fix_status: 'fixed', base_sha: `gbase${st.fix}`, commit: `gc${st.fix}` }) }
  if (l.startsWith('gintent:')) return { verdict: 'match', findings: [] }
  if (l.startsWith('gci:')) return { checks: [{ name: 'harness-ci', bucket: 'pass' }], headRefOid: st.tip || `sha${n}abcdef` }
  if (l.startsWith('gbody:')) return ok()
  if (l === 'ci-snapshot') return { checks: [{ name: 'harness-ci', bucket: 'pass' }], headRefOid: 'finalsha' }
  if (l === 'diffstat') return { files: [{ path: 'src/a.js', added: 10, deleted: 2 }] }
  if (l.startsWith('review:')) return ok({ findings: [], skill_invoked: true, skill_error: '' })
  if (l.startsWith('fix:') || l === 'intent-fix') { st.fix++; return ok({ fix_status: 'fixed', base_sha: `base${st.fix}`, commit: `c${st.fix}` }) }
  if (l.startsWith('request:')) return { body: `REQUEST-BODY-${n}` }
  if (l === 'intent-review') return { verdict: 'match', findings: [] }
  if (l === 'suite') return { passed: 10, failed: 0, skipped: 1, failing: [] }
  if (l === 'suite-fix') return ok()
  if (l === 'suite-rerun') return { passed: 2, failed: 0, skipped: 0, failing: [] }
  if (l === 'artifact') return { created: false, fallback: 'docs/adr/' }
  if (l === 'adr') return ok({ adrs: [{ number: 2, path: 'docs/adr/0002-x.md', needs_review: true }] })
  if (l === 'specs' || l === 'specs-early') return ok()
  throw new Error(`no scripted answer for label '${l}'`)
}

let args0
function baseArgs(over) {
  return {
    repo: 'o/r', repoDir: '/repo', pluginDir: '/plug', remote: 'origin', base: 'v5.0.0', slug: 'ms',
    tickets: [{ n: 1, title: 'Add the thing', depth: 'S', group: 1, deps: [], confirmed: '' }],
    testCmd: 'run-related', lintCmd: 'lint-it', fullTestCmd: 'run-all', advisorModel: 'opus', noAsk: false, local: false, ...over,
  }
}

// override(call, state) may return a value (including null) or undefined to use the default.
async function run(over, override) {
  const args = baseArgs(over)
  args0 = args
  const calls = [], logs = [], st = { fix: 0 }
  const agent = async (prompt, opts = {}) => {
    const call = { prompt, opts, label: legacyLabel(opts.label), display: opts.label, schema: opts.schema }
    calls.push(call)
    if (override) {
      const v = override(call, calls, st)
      if (v !== undefined) { if (v instanceof Error) throw v; return v }
    }
    return defaults(call, st)
  }
  const parallel = thunks => Promise.all(thunks.map(async f => { try { return await f() } catch (e) { return null } }))
  const pipeline = async () => { throw new Error('pipeline is not used by ship.js') }
  const body = SRC.replace('export const meta =', 'const meta =')
  const fn = new AsyncFunction('agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow', body)
  const result = await fn(agent, parallel, pipeline, () => {}, m => logs.push(m), args, { total: null, spent: () => 0, remaining: () => Infinity }, async () => { throw new Error('no nested workflow') })
  return { result, calls, logs, args }
}

const labelsOf = calls => calls.map(c => c.label)
const named = (calls, re) => calls.filter(c => re.test(c.label || ''))
const T = (n, group, deps, extra) => ({ n, title: `Ticket ${n}`, depth: 'S', group, deps: deps || [], confirmed: '', ...extra })

const cases = []
const test = (name, fn) => cases.push({ name, fn })

test('meta is a pure literal', async () => {
  const text = metaText()
  const noStrings = text.replace(/'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"/g, '""')
  assert(!/[`()+]|\.\.\./.test(noStrings), 'meta contains a call, template, spread or operator')
  const noKeys = noStrings.replace(/\b[a-zA-Z_]+\s*:/g, '')
  assert(/^[\s{}\[\],"]*$/.test(noKeys), `meta contains an identifier or expression: ${noKeys.replace(/\s+/g, ' ').slice(0, 80)}`)
  assert(!/Date\.now|Math\.random|new Date\(\)/.test(SRC.replace(/\/\/.*$/gm, '')), 'forbidden nondeterministic call')
})

test('i1: the first log line names the tickets and the base', async () => {
  const multi = await run({ tickets: [T(1, 1), T(2, 1), T(3, 2, [1])] }, null)
  assert(multi.logs[0].startsWith('ship #1 #2 #3 -> v5.0.0:'), multi.logs[0])
  assert(multi.logs[0].includes('3 ticket(s)'), multi.logs[0])
  const one = await run({}, null)
  assert(one.logs[0].startsWith('ship #1 -> v5.0.0:'), one.logs[0])
})

test('a: one ticket has no integration or merge agent and a feat/<n>- branch', async () => {
  const { result, calls } = await run({}, null)
  const ls = labelsOf(calls)
  assert(!ls.includes('setup-integration') && !ls.some(l => l.startsWith('merge:')) && !ls.includes('final-pr'), ls.join())
  const impl = named(calls, /^implement:1$/)[0]
  assert(impl.prompt.includes('git -C /repo worktree add -b feat/1-add-the-thing /.ship-repo/ms/t1 origin/v5.0.0'), impl.prompt.slice(0, 300))
  assert.strictEqual(result.single, true)
  assert.strictEqual(result.final.branch, 'feat/1-add-the-thing')
  assert.strictEqual(result.final.pr, 101)
  assert(named(calls, /^finish:1$/)[0].prompt.includes('base v5.0.0'))
})

const noRepoTouch = /^(request:|artifact|final-pr)/
test('a2: no agent call uses isolation (it binds to the session cwd, not the target repo)', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], { depth: 'L' }), T(2, 1), T(3, 2, [1])] }, c => (c.label === 'suite' ? { passed: 1, failed: 1, skipped: 0, failing: ['t'] } : undefined))
  assert(calls.length > 15)
  for (const c of calls) assert(!('isolation' in c.opts), `${c.label} has isolation`)
})

test('b2: every repo-touching agent names the repo or a .ship- worktree and says the session cwd is not the repo', async () => {
  for (const local of [false, true]) {
    const { calls } = await run({ local, tickets: [T(1, 1, [], { depth: 'L' }), T(2, 1), T(3, 2, [1])] }, c => (c.label === 'suite' ? { passed: 1, failed: 1, skipped: 0, failing: ['t'] } : undefined))
    for (const c of calls) {
      if (noRepoTouch.test(c.label)) continue
      assert(c.prompt.includes('/repo') || c.prompt.includes('/.ship-repo/'), `${c.label}: no path`)
      assert(c.prompt.includes('Your session working directory is NOT the target repo'), `${c.label}: no cwd sentence`)
    }
    const wt = calls.filter(c => c.prompt.includes('worktree add') && !/^finish:/.test(c.label))
    assert(wt.length > 8)
    for (const c of wt) assert(c.prompt.includes('git -C /repo fetch origin') && c.prompt.includes(' /.ship-repo/ms/'), `${c.label}: ${c.prompt.slice(0, 120)}`)
  }
})

test('b3: the result lists the worktree dirs outside the repo', async () => {
  const { result } = await run({}, null)
  assert(result.worktrees.length > 3)
  for (const d of result.worktrees) assert(d.startsWith('/.ship-repo/ms/'), d)
  assert(result.worktrees.includes('/.ship-repo/ms/t1'))
})

test('c4: skill and role reads use absolute paths under pluginDir, not the worktree or .claude', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], { depth: 'L' })] }, null)
  const want = { 'research:1': 'xia2', 'design:1': 'brainstorming', 'plan:1': 'writing-plans', 'implement:1': 'implement' }
  for (const [l, sk] of Object.entries(want)) {
    const p = named(calls, new RegExp(`^${l}$`))[0].prompt
    assert(p.includes(`Read /plug/skills/${sk}/SKILL.md`) && !/\.claude\/(?!rules\/)/.test(p), `${l}: ${p.match(/Read [^\n]*/)}`)
    assert(!/Read skills\//.test(p), l)
  }
  const fin = named(calls, /^finish:1$/)[0].prompt
  assert(fin.includes('Read /plug/skills/finishing-a-development-branch/SKILL.md'), fin.match(/Read [^\n]*/)[0])
  assert(named(calls, /^implement:1$/)[0].prompt.includes('/plug/agents/implementer.md') && !/\.claude\/(?!rules\/)/.test(named(calls, /^implement:1$/)[0].prompt))
})

test('d3: review stage prompts require the Skill tool and forbid a self-made review', async () => {
  const { calls } = await run({}, null)
  const p = named(calls, /^review:r0$/)[0].prompt
  assert(p.includes("skill 'code-review'") && p.includes('Do not substitute your own review') && p.includes('reading the diff yourself does not count') && p.includes('skill_invoked: false'))
})

test('d4: code-review not run: one retry with the error, then NOT RUN, a needs_review decision, no fix', async () => {
  const { result, calls } = await run({}, c => {
    if (c.label === 'review:r0') return ok({ findings: [{ id: 'x', summary: 's', score: 90 }], skill_invoked: false, skill_error: 'Skill tool unavailable' })
    if (c.label === 'review:r0:retry') return ok({ findings: [], skill_invoked: false, skill_error: 'still unavailable' })
  })
  assert.strictEqual(named(calls, /^review:/).length, 2, labelsOf(calls).join())
  assert(named(calls, /^review:r0:retry$/)[0].prompt.includes('Skill tool unavailable'))
  assert(named(calls, /^review:r0:retry$/)[0].prompt.includes('Do not substitute your own review'))
  assert.strictEqual(named(calls, /^fix:/).length, 0, 'no fix when the review did not run')
  assert.strictEqual(result.review.status, 'not run')
  const d = result.decisions.find(x => /^Review skipped: code-review did not run \(still unavailable\)/.test(x.title))
  assert(d && d.needs_review === true, JSON.stringify(result.decisions.map(x => x.title)))
  const body = named(calls, /^adr$/)[0].prompt
  assert(body.includes('Review: NOT RUN (still unavailable)'))
  assert(!body.includes('0 findings') && !body.includes('Level low'))
  assert(labelsOf(calls).includes('intent-review') && labelsOf(calls).includes('suite'), 'the pipeline continues')
})

test('d5: a retry that runs the skill is used; findings then behave as before', async () => {
  const { result, calls } = await run({}, c => {
    if (c.label === 'review:r0') return ok({ findings: [], skill_invoked: false, skill_error: 'boom' })
    if (c.label === 'review:r0:retry') return ok({ findings: [{ id: 'f', path: 'a.js', summary: 'S-f', score: 80 }], skill_invoked: true })
  })
  assert.strictEqual(result.review.status, 'ran')
  assert.strictEqual(named(calls, /^fix:/).length, 1)
  assert(!named(calls, /^adr$/)[0].prompt.includes('NOT RUN'))
})

test('d6: a re-review that does not run is reported, not treated as clean', async () => {
  const { result, calls } = await run({}, c => {
    if (c.label === 'review:r0') return ok({ findings: [{ id: 'f', summary: 'S-f', score: 80 }], skill_invoked: true })
    if (/^review:r1/.test(c.label)) return ok({ findings: [], skill_invoked: false, skill_error: 'gone' })
  })
  assert.strictEqual(result.review.status, 'ran')
  assert(named(calls, /^adr$/)[0].prompt.includes('Re-review of the fix commits: NOT RUN (gone)'))
  assert(result.decisions.some(d => d.needs_review && /^Review skipped/.test(d.title)))
})

test('e4: RULES and the decision schema carry the needs_review criteria', async () => {
  const { calls } = await run({}, null)
  const p = named(calls, /^intent:1$/)[0].prompt
  assert(p.includes('needs_review: true ONLY when the decision affects another ticket, a public contract or interface, stored data, security or cost, or is a trade-off that is costly to reverse, or contradicts the ticket text or an owner-confirmed answer'))
  assert(p.includes('needs_review: false'))
  const dec = named(calls, /^intent:1$/)[0].schema.properties.decisions.items.properties.needs_review
  assert(/ONLY when/.test(dec.description) && /false/.test(dec.description))
})

test('e5: owner_confirmed wording in RULES and schema says needs_review still gets an ADR file', async () => {
  const { calls } = await run({}, null)
  const c = named(calls, /^intent:1$/)[0]
  assert(c.prompt.includes('no ADR file unless it also has needs_review: true'), 'RULES omit the needs_review exception')
  const oc = c.schema.properties.decisions.items.properties.owner_confirmed.description
  assert(/unless needs_review is also true/.test(oc), 'schema omits the needs_review exception')
})

test('e7: RULES gives one source for project rules, not the owner checkout and the worktree at once', async () => {
  const { calls } = await run()
  const c = calls.find(x => x.prompt.includes('Rules (all of them apply)'))
  assert(c.prompt.includes('read the tracked ones (CLAUDE.md, .claude/rules/*.md) from it'), 'no worktree-first rule')
  assert(!c.prompt.includes('read the same files at the same relative paths'), 'old contradictory sentence is back')
  assert(c.prompt.includes('/repo/CLAUDE.local.md'), 'untracked CLAUDE.local.md source missing')
  assert(c.prompt.includes('git -C /repo status --porcelain -- CLAUDE.md .claude/rules'), 'uncommitted rule edits in the owner checkout are not covered')
})

test('e8: the project-rules text lives in one place (rulesCommon) and names the repoDir paths', async () => {
  const src = require('fs').readFileSync(require('path').join(__dirname, '../../plugins/harness/workflows/ship.js'), 'utf8')
  assert(!/Project rule files:/.test(src), 'second copy of the project-rules text is back in RULES')
  assert(/const rulesCommon = repoDir =>/.test(src), 'rulesCommon is not a function of repoDir')
  const { calls } = await run()
  const c = calls.find(x => x.prompt.includes('Rules (all of them apply)'))
  assert(c.prompt.includes('Read /repo/CLAUDE.md, /repo/CLAUDE.local.md'), 'RULES_COMMON text does not name repoDir')
  assert(!c.prompt.includes('from the repo root'), 'vague repo-root wording is back')
})

test('e6: every stage prompt tells the agent to read the repo CLAUDE.md and .claude/rules', async () => {
  const { calls } = await run({}, null)
  const staged = calls.filter(c => !String(c.label).startsWith('advisor:') && c.prompt.includes('Rules (all of them apply)'))
  assert(staged.length > 3, 'too few stage prompts carry RULES')
  for (const c of staged) {
    assert(c.prompt.includes('/repo/CLAUDE.md'), `${c.label} omits /repo/CLAUDE.md`)
    assert(c.prompt.includes('/repo/.claude/rules/'), `${c.label} omits /repo/.claude/rules/`)
    assert(c.prompt.includes('cannot be overridden by project rules'), `${c.label} omits the hard-rule exception`)
  }
})

test('g1: a multi-ticket intent plans against the integration ref, not the repo checkout; decisions exclude environment facts', async () => {
  const multi = await run({ local: true, tickets: [T(1, 1), T(2, 2, [1])] }, null)
  const p = named(multi.calls, /^intent:2$/)[0].prompt
  assert(/Plan against the code as it is on /.test(p) && /is NOT that code/.test(p), 'intent:2 does not name the integration ref')
  const single = await run({ local: true, tickets: [T(1, 1)] }, null)
  assert(!/is NOT that code/.test(named(single.calls, /^intent:1$/)[0].prompt))
  assert(p.includes('Facts about the environment') && p.includes('are not decisions'))
})

test('f2: local mode PR body has no Closes or Refs and uses Ticket n', async () => {
  const { calls } = await run({ local: true, tickets: [T(1, 1), T(2, 2, [1])] }, c => (c.label === 'implement:2' ? ok({ status: 'blocked', blocked_reason: 'x', worktree: '', branch: '' }) : undefined))
  const body = named(calls, /^adr$/)[0].prompt
  assert(!/Closes|Refs/.test(body), 'local body mentions Closes/Refs')
  assert(body.includes('Ticket 1'))
  const rem = await run({ tickets: [T(1, 1)] }, null)
  assert(named(rem.calls, /^adr$/)[0].prompt.includes('Closes #1'))
})

test('g3: intent review schema has no unknown kind; its prompt names the role file and the worktree diff', async () => {
  const { calls } = await run({}, null)
  const c = named(calls, /^intent-review$/)[0]
  assert.deepStrictEqual(c.schema.properties.findings.items.properties.kind.enum, ['gap', 'drift', 'excess'])
  assert(c.prompt.includes('/plug/agents/intent-reviewer.md') && !/\.claude\/(?!rules\/)/.test(c.prompt))
  assert(c.prompt.includes('git -C /.ship-repo/ms/intent-review diff origin/v5.0.0..origin/feat/1-add-the-thing'))
  assert(c.prompt.includes('Do not report anything else'))
  assert(c.prompt.includes('worktree add --detach /.ship-repo/ms/intent-review'))
})

test('h2: the per-ticket summary is capped and shows no raw agent narration of pushes', async () => {
  const long = 'x'.repeat(500)
  const { calls, result } = await run({}, c => (c.label === 'implement:1' ? ok({ worktree: '/wt/1', branch: 'b1', summary: long }) : c.label === 'finish:1' ? ok({ pr: 101, url: 'u', summary: 'Nothing was pushed and no PR was opened' }) : undefined))
  const body = named(calls, /^adr$/)[0].prompt
  assert(body.includes('- #1 done: ' + 'x'.repeat(199) + '…'))
  assert(!body.includes('x'.repeat(201)) && !body.includes('Nothing was pushed'))
  assert(result.tickets[0].summary.length <= 200)
  const sd = named(calls, /^intent:1$/)[0].schema.properties.summary.description
  assert(/pushes/.test(sd) && /test counts/.test(sd))
})

test('b: three tickets, groups 1,1,2: setup, parallel, merge, group 2, merge, one final PR', async () => {
  const { result, calls } = await run({ tickets: [T(1, 1), T(2, 1), T(3, 2, [1])] }, null)
  const ls = labelsOf(calls)
  const at = l => ls.indexOf(l)
  assert.strictEqual(at('plugin-check'), 0); assert.strictEqual(at('setup-integration'), 1)
  assert(at('intent:2') < at('implement:1'), 'group 1 tickets run in parallel')
  assert(at('finish:1') < at('merge:g1') && at('finish:2') < at('merge:g1'))
  assert(at('merge:g1') < at('intent:3'), 'group 2 starts after the merge')
  assert(at('finish:3') < at('merge:g2') && at('merge:g2') < at('final-pr'))
  assert.strictEqual(named(calls, /^final-pr$/).length, 1)
  assert(named(calls, /^implement:3$/)[0].prompt.startsWith('git -C /repo fetch origin\ngit -C /repo worktree add -b feat/ms-3 /.ship-repo/ms/t3 origin/feat/ms'))
  assert(named(calls, /^finish:1$/)[0].prompt.includes('base feat/ms'))
  assert(named(calls, /^final-pr$/)[0].prompt.includes('--base v5.0.0 --head feat/ms'))
  assert.deepStrictEqual(result.tickets.map(t => t.status), ['done', 'done', 'done'])
  assert.strictEqual(result.final.branch, 'feat/ms')
  const body = named(calls, /^adr$/)[0].prompt
  for (const n of [1, 2, 3]) assert(body.includes(`Closes #${n}`))
})

test('b2: the merge prompt counts an already MERGED PR as merged and names the permission on a denial', async () => {
  const { calls } = await run({ tickets: [T(1, 1), T(2, 1)] }, null)
  const p = named(calls, /^merge:g1$/)[0].prompt
  assert(/already MERGED into feat\/ms counts as merged/.test(p), p)
  assert(p.includes('gh pr view <pr> --repo o/r --json state') && p.includes('do not merge it again'))
  assert(p.includes('names the denial') && p.includes('allows gh pr merge into feat/ms*'))
  const l = await run({ tickets: [T(1, 1), T(2, 1)], local: true }, null)
  assert(!named(l.calls, /^merge:g1$/)[0].prompt.includes('gh pr view'), 'local mode has no PRs')
})

test('b3: the merge prompt says each command is its own call and names gh pr merge as one', async () => {
  const { calls } = await run({ tickets: [T(1, 1), T(2, 1)] }, null)
  const p = named(calls, /^merge:g1$/)[0].prompt
  assert(p.includes('each command as its own Bash call, never joined with &&, ; or a subshell'), p)
  assert(p.includes('gh pr merge <pr> --repo o/r --merge --match-head-commit <head>'), p)
})

test('b4b: a failed merge rewrites the PR body block from Merge: auto to Merge: human', async () => {
  const stub = c => { if (c.label === 'merge:g1') return ok({ merged: [2], failed: [{ n: 1, reason: 'head mismatch' }] }) }
  const { calls } = await run({ tickets: [T(1, 1), T(2, 1)] }, stub)
  const b = named(calls, /^merge failed:1$/)
  assert.strictEqual(b.length, 1, JSON.stringify(calls.map(c => c.label)))
  assert(b[0].prompt.includes('Merge: human') && b[0].prompt.includes('merge into') && !b[0].prompt.includes('Merge: auto'), b[0].prompt)
})

test('b4c: a null merge result rewrites every ready PR body to Merge: human', async () => {
  const stub = c => { if (c.label === 'merge:g1') return null }
  const { calls, result } = await run({ tickets: [T(1, 1), T(2, 1)] }, stub)
  for (const n of [1, 2]) {
    const b = named(calls, new RegExp(`^merge failed:${n}$`))
    assert.strictEqual(b.length, 1, JSON.stringify(calls.map(c => c.label)))
    assert(b[0].prompt.includes('Merge: human') && !b[0].prompt.includes('Merge: auto'), b[0].prompt)
  }
  assert.strictEqual(result.tickets.find(t => t.n === 1).status, 'blocked')
})

test('b4: a failed merge gives a needs_review decision with the exact command; local mode gives none', async () => {
  const stub = c => { if (c.label === 'merge:g1') return ok({ merged: [2], failed: [{ n: 1, reason: 'denied by a permission rule' }] }) }
  const { result } = await run({ tickets: [T(1, 1), T(2, 1)] }, stub)
  const d = result.decisions.filter(x => x.stage === 'merge')
  assert.strictEqual(d.length, 1, JSON.stringify(d))
  assert.strictEqual(d[0].ticket, 1)
  assert(d[0].decision.includes('run: gh pr merge 101 --repo o/r --merge.'), d[0].decision)
  assert(d[0].context.includes('The gate passed for #1') && !d[0].decision.includes('may have landed it by hand'), d[0].context)
  assert.strictEqual(d[0].needs_review, true)
  assert(d[0].context.includes('denied by a permission rule'))
  assert.strictEqual(result.tickets.find(t => t.n === 1).status, 'blocked')
  const l = await run({ tickets: [T(1, 1), T(2, 1)], local: true }, stub)
  assert.strictEqual(l.result.decisions.filter(x => x.stage === 'merge').length, 0)
  assert.strictEqual(l.result.tickets.find(t => t.n === 1).status, 'blocked')
})

// ---- #516 merge policy: per-ticket gate, gated merge, PR body block ------------------------------
const gateFlow = (over, ovr) => run({ tickets: [T(1, 1), T(2, 1)], ...over }, ovr)
const mergePrompt = calls => (named(calls, /^merge:g1$/)[0] || {}).prompt
const t1 = r => r.result.tickets.find(t => t.n === 1)
const failingCi = checks => c => { if (c.label === 'gci:1') return { checks, headRefOid: 'sha1abcdef' } }

test('g1: a passing gate runs review, intent review and CI in order, edits the PR body to Merge: auto, then merges the head it judged', async () => {
  const r = await gateFlow({})
  const order = r.calls.map(c => c.label).filter(l => /^g(diffstat|review|intent|ci|body):1/.test(l || ''))
  assert.deepStrictEqual(order, ['gdiffstat:1', 'greview:1:r0', 'gintent:1', 'gci:1', 'gbody:1'])
  assert.strictEqual(t1(r).status, 'done')
  const body = named(r.calls, /^gbody:1$/)[0].prompt
  assert(body.includes('Merge: auto') && !body.includes('Merge: auto (pending'), body)
  assert(body.includes('- [x] CI:') && body.includes('- [x] Review:') && body.includes('- [x] Intent:') && body.includes('- [x] needs_review ADRs: none'), body)
  const mp = mergePrompt(r.calls)
  assert(mp.includes('- #1 branch b1 PR 101 head sha1abcdef') && mp.includes('- #2 branch b2 PR 102 head sha2abcdef'), mp)
  const ci = named(r.calls, /^gci:1$/)[0].prompt
  assert(ci.includes('gh pr checks 101 --repo o/r --watch --interval 30') && ci.includes('600000') && ci.includes('--json name,bucket'), ci)
})

const gateFails = [
  ['ci: a failing check', 'ci', failingCi([{ name: 'x', bucket: 'fail' }])],
  ['ci: no checks at all fails closed', 'ci', failingCi([])],
  ['ci: a check still pending fails', 'ci', failingCi([{ name: 'x', bucket: 'pass' }, { name: 'y', bucket: 'pending' }])],
  ['ci: only skipped checks fail', 'ci', failingCi([{ name: 'x', bucket: 'skipping' }])],
  ['ci: the agent returned nothing', 'ci', c => (c.label === 'gci:1' ? null : undefined)],
  ['review: a finding that cannot be fixed', 'review', c => {
    if (c.label === 'greview:1:r0') return ok({ findings: [{ id: 'f1', summary: 'bug', score: 80, path: 'a.js', line: 3 }], skill_invoked: true })
    if (c.label === 'gfix:1:r1:1') return ok({ fix_status: 'failed' })
  }],
  ['review: a finding at 50 or more is left after the fix rounds', 'review', c => {
    if (/^greview:1:r\d$/.test(c.label)) return ok({ findings: [{ id: 'f1', summary: 'bug', score: 60 }], skill_invoked: true })
  }],
  ['review: the skill did not run', 'review', c => { if (/^greview:1/.test(c.label)) return ok({ findings: [], skill_invoked: false, skill_error: 'no skill' }) }],
  ['intent: verdict is not match', 'intent', c => { if (c.label === 'gintent:1') return { verdict: 'gaps found', findings: [{ kind: 'excess', clause: 'c', detail: 'd' }] } }],
  ['needs_review: the ticket has an open needs_review decision', 'needs_review', c => {
    if (c.label === 'implement:1') return ok({ worktree: '/wt/1', branch: 'b1', files: [], commits: [], verify: [],
      decisions: [{ title: 'Pick a thing', context: 'c', options: ['a', 'b'], decision: 'a', why: 'w', consequences: 'x', how_to_reverse: 'y', confidence: 'low', needs_review: true }] })
  }],
]
for (const [name, gate, ovr] of gateFails) {
  test(`g2: gate fails (${name}): the ticket stays open as a human merge, its PR is kept, the other ticket still merges`, async () => {
    const r = await gateFlow({}, ovr)
    const a = t1(r)
    assert.strictEqual(a.status, 'blocked')
    assert(a.reason.startsWith('human merge: gate ') && a.reason.includes(gate), a.reason)
    assert.strictEqual(a.pr, 101, 'the PR number is kept')
    const mp = mergePrompt(r.calls)
    assert(mp.includes('- #2 ') && !mp.includes('- #1 '), mp)
    const d = r.result.decisions.filter(x => x.stage === 'merge' && x.ticket === 1)
    assert.strictEqual(d.length, 1, JSON.stringify(d))
    assert(d[0].needs_review && d[0].decision.includes('gh pr merge 101 --repo o/r --merge') && d[0].title.includes(gate), JSON.stringify(d[0]))
    const body = named(r.calls, /^gbody:1$/)[0].prompt
    assert(body.includes('Merge: human') && body.includes(`gate ${gate}`), body)
    assert(r.result.final && r.result.final.pr === 900, 'the final PR is still opened')
  })
}

test('g3: a gate stops the CI wait when review already failed, and a throwing gate blocks the ticket with the PR kept', async () => {
  const r = await gateFlow({}, c => { if (/^greview:1/.test(c.label)) return ok({ findings: [], skill_invoked: false, skill_error: 'e' }) })
  assert.strictEqual(named(r.calls, /^gci:1$/).length, 0, 'no CI wait after a failed gate')
  const x = await gateFlow({}, c => { if (c.label === 'gdiffstat:1') return new Error('boom') })
  assert.strictEqual(t1(x).status, 'blocked')
  assert.strictEqual(t1(x).pr, 101)
})

test('g4: a single-ticket run has no gate and never calls the merge stage; local mode has no gate either', async () => {
  const s = await run({}, null)
  assert(!s.calls.some(c => /^g(diffstat|review|intent|ci|body):/.test(c.label || '')), 'no gate in a single run')
  assert.strictEqual(named(s.calls, /^merge:/).length, 0)
  const l = await gateFlow({ local: true }, null)
  assert(!l.calls.some(c => /^g(diffstat|review|intent|ci|body):/.test(c.label || '')), 'no gate in local mode')
  assert.strictEqual(named(l.calls, /^merge:g1$/).length, 1, 'local mode still merges its branches')
  assert(mergePrompt(l.calls).includes('git merge --abort'))
})

test('g5: the remote merge prompt has no conflict path: no local merge, no push, no PR close', async () => {
  const p = mergePrompt((await gateFlow({})).calls)
  assert(!/git push|git merge|git update-ref|close that PR|resolve it/.test(p), p)
  assert(p.includes('do not merge locally, do not push, do not close the PR'), p)
})

test('g6: gate review, fix and intent stages work on the ticket ref and branch; decisions are recorded under the ticket', async () => {
  const r = await gateFlow({}, c => {
    if (c.label === 'greview:1:r0') return ok({ findings: [{ id: 'f1', summary: 'bug', score: 80, path: 'a.js', line: 3 }], skill_invoked: true,
      decisions: [{ title: 'Review note', context: 'c', options: ['a'], decision: 'a', why: 'w', consequences: 'x', how_to_reverse: 'y', confidence: 'high', needs_review: false }] })
    if (c.label === 'greview:1:r1') return ok({ findings: [], skill_invoked: true })
  })
  const rev = named(r.calls, /^greview:1:r0$/)[0].prompt
  assert(rev.includes('origin/feat/ms...origin/b1') && rev.includes('origin/b1 is checked out'), rev)
  const fix = named(r.calls, /^gfix:1:r1:1$/)[0].prompt
  assert(fix.includes('git push origin HEAD:b1') && fix.includes('Boundary (ticket #1)') && !fix.includes('union over the tickets'), fix)
  const intent = named(r.calls, /^gintent:1$/)[0].prompt
  assert(intent.includes('Diff range: origin/feat/ms..origin/b1'), intent)
  const note = r.result.decisions.filter(d => d.title === 'Review note')
  assert(note.length === 1 && note[0].ticket === 1, JSON.stringify(note))
  // the final cross-ticket review is unchanged: it still reviews the integration branch under 'run'
  const fin = named(r.calls, /^review:r0$/)[0].prompt
  assert(fin.includes('origin/feat/ms is checked out') && fin.includes('baseRef') === false, fin)
})

test('g7: every gate agent gets its own worktree dir, distinct from the other ticket and from the final review', async () => {
  const r = await gateFlow({}, null)
  const dirOf = c => (c.prompt.match(/Your worktree is (\S+)\.\s/) || [])[1]
  const gate = r.calls.filter(c => /^g(diffstat|review|intent):/.test(c.label || '')).filter(c => dirOf(c))
  const dirs = gate.map(dirOf)
  assert(dirs.length >= 4, `expected review and intent worktrees for two tickets, got ${dirs}`)
  assert.strictEqual(new Set(dirs).size, dirs.length, dirs.join('\n'))
  const finalDirs = r.calls.filter(c => /^(review:r0|intent-review)$/.test(c.label || '')).map(dirOf)
  for (const d of finalDirs) assert(!dirs.includes(d), `final stage reuses a gate worktree: ${d}`)
})

test('g8: an intent fix is reviewed before the gate passes; a second intent fix fails the gate', async () => {
  let n = 0
  const gaps = { verdict: 'gaps found', findings: [{ kind: 'gap', clause: 'c', detail: 'd' }] }
  const r = await gateFlow({}, c => { if (c.label === 'gintent:1') { n++; return n === 1 ? gaps : { verdict: 'match', findings: [] } } })
  assert(named(r.calls, /^greview:1:rif$/).length === 1, 'the intent fix range is reviewed')
  assert.strictEqual(t1(r).status, 'done')
  const r2 = await gateFlow({}, c => { if (c.label === 'gintent:1') return gaps })
  assert.strictEqual(t1(r2).status, 'blocked')
  assert(t1(r2).reason.includes('review') && t1(r2).reason.includes('intent'), t1(r2).reason)
  const r3 = await gateFlow({}, c => {
    if (c.label === 'greview:1:rif') return ok({ findings: [{ id: 'z', summary: 'bad fix', score: 90 }], skill_invoked: true })
    if (c.label === 'gintent:1') return n++ === 99 ? undefined : { verdict: 'match', findings: [{ kind: 'gap', clause: 'c', detail: 'd' }] }
  })
  assert.strictEqual(t1(r3).status, 'blocked')
})

test('g9: the finish prompt carries the pending merge block; a single-ticket PR says Merge: human', async () => {
  const multi = await gateFlow({}, null)
  const f = named(multi.calls, /^finish:1$/)[0].prompt
  assert(f.includes('<!-- merge-policy -->') && f.includes('Merge: auto (pending gates)') && f.includes('<!-- /merge-policy -->'), f)
  const one = await run({}, null)
  const g = named(one.calls, /^finish:1$/)[0].prompt
  assert(g.includes('Merge: human') && !g.includes('Merge: auto'), g)
})

test('g10: the final PR body always says Merge: human and lists the five readiness rows; local mode shows CI as n/a', async () => {
  for (const local of [false, true]) {
    const r = await gateFlow({ local }, null)
    const pre = named(r.calls, /^final-pr$/)[0].prompt
    assert(pre.includes('Merge: human') && pre.includes(local ? 'CI: n/a (local mode)' : '- [ ] CI: pending'), pre.slice(-1500))
    const adr = named(r.calls, /^adr$/)[0].prompt
    assert(adr.includes('Merge: human') && !adr.includes('Merge: auto'), adr.slice(-1500))
    for (const row of ['CI:', 'Review:', 'Intent:', 'needs_review ADRs:', 'UAT:']) assert(adr.includes(`] ${row}`), `${row} missing in\n${adr}`)
    if (local) assert(adr.includes('CI: n/a (local mode)'), adr)
    else assert(adr.includes('CI: 1 pass'), adr)
  }
})

test('c: needs_advisor triggers one advisor call and one stage re-run; a second request is ignored', async () => {
  let intents = 0
  const { calls } = await run({ advisorModel: 'fable' }, c => {
    if (/^intent:1/.test(c.label)) { intents++; return { ...defaults(c, {}), needs_advisor: true, advisor_question: 'Q-ONE' } }
  })
  const adv = named(calls, /^advisor:/)
  assert.strictEqual(adv.length, 1, labelsOf(calls).join())
  assert.strictEqual(adv[0].opts.model, 'fable')
  assert.strictEqual(adv[0].opts.agentType, 'harness:advisor')
  assert.strictEqual(adv[0].opts.effort, 'high')
  assert(adv[0].prompt.includes('Q-ONE'))
  assert.strictEqual(intents, 2)
  assert.strictEqual(named(calls, /^intent:1:retry$/).length, 1)
  assert(named(calls, /^intent:1:retry$/)[0].prompt.includes('ADVICE-TEXT'))
})

test('c2: depth L gets one advisor call on design and plan before implement', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], { depth: 'L' })] }, null)
  const ls = labelsOf(calls)
  assert.strictEqual(named(calls, /^advisor:plan-review:1$/).length, 1, ls.join())
  assert(ls.indexOf('advisor:plan-review:1') < ls.indexOf('implement:1'))
  assert(ls.indexOf('research:1') < ls.indexOf('design:1') && ls.indexOf('design:1') < ls.indexOf('plan:1'))
  assert(named(calls, /^implement:1$/)[0].prompt.includes('ADVICE-TEXT'))
})

test('c3: an unknown agent type falls back to the default agent with the role file', async () => {
  const { calls, result } = await run({}, c => (c.opts.agentType === 'harness:intent-reviewer' ? new Error('unknown agent type') : undefined))
  const rr = named(calls, /^intent-review$/)
  assert.strictEqual(rr.length, 2)
  assert(!rr[1].opts.agentType && rr[1].prompt.includes('/plug/agents/intent-reviewer.md'))
  assert.strictEqual(result.intent.verdict, 'match')
})

test('d: a blocked ticket does not stop siblings and its dependents are skipped', async () => {
  const { result, calls, logs } = await run({ tickets: [T(1, 1), T(2, 1), T(3, 2, [1]), T(4, 2, [2])] },
    c => (c.label === 'implement:1' ? ok({ status: 'blocked', blocked_reason: 'cannot build', worktree: '', branch: '' }) : undefined))
  const by = Object.fromEntries(result.tickets.map(t => [t.n, t]))
  assert.strictEqual(by[1].status, 'blocked'); assert(by[1].reason.includes('cannot build'))
  assert.strictEqual(by[2].status, 'done')
  assert.strictEqual(by[3].status, 'skipped'); assert(by[3].reason.includes('#1'))
  assert.strictEqual(by[4].status, 'done')
  assert(!labelsOf(calls).some(l => /:3$/.test(l)), 'a skipped ticket must run no agent')
  assert(logs.some(m => m.includes('#3 skipped')))
  assert(named(calls, /^merge:g1$/)[0].prompt.includes('- #2') && !named(calls, /^merge:g1$/)[0].prompt.includes('- #1'))
  const body = named(calls, /^adr$/)[0].prompt
  assert(body.includes('Closes #2') && body.includes('Refs #1') && !body.includes('Closes #1'))
})

test('d2: a decision that contradicts a confirmed answer blocks the ticket', async () => {
  const bad = { title: 'T', context: 'c', options: ['a'], decision: 'd', why: 'w', consequences: 'x', how_to_reverse: 'r', confidence: 'high', needs_review: true, contradicts_confirmed: true }
  const { result, calls } = await run({}, c => (c.label === 'intent:1' ? ok({ decisions: [bad] }) : undefined))
  assert.strictEqual(result.tickets[0].status, 'blocked')
  assert(!labelsOf(calls).includes('implement:1'))
})

test('e: review loop fixes findings >= threshold, re-reviews the fix diff only, caps at 2 rounds', async () => {
  const F = (id, score, pre) => ({ id, path: 'a.js', line: 1, summary: `S-${id}`, score, pre_existing: !!pre })
  const { result, calls } = await run({}, c => {
    if (c.label === 'review:r0') return ok({ skill_invoked: true, findings: [F('f1', 80), F('f2', 60), F('f3', 30), F('f4', 90, true)] })
    if (c.label === 'review:r1') return ok({ skill_invoked: true, findings: [F('f5', 70)] })
    if (c.label === 'review:r2') return ok({ skill_invoked: true, findings: [F('f6', 75)] })
  })
  assert.strictEqual(named(calls, /^fix:/).length, 3, labelsOf(calls).join())
  assert.strictEqual(named(calls, /^review:/).length, 3)
  const ls = labelsOf(calls)
  assert(ls.indexOf('fix:r1:1') < ls.indexOf('fix:r1:2') && ls.indexOf('fix:r1:2') < ls.indexOf('review:r1'), 'fixes run sequentially, then re-review')
  assert(named(calls, /^review:r1$/)[0].prompt.includes('base1..c2'), 're-review range is the fix commits')
  assert(named(calls, /^review:r2$/)[0].prompt.includes('base3..c3'))
  assert(!named(calls, /^review:r1$/)[0].prompt.includes('origin/v5.0.0...') )
  assert(named(calls, /^review:r0$/)[0].prompt.includes("args 'low 101'") || named(calls, /^review:r0$/)[0].prompt.includes("'low 101'"))
  assert.strictEqual(result.review.rounds, 2)
  assert.strictEqual(result.review.fixed.length, 3)
  assert(result.review.leftover.some(f => f.id === 'f6'))
  assert(result.review.preExisting.some(f => f.id === 'f4'))
  assert(!named(calls, /^fix:/).some(c => c.prompt.includes('f4') && c.prompt.includes('S-f4')), 'pre-existing findings are not fixed')
})

test('e2: nothing at or above the threshold means no fix agent', async () => {
  const { calls, result } = await run({}, c => (c.label === 'review:r0' ? ok({ skill_invoked: true, findings: [{ id: 'x', summary: 's', score: 49 }] }) : undefined))
  assert.strictEqual(named(calls, /^fix:/).length, 0)
  assert.strictEqual(named(calls, /^review:/).length, 1)
  assert.strictEqual(result.review.rounds, 0)
  assert.strictEqual(result.review.leftover.length, 1)
})

test('e3: review level follows diff size and risky paths; never max or ultra', async () => {
  const lvl = async files => (await run({}, c => (c.label === 'diffstat' ? { files } : undefined))).calls.find(c => c.label === 'review:r0').prompt.match(/args '(\w+) /)[1]
  assert.strictEqual(await lvl([{ path: 'a.js', added: 5, deleted: 1 }]), 'low')
  assert.strictEqual(await lvl([{ path: 'a.js', added: 300, deleted: 1 }]), 'medium')
  assert.strictEqual(await lvl([{ path: 'a.js', added: 900, deleted: 1 }]), 'high')
  assert.strictEqual(await lvl([{ path: 'hooks/x.sh', added: 1, deleted: 1 }]), 'high')
})

test('f: intent review sees the request and not the plan or decisions', async () => {
  const dec = { title: 'DECISION-TITLE-XYZ', context: 'c', options: ['a'], decision: 'd', why: 'w', consequences: 'x', how_to_reverse: 'r', confidence: 'high', needs_review: false }
  const { calls, result } = await run({ tickets: [T(1, 1, [], { confirmed: 'CONFIRMED-ANSWER-QQ' })] }, c => {
    if (c.label === 'intent:1') return ok({ goal: 'GOAL-SECRET', decisions: [dec], summary: 'SUMMARY-SECRET', plan_steps: [{ title: 'PLANSTEP-ABC', files: [], done_when: 'x' }] })
    if (c.label === 'intent-review') return { verdict: 'gaps found', findings: [{ kind: 'gap', clause: 'CLAUSE-1', detail: 'missing' }, { kind: 'excess', clause: 'C2', detail: 'extra' }] }
  })
  const p = named(calls, /^intent-review$/)[0]
  assert.strictEqual(p.opts.agentType, 'harness:intent-reviewer')
  assert(p.prompt.includes('REQUEST-BODY-1') && p.prompt.includes('origin/v5.0.0..origin/feat/1-ticket-1'))
  for (const bad of ['PLANSTEP-ABC', 'DECISION-TITLE-XYZ', 'GOAL-SECRET', 'SUMMARY-SECRET', 'did it']) assert(!p.prompt.includes(bad), `leaked ${bad}`)
  assert.strictEqual(named(calls, /^request:1$/)[0].prompt.includes('gh issue view 1 --repo o/r --json body -q .body'), true)
  assert.strictEqual(named(calls, /^intent-fix$/).length, 1, 'a gap gets one fix round')
  assert(result.intent.gaps.length === 2)
  const ls = labelsOf(calls)
  assert(ls.indexOf('intent-fix') < ls.indexOf('suite'))
})

test('f2: owner-confirmed decisions reach intent-review as owner words and intent-fix never reverts them', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], { confirmed: 'CONFIRMED-ANSWER-QQ' })] }, c => {
    if (c.label === 'intent-review') return { verdict: 'gaps found', findings: [{ kind: 'drift', clause: 'C', detail: 'd', behaviour_changing: true }] }
  })
  const p = named(calls, /^intent-review$/)[0].prompt
  assert(p.includes('CONFIRMED-ANSWER-QQ') && /NOT a gap/.test(p), 'confirmed decisions missing or unlabelled')
  const f = named(calls, /^intent-fix$/)[0].prompt
  assert(f.includes('CONFIRMED-ANSWER-QQ') && /never revert/.test(f) && f.includes('needs_review: true'))
  const none = await run({}, c => (c.label === 'intent-review' ? { verdict: 'gaps found', findings: [{ kind: 'gap', clause: 'C', detail: 'd' }] } : undefined))
  assert(!/Owner-confirmed/.test(named(none.calls, /^intent-review$/)[0].prompt + named(none.calls, /^intent-fix$/)[0].prompt), 'no confirmed text, no block')
})

test('g: the full suite runs once, after review and intent review', async () => {
  const { calls, result } = await run({ tickets: [T(1, 1), T(2, 1)] }, null)
  const ls = labelsOf(calls)
  assert.strictEqual(ls.filter(l => l === 'suite').length, 1)
  assert(ls.indexOf('suite') > ls.lastIndexOf('review:r0') && ls.indexOf('suite') > ls.indexOf('intent-review'))
  assert(named(calls, /^suite$/)[0].prompt.includes('run-all') && named(calls, /^suite$/)[0].opts.model === 'haiku')
  assert.deepStrictEqual(result.suite, { passed: 10, failed: 0, skipped: 1 })
  assert(named(calls, /^adr$/)[0].prompt.includes('Passed 10, failed 0, skipped 1'))
})

test('g2: a failing suite gets one fix agent and a re-run of only the failing tests', async () => {
  const { calls, result } = await run({}, c => {
    if (c.label === 'suite') return { passed: 8, failed: 2, skipped: 0, failing: ['t_a', 't_b'], tail: 'FAILED' }
    if (c.label === 'suite-rerun') return { passed: 2, failed: 0, skipped: 0, failing: [] }
  })
  assert.strictEqual(named(calls, /^suite$/).length, 1)
  assert.strictEqual(named(calls, /^suite-fix$/).length, 1)
  assert(named(calls, /^suite-rerun$/)[0].prompt.includes('t_a, t_b'))
  assert.strictEqual(result.suite.passed, 10); assert.strictEqual(result.suite.failed, 0)
})

test('h6: six stubbed decisions all reach the ADR stage with --table-out; owner_confirmed survives on exactly one', async () => {
  const D = (title, extra) => ({ title, context: 'ctx ' + title, options: ['a', 'b'], decision: 'd', why: 'w', consequences: 'x', how_to_reverse: 'r', confidence: 'high', needs_review: false, ...extra })
  const six = [
    D('DUP-one'), D('DUP-one', { context: 'other' }), D('OWNER-ok', { owner_confirmed: true }),
    D('REVIEW-me', { needs_review: true }), D('LOW-conf', { confidence: 'low' }), D('PLAIN'),
  ]
  const { calls } = await run({ tickets: [T(1, 1)] }, c => (c.label === 'intent:1' ? ok({ goal: 'g', plan_steps: [], decisions: six }) : undefined))
  const p = named(calls, /^adr$/)[0].prompt
  const saved = JSON.parse(p.split('\n').find(l => l.startsWith('{"run"')))
  assert.strictEqual(saved.decisions.length, 6)
  assert.strictEqual(saved.decisions.filter(d => d.owner_confirmed === true).length, 1)
  assert.strictEqual(saved.decisions.find(d => d.title === 'OWNER-ok').owner_confirmed, true)
  assert(p.includes('--table-out .ship/decisions-table.md') && p.includes('.ship/decisions-table.md unchanged'))
  const dec = named(calls, /^intent:1$/)[0].schema.properties.decisions.items.properties.owner_confirmed
  assert(dec && dec.type === 'boolean')
})

test('h: the ADR stage runs once and receives decisions from every ticket', async () => {
  const D = t => ({ title: t, context: 'c', options: ['a', 'b'], decision: 'd', why: 'w', consequences: 'x', how_to_reverse: 'r', confidence: 'medium', needs_review: t === 'D-two' })
  const { calls, result } = await run({ tickets: [T(1, 1), T(2, 1)] }, c => {
    if (c.label === 'intent:1') return ok({ goal: 'g', plan_steps: [], decisions: [D('D-one')] })
    if (c.label === 'implement:2') return ok({ worktree: '/wt/2', branch: 'b2', decisions: [D('D-two')] })
  })
  const adr = named(calls, /^adr$/)
  assert.strictEqual(adr.length, 1)
  const p = adr[0].prompt
  assert(p.includes('"title":"D-one"') && p.includes('"ticket":1') && p.includes('"title":"D-two"') && p.includes('"ticket":2'))
  assert(p.includes('"run":"ms"') && p.includes('--input .ship/decisions.json') && p.includes('--render-section') && p.includes('{{DECISIONS}}'))
  assert(p.includes('"stage":"intent"') && p.includes('"decided_by"'))
  const noSpecs = labelsOf(calls).filter(l => l !== 'specs' && l !== 'specs-early')   // the local spec write needs the ADR paths
  assert.strictEqual(noSpecs[noSpecs.length - 1], 'adr')
  assert.deepStrictEqual(result.adrs, [{ number: 2, path: 'docs/adr/0002-x.md', needsReview: true }])
  assert.strictEqual(result.artifact.fallback, 'docs/adr/')
})

test('i: local mode never mentions pushing or opening a PR and fetches no issue', async () => {
  for (const tickets of [[T(1, 1)], [T(1, 1), T(2, 2, [1])]]) {
    const { calls, result } = await run({ local: true, tickets }, null)
    for (const c of calls) {
      assert(!c.prompt.includes('gh pr create'), `${c.label} mentions gh pr create`)
      assert(!c.prompt.includes('git push'), `${c.label} mentions git push`)
    }
    assert.strictEqual(named(calls, /^request:/).length, 0)
    assert.strictEqual(named(calls, /^artifact/).length, 0, 'local mode publishes no artifact')
    assert.strictEqual(result.final.pr, null)
    assert(result.tickets.every(t => t.status === 'done'))
  }
})

test('j: no agent gets max or ultra effort, and every agent gets an explicit effort', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], { depth: 'L' }), T(2, 1, [], { depth: 'M' }), T(3, 2, [1])] }, null)
  for (const c of calls) assert(['low', 'medium', 'high'].includes(c.opts.effort), `${c.label}: ${c.opts.effort}`)
  const models = Object.fromEntries(calls.map(c => [c.label.split(':')[0], c.opts.model]))
  assert.strictEqual(models.suite, 'haiku'); assert.strictEqual(models.research, 'haiku'); assert.strictEqual(models.implement, 'sonnet')
})

test('j2: design and plan run on opus at depth L only; plan stays sonnet at depth M, S runs neither', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], { depth: 'S' }), T(2, 1, [], { depth: 'M' }), T(3, 1, [], { depth: 'L' })] }, null)
  const models = (n, stage) => named(calls, new RegExp(`^${stage}:${n}$`)).map(c => c.opts.model)
  assert.deepStrictEqual(models(1, 'plan'), []); assert.deepStrictEqual(models(2, 'plan'), ['sonnet'])   // depth S writes no plan stage
  assert.deepStrictEqual(models(1, 'design'), []); assert.deepStrictEqual(models(2, 'design'), [])
  assert(models(3, 'design').length > 0 && models(3, 'design').every(m => m === 'opus'), 'L design on opus')
  assert(models(3, 'plan').length > 0 && models(3, 'plan').every(m => m === 'opus'), 'L plan on opus')
})

test('k: argument validation', async () => {
  const bad = async (over, re) => { await assert.rejects(() => run(over, null), re) }
  await bad({ tickets: [T(1, 1), T(1, 2)] }, /duplicate ticket number #1/)
  await bad({ repoDir: undefined }, /args\.repoDir is required/)
  await bad({ pluginDir: undefined }, /args\.pluginDir is required/)
  await bad({ tickets: [] }, /non-empty array/)
  await bad({ tickets: [T(1, 1, [], { depth: 'XL' })] }, /depth/)
})

test('l: pluginDir is used for the role files, the skills and the ADR script, and is checked in Setup', async () => {
  const { calls } = await run({ pluginDir: '/other/plugin' }, null)
  assert.strictEqual(calls[0].label, 'plugin-check')
  assert(calls[0].prompt.includes('/other/plugin/agents/implementer.md'))
  const all = calls.map(c => c.prompt).join('\n')
  assert(all.includes('/other/plugin/agents/implementer.md') && all.includes('/other/plugin/agents/intent-reviewer.md'))
  assert(all.includes('/other/plugin/scripts/write_adrs.py') && all.includes('/other/plugin/skills/'))
  assert(!all.includes('/plug/') && !/\.claude\/(?!rules\/)/.test(all))
})

test('m: a plugin check that fails stops the run before any ticket stage', async () => {
  await assert.rejects(() => run({}, c => (c.label === 'plugin-check' ? { status: 'blocked', blocked_reason: 'pluginDir missing', summary: '' } : undefined)), /pluginDir missing/)
})

const BDEC = { title: 'Boundary: touches docs/x.md', context: 'c', options: ['a', 'b'], decision: 'DECISION-TEXT-BD', why: 'w', consequences: 'x', how_to_reverse: 'r', confidence: 'high', needs_review: true }
const intentOos = c => (c.label === 'intent:1'
  ? ok({ goal: 'g', acceptance: [], files: ['src/keep.js'], out_of_scope: ['OOS-LINE-1'], plan_steps: [{ title: 's', files: ['src/step.js'], done_when: 'true' }] })
  : undefined)

test('n: out_of_scope and the file set reach implement, fix and intent-fix prompts', async () => {
  const { calls } = await run({}, c => {
    if (c.label === 'intent:1') return intentOos(c)
    if (c.label.startsWith('review:')) return c.label === 'review:r0' ? ok({ findings: [{ id: 'F1', summary: 'bad', score: 90 }], skill_invoked: true }) : ok({ findings: [], skill_invoked: true })
    if (c.label === 'intent-review') return { verdict: 'gaps found', findings: [{ kind: 'gap', clause: 'C', detail: 'd' }] }
  })
  assert(/OOS-LINE-1/.test(named(calls, /^intent:1$/)[0].prompt) === false, 'intent prompt does not carry the list itself')
  assert(named(calls, /^intent:1$/)[0].prompt.includes('out_of_scope'))
  for (const re of [/^implement:1$/, /^fix:/, /^intent-fix$/]) {
    const cs = named(calls, re)
    assert(cs.length >= 1, String(re))
    for (const p of cs.map(c => c.prompt)) assert(p.includes('OOS-LINE-1') && p.includes('src/keep.js') && p.includes('src/step.js') && p.includes('Boundary: '), `${re}: boundary missing`)
  }
})

test('n2: no prompt says tests count only when the ticket lists them; implement and intent-fix allow the proving test', async () => {
  const { calls } = await run({}, c => {
    if (c.label === 'intent:1') return intentOos(c)
    if (c.label.startsWith('review:')) return c.label === 'review:r0' ? ok({ findings: [{ id: 'F1', summary: 'bad', score: 90 }], skill_invoked: true }) : ok({ findings: [], skill_invoked: true })
    if (c.label === 'intent-review') return { verdict: 'gaps found', findings: [{ kind: 'gap', clause: 'C', detail: 'd' }] }
  })
  for (const re of [/^implement:1$/, /^fix:/, /^intent-fix$/]) {
    const cs = named(calls, re)
    assert(cs.length >= 1, String(re))
    for (const c of cs) assert(!/count only when the ticket lists/.test(c.prompt) && /in bounds only when/.test(c.prompt) && !/always allowed/.test(c.prompt), `${re}: test/doc files must be in bounds only when the ticket lists them`)
  }
})

test('o: a skipped boundary fix is not fixed, needs a decision, and is listed under Review', async () => {
  const { calls, result } = await run({}, c => {
    if (c.label === 'intent:1') return intentOos(c)
    if (c.label === 'review:r0') return ok({ findings: [{ id: 'F1', summary: 'FINDING-SUM', score: 90 }], skill_invoked: true })
    if (c.label.startsWith('fix:')) return ok({ fix_status: 'skipped', summary: 'skipped it', decisions: [BDEC] })
  })
  assert.strictEqual(result.review.fixed.length, 0)
  assert.strictEqual(result.review.notFixed.length, 1)
  assert(result.review.notFixed[0].reason.includes('needs your decision: Boundary: touches docs/x.md'))
  const p = named(calls, /^adr$/)[0].prompt
  assert(p.includes('"title":"Boundary: touches docs/x.md"') && p.includes('"needs_review":true'))
  const body = p.slice(p.indexOf('## Summary'))
  assert(body.indexOf('## Review') < body.indexOf('needs your decision: Boundary: touches docs/x.md'))
  assert(body.indexOf('needs your decision') < body.indexOf('## Intent review'))
})

test('o2: a skipped fix whose decision is not a boundary keeps its title and is not forced to review', async () => {
  const PD = { title: 'Finding is a false positive', context: 'c', options: ['a', 'b'], decision: 'D', why: 'w', consequences: 'x', how_to_reverse: 'r', confidence: 'high', needs_review: false }
  const { calls, result } = await run({}, c => {
    if (c.label === 'review:r0') return ok({ findings: [{ id: 'F1', summary: 'FINDING-SUM', score: 90 }], skill_invoked: true })
    if (c.label.startsWith('fix:')) return ok({ fix_status: 'skipped', summary: 'SKIP-REASON-TEXT', decisions: [PD] })
  })
  const d = result.decisions.find(x => /false positive/.test(x.title))
  assert(d, 'decision recorded')
  assert(!d.title.startsWith('Boundary: ') && d.needs_review === false && d.boundary === false, 'not relabelled as a boundary')
  assert(result.review.notFixed[0].reason.includes('SKIP-REASON-TEXT') && !result.review.notFixed[0].reason.includes('Boundary'))
})

test('o2b: a skipped fix whose decision needs review is listed as needs your decision even without the Boundary prefix', async () => {
  const UD = { title: 'Fix would change a public contract', context: 'c', options: ['a', 'b'], decision: 'D', why: 'w', consequences: 'x', how_to_reverse: 'r', confidence: 'medium', needs_review: true }
  const { result } = await run({}, c => {
    if (c.label === 'review:r0') return ok({ findings: [{ id: 'F1', summary: 'FINDING-SUM', score: 90 }], skill_invoked: true })
    if (c.label.startsWith('fix:')) return ok({ fix_status: 'skipped', summary: 'SKIP-REASON-TEXT', decisions: [UD] })
  })
  assert(result.review.notFixed[0].reason.includes('needs your decision: Fix would change a public contract'), result.review.notFixed[0].reason)
})

test('o3: fix prompt allows the proving test and a null decision entry does not throw', async () => {
  const { calls, result } = await run({}, c => {
    if (c.label === 'intent:1') return intentOos(c)
    if (c.label === 'review:r0') return ok({ findings: [{ id: 'F1', summary: 'FINDING-SUM', score: 90 }], skill_invoked: true })
    if (c.label.startsWith('fix:')) return ok({ fix_status: 'skipped', summary: 'SKIP-REASON-TEXT', decisions: [null, { context: 'no title' }] })
  })
  assert(named(calls, /^fix:/)[0].prompt.includes('in bounds only when the list above names it') && !named(calls, /^fix:/)[0].prompt.includes('always allowed'), 'test/doc files bound by the ticket list in fix prompt')
  assert(result.review.notFixed[0].reason.includes('SKIP-REASON-TEXT'))
})

test('p: Needs your decision sits above Summary and is omitted when empty', async () => {
  const withGap = await run({}, c => (c.label === 'intent-review' ? { verdict: 'gaps found', findings: [{ kind: 'excess', behaviour_changing: true, clause: 'CL-EXCESS', detail: 'did more' }, { kind: 'excess', clause: 'CL-QUIET', detail: 'harmless' }] } : undefined))
  const p = named(withGap.calls, /^adr$/)[0].prompt
  const i = p.indexOf('## Needs your decision')
  assert(i >= 0 && i < p.indexOf('## Summary'), 'section above Summary')
  const sec = p.slice(i, p.indexOf('## Summary'))
  assert(sec.includes('CL-EXCESS') && !sec.includes('CL-QUIET'), 'only behaviour-changing excess is listed')
  const none = await run({}, null)
  assert(!named(none.calls, /^adr$/)[0].prompt.includes('## Needs your decision'))
})

test('q: {{DECISIONS}} still sits between Final verification and the footer', async () => {
  const { calls } = await run({}, null)
  const p = named(calls, /^adr$/)[0].prompt
  const b = p.slice(p.indexOf('## Summary'))
  const a = b.indexOf('## Final verification'), d = b.indexOf('{{DECISIONS}}'), f = b.indexOf('Generated with')
  assert(a >= 0 && a < d && d < f, `${a} ${d} ${f}`)
})

// ---- verify stage (#413) --------------------------------------------------------------------
const vres = (passed, kind, extra) => ok({ passed, kind, failedStep: passed ? '' : 'step 2', consoleErrors: passed ? [] : ['TypeError x'], stills: ['/wt/1/.playwright-mcp/1/step-1.png'], report: passed ? 'ALL-PASS' : 'STEP-2-FAILED', ...extra })

test('v1: an FE ticket runs implement, verify, base check, finish in that order, and the result reaches finish', async () => {
  const { result, calls } = await run({}, c => {
    if (c.label === 'verify:1') return vres(true, 'FE')
    if (c.label === 'verify-base:1') return vres(false, 'FE')
  })
  const ls = labelsOf(calls).filter(l => /^(implement|verify|gif|finish)/.test(l))
  assert.deepStrictEqual(ls, ['implement:1', 'verify:1', 'verify-base:1', 'gif:1', 'finish:1'])
  const v = named(calls, /^verify:1$/)[0]
  assert(v.prompt.includes('/wt/1') && v.prompt.includes('/plug/skills/verify/SKILL.md') && v.prompt.includes('gh issue view 1 --repo o/r --json body'), v.prompt)
  assert(!('agentType' in v.opts) && v.opts.model === 'sonnet' && v.opts.effort === 'medium' && v.opts.phase === 'Tickets')
  assert(v.schema.properties.passed && v.schema.properties.stills && v.schema.required.includes('kind'))
  const b = named(calls, /^verify-base:1$/)[0]
  assert(b.prompt.includes('worktree add --detach /.ship-repo/ms/verify-base-1 origin/v5.0.0') && b.prompt.includes('Mode: base') && b.prompt.includes('/wt/1/verify.config.json') && b.prompt.includes('Commit nothing'), b.prompt)
  const f = named(calls, /^finish:1$/)[0].prompt
  assert(f.includes('Verify result: pass') && f.includes('/wt/1/.playwright-mcp/1/step-1.png') && f.includes('Evidence stays uncommitted') && !f.includes('Nothing is attached'), f)
  const g = named(calls, /^gif:1$/)[0]
  assert(g.opts.model === 'haiku' && g.schema.properties.gif && g.prompt.includes('ffmpeg') && g.prompt.includes('palettegen') && g.prompt.includes('/wt/1/.playwright-mcp/1') && !g.prompt.includes('*.png') && g.prompt.includes('concat') && g.prompt.includes('repeat the last still'), g.prompt)
  assert.strictEqual(result.final.pr, 101)
})

test('v2: a retry that passes gives flaky', async () => {
  const { calls } = await run({}, c => {
    if (c.label === 'verify:1') return vres(false, 'FE')
    if (c.label === 'verify-retry:1') return vres(true, 'FE')
    if (c.label === 'verify-base:1') return vres(false, 'FE')
  })
  assert.deepStrictEqual(labelsOf(calls).filter(l => /^(verify|finish)/.test(l)), ['verify:1', 'verify-retry:1', 'verify-base:1', 'finish:1'])
  assert(named(calls, /^finish:1$/)[0].prompt.includes('Verify result: flaky'))
  assert.strictEqual(named(calls, /^verify-comment:/).length, 0)
})

test('v3: two failures block ticket 1 with the report and an issue comment; ticket 2 still finishes', async () => {
  const { result, calls } = await run({ tickets: [T(1, 1), T(2, 1)] }, c => {
    if (c.label === 'verify:1' || c.label === 'verify-retry:1') return vres(false, 'FE')
  })
  const r1 = result.tickets.find(r => r.n === 1), r2 = result.tickets.find(r => r.n === 2)
  assert.strictEqual(r1.status, 'blocked')
  assert(r1.reason.includes('step 2') && r1.reason.includes('TypeError x'), r1.reason)
  assert.strictEqual(r2.status, 'done')
  assert.strictEqual(named(calls, /^finish:1$/).length, 0)
  assert.strictEqual(named(calls, /^finish:2$/).length, 1)
  assert.strictEqual(named(calls, /^verify-base:1$/).length, 0)
  const cm = named(calls, /^verify-comment:1$/)
  assert.strictEqual(cm.length, 1)
  assert(cm[0].prompt.includes('gh issue comment 1 --repo o/r') && cm[0].prompt.includes('STEP-2-FAILED'), cm[0].prompt)
})

test('v4: a failing comment is only logged; the ticket stays blocked', async () => {
  const { result, logs } = await run({}, c => {
    if (c.label === 'verify:1' || c.label === 'verify-retry:1') return vres(false, 'FE+BE')
    if (c.label === 'verify-comment:1') return new Error('gh down')
  })
  assert.strictEqual(result.tickets[0].status, 'blocked')
  assert(logs.some(l => l.includes('verify comment failed')))
})

test('v5: steps that pass on base block the ticket as a weak test, with a comment', async () => {
  const { result, calls } = await run({}, c => {
    if (c.label === 'verify:1' || c.label === 'verify-base:1') return vres(true, 'FE')
  })
  assert.strictEqual(result.tickets[0].status, 'blocked')
  assert(/weak test/.test(result.tickets[0].reason))
  assert.strictEqual(named(calls, /^verify-comment:1$/).length, 1)
  assert.strictEqual(named(calls, /^finish:/).length, 0)
})

test('v6: BE and docs tickets skip the base check', async () => {
  for (const kind of ['BE', 'docs']) {
    const { calls } = await run({}, c => (c.label === 'verify:1' ? vres(true, kind) : undefined))
    assert.strictEqual(named(calls, /^verify-base:/).length, 0, kind)
    assert(named(calls, /^finish:1$/)[0].prompt.includes('Verify result: pass'))
  }
})

test('v7: local mode skips the verify stage, the issue fetch and the comment', async () => {
  const { calls } = await run({ local: true }, null)
  assert.strictEqual(named(calls, /^verify/).length, 0, labelsOf(calls).join())
  assert(!named(calls, /^finish:1$/)[0].prompt.includes('Verify result'))
})

// ---- GIF and attach (#414) ------------------------------------------------------------------
const gifOk = c => (c.label === 'gif:1' ? ok({ gif: '/wt/1/.playwright-mcp/1/evidence.gif' }) : undefined)
const withVerify = (kind, extra) => c => {
  if (c.label === 'verify:1') return vres(true, kind)
  if (c.label === 'verify-base:1') return vres(false, kind)
  return (extra || gifOk)(c)
}

test('a1: pass with a GIF attaches after finish, without the flaky note', async () => {
  const { calls, result } = await run({}, withVerify('FE'))
  const ls = labelsOf(calls).filter(l => /^(gif|finish|attach)/.test(l))
  assert.deepStrictEqual(ls, ['gif:1', 'finish:1', 'attach:1'])
  const a = named(calls, /^attach:1$/)[0]
  assert(a.prompt.includes('gh pr comment 101 --repo o/r --attach /wt/1/.playwright-mcp/1/evidence.gif') && !a.prompt.includes('gh pr edit') && a.opts.model === 'haiku', a.prompt)
  assert.strictEqual(result.tickets[0].status, 'done')
})

test('a1b: the gif prompt names sha256sum, the distinct-still rule and the PNG fallback', async () => {
  const { calls } = await run({}, withVerify('FE'))
  const g = named(calls, /^gif:1$/)[0]
  assert(g.prompt.includes('sha256sum') && g.prompt.includes('fewer than 2 distinct') && g.prompt.includes('identical to the one before it') && g.prompt.includes('PNG'), g.prompt)
})

test('a1c: an empty gif with a still present attaches the first still, in order gif, finish, attach', async () => {
  const { calls, result } = await run({}, withVerify('FE', c => (c.label === 'gif:1' ? ok({ gif: '' }) : undefined)))
  const ls = labelsOf(calls).filter(l => /^(gif|finish|attach)/.test(l))
  assert.deepStrictEqual(ls, ['gif:1', 'finish:1', 'attach:1'])
  assert(named(calls, /^attach:1$/)[0].prompt.includes('--attach /wt/1/.playwright-mcp/1/step-1.png'), 'attach prompt')
  assert.strictEqual(result.tickets[0].status, 'done')
})

test('a2: flaky adds the note to the PR body', async () => {
  const { calls } = await run({}, c => {
    if (c.label === 'verify:1') return vres(false, 'FE')
    if (c.label === 'verify-retry:1') return vres(true, 'FE')
    if (c.label === 'verify-base:1') return vres(false, 'FE')
    return gifOk(c)
  })
  const a = named(calls, /^attach:1$/)[0]
  assert(a.prompt.includes('--attach') && a.prompt.includes('gh pr edit 101 --repo o/r') && a.prompt.includes('was flaky'), a.prompt)
})

test('a3: no GIF path attaches the first still as a PNG, and the ticket is done', async () => {
  const { calls, result, logs } = await run({}, withVerify('FE', c => (c.label === 'gif:1' ? ok({ gif: '' }) : undefined)))
  const at = named(calls, /^attach:/)
  assert.strictEqual(at.length, 1)
  assert(at[0].prompt.includes('--attach /wt/1/.playwright-mcp/1/step-1.png'), at[0].prompt)
  assert(logs.some(l => l.includes('no GIF built')))
  assert.strictEqual(result.tickets[0].status, 'done')
})

test('a3b: no GIF and no stills makes no attach call', async () => {
  const { calls, result } = await run({}, c => {
    if (c.label === 'verify:1') return vres(true, 'FE', { stills: [] })
    if (c.label === 'verify-base:1') return vres(false, 'FE')
  })
  assert.strictEqual(named(calls, /^attach:/).length, 0)
  assert.strictEqual(result.tickets[0].status, 'done')
})

test('a4: local mode builds no GIF and makes no attach call', async () => {
  const { calls } = await run({ local: true }, null)
  assert.strictEqual(named(calls, /^(gif|attach):/).length, 0, labelsOf(calls).join())
})

test('a5: an attach failure is logged and the ticket is still done', async () => {
  const { calls, result, logs } = await run({}, withVerify('FE', c => (c.label === 'attach:1' ? new Error('gh too old') : gifOk(c))))
  assert.strictEqual(named(calls, /^attach:1$/).length, 1)
  assert(logs.some(l => l.includes('attach failed')))
  assert.strictEqual(result.tickets[0].status, 'done')
})

test('a8: the attach prompt names --attach, gh 2.99.0 and bans an image line', async () => {
  const { calls } = await run({}, withVerify('FE'))
  const a = named(calls, /^attach:1$/)[0]
  assert(a.prompt.includes('--attach') && a.prompt.includes('2.99.0') && a.prompt.includes('must not contain an image line'), a.prompt)
})

test('a9: a needs_review decision from the attach agent reaches the run and the ticket is done', async () => {
  const d = { title: 'Attach by hand', context: 'denied', options: ['a'], decision: 'gh pr comment 101 --repo o/r --attach /wt/1/.playwright-mcp/1/evidence.gif', why: 'w', consequences: 'c', how_to_reverse: 'n', confidence: 'high', needs_review: true }
  const { result } = await run({}, withVerify('FE', c => (c.label === 'attach:1' ? ok({ decisions: [d] }) : gifOk(c))))
  assert(result.decisions.some(x => x.title === 'Attach by hand' && x.needs_review === true && x.stage === 'attach'), JSON.stringify(result.decisions))
  assert.strictEqual(result.tickets[0].status, 'done')
})

test('a10: an attach call that throws records a needs_review decision with the command', async () => {
  const { result } = await run({}, withVerify('FE', c => (c.label === 'attach:1' ? new Error('denied') : gifOk(c))))
  assert(result.decisions.some(x => x.needs_review === true && String(x.decision).includes('gh pr comment 101 --repo o/r --attach /wt/1/.playwright-mcp/1/evidence.gif')), JSON.stringify(result.decisions))
  assert.strictEqual(result.tickets[0].status, 'done')
})

test('a6: a GIF build failure keeps gif null, attaches the first still and does not change the result', async () => {
  const { calls, result, logs } = await run({}, withVerify('FE', c => (c.label === 'gif:1' ? new Error('no ffmpeg') : undefined)))
  const at = named(calls, /^attach:/)
  assert.strictEqual(at.length, 1)
  assert(at[0].prompt.includes('--attach /wt/1/.playwright-mcp/1/step-1.png'), at[0].prompt)
  assert(logs.some(l => l.includes('gif build failed')))
  assert(named(calls, /^finish:1$/)[0].prompt.includes('Verify result: pass'))
  assert.strictEqual(result.tickets[0].status, 'done')
})

test('a7: a pr of 0 never attaches even with a GIF', async () => {
  const { calls } = await run({}, c => (c.label === 'finish:1' ? ok({ pr: 0, url: '' }) : withVerify('FE')(c)))
  assert.strictEqual(named(calls, /^attach:/).length, 0)
})

// ---- Verify section in the PR body (#426) ---------------------------------------------------
const adrBody = calls => named(calls, /^adr$/)[0].prompt

test('vb1: FE pass with a failed base check and an attached GIF is listed under Verify', async () => {
  const { calls } = await run({}, withVerify('FE', gifOk))
  const b = adrBody(calls)
  assert(b.includes('## Verify') && b.includes('- #1 FE: pass; base: failed on base as required; stills: /wt/1/.playwright-mcp/1; GIF: built and attached'), b)
  assert(b.indexOf('## Review') < b.indexOf('## Verify') && b.indexOf('## Verify') < b.indexOf('## Intent review'), b)
})

test('vb2: a flaky result is shown as flaky', async () => {
  const { calls } = await run({}, c => {
    if (c.label === 'verify:1') return vres(false, 'FE')
    if (c.label === 'verify-retry:1') return vres(true, 'FE')
    if (c.label === 'verify-base:1') return vres(false, 'FE')
    return gifOk(c)
  })
  assert(adrBody(calls).includes('- #1 FE: flaky;'), adrBody(calls))
})

test('vb2b: the Verify line uses v.result directly, no dead ternary', () => {
  assert(!/v\.result === 'flaky' \? 'flaky'/.test(SRC), 'dead ternary on v.result')
})

test('vb3: a weak-test blocked ticket shows fail and passed on base', async () => {
  const { calls } = await run({ tickets: [T(1, 1), T(2, 1)] }, c => {
    if (c.label === 'verify:1' || c.label === 'verify-base:1') return vres(true, 'FE')
  })
  const b = adrBody(calls)
  assert(b.includes('- #1 FE: fail; base: passed on base (weak test); stills: /wt/1/.playwright-mcp/1; GIF: not built'), b)
})

test('vb4: a GIF built but a failed attach shows built, not attached', async () => {
  const { calls } = await run({}, withVerify('FE', c => (c.label === 'attach:1' ? new Error('gh too old') : gifOk(c))))
  assert(adrBody(calls).includes('GIF: built, not attached'), adrBody(calls))
})

test('vb5: no GIF shows not built, and a BE ticket has base not run', async () => {
  const { calls } = await run({}, c => (c.label === 'verify:1' ? vres(true, 'BE') : undefined))
  assert(adrBody(calls).includes('- #1 BE: pass; base: not run; stills: /wt/1/.playwright-mcp/1; GIF: not built'), adrBody(calls))
})

test('vb6: failing twice shows fail with base not run', async () => {
  const { calls } = await run({ tickets: [T(1, 1), T(2, 1)] }, c => (c.label === 'verify:1' || c.label === 'verify-retry:1' ? vres(false, 'FE') : undefined))
  assert(adrBody(calls).includes('- #1 FE: fail; base: not run;'), adrBody(calls))
})

test('vb7: local mode has no Verify heading', async () => {
  const { calls } = await run({ local: true }, null)
  assert(!adrBody(calls).includes('## Verify'))
})

test('s1: one writer at the end puts the five flow files of every ticket in the main checkout specs/', async () => {
  for (const depth of ['S', 'M', 'L']) {
    const dec = { title: 'D-ADR', context: 'c', options: ['a'], decision: 'd', why: 'w', consequences: 'x', how_to_reverse: 'r', confidence: 'low', needs_review: true }
    const { calls } = await run({ tickets: [T(1, 1, [], { depth })] }, c => {
      if (c.label === 'intent:1') return ok({ goal: 'GOAL-1', approach: 'APPROACH-1', acceptance: ['works'], decisions: [dec], plan_steps: [{ title: 'STEP-1', files: ['a.js'], covers: ['AC1'], done_when: 'true' }] })
      if (c.label === 'adr') return ok({ adrs: [{ number: 2, path: 'docs/adr/0002-d-adr.md', needs_review: true, ticket: '1', title: 'D-ADR' }] })
    })
    const w = named(calls, /^specs$/)
    assert.strictEqual(w.length, 1, `${depth}: ${labelsOf(calls).join()}`)
    const p = w[0].prompt
    for (const f of ['intent.md', 'design.md', 'decision.md', 'plan.md', 'summary.md']) assert(p.includes(`=== /repo/specs/1-ticket-1/${f}`), `${depth}: ${f} missing`)
    assert(p.includes('check-ignore') && p.includes('date +%F') && p.includes('Date: {{DATE}}') && p.includes('gh issue view 1 --repo o/r --json body -q .body'), depth)
    assert(!p.includes('/.ship-repo/'), `${depth}: spec files must not go to a worktree`)
    assert(p.includes("<<'SPEC_EOF'") && !p.includes('Write tool'), `${depth}: summary.md must be written with a Bash quoted heredoc, not the Write tool`)
    assert(p.includes(depth === 'S' ? '- Covers: AC1' : 'PLAN-MD'), `${depth}: plan text`)
    assert(p.includes(depth === 'L' ? '=== /repo/specs/1-ticket-1/research-brief.md' : 'APPROACH-1'), `${depth}: design or research`)
    assert(p.includes('AC1: works') && p.includes('- ADR: docs/adr/0002-d-adr.md') && p.includes('D1 D-ADR → docs/adr/0002-d-adr.md') && p.includes('- intent-review: match'), depth)
    assert(labelsOf(calls).indexOf('specs') > labelsOf(calls).indexOf('adr'))
    assert(!named(calls, /^implement:1$/)[0].prompt.includes('PLAN.md'), `${depth}: implement still told to write PLAN.md`)
  }
})

test('s2: blocked, merge-blocked and skipped tickets get spec files with their real status; a failed write changes nothing', async () => {
  const { calls, result } = await run({ local: true, tickets: [T(1, 1, [], { body: 'FULL-BODY-1' }), T(2, 1), T(3, 2, [1]), T(4, 2)] }, c => {
    if (c.label === 'implement:1') return ok({ status: 'blocked', blocked_reason: 'cannot build', worktree: '', branch: '' })
    if (c.label === 'merge:g2') return ok({ merged: [], failed: [{ n: 4, reason: 'conflict' }] })
    if (c.label === 'specs') return new Error('write failed')
  })
  const p = named(calls, /^specs$/)[0].prompt
  assert(p.includes('Status: blocked (implement: cannot build)'), 'blocked ticket')
  assert(p.includes('=== /repo/specs/3-ticket-3/summary.md') && p.includes('Status: skipped (dependency #1 is blocked)'), 'skipped ticket')
  assert(p.includes('Status: blocked (merge into feat/ms failed: conflict)'), 'merge-blocked ticket')
  assert(p.includes('FULL-BODY-1') && !p.includes('{{REQUEST}}'), 'local mode uses the ticket body as the request')
  assert(p.includes('## Original request') && p.includes('## Deviations from plan') && p.includes('| Command | Result | Covers |'), 'template headings')
  assert.strictEqual(result.tickets.find(t => t.n === 2).status, 'done')
})

test('s3: when no ticket is delivered the spec files are still written', async () => {
  const { calls } = await run({}, c => (c.label === 'implement:1' ? ok({ status: 'blocked', blocked_reason: 'nope', worktree: '', branch: '' }) : undefined))
  const w = named(calls, /^specs$/)
  assert.strictEqual(w.length, 1, labelsOf(calls).join())
  assert(w[0].prompt.includes('Status: blocked (implement: nope)') && w[0].prompt.includes('code review: not run'))
})

test('s4: early spec writes happen after the intent and plan stages, before implement, in the main checkout', async () => {
  for (const depth of ['S', 'M', 'L']) {
    const { calls } = await run({ tickets: [T(1, 1, [], { depth })] }, null)
    const labels = labelsOf(calls), impl = labels.indexOf('implement:1')
    const early = named(calls, /^specs-early$/)
    assert(early.length >= 1 && early.every(c => labels.indexOf('specs-early') < impl && labels.lastIndexOf('specs-early') < impl), `${depth}: ${labels.join()}`)
    assert(labels.indexOf('specs-early') > labels.indexOf('intent:1'), `${depth}: after intent`)
    if (depth !== 'S') assert(labels.lastIndexOf('specs-early') > labels.indexOf('plan:1'), `${depth}: after plan`)
    const p = early.map(c => c.prompt).join('\n')
    for (const f of ['intent.md', 'plan.md']) assert(p.includes(`=== /repo/specs/1-ticket-1/${f}`), `${depth}: ${f}`)
    if (depth !== 'S') assert(p.includes('=== /repo/specs/1-ticket-1/design.md'), `${depth}: design.md`)
    if (depth === 'L') assert(p.includes('=== /repo/specs/1-ticket-1/research-brief.md'), 'research-brief.md')
    assert(!p.includes('decision.md') && !p.includes('summary.md'), `${depth}: end-of-run files`)
    assert(p.includes('check-ignore') && !p.includes('/.ship-repo/') && !p.includes('/wt/'), depth)
    assert(early.every(c => c.opts.model === 'haiku' && c.opts.effort === 'low'), `${depth}: cheap model`)
    assert(early.every(c => c.opts.phase === 'Tickets'), `${depth}: early phase`)
    assert.strictEqual(named(calls, /^specs$/).length, 1, `${depth}: final pass`)
    assert.strictEqual(named(calls, /^specs$/)[0].opts.phase, 'Decisions', `${depth}: final phase`)
  }
})

test('s5: the intent.md early write exists when implement is blocked or the plan stage throws', async () => {
  const a = await run({}, c => (c.label === 'implement:1' ? ok({ status: 'blocked', blocked_reason: 'nope', worktree: '', branch: '' }) : undefined))
  assert(named(a.calls, /^specs-early$/)[0].prompt.includes("=== /repo/specs/1-add-the-thing/intent.md"))
  const b = await run({ tickets: [T(1, 1, [], { depth: 'M' })] }, c => (c.label === 'plan:1' ? new Error('plan failed') : undefined))
  assert(named(b.calls, /^specs-early$/)[0].prompt.includes('=== /repo/specs/1-ticket-1/intent.md'))
  assert.strictEqual(named(b.calls, /^implement:/).length, 0)
})

test('s6: a failing or blocked early write changes nothing', async () => {
  const base = await run({}, null)
  for (const out of [new Error('write failed'), { status: 'blocked', blocked_reason: 'not ignored', summary: '' }]) {
    const r = await run({}, c => (c.label === 'specs-early' ? out : undefined))
    assert.strictEqual(named(r.calls, /^implement:1$/).length, 1)
    assert.strictEqual(r.result.tickets[0].status, 'done')
    assert.deepStrictEqual(r.result.tickets, base.result.tickets)
  }
})

// ---- UAT phase (#462) -----------------------------------------------------------------------
const uatRes = (passed, scenarios, extra) => ok({ passed_ac: passed, scenarios, non_ac_failures: [], console_errors: 0, ...extra })
const sc = (id, covers, kind, status) => ({ id, covers, kind, status, assertion: `A-${id}`, still: '' })

test('u1: a docs ticket gets no UAT agent', async () => {
  const { calls, logs } = await run({}, c => (c.label === 'verify:1' ? vres(true, 'docs') : undefined))
  assert.strictEqual(named(calls, /^uat/).length, 0, labelsOf(calls).join())
  assert(logs.some(l => l.includes('UAT #1 skipped: docs')), logs.join('\n'))
  const local = await run({ local: true }, null)
  assert.strictEqual(named(local.calls, /^uat/).length, 0)
  assert(local.logs.some(l => l.includes('UAT skipped: local mode')))
})

test('u2: the UAT prompt holds the body and owner block, never the plan, diff or Verify text', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], { confirmed: 'Owner said X.\nVerify: OWNER-SECRET\n  continues here' })] }, c => {
    if (c.label === 'request:1') return { body: 'Do the thing.\nAC one\n\nVerify: SECRET-V start the app\n  then click SECRET-V2\n\nTail text' }
    if (c.label === 'plan:1') return ok({ plan_md: 'PLAN-MD', plan_steps: [] })
  })
  const u = named(calls, /^uat:1$/)[0]
  assert(u, labelsOf(calls).join())
  for (const bad of ['SECRET-V', 'SECRET-V2', 'OWNER-SECRET', 'PLAN-MD', 'continues here', 'gh issue view 1']) assert(!u.prompt.includes(bad), `UAT prompt leaks ${bad}`)
  assert(u.prompt.includes('Do the thing.') && u.prompt.includes('Tail text') && u.prompt.includes('Owner said X.'), u.prompt)
  assert(u.prompt.includes('Config: /wt/1/verify.config.json') && u.prompt.includes('/plug/skills/uat/SKILL.md'), u.prompt)
  assert.strictEqual(u.opts.phase, 'UAT')
  const ir = named(calls, /^intent-review$/)[0]
  assert(ir.prompt.includes('SECRET-V'), 'intent review still gets the raw body')
  assert.strictEqual(named(calls, /^request:/).length, 1, 'the request text is cached, not fetched again')
})

test('u2b: tight AC bullets under a Verify row stay in the UAT prompt', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], {})] }, c => {
    if (c.label === 'request:1') return { body: 'Do the thing.\nVerify: SECRET-V start\n  then SECRET-V2\n- AC-KEEP-ONE\n- AC-KEEP-TWO' }
  })
  const u = named(calls, /^uat:1$/)[0]
  assert(u, labelsOf(calls).join())
  for (const bad of ['SECRET-V', 'SECRET-V2']) assert(!u.prompt.includes(bad), `UAT prompt leaks ${bad}`)
  assert(u.prompt.includes('AC-KEEP-ONE') && u.prompt.includes('AC-KEEP-TWO'), u.prompt)
})

test('u2c: wrapped Verify text and indented sub-bullets stay out of the UAT prompt', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], {})] }, c => {
    if (c.label === 'request:1') return { body: 'Do the thing.\nVerify: SECRET-V start the app and\nSECRET-WRAP then click\n  - SECRET-SUB one\n    - SECRET-SUB2 deeper\n- AC-KEEP-ONE\nAC-KEEP-TWO: tight' }
  })
  const u = named(calls, /^uat:1$/)[0]
  assert(u, labelsOf(calls).join())
  for (const bad of ['SECRET-V', 'SECRET-WRAP', 'SECRET-SUB', 'SECRET-SUB2']) assert(!u.prompt.includes(bad), `UAT prompt leaks ${bad}`)
  assert(u.prompt.includes('AC-KEEP-ONE') && u.prompt.includes('AC-KEEP-TWO'), u.prompt)
})

test('u2d: a hyphenated AC label under a Verify row ends the row and stays in the UAT prompt', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], {})] }, c => {
    if (c.label === 'request:1') return { body: 'Do the thing.\nVerify: SECRET-V start the app\nAC-2: AC-KEEP-HYPHEN\nUser-Story: AC-KEEP-LABEL' }
  })
  const u = named(calls, /^uat:1$/)[0]
  assert(u, labelsOf(calls).join())
  assert(!u.prompt.includes('SECRET-V'), 'UAT prompt leaks SECRET-V')
  assert(u.prompt.includes('AC-2: AC-KEEP-HYPHEN') && u.prompt.includes('User-Story: AC-KEEP-LABEL'), u.prompt)
})

test('u3: the UAT phase sits between Intent review and Testing', async () => {
  const { calls } = await run({}, null)
  const ls = labelsOf(calls)
  assert(ls.indexOf('intent-review') < ls.indexOf('uat:1') && ls.indexOf('uat:1') < ls.indexOf('suite'), ls.join())
  assert(/title: 'Intent review'[\s\S]*title: 'UAT'[\s\S]*title: 'Testing'/.test(metaText()))
})

test('u4: an AC failure gives one fix and one rerun in its own worktree; passing on the rerun keeps the ticket done', async () => {
  const { calls, result } = await run({}, c => {
    if (c.label === 'uat:1') return uatRes(false, [sc('S1', 'AC1', 'ac', 'FAIL')])
  })
  assert.deepStrictEqual(labelsOf(calls).filter(l => /^uat/.test(l)), ['uat:1', 'uat-fix:1', 'uat-rerun:1'])
  const first = named(calls, /^uat:1$/)[0], again = named(calls, /^uat-rerun:1$/)[0], fix = named(calls, /^uat-fix:1$/)[0]
  assert(first.prompt.includes('/.ship-repo/ms/uat-1'), first.prompt.slice(0, 200))
  assert(again.prompt.includes('/.ship-repo/ms/uat-rerun-1') && !again.prompt.includes('worktree add --detach /.ship-repo/ms/uat-1 '), again.prompt.slice(0, 200))
  assert.strictEqual(fix.opts.phase, 'UAT')
  assert.strictEqual(result.tickets[0].status, 'done')
})

test('u5b: a skipped or failed UAT fix starts no rerun and the AC failure stands', async () => {
  for (const fix_status of ['skipped', 'failed']) {
    const { calls, result } = await run({}, c => {
      if (c.label === 'uat:1') return uatRes(false, [sc('S1', 'AC1', 'ac', 'FAIL')])
      if (c.label === 'uat-fix:1') return ok({ fix_status })
    })
    assert.strictEqual(named(calls, /^uat-fix:/).length, 1)
    assert.strictEqual(named(calls, /^uat-rerun:/).length, 0, fix_status)
    assert.strictEqual(result.tickets[0].reason, 'UAT AC failed')
  }
})

test('u5c: a FAIL row fails the run even when passed_ac is true', async () => {
  const { calls, result } = await run({}, c => (/^uat(-rerun)?:1$/.test(c.label) ? uatRes(true, [sc('S1', 'AC1', 'ac', 'FAIL')]) : undefined))
  assert.strictEqual(named(calls, /^uat-fix:/).length, 1)
  assert.strictEqual(result.tickets[0].reason, 'UAT AC failed')
})

test('u5e: a missing passed_ac is not a pass', async () => {
  const { calls, result } = await run({}, c => (/^uat(-rerun)?:1$/.test(c.label) ? uatRes(undefined, [sc('S1', 'AC1', 'ac', 'PASS')]) : undefined))
  assert.strictEqual(named(calls, /^uat-fix:/).length, 1)
  assert.strictEqual(result.tickets[0].reason, 'UAT AC failed')
})

test('u5f: the uat-fix prompt says console errors are report-only and never asks to fix them', async () => {
  const { calls } = await run({}, c => (c.label === 'uat:1' ? uatRes(false, [sc('S1', 'AC1', 'ac', 'FAIL')], { console_errors: 3 }) : undefined))
  const fix = named(calls, /^uat-fix:1$/)[0]
  assert(fix, labelsOf(calls).join())
  assert(!fix.prompt.includes('the console had'), fix.prompt)
  assert(fix.prompt.includes('Console errors are report-only'), fix.prompt)
})

test('u5d: console errors alone do not fail a run whose ACs all pass', async () => {
  const { calls, result } = await run({}, c => (/^uat(-rerun)?:1$/.test(c.label) ? uatRes(true, [sc('S1', 'AC1', 'ac', 'PASS')], { console_errors: 2 }) : undefined))
  assert.strictEqual(named(calls, /^uat-fix:/).length, 0)
  assert.notStrictEqual(result.tickets[0].reason, 'UAT AC failed')
})

test('u5: a second AC failure marks the ticket blocked with reason UAT AC failed; the PR still opens', async () => {
  const { calls, result } = await run({}, c => {
    if (/^uat(-rerun)?:1$/.test(c.label)) return uatRes(false, [sc('S1', 'AC1', 'ac', 'FAIL')])
  })
  assert.strictEqual(named(calls, /^uat-fix:/).length, 1)
  assert.strictEqual(named(calls, /^uat-rerun:/).length, 1)
  assert.strictEqual(result.tickets[0].status, 'blocked')
  assert.strictEqual(result.tickets[0].reason, 'UAT AC failed')
  assert.strictEqual(result.final.pr, 101)
  const body = named(calls, /^adr$/)[0].prompt
  assert(body.includes('- #1 blocked') && body.includes('(UAT AC failed)') && body.includes('Refs #1') && !body.includes('Closes #1'), body)
  assert(result.decisions.some(d => d.stage === 'uat' && d.needs_review === true && d.title.includes('UAT AC failed')))
})

test('u6: a negative failure becomes a needs_review decision and the run continues', async () => {
  const { calls, result } = await run({}, c => {
    if (c.label === 'uat:1') return uatRes(true, [sc('S1', 'AC1', 'ac', 'PASS'), sc('S2', 'negative', 'negative', 'FAIL')], { non_ac_failures: [{ id: 'S2', detail: 'empty password was accepted' }] })
  })
  assert.strictEqual(named(calls, /^uat-fix:/).length, 0)
  assert.strictEqual(result.tickets[0].status, 'done')
  const d = result.decisions.find(x => x.stage === 'uat' && x.title.includes('S2'))
  assert(d && d.needs_review === true, JSON.stringify(result.decisions))
  assert(labelsOf(calls).includes('suite') && labelsOf(calls).includes('adr'))
})

test('u7: a blocked or empty UAT run is not an AC failure: no fix, ticket stays done, decision recorded', async () => {
  for (const reply of [ok({ status: 'blocked', blocked_reason: 'no verify.config.json', passed_ac: false, scenarios: [] }), null, new Error('boom')]) {
    const { calls, result } = await run({}, c => (c.label === 'uat:1' ? reply : undefined))
    assert.strictEqual(named(calls, /^uat-(fix|rerun)/).length, 0)
    assert.strictEqual(result.tickets[0].status, 'done')
    assert(result.decisions.some(d => d.title === 'UAT not run for #1' && d.needs_review === true))
    assert(named(calls, /^adr$/)[0].prompt.includes('UAT: not run'))
  }
})

test('u8: tickets run UAT in input order, one agent per ticket with its own worktree', async () => {
  const { calls } = await run({ tickets: [T(1, 1), T(2, 1)] }, null)
  const us = named(calls, /^uat:/)
  assert.deepStrictEqual(us.map(c => c.label), ['uat:1', 'uat:2'])
  assert(us[0].prompt.includes('/uat-1') && us[1].prompt.includes('/uat-2'))
})

test('u9: the PR body has a UAT sign-off with one checkbox per scenario and the human-only points', async () => {
  const { calls } = await run({}, c => {
    if (c.label === 'uat:1') return uatRes(true, [sc('S1', 'AC1', 'ac', 'PASS'), sc('S2', 'AC2', 'not-browser-checkable', 'SKIPPED')])
  })
  const body = named(calls, /^adr$/)[0].prompt
  assert(body.includes('## UAT sign-off'), body)
  assert(body.includes('- [ ] S1 AC1 (ac): PASS: A-S1') && body.includes('- [ ] S2 AC2 (not-browser-checkable): SKIPPED'), body)
  for (const h of ['Copy reads right', 'Layout looks right', 'The flow feels right']) assert(body.includes(`- [ ] ${h}`), h)
})

test('u10: verify reports its config path and UAT gets it', async () => {
  const { calls } = await run({}, c => (c.label === 'verify:1' ? vres(true, 'FE', { configPath: '/wt/1/tests/fixtures/verify-app/verify.config.json' }) : c.label === 'verify-base:1' ? vres(false, 'FE') : undefined))
  assert(named(calls, /^uat:1$/)[0].prompt.includes('Config: /wt/1/tests/fixtures/verify-app/verify.config.json'))
})

test('u10b: UAT prompt falls back to the config in its own worktree when the path is missing', async () => {
  const { calls } = await run({})
  const p = named(calls, /^uat:1$/)[0].prompt
  assert(/If that file does not exist, use verify\.config\.json at the root of your own worktree/.test(p), p)
})

test('u11: UAT and uat-fix prompts hold real newlines, never a literal backslash-n', async () => {
  const { calls } = await run({}, c => (c.label === 'uat:1' ? uatRes(false, [sc('S1', 'AC1', 'ac', 'FAIL')]) : c.label === 'uat-rerun:1' ? uatRes(true, [sc('S1', 'AC1', 'ac', 'PASS')]) : undefined))
  for (const re of [/^uat:1$/, /^uat-fix:1$/]) {
    const p = named(calls, re)[0].prompt
    assert(!p.includes('\\n'), `${re} prompt has a literal backslash-n`)
  }
  assert(named(calls, /^uat:1$/)[0].prompt.includes('<<<\n'))
})

test('agent labels say what the agent does and fit the pane', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], { title: `😀 ${'long title '.repeat(20)}` })] }, c => (c.label === 'review:r0' ? ok({ findings: [{ id: 'f', path: 'src/some/very/long/path/to/a/file.js', line: 7, summary: 's', score: 90 }], skill_invoked: true }) : undefined))
  const shown = calls.map(c => c.display)
  for (const d of shown) assert(d && Array.from(d).length <= 70 && !/[\ud800-\udbff](?![\udc00-\udfff])/.test(d), `label too long or empty: ${d}`)
  assert(shown.some(d => /^#1 intent · .{1,40}$/u.test(d)), shown.join(' | '))
  assert(shown.includes('test · run full suite'), shown.join(' | '))
  assert(shown.some(d => d === 'fix r1.1 · file.js:7'), shown.join(' | '))
  assert(shown.every(d => !/^[a-z-]+:\w+/.test(d)), `a terse role:key label leaked: ${shown.join(' | ')}`)
})

test('schemas are well-formed (object root, required within properties)', async () => {
  const { calls } = await run({ tickets: [T(1, 1, [], { depth: 'L' }), T(2, 2, [1])] }, c => (c.label === 'suite' ? { passed: 1, failed: 1, skipped: 0, failing: ['t'] } : undefined))
  const check = (s, where) => {
    if (!s || typeof s !== 'object') return
    if (s.type === 'object' && s.required) for (const r of s.required) assert(s.properties && r in s.properties, `${where}: required '${r}' not in properties`)
    for (const [k, v] of Object.entries(s.properties || {})) check(v, `${where}.${k}`)
    if (s.items) check(s.items, `${where}[]`)
  }
  let seen = 0
  for (const c of calls) if (c.schema) { assert.strictEqual(c.schema.type, 'object', c.label); check(c.schema, c.label); seen++ }
  assert(seen > 10)
})

;(async () => {
  let failed = 0
  for (const c of cases) {
    try { await c.fn(); console.log(`PASS ${c.name}`) } catch (e) { failed++; console.log(`FAIL ${c.name}: ${String(e && e.message).split('\n')[0]}`) }
  }
  process.exit(failed ? 1 : 0)
})()

test('g1b: CI that ran on a head other than the branch tip fails the gate even with no fix commit', async () => {
  const r = await gateFlow({}, c => {
    if (c.label === 'gci:1') return { checks: [{ name: 'harness-ci', bucket: 'pass' }], headRefOid: 'oldheadsha1', branchTip: 'newtipsha22' }
  })
  assert.notStrictEqual(t1(r).status, 'done')
  const body = named(r.calls, /^gbody:1$/)[0].prompt
  assert(body.includes('stale'), body)
})

test('g1: CI that ran on a head older than the last pushed fix commit fails the gate', async () => {
  const r = await gateFlow({}, c => {
    if (c.label === 'greview:1:r0') return { findings: [{ id: 'F1', file: 'a.js', line: 1, score: 90, summary: 's', pre_existing: false }], skill_invoked: true, skill_error: '' }
    if (c.label === 'gci:1') return { checks: [{ name: 'harness-ci', bucket: 'pass' }], headRefOid: 'staleoldsha' }
  })
  assert.notStrictEqual(t1(r).status, 'done')
  const body = named(r.calls, /^gbody:1$/)[0].prompt
  assert(body.includes('stale'), body)
})
