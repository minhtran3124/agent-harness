#!/usr/bin/env node
'use strict';
// Acceptance tests for #688, the /fleet page (AC5 and the owner's phone answer), in a real browser.
// They need Playwright with a Chromium; without it the file prints "skip" and exits 0, like tests/board/board-ui.test.js.
// Each case starts its own board through the CLI (`--port <free port> --ledger <file>`) with HOME set to a fresh
// temp dir, and stops it afterwards. Prints one PASS/FAIL line per case and exits 1 on any failure.
// Run: NODE_PATH=<dir with playwright> node tests/acceptance/688/fleet-page.test.js
//
// Selectors: the page's markup is not known yet, so the tests never use CSS classes. A ticket "row" is found by
// its text: every fixture ticket has a unique worker session name; the row is the smallest element that holds
// that name and also the ticket's reviewer session, its state, and its id as a separate token. "Stands out" is
// checked on what a viewer sees: the computed styles of the row, its ancestors and its descendants, or a heading
// that names the state above the row.
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const net = require('net');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { console.log('acceptance 688 (page): skip — no playwright'); process.exit(0); }

const root = path.join(__dirname, '..', '..', '..');
const BOARD = path.join(root, 'plugins', 'harness', 'board', 'board.js');
const cases = [];
const test = (name, fn) => cases.push([name, fn]);
const tmp = p => fs.mkdtempSync(path.join(os.tmpdir(), `acc688p-${p}-`));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const get = (port, p) => new Promise((res, rej) => http.get({ host: '127.0.0.1', port, path: p }, r => {
  let b = ''; r.on('data', c => { b += c; }); r.on('end', () => res({ status: r.statusCode, body: b }));
}).on('error', rej));
const freePort = () => new Promise((res, rej) => {
  const s = net.createServer(); s.unref(); s.on('error', rej);
  s.listen(0, '127.0.0.1', () => { const { port } = s.address(); s.close(() => res(port)); });
});
async function board(args) {
  const port = await freePort();
  const env = { ...process.env, HOME: tmp('home') };
  delete env.CLAUDE_CONFIG_DIR;
  const child = spawn(process.execPath, [BOARD, '--port', String(port), ...args], { cwd: tmp('cwd'), env, stdio: ['ignore', 'pipe', 'pipe'] });
  let out = ''; child.stdout.on('data', c => { out += c; }); child.stderr.on('data', c => { out += c; });
  let exited = null; child.on('exit', code => { exited = code; });
  for (let i = 0; i < 100; i++) {
    if (exited !== null) throw new Error(`board exited with code ${exited} before it answered: ${out.trim().split('\n')[0]}`);
    try { if ((await get(port, '/healthz')).status === 200) return { port, stop: () => child.kill() }; } catch (e) { /* not up yet */ }
    await sleep(50);
  }
  child.kill();
  throw new Error(`board did not answer on port ${port} within 5 s`);
}

const PR = n => `https://github.com/owner/name/pull/${n}`;
// Ledger format: plugins/harness/skills/pd-orchestrate/references/protocol.md, section "Ledger".
const TICKETS = {
  '9': { state: 'blocked', kind: 'bug', depth: 'S', worker: { session: 'w-nine-sess' }, reviewer: { session: 'r-nine-sess' }, head: 'h9', pr: PR(9) },
  '10': { state: 'in_review', kind: 'feature', depth: 'M', worker: { session: 'w-ten-sess' }, reviewer: { session: 'r-ten-sess' }, head: 'h10', pr: PR(10) },
  '11': { state: 'escalated', kind: 'bug', depth: 'M', worker: { session: 'w-eleven-sess' }, reviewer: { session: 'r-eleven-sess' }, head: 'h11', pr: PR(11) },
  '12': { state: 'done', kind: 'docs', depth: 'S', worker: { session: 'w-twelve-sess' }, reviewer: { session: 'r-twelve-sess' }, head: 'h12', pr: PR(12) },
  '3': { state: 'assigned', kind: 'feature', depth: 'S', worker: { session: 'w-three-sess' }, reviewer: null, pr: null },
};
const ledger = tickets => ({ v: 1, run: 'r688ui', base: 'main', repo: 'owner/name', tickets });
function ledgerFile(obj) {
  const file = path.join(tmp('led'), 'specs', 'fleet', 'r688ui', 'ledger.json');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(obj, null, 2));
  return file;
}

// In the page: find the row of one ticket (see the header) and return a description of it.
function rowInfo({ id, worker, reviewer, state, pr, others }) {
  // The id as a separate token, once the session names and the PR URL (which can hold the same digits) are cut out.
  const hasId = t => new RegExp(`(^|[^0-9A-Za-z])${id}([^0-9A-Za-z]|$)`)
    .test([worker, reviewer, pr].filter(Boolean).reduce((acc, s) => acc.split(s).join(' '), t));
  // The state as in the ledger, or with "_" shown as a space, in any case.
  const norm = t => t.toLowerCase().replace(/_/g, ' ');
  const hasState = t => norm(t).includes(norm(state));
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let start = null;
  while (walker.nextNode()) if (walker.currentNode.nodeValue.includes(worker)) { start = walker.currentNode.parentElement; break; }
  if (!start) return null;
  let row = start;
  while (row && row !== document.body) {
    const t = row.innerText || '';
    if (t.includes(worker) && (!reviewer || t.includes(reviewer)) && hasState(t) && hasId(t)) break;
    row = row.parentElement;
  }
  if (!row || row === document.body) return { found: false };
  const text = row.innerText;
  const PROPS = ['backgroundColor', 'color', 'borderTopColor', 'borderRightColor', 'borderBottomColor', 'borderLeftColor',
    'borderTopWidth', 'borderLeftWidth', 'outlineColor', 'outlineStyle', 'boxShadow', 'fontWeight', 'opacity', 'textDecorationLine', 'backgroundImage'];
  const sig = el => { const cs = getComputedStyle(el); return el.tagName + ':' + PROPS.map(p => cs[p]).join('|'); };
  const chain = [];
  for (let el = row; el && el !== document.documentElement; el = el.parentElement) chain.push(sig(el));
  const inner = [...row.querySelectorAll('*')].map(sig);
  // The nearest heading-like element before the row in document order (a group title), if any.
  const heads = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6,[role=heading],legend,caption,summary')];
  let heading = null;
  for (const h of heads) {
    if (h.contains(row) || row.contains(h)) continue;
    if (h.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING) heading = h.innerText.trim().toLowerCase();
  }
  return { found: true, text, crossesRows: others.some(o => text.includes(o)), style: chain.join('>') + '#' + inner.join(','), heading,
    links: [...row.querySelectorAll('a[href]')].map(a => a.href) };
}
const info = (page, id) => {
  const t = TICKETS[id];
  return page.evaluate(rowInfo, { id, worker: t.worker.session, reviewer: t.reviewer && t.reviewer.session, state: t.state, pr: t.pr,
    others: Object.entries(TICKETS).filter(([k]) => k !== id).map(([, o]) => o.worker.session) });
};

async function openFleet(browser, file, viewport = { width: 1280, height: 900 }) {
  const b = await board(['--ledger', file]);
  const page = await browser.newPage({ viewport });
  const resp = await page.goto(`http://127.0.0.1:${b.port}/fleet`);
  assert.strictEqual(resp.status(), 200, `GET /fleet status ${resp.status()}`);
  await page.waitForFunction(w => document.body && document.body.innerText.includes(w), TICKETS['10'].worker.session, { timeout: 5000 })
    .catch(() => { throw new Error('the /fleet page never showed the ticket rows'); });
  return { page, stop: async () => { await page.close(); b.stop(); } };
}

// "`GET /fleet` returns an HTML page that shows one row per ticket with its id, state, worker, reviewer and pull request"
test('AC5: /fleet shows one row per ticket with id, state, worker, reviewer and pull request', async browser => {
  const f = await openFleet(browser, ledgerFile(ledger(TICKETS)));
  try {
    for (const id of Object.keys(TICKETS)) {
      const r = await info(f.page, id);
      assert.ok(r && r.found, `no row holds id, state, worker and reviewer of ticket ${id}`);
      assert.ok(!r.crossesRows, `the row of ticket ${id} also holds another ticket`);
      if (TICKETS[id].pr) assert.ok(r.text.includes(TICKETS[id].pr) || r.links.includes(TICKETS[id].pr), `row ${id} does not show its pull request`);
    }
  } finally { await f.stop(); }
});
// Owner answer 1: "the page shows it [pr] as a link when it is an http(s) URL."
test('AC5: the pull request is a link when it is an http(s) URL', async browser => {
  const f = await openFleet(browser, ledgerFile(ledger(TICKETS)));
  try {
    for (const id of ['9', '10', '11', '12']) {
      const r = await info(f.page, id);
      assert.ok(r && r.found, `no row for ticket ${id}`);
      assert.ok(r.links.includes(TICKETS[id].pr), `row ${id} has no link to ${TICKETS[id].pr} (links: ${r.links.join(' ') || 'none'})`);
    }
  } finally { await f.stop(); }
});
// "groups or marks tickets by state so that `blocked` and `escalated` stand out"
// Passes when the blocked (and escalated) row looks different from a plain in_review row and a plain done row
// (computed styles of the row, its ancestors or its children differ), or sits under a group heading that names its
// state while those plain rows do not.
test('AC5: blocked and escalated rows stand out from other rows', async browser => {
  const f = await openFleet(browser, ledgerFile(ledger(TICKETS)));
  try {
    const plain = [await info(f.page, '10'), await info(f.page, '12')];
    for (const p of plain) assert.ok(p && p.found, 'plain rows not found');
    for (const [id, state] of [['9', 'blocked'], ['11', 'escalated']]) {
      const r = await info(f.page, id);
      assert.ok(r && r.found, `no row for ticket ${id}`);
      const styled = plain.every(p => p.style !== r.style);
      const grouped = !!r.heading && r.heading.includes(state) && plain.every(p => p.heading !== r.heading);
      assert.ok(styled || grouped, `the ${state} row looks like a plain row and has no "${state}" group heading (heading: ${r.heading})`);
    }
  } finally { await f.stop(); }
});
// "and refreshes by itself at least every 5 seconds."  (No reload by the test; 5 s plus 1.5 s for the request.)
test('AC5: the page refreshes by itself within 5 s after the ledger changes', async browser => {
  const file = ledgerFile(ledger(TICKETS));
  const f = await openFleet(browser, file);
  try {
    const next = JSON.parse(JSON.stringify(TICKETS));
    next['10'].worker.session = 'w-ten-changed';
    next['10'].state = 'fixing';
    next['13'] = { state: 'queued', worker: { session: 'w-thirteen-new' }, reviewer: null };
    fs.writeFileSync(file, JSON.stringify(ledger(next), null, 2));
    await f.page.waitForFunction(() => document.body.innerText.includes('w-ten-changed') && document.body.innerText.includes('w-thirteen-new'),
      null, { timeout: 6500 }).catch(() => { throw new Error('the change to the ledger did not show within 6.5 s'); });
  } finally { await f.stop(); }
});
// Owner answer 2: "The new /fleet page must be phone-friendly itself: no horizontal page scroll at 390 px."
test('AC5: no horizontal page scroll at 390x844', async browser => {
  const f = await openFleet(browser, ledgerFile(ledger(TICKETS)), { width: 390, height: 844 });
  try {
    const w = await f.page.evaluate(() => ({ doc: document.documentElement.scrollWidth, body: document.body.scrollWidth, view: document.documentElement.clientWidth }));
    assert.ok(w.doc <= w.view && w.body <= w.view, `page is wider than the 390 px screen: ${JSON.stringify(w)}`);
  } finally { await f.stop(); }
});

(async () => {
  const browser = await chromium.launch();
  let failed = 0;
  try {
    for (const [name, fn] of cases) {
      try { await fn(browser); console.log(`PASS ${name}`); } catch (e) { failed++; console.log(`FAIL ${name}\n  ${e && e.message ? e.message.split('\n')[0] : e}`); }
    }
  } finally { await browser.close(); }
  console.log(failed ? `acceptance 688 (page): ${failed} of ${cases.length} failed` : `acceptance 688 (page): ${cases.length} passed`);
  process.exit(failed ? 1 : 0);
})();
