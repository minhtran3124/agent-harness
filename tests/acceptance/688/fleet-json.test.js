#!/usr/bin/env node
'use strict';
// Acceptance tests for #688 "board: show a Pod Bay fleet run": the JSON, discovery and route criteria.
// Plain node, no browser. Each case starts its own board through the CLI
//   node plugins/harness/board/board.js --port <free port> [--ledger <file>] [--project <dir>]
// on a free port, with HOME set to a fresh temp dir (so no real ~/.claude run leaks in), and stops it afterwards.
// Prints one PASS/FAIL line per case and exits 1 on any failure.
// Run: node tests/acceptance/688/fleet-json.test.js
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const net = require('net');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

const root = path.join(__dirname, '..', '..', '..');
const BOARD = path.join(root, 'plugins', 'harness', 'board', 'board.js');

const cases = [];
const test = (name, fn) => cases.push([name, fn]);
const tmp = p => fs.mkdtempSync(path.join(os.tmpdir(), `acc688-${p}-`));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const get = (port, p) => new Promise((res, rej) => http.get({ host: '127.0.0.1', port, path: p }, r => {
  let b = ''; r.on('data', c => { b += c; }); r.on('end', () => res({ status: r.statusCode, type: r.headers['content-type'] || '', body: b }));
}).on('error', rej));
// The first response headers only (for the SSE stream, which never ends).
const head = (port, p) => new Promise((res, rej) => {
  const req = http.get({ host: '127.0.0.1', port, path: p }, r => { res({ status: r.statusCode, type: r.headers['content-type'] || '' }); req.destroy(); });
  req.on('error', e => { if (e.code !== 'ECONNRESET') rej(e); });
});
const freePort = () => new Promise((res, rej) => {
  const s = net.createServer(); s.unref(); s.on('error', rej);
  s.listen(0, '127.0.0.1', () => { const { port } = s.address(); s.close(() => res(port)); });
});

// Start the board CLI; resolve once /healthz answers. Fails with the board's own output if it exits first.
async function board(args, cwd) {
  const port = await freePort();
  const env = { ...process.env, HOME: tmp('home') };
  delete env.CLAUDE_CONFIG_DIR;
  const child = spawn(process.execPath, [BOARD, '--port', String(port), ...args], { cwd: cwd || tmp('cwd'), env, stdio: ['ignore', 'pipe', 'pipe'] });
  let out = ''; child.stdout.on('data', c => { out += c; }); child.stderr.on('data', c => { out += c; });
  let exited = null; child.on('exit', code => { exited = code; });
  for (let i = 0; i < 100; i++) {
    if (exited !== null) throw new Error(`board exited with code ${exited} before it answered: ${out.trim()}`);
    try { const r = await get(port, '/healthz'); if (r.status === 200) return { port, child, stop: () => child.kill() }; } catch (e) { /* not up yet */ }
    await sleep(50);
  }
  child.kill();
  throw new Error(`board did not answer on port ${port} within 5 s: ${out.trim()}`);
}
async function withBoard(args, cwd, fn) {
  const b = await board(args, cwd);
  try { return await fn(b.port, b); } finally { b.stop(); }
}

// A ledger in the format of plugins/harness/skills/pd-orchestrate/references/protocol.md, section "Ledger".
const LEDGER = {
  v: 1, run: 'r688', base: 'feat/fleet', repo: 'owner/name',
  tickets: {
    '10': { state: 'in_review', kind: 'feature', depth: 'M', app: 'none', risky: false, deps: [], text: 'ten',
      worker: { session: 'w-ten', workspace: 'src-02', checkout: '/abs/src-02', model: 'm' },
      reviewer: { session: 'r-ten', model: 'm' }, branch: 'feat/10', head: 'head10', pr: 'https://github.com/owner/name/pull/10' },
    '9': { state: 'blocked', kind: 'bug', depth: 'S', worker: { session: 'w-nine' }, reviewer: null, head: 'head9', pr: 42 },
    'x-a': { state: 'queued' },
    '2': { state: 'escalated', worker: { workspace: 'src-03' } },
    'b7': { state: 'done', kind: 'docs', depth: 'S', worker: { session: 'w-b7' }, reviewer: { session: 'r-b7' }, head: 'headb7', pr: null },
  },
};
const writeLedger = (file, obj) => { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2)); return file; };
const ledgerFile = (obj = LEDGER) => writeLedger(path.join(tmp('led'), 'specs', 'fleet', 'r688', 'ledger.json'), obj);
const KEYS = ['id', 'state', 'kind', 'depth', 'worker', 'reviewer', 'head', 'pr'];
const json = r => { try { return JSON.parse(r.body); } catch (e) { throw new Error(`body is not JSON (status ${r.status}): ${r.body.slice(0, 200)}`); } };
const fleet = async port => { const r = await get(port, '/fleet.json'); return { r, j: r.status === 200 ? json(r) : null }; };
const ids = j => j.tickets.map(t => t.id);

// ---------- AC1 ----------
// "`node plugins/harness/board/board.js --ledger <path to ledger.json>` serves the fleet view of that ledger."
test('AC1: --ledger <file> serves the fleet view of that ledger', () => withBoard(['--ledger', ledgerFile()], null, async port => {
  const { r, j } = await fleet(port);
  assert.strictEqual(r.status, 200, `GET /fleet.json status ${r.status}: ${r.body.slice(0, 200)}`);
  assert.strictEqual(j.run, 'r688'); assert.strictEqual(j.base, 'feat/fleet');
}));

// "Without `--ledger`, the board picks the newest `specs/fleet/*/ledger.json` (by modification time) under the
// project directory (`--project`, default the current directory)"
function twoLedgers() {
  const proj = tmp('proj');
  // Name order is the opposite of time order, so a pick by name fails.
  const older = writeLedger(path.join(proj, 'specs', 'fleet', 'z-older', 'ledger.json'), { ...LEDGER, run: 'z-older' });
  const newer = writeLedger(path.join(proj, 'specs', 'fleet', 'a-newer', 'ledger.json'), { ...LEDGER, run: 'a-newer' });
  const now = Date.now() / 1000;
  fs.utimesSync(older, now - 3600, now - 3600);
  fs.utimesSync(newer, now - 60, now - 60);
  return proj;
}
test('AC1: without --ledger, picks the newest specs/fleet/*/ledger.json by mtime under --project', () => withBoard(['--project', twoLedgers()], null, async port => {
  const { r, j } = await fleet(port);
  assert.strictEqual(r.status, 200, `GET /fleet.json status ${r.status}: ${r.body.slice(0, 200)}`);
  assert.strictEqual(j.run, 'a-newer');
}));
test('AC1: without --ledger and --project, the project is the current directory', () => withBoard([], twoLedgers(), async port => {
  const { r, j } = await fleet(port);
  assert.strictEqual(r.status, 200, `GET /fleet.json status ${r.status}: ${r.body.slice(0, 200)}`);
  assert.strictEqual(j.run, 'a-newer');
}));

// ---------- AC2 ----------
// "`GET /fleet.json` returns 200 and `application/json` with {"run":<ledger run>,"base":<ledger base>,"tickets":[{"id",
// "state","kind","depth","worker","reviewer","head","pr"}]}: one entry per ticket of the ledger, sorted by id, where
// `worker` and `reviewer` are the session names (`worker.session`, `reviewer.session`, or null) and missing fields are null."
// Owner: sort numerically when both ids are all digits (9 before 10), otherwise as strings; pass `pr` through unchanged.
test('AC2: GET /fleet.json is 200 application/json with run, base and one entry per ticket', () => withBoard(['--ledger', ledgerFile()], null, async port => {
  const { r, j } = await fleet(port);
  assert.strictEqual(r.status, 200, `status ${r.status}: ${r.body.slice(0, 200)}`);
  assert.ok(r.type.startsWith('application/json'), `content-type ${r.type}`);
  assert.strictEqual(j.run, 'r688'); assert.strictEqual(j.base, 'feat/fleet');
  assert.ok(Array.isArray(j.tickets), 'tickets is not an array');
  assert.strictEqual(j.tickets.length, 5);
  for (const t of j.tickets) for (const k of KEYS) assert.ok(Object.prototype.hasOwnProperty.call(t, k), `ticket ${t.id} has no "${k}"`);
}));
test('AC2: tickets sorted by id: numeric ids numerically (9 before 10), other ids as strings', () => withBoard(['--ledger', ledgerFile()], null, async port => {
  const { r, j } = await fleet(port);
  assert.strictEqual(r.status, 200, `status ${r.status}`);
  assert.deepStrictEqual(ids(j), ['2', '9', '10', 'b7', 'x-a']);
}));
test('AC2: worker and reviewer are session names or null; missing fields are null; pr passes through unchanged', () => withBoard(['--ledger', ledgerFile()], null, async port => {
  const { r, j } = await fleet(port);
  assert.strictEqual(r.status, 200, `status ${r.status}`);
  const by = Object.fromEntries(j.tickets.map(t => [t.id, Object.fromEntries(KEYS.map(k => [k, t[k]]))]));
  assert.deepStrictEqual(by['10'], { id: '10', state: 'in_review', kind: 'feature', depth: 'M', worker: 'w-ten', reviewer: 'r-ten', head: 'head10', pr: 'https://github.com/owner/name/pull/10' });
  assert.deepStrictEqual(by['9'], { id: '9', state: 'blocked', kind: 'bug', depth: 'S', worker: 'w-nine', reviewer: null, head: 'head9', pr: 42 });
  assert.deepStrictEqual(by['2'], { id: '2', state: 'escalated', kind: null, depth: null, worker: null, reviewer: null, head: null, pr: null });
  assert.deepStrictEqual(by['x-a'], { id: 'x-a', state: 'queued', kind: null, depth: null, worker: null, reviewer: null, head: null, pr: null });
  assert.deepStrictEqual(by['b7'], { id: 'b7', state: 'done', kind: 'docs', depth: 'S', worker: 'w-b7', reviewer: 'r-b7', head: 'headb7', pr: null });
}));

// ---------- AC3 ----------
// "With no fleet run, `GET /fleet.json` returns 404 and `{"error":"no fleet run"}`."
// (AC1: "when there is none, it has no fleet run.")
test('AC3: no ledger under --project -> 404 {"error":"no fleet run"}', () => withBoard(['--project', tmp('empty')], null, async port => {
  const r = await get(port, '/fleet.json');
  assert.strictEqual(r.status, 404);
  assert.deepStrictEqual(json(r), { error: 'no fleet run' });
}));
test('AC3: no ledger in the current directory (no --project) -> 404 {"error":"no fleet run"}', () => withBoard([], tmp('emptycwd'), async port => {
  const r = await get(port, '/fleet.json');
  assert.strictEqual(r.status, 404);
  assert.deepStrictEqual(json(r), { error: 'no fleet run' });
}));
// "With a ledger that does not parse, it returns 503 and `{"error":"<short reason>"}`, and the board keeps running."
test('AC3: a ledger that does not parse -> 503 {"error":<reason>}, and the board keeps running', () => {
  const file = ledgerFile('{"v": 1, "run": "r688", "tickets": {');
  return withBoard(['--ledger', file], null, async (port, b) => {
    const r = await get(port, '/fleet.json');
    assert.strictEqual(r.status, 503, `status ${r.status}: ${r.body.slice(0, 200)}`);
    const j = json(r);
    assert.deepStrictEqual(Object.keys(j), ['error']);
    assert.ok(typeof j.error === 'string' && j.error.length > 0, 'error is not a non-empty string');
    await sleep(200);
    assert.strictEqual(b.child.exitCode, null, 'the board process exited');
    assert.strictEqual((await get(port, '/healthz')).status, 200, '/healthz no longer answers');
    assert.strictEqual((await get(port, '/fleet.json')).status, 503, 'a second request does not answer 503');
  });
});
test('AC3: discovered ledger that does not parse -> 503, and the board keeps running', () => {
  const proj = tmp('badproj');
  writeLedger(path.join(proj, 'specs', 'fleet', 'r1', 'ledger.json'), 'not json at all');
  return withBoard(['--project', proj], null, async port => {
    const r = await get(port, '/fleet.json');
    assert.strictEqual(r.status, 503, `status ${r.status}: ${r.body.slice(0, 200)}`);
    assert.ok(typeof json(r).error === 'string' && json(r).error.length > 0);
    assert.strictEqual((await get(port, '/healthz')).status, 200);
  });
});

// ---------- AC4 ----------
// "The ledger is read again on every request, so a change shows without a restart."
test('AC4: a change to the ledger shows on the next request without a restart', () => {
  const file = ledgerFile();
  return withBoard(['--ledger', file], null, async port => {
    let { r, j } = await fleet(port);
    assert.strictEqual(r.status, 200, `status ${r.status}`);
    assert.strictEqual(j.tickets.find(t => t.id === '10').state, 'in_review');
    const next = JSON.parse(JSON.stringify(LEDGER));
    next.tickets['10'].state = 'pr_open';
    next.tickets['10'].worker.session = 'w-ten-2';
    next.tickets['11'] = { state: 'assigned' };
    writeLedger(file, next);
    ({ r, j } = await fleet(port));
    assert.strictEqual(r.status, 200, `status ${r.status}`);
    const t10 = j.tickets.find(t => t.id === '10');
    assert.strictEqual(t10.state, 'pr_open'); assert.strictEqual(t10.worker, 'w-ten-2');
    assert.deepStrictEqual(ids(j), ['2', '9', '10', '11', 'b7', 'x-a']);
  });
});
test('AC4: a ledger broken and then fixed answers 503 and then 200 without a restart', () => {
  const file = ledgerFile();
  return withBoard(['--ledger', file], null, async port => {
    assert.strictEqual((await get(port, '/fleet.json')).status, 200);
    writeLedger(file, '{ torn write');
    assert.strictEqual((await get(port, '/fleet.json')).status, 503);
    writeLedger(file, { ...LEDGER, run: 'r688-fixed' });
    const { r, j } = await fleet(port);
    assert.strictEqual(r.status, 200);
    assert.strictEqual(j.run, 'r688-fixed');
  });
});

// ---------- AC5 (the server half; the page itself is checked in fleet-page.test.js with a browser) ----------
// "`GET /fleet` returns an HTML page ..."
test('AC5: GET /fleet returns 200 and an HTML page', () => withBoard(['--ledger', ledgerFile()], null, async port => {
  const r = await get(port, '/fleet');
  assert.strictEqual(r.status, 200, `status ${r.status}`);
  assert.ok(r.type.startsWith('text/html'), `content-type ${r.type}`);
  assert.ok(/<html/i.test(r.body), 'body is not an HTML page');
}));

// ---------- AC6 ----------
// "The existing routes and the ship.js view do not change. The board README documents the fleet view."
const FLOW = JSON.parse(fs.readFileSync(path.join(root, 'plugins', 'harness', 'board', 'flow.json'), 'utf8'));
async function existingRoutes(port) {
  const h = await get(port, '/healthz');
  assert.strictEqual(h.status, 200); assert.ok(h.type.startsWith('application/json'));
  assert.deepStrictEqual(json(h), { ok: true, run: null, running: false });
  const s = await get(port, '/state.json');
  assert.strictEqual(s.status, 200); assert.ok(s.type.startsWith('application/json'));
  const sj = json(s); assert.strictEqual(sj.run, null); assert.deepStrictEqual(sj.events, []);
  const f = await get(port, '/flow.json');
  assert.strictEqual(f.status, 200); assert.deepStrictEqual(json(f), FLOW);
  for (const p of ['/', '/index.html']) {
    const r = await get(port, p);
    assert.strictEqual(r.status, 200, `${p} status ${r.status}`); assert.ok(r.type.startsWith('text/html'), `${p} type ${r.type}`);
    assert.ok(r.body.includes('Agent Flow Board'), `${p} is not the ship.js board page`);
  }
  const e = await head(port, '/events');
  assert.strictEqual(e.status, 200); assert.ok(e.type.startsWith('text/event-stream'), `/events type ${e.type}`);
  assert.strictEqual((await get(port, '/no-such-route')).status, 404);
}
test('AC6: existing routes answer as before with no fleet run', () => withBoard(['--project', tmp('plain')], null, existingRoutes));
test('AC6: existing routes answer as before when --ledger is given', () => withBoard(['--ledger', ledgerFile()], null, existingRoutes));
test('AC6: the board README documents the fleet view (--ledger, /fleet, /fleet.json)', () => {
  const readme = fs.readFileSync(path.join(root, 'plugins', 'harness', 'board', 'README.md'), 'utf8');
  assert.ok(readme.includes('--ledger'), 'README does not mention --ledger');
  assert.ok(readme.includes('/fleet.json'), 'README does not mention /fleet.json');
  assert.ok(/\/fleet(?!\.json)\b/.test(readme), 'README does not mention the /fleet page');
});

(async () => {
  let failed = 0;
  for (const [name, fn] of cases) {
    try { await fn(); console.log(`PASS ${name}`); } catch (e) { failed++; console.log(`FAIL ${name}\n  ${e && e.message ? e.message.split('\n').slice(0, 4).join('\n  ') : e}`); }
  }
  console.log(failed ? `acceptance 688 (json): ${failed} of ${cases.length} failed` : `acceptance 688 (json): ${cases.length} passed`);
  process.exit(failed ? 1 : 0);
})();
