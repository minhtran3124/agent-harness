#!/usr/bin/env node
'use strict';
// Tests for plugins/harness/board/board.js: label parsing, the stage -> box map, tailing a run dir, and the
// SSE server. No dependencies. Prints one PASS/FAIL line per case and exits 1 on any failure.
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const root = path.join(__dirname, '..', '..');
const B = require(path.join(root, 'plugins', 'harness', 'board', 'board.js'));
const FLOW = JSON.parse(fs.readFileSync(path.join(root, 'plugins', 'harness', 'board', 'flow.json'), 'utf8'));

const cases = [];
const test = (name, fn) => cases.push([name, fn]);
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'board-'));
const jl = rows => rows.map(r => JSON.stringify(r)).join('\n') + '\n';
const get = (port, p) => new Promise((res, rej) => http.get({ host: '127.0.0.1', port, path: p }, r => {
  let b = ''; r.on('data', c => { b += c; }); r.on('end', () => res({ status: r.statusCode, type: r.headers['content-type'], body: b }));
}).on('error', rej));
// Read SSE data lines until `want` returns true or the time runs out.
const sse = (port, want, ms = 3000) => new Promise((res, rej) => {
  const evs = [];
  const req = http.get({ host: '127.0.0.1', port, path: '/events' }, r => {
    let buf = '';
    r.on('data', c => {
      buf += c;
      let i;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, i); buf = buf.slice(i + 2);
        const line = block.split('\n').find(l => l.startsWith('data: '));
        if (line) evs.push(JSON.parse(line.slice(6)));
      }
      if (want(evs)) { req.destroy(); res(evs); }
    });
  });
  req.on('error', e => { if (e.code !== 'ECONNRESET') rej(e); });
  setTimeout(() => { req.destroy(); res(evs); }, ms);
});
const sleep = ms => new Promise(r => setTimeout(r, ms));

function makeRun(base, id, journal, agents, summary) {
  const dir = path.join(base, 'sess1', 'subagents', 'workflows', id);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'journal.jsonl'), jl(journal));
  for (const [aid, rows] of Object.entries(agents || {})) fs.writeFileSync(path.join(dir, `agent-${aid}.jsonl`), jl(rows));
  if (summary) {
    fs.mkdirSync(path.join(base, 'sess1', 'workflows'), { recursive: true });
    fs.writeFileSync(path.join(base, 'sess1', 'workflows', `${id}.json`), JSON.stringify(summary));
  }
  return dir;
}
const transcript = (t0, t1, model, effort) => [
  { type: 'user', timestamp: t0, effort, message: { role: 'user', content: 'SECRET PROMPT TEXT' } },
  { type: 'assistant', timestamp: t1, message: { id: 'm1', model, usage: { output_tokens: 9 }, content: [{ type: 'text', text: 'SECRET ANSWER' }] } },
];

test('qb1: parseLabel splits ticket, stage, round, retry and subject', () => {
  assert.deepStrictEqual(B.parseLabel('#321 QA check fix r2 · Lesson 4 follow-up'),
    { ticket: '321', stage: 'QA check fix', round: 2, retry: false, subject: 'Lesson 4 follow-up' });
  assert.deepStrictEqual(B.parseLabel('#7 implement retry · x'), { ticket: '7', stage: 'implement', round: null, retry: true, subject: 'x' });
  assert.deepStrictEqual(B.parseLabel('code-review · round 0'), { ticket: null, stage: 'code-review', round: null, retry: false, subject: 'round 0' });
  assert.strictEqual(B.parseLabel('fix r1.2 · finding').stage, 'fix');
  assert.strictEqual(B.parseLabel(undefined).stage, '?');
});

test('qb2: every agent label ship.js builds lands on the right box, or on none by design', () => {
  const want = {
    'intent': 'intent', 'design': 'intent', 'plan': 'intent', 'advisor plan-review': 'intent', 'qa': 'qaw',
    'implement': 'impl', 'verify': 'verify', 'verify-retry': 'verify', 'security gate': 'sec', 'finish': 'pr',
    'gate code-review': 'gate', 'gate CI checks': 'gate', 'merge ticket branches': 'gate', 'code-review': 'review', 'fix': 'review', 'measure diff size': 'review', 'gate measure diff size': 'gate',
    'intent review': 'irev', 'intent fix': 'irev', 'UAT': 'check', 'QA check': 'check', 'UAT fix': 'fix', 'QA check fix': 'fix',
    'UAT rerun': 'rerun', 'QA check rerun': 'rerun', 'advisor uat-fix': 'adv', 'advisor qa-verify-fix': 'adv', 'test': 'test',
    'write ADRs': 'adr', 'write specs/ flow files': 'adr', 'open final PR': 'final', 'CI snapshot': 'final',
    'check plugin and tools': null, 'set up integration branch': null, 'fetch owner request': null,
  };
  for (const [stage, node] of Object.entries(want)) assert.strictEqual(B.nodeFor(FLOW, stage), node, `stage "${stage}"`);
  // Drift guard: the fixed labels in ship.js must still be ones this map knows.
  const ship = fs.readFileSync(path.join(root, 'plugins', 'harness', 'workflows', 'ship.js'), 'utf8');
  const fixed = [...ship.matchAll(/label: '([^']+)'/g)].map(m => B.parseLabel(m[1]).stage);
  const known = new Set([...Object.keys(want), 'update run artifact', 'write specs/ early']);
  for (const s of fixed) assert.ok(known.has(s), `ship.js label stage "${s}" is not in the board map; add it to flow.json or to this list`);
});

test('qb3: statusOf maps agent results to board states', () => {
  assert.strictEqual(B.statusOf({ status: 'ok' }), 'done');
  assert.strictEqual(B.statusOf({ status: 'blocked' }), 'waiting');
  assert.strictEqual(B.statusOf({ status: 'failed' }), 'failed');
  assert.strictEqual(B.statusOf({ status: 'ok', passed_ac: false }), 'failed');
  assert.strictEqual(B.statusOf(null), 'done');
});

test('qb4: splitLines keeps a torn last line until the rest arrives', () => {
  const a = B.splitLines('', '{"a":1}\n{"b":');
  assert.deepStrictEqual(a.rows, [{ a: 1 }]);
  const b = B.splitLines(a.carry, '2}\nnot json\n');
  assert.deepStrictEqual(b.rows, [{ b: 2 }]);
  assert.strictEqual(b.carry, '');
});

test('qb5: RunTail emits started, facts and result with model, effort and times, and never prompt text', () => {
  const base = tmp();
  const dir = makeRun(base, 'wf_t1', [
    { type: 'launched' },
    { type: 'started', key: 'k1', agentId: 'a1', label: '#9 QA check · Fix docs', phase: 'UAT' },
  ], { a1: transcript('2026-11-11T08:00:00.000Z', '2026-11-11T08:01:00.000Z', 'claude-sonnet-5-5', 'medium') });
  const evs = [];
  const t = new B.RunTail({ id: 'wf_t1', dir, summary: path.join(base, 'sess1', 'workflows', 'wf_t1.json') }, FLOW, e => evs.push(e));
  t.tick();
  const st = evs.find(e => e.kind === 'started');
  assert.strictEqual(st.node, 'check'); assert.strictEqual(st.ticket, '9'); assert.strictEqual(st.ts, '2026-11-11T08:00:00.000Z');
  const f = evs.find(e => e.kind === 'agent_facts');
  assert.ok(evs.indexOf(st) < evs.indexOf(f), 'facts must follow started, or the page drops them');
  assert.strictEqual(f.model, 'claude-sonnet-5-5'); assert.strictEqual(f.effort, 'medium');
  fs.appendFileSync(path.join(dir, 'journal.jsonl'), jl([{ type: 'result', key: 'k1', agentId: 'a1',
    result: { status: 'ok', passed_ac: false, summary: 'AC2 fails', head_sha: 'abcdef1234567890',
      scenarios: [{ id: 'AC1', kind: 'ac', status: 'PASS' }, { id: 'AC2', kind: 'ac', status: 'FAIL' }, { id: 'S3', kind: 'not-checkable', status: 'SKIPPED' }] } }]));
  t.tick();
  const r = evs.find(e => e.kind === 'result');
  assert.strictEqual(r.status, 'failed');
  assert.deepStrictEqual(r.checks, { total: 3, passed: 1, failed: 1, not_checkable: 1 });
  assert.strictEqual(r.head_sha, 'abcdef123456');
  assert.ok(!JSON.stringify(evs).includes('SECRET'), 'an event carries transcript text');
});

test('qb6: the run summary ends the run; an agent with no result stays open until then', () => {
  const base = tmp();
  const dir = makeRun(base, 'wf_k', [{ type: 'started', key: 'k', agentId: 'a1', label: '#5 QA check · t', phase: 'UAT' }], {},
    { status: 'killed', durationMs: 609006, result: null, logs: ['ship #5 -> feat/x', 'a'.repeat(500)] });
  const evs = [];
  const t = new B.RunTail({ id: 'wf_k', dir, summary: path.join(base, 'sess1', 'workflows', 'wf_k.json') }, FLOW, e => evs.push(e));
  t.tick(); t.tick();
  const end = evs.filter(e => e.kind === 'run_end');
  assert.strictEqual(end.length, 1, 'run_end is sent once');
  assert.strictEqual(end[0].status, 'killed');
  assert.ok(end[0].logs[1].length <= 200);
});

test('qb7: runsOf finds runs newest first; projectKey matches the Claude Code dir name', async () => {
  assert.strictEqual(B.projectKey('/home/minhtran/Documents/minh.tran/projects/agent-harness'),
    '-home-minhtran-Documents-minh-tran-projects-agent-harness');
  const base = tmp();
  makeRun(base, 'wf_old', [{ type: 'launched' }]);
  await sleep(20);
  makeRun(base, 'wf_new', [{ type: 'launched' }]);
  assert.deepStrictEqual(B.runsOf(base).map(r => r.id), ['wf_new', 'wf_old']);
  assert.strictEqual(B.resolveRun(path.join(base, 'sess1', 'subagents', 'workflows', 'wf_old')).id, 'wf_old');
  assert.throws(() => B.resolveRun('../etc', base), /neither a run dir nor a run id/);
});

test('qb8: the server binds 127.0.0.1, serves the page and flow, replays and streams events', async () => {
  const base = tmp();
  const dir = makeRun(base, 'wf_s', [{ type: 'started', key: 'k', agentId: 'a1', label: '#3 implement · t', phase: 'Tickets' }],
    { a1: transcript('2026-11-11T08:00:00.000Z', '2026-11-11T08:00:05.000Z', 'claude-opus-5-5', 'high') });
  const { server, port } = await B.start({ port: 0, projectDir: base, follow: true, pollMs: 50 });
  try {
    assert.strictEqual(server.address().address, '127.0.0.1');
    const page = await get(port, '/');
    assert.ok(page.type.startsWith('text/html') && page.body.includes('Agent Flow Board'));
    assert.strictEqual(JSON.parse((await get(port, '/flow.json')).body).nodes.length, FLOW.nodes.length);
    assert.strictEqual((await get(port, '/nope')).status, 404);
    const first = await sse(port, evs => evs.some(e => e.kind === 'started'));
    assert.ok(first.some(e => e.kind === 'run' && e.run_id === 'wf_s'), 'replay names the run');
    const live = sse(port, evs => evs.some(e => e.kind === 'result'));
    await sleep(100);
    fs.appendFileSync(path.join(dir, 'journal.jsonl'), jl([{ type: 'result', key: 'k', agentId: 'a1', result: { status: 'ok', summary: 'done' } }]));
    const evs = await live;
    const r = evs.find(e => e.kind === 'result');
    assert.ok(r && r.node === 'impl' && r.status === 'done', 'a line appended to the journal reaches the page');
  } finally { server.close(); }
});

test('qb9: the server follows a newer run of the project', async () => {
  const base = tmp();
  makeRun(base, 'wf_a', [{ type: 'launched' }]);
  const { server, port } = await B.start({ port: 0, projectDir: base, follow: true, pollMs: 50 });
  try {
    await sleep(60);
    makeRun(base, 'wf_b', [{ type: 'started', key: 'k', agentId: 'b1', label: 'test · run full suite', phase: 'Testing' }]);
    await sleep(300);
    const st = JSON.parse((await get(port, '/state.json')).body);
    assert.strictEqual(st.run, 'wf_b');
    assert.ok(st.events.some(e => e.kind === 'started' && e.node === 'test'));
  } finally { server.close(); }
});

test('qb10: flow.json is consistent and the page has no external resources', () => {
  const ids = new Set(FLOW.nodes.map(n => n.id));
  assert.strictEqual(ids.size, FLOW.nodes.length, 'duplicate node id');
  for (const e of FLOW.edges) assert.ok(ids.has(e[0]) && ids.has(e[1]), `edge ${e[0]} -> ${e[1]}`);
  for (const n of FLOW.nodes) { assert.ok(n.match && n.match.length, `${n.id} has no match`); n.match.forEach(re => new RegExp(re)); }
  const html = fs.readFileSync(path.join(root, 'plugins', 'harness', 'board', 'board.html'), 'utf8');
  assert.ok(!/(src|href)=["']https?:/i.test(html) && !/@import|fonts\.googleapis/.test(html), 'the page loads something from the network');
  assert.throws(() => B.parseArgs(['--port', '70000']), /--port/);
});

test('qb11: --idle-exit stops the server once no run is going, and not while one runs', async () => {
  const base = tmp();
  makeRun(base, 'wf_live', [{ type: 'started', key: 'k', agentId: 'a1', label: '#1 implement · t', phase: 'Tickets' }]);
  const live = await B.start({ port: 0, projectDir: base, follow: true, pollMs: 30, idleExit: 0.002 });
  let closed = false; live.server.on('close', () => { closed = true; });
  await sleep(400);
  assert.ok(!closed, 'a running run keeps the board up');
  fs.mkdirSync(path.join(base, 'sess1', 'workflows'), { recursive: true });
  fs.writeFileSync(path.join(base, 'sess1', 'workflows', 'wf_live.json'), JSON.stringify({ status: 'completed', durationMs: 1, result: null }));
  for (let i = 0; i < 40 && !closed; i++) await sleep(50);
  assert.ok(closed, 'the board stops after the idle time once the run ended');
  assert.throws(() => B.parseArgs(['--idle-exit', 'x']), /--idle-exit/);
});

test('qb12: the page works under a path prefix and has an embed mode', () => {
  const html = fs.readFileSync(path.join(root, 'plugins', 'harness', 'board', 'board.html'), 'utf8');
  // A proxy can serve the board at /board/<project>/: every URL the page loads is relative.
  assert.ok(!/(fetch|EventSource)\(\s*['"]\//.test(html), 'the page requests an absolute path');
  assert.ok(/EventSource\('events'\)/.test(html) && /fetch\('flow\.json'\)/.test(html));
  // ?embed=1 hides the page header and footer note; the host page gets only a height number.
  assert.ok(/\.embed \.top,\.embed \.note\{display:none\}/.test(html));
  assert.ok(/postMessage\(\{type:'afb-height',height:h\}/.test(html));
});

(async () => {
  let failed = 0;
  for (const [name, fn] of cases) {
    try { await fn(); console.log(`PASS ${name}`); } catch (e) { failed++; console.log(`FAIL ${name}\n  ${e && e.stack ? e.stack.split('\n').slice(0, 3).join('\n  ') : e}`); }
  }
  console.log(failed ? `board: ${failed} failed` : `board: ${cases.length} passed`);
  process.exit(failed ? 1 : 0);
})();
