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
  if (l.startsWith('finish:')) return ok({ pr: args0.local ? 0 : 100 + Number(n), url: `https://x/pull/${100 + Number(n)}` })
  if (l.startsWith('merge:')) return ok({ merged: [...c.prompt.matchAll(/^- #(\d+)/gm)].map(m => Number(m[1])), failed: [] })
  if (l === 'final-pr') return ok({ pr: args0.local ? 0 : 900, url: 'https://x/pull/900' })
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
    const call = { prompt, opts, label: opts.label, schema: opts.schema }
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
    assert(p.includes(`Read /plug/skills/${sk}/SKILL.md`) && !p.includes('.claude/'), `${l}: ${p.match(/Read [^\n]*/)}`)
    assert(!/Read skills\//.test(p), l)
  }
  const fin = named(calls, /^finish:1$/)[0].prompt
  assert(fin.includes('Read /plug/skills/finishing-a-development-branch/SKILL.md'), fin.match(/Read [^\n]*/)[0])
  assert(named(calls, /^implement:1$/)[0].prompt.includes('/plug/agents/implementer.md') && !named(calls, /^implement:1$/)[0].prompt.includes('.claude/'))
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
  assert(p.includes('needs_review: true ONLY when the decision affects another ticket, a public contract or interface, stored data, security or cost, or contradicts the ticket text or an owner-confirmed answer'))
  assert(p.includes('needs_review: false'))
  const dec = named(calls, /^intent:1$/)[0].schema.properties.decisions.items.properties.needs_review
  assert(/ONLY when/.test(dec.description) && /false/.test(dec.description))
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
  assert(c.prompt.includes('/plug/agents/intent-reviewer.md') && !c.prompt.includes('.claude/'))
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
  assert(p.includes('names the missing permission') && p.includes('allows gh pr merge into feat/ms*'))
  const l = await run({ tickets: [T(1, 1), T(2, 1)], local: true }, null)
  assert(!named(l.calls, /^merge:g1$/)[0].prompt.includes('gh pr view'), 'local mode has no PRs')
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

test('f: intent review sees the request and not the plan, confirmed answers or decisions', async () => {
  const dec = { title: 'DECISION-TITLE-XYZ', context: 'c', options: ['a'], decision: 'd', why: 'w', consequences: 'x', how_to_reverse: 'r', confidence: 'high', needs_review: false }
  const { calls, result } = await run({ tickets: [T(1, 1, [], { confirmed: 'CONFIRMED-ANSWER-QQ' })] }, c => {
    if (c.label === 'intent:1') return ok({ goal: 'GOAL-SECRET', decisions: [dec], summary: 'SUMMARY-SECRET', plan_steps: [{ title: 'PLANSTEP-ABC', files: [], done_when: 'x' }] })
    if (c.label === 'intent-review') return { verdict: 'gaps found', findings: [{ kind: 'gap', clause: 'CLAUSE-1', detail: 'missing' }, { kind: 'excess', clause: 'C2', detail: 'extra' }] }
  })
  const p = named(calls, /^intent-review$/)[0]
  assert.strictEqual(p.opts.agentType, 'harness:intent-reviewer')
  assert(p.prompt.includes('REQUEST-BODY-1') && p.prompt.includes('origin/v5.0.0..origin/feat/1-ticket-1'))
  for (const bad of ['CONFIRMED-ANSWER-QQ', 'PLANSTEP-ABC', 'DECISION-TITLE-XYZ', 'GOAL-SECRET', 'SUMMARY-SECRET', 'did it']) assert(!p.prompt.includes(bad), `leaked ${bad}`)
  assert.strictEqual(named(calls, /^request:1$/)[0].prompt.includes('gh issue view 1 --repo o/r --json body -q .body'), true)
  assert.strictEqual(named(calls, /^intent-fix$/).length, 1, 'a gap gets one fix round')
  assert(result.intent.gaps.length === 2)
  const ls = labelsOf(calls)
  assert(ls.indexOf('intent-fix') < ls.indexOf('suite'))
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
  assert.strictEqual(labelsOf(calls)[labelsOf(calls).length - 1], 'adr')
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
  assert(!all.includes('/plug/') && !all.includes('.claude/'))
})

test('m: a plugin check that fails stops the run before any ticket stage', async () => {
  await assert.rejects(() => run({}, c => (c.label === 'plugin-check' ? { status: 'blocked', blocked_reason: 'pluginDir missing', summary: '' } : undefined)), /pluginDir missing/)
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
