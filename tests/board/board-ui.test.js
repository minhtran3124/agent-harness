#!/usr/bin/env node
'use strict';
// Browser tests for the Workflow panel of plugins/harness/board/board.html (the crew-style cards).
// They need Playwright with a Chromium; without it the file prints "skip" and exits 0 (CI installs neither on purpose).
// BOARD_PERF=1 also runs the slow-CPU smoothness case, which depends on the machine and is not run by default.
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const root = path.join(__dirname, '..', '..');
const B = require(path.join(root, 'plugins', 'harness', 'board', 'board.js'));
const FLOW = JSON.parse(fs.readFileSync(path.join(root, 'plugins', 'harness', 'board', 'flow.json'), 'utf8'));

let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { console.log('board-ui: skip — no playwright'); process.exit(0); }

const jl = rows => rows.map(r => JSON.stringify(r)).join('\n') + '\n';
const transcript = (t0, t1, tokens, tools) => [
  { type: 'user', timestamp: t0, effort: 'medium', message: { role: 'user', content: 'SECRET PROMPT TEXT' } },
  { type: 'assistant', timestamp: t1, message: { id: 'm1', model: 'claude-sonnet-5-5',
    usage: { input_tokens: 1000, cache_read_input_tokens: tokens - 1050, output_tokens: 50 },
    content: [{ type: 'text', text: 'SECRET ANSWER' }, ...tools.map(name => ({ type: 'tool_use', name, input: { cmd: 'SECRET TOOL INPUT' } }))] } },
];

// Build a run dir from [label, result|null, tokens, tools] rows. Times: agent n starts at 08:00:00 and ends n minutes later.
function makeRun(rows, summary) {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'board-ui-'));
  const dir = path.join(base, 's1', 'subagents', 'workflows', 'wf_ui');
  fs.mkdirSync(dir, { recursive: true });
  const journal = [];
  rows.forEach(([label, result, tokens, tools], i) => {
    const id = `a${i + 1}`;
    journal.push({ type: 'started', agentId: id, label, phase: 'P' });
    if (result) journal.push({ type: 'result', agentId: id, result });
    fs.writeFileSync(path.join(dir, `agent-${id}.jsonl`),
      jl(transcript('2026-11-16T08:00:00.000Z', `2026-11-16T08:0${i + 1}:00.000Z`, tokens, tools)));
  });
  fs.writeFileSync(path.join(dir, 'journal.jsonl'), jl(journal));
  if (summary) {
    fs.mkdirSync(path.join(base, 's1', 'workflows'), { recursive: true });
    fs.writeFileSync(path.join(base, 's1', 'workflows', 'wf_ui.json'), JSON.stringify(summary));
  }
  const flow = { ...FLOW, models: { 'claude-sonnet-5-5': 200000 } };
  const flowFile = path.join(base, 'flow.json');
  fs.writeFileSync(flowFile, JSON.stringify(flow));
  return { base, flowFile };
}
const ok = { status: 'ok' };
const failAc = { status: 'ok', passed_ac: false, summary: 'AC2 fails' };
const passAc = { status: 'ok', passed_ac: true, summary: 'all pass' };
// Check fails, fix r1, re-check r1 fails, fix r2, re-check r2 passes.
const TWO_FAILS = [
  ['#9 implement · Add thing', { ...ok, summary: 'Added the thing and the tests for it, all passing now in the module, nothing else touched at all' }, 58000, ['Read', 'Edit', 'Bash', 'Grep', 'Write', 'WebFetch', 'Foo']],
  ['#9 QA check · Add thing', failAc, 30000, ['Bash']],
  ['#9 QA check fix r1 · Add thing', { ...ok, summary: 'fixed 1' }, 20000, ['Edit']],
  ['#9 QA check rerun r1 · Add thing', failAc, 20000, ['Bash']],
  ['#9 QA check fix r2 · Add thing', { ...ok, summary: 'fixed 2' }, 20000, ['Edit']],
  ['#9 QA check rerun r2 · Add thing', passAc, 20000, ['Bash']],
  ['#9 code-review · x', null, 90000, ['Grep', 'Read']],
];
const CAP = [
  ['#9 QA check · Add thing', failAc, 30000, ['Bash']],
  ['#9 QA check fix r1 · t', ok, 1000, []], ['#9 QA check rerun r1 · t', failAc, 1000, []],
  ['#9 QA check fix r2 · t', ok, 1000, []], ['#9 QA check rerun r2 · t', failAc, 1000, []],
  ['#9 QA check fix r3 · t', ok, 1000, []], ['#9 QA check rerun r3 · t', failAc, 1000, []],
];

const cases = [];
const test = (name, fn) => cases.push([name, fn]);
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function open(browser, rows, summary, opts = {}) {
  const { base, flowFile } = makeRun(rows, summary);
  const srv = await B.start({ port: 0, projectDir: base, flowFile, pollMs: 50 });
  const page = await browser.newPage({ viewport: { width: opts.width || 1440, height: 1300 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(`http://127.0.0.1:${srv.port}/${opts.query || ''}`);
  await page.waitForFunction(n => document.querySelectorAll('.node').length === n, FLOW.nodes.length);
  await page.waitForFunction(() => /^wf_ui$/.test(document.getElementById('runid').textContent));
  await sleep(opts.settle || 700);
  return { page, srv, errors, close: async () => { await page.close(); srv.server.close(); } };
}
const text = (page, sel) => page.$eval(sel, e => e.textContent);
const cap = (page, id) => text(page, `.cap[data-node="${id}"]`);

test('ui1: one card per node id with title and role from flow.json, two lanes, and the 18 arrows', async b => {
  const t = await open(b, TWO_FAILS);
  assert.strictEqual(FLOW.edges.length, 18);
  const ids = await t.page.$$eval('.node', els => els.map(e => e.getAttribute('data-node')));
  assert.deepStrictEqual(ids.slice().sort(), FLOW.nodes.map(n => n.id).sort());
  for (const n of FLOW.nodes) {
    assert.strictEqual(await text(t.page, `.node[data-node="${n.id}"] .txt b`), n.t);
    assert.strictEqual(await text(t.page, `.node[data-node="${n.id}"] .txt i`), n.a);
  }
  assert.strictEqual(await t.page.$$eval('.lane', e => e.length), 2);
  assert.strictEqual(await t.page.$$eval('path.edge', e => e.length), 18);
  assert.deepStrictEqual(t.errors, []);
  await t.close();
});

test('ui2: model chip, badge text, tokens, tool icons and card height', async b => {
  const t = await open(b, TWO_FAILS);
  assert.strictEqual(await text(t.page, '.node[data-node="impl"] .mdl'), 'Sonnet 5.5 · medium');
  assert.strictEqual(await text(t.page, '.node[data-node="intent"] .mdl'), 'no agent yet');
  assert.strictEqual(await cap(t.page, 'intent'), 'Waiting');
  assert.match(await cap(t.page, 'impl'), /^Done in \d+:\d\d$/);
  assert.match(await cap(t.page, 'check'), /^Failed in \d+:\d\d$/);
  assert.match(await cap(t.page, 'fix'), /^Done in \d+:\d\d · 2 agents$/);
  assert.match(await cap(t.page, 'rerun'), /^Done in \d+:\d\d · 2 agents$/);
  assert.match(await cap(t.page, 'review'), /^Running \d+:\d\d$/);
  assert.strictEqual(await text(t.page, '#round'), '2 / 3');
  // 58000 used, 200000 limit
  assert.strictEqual(await text(t.page, '.node[data-node="impl"] .tkt'), '58k / 200k');
  assert.strictEqual(await t.page.$eval('.node[data-node="impl"] .tbar i', e => e.style.width), '29%');
  // no data -> n/a, no bar, same height
  assert.strictEqual(await text(t.page, '.node[data-node="intent"] .tkt'), 'tokens n/a');
  assert.strictEqual(await t.page.$$eval('.node[data-node="intent"] .tbar', e => e.length), 0);
  for (const n of FLOW.nodes) assert.strictEqual(await t.page.$eval(`.node[data-node="${n.id}"]`, e => e.offsetHeight), 130, n.id);
  // 4 icons then +N; a tool with no icon still gets one
  assert.strictEqual(await t.page.$$eval('.node[data-node="impl"] .tool', e => e.length), 4);
  assert.strictEqual(await text(t.page, '.node[data-node="impl"] .more'), '+3');
  assert.strictEqual(await t.page.$$eval('.node[data-node="intent"] .tool', e => e.length), 0);
  // one spinner on the running card, none elsewhere
  assert.strictEqual(await t.page.$$eval('.node[data-node="review"] .spin', e => e.length), 1);
  assert.strictEqual(await t.page.$$eval('.node .spin', e => e.length), 1);
  assert.strictEqual(await t.page.$eval('.node[data-node="review"] .act', e => e.textContent), 'Using Read');
  assert.ok((await text(t.page, '.node[data-node="impl"] .act')).length <= 80);
  await t.close();
});

test('ui3: arrows are active, done or idle by the rules', async b => {
  const t = await open(b, TWO_FAILS);
  const cls = i => t.page.$eval(`#e${i}`, e => e.getAttribute('class'));
  const idx = (a, c, k) => FLOW.edges.findIndex(e => e[0] === a && e[1] === c && (e[2] || 'n') === (k || 'n'));
  assert.match(await cls(idx('gate', 'review', 'down')), /\bactive\b/, 'target review runs');
  assert.match(await cls(idx('check', 'fix', 'vdown')), /\bidle\b/, 'the first check stays failed');
  assert.match(await cls(idx('fix', 'rerun')), /\bdone\b/);
  assert.doesNotMatch(await cls(idx('rerun', 'fix', 'loop')), /\bactive\b/, 'fix is not running');
  assert.doesNotMatch(await cls(idx('adv', 'fix', 'bus')), /\bactive\b/);
  await t.close();
});

test('ui4: round cap: Re-check says Needs you, later boxes say Not run, the pill says Needs you', async b => {
  const t = await open(b, CAP, { status: 'completed', durationMs: 1, result: null, logs: [] });
  assert.strictEqual(await cap(t.page, 'rerun'), 'Needs you');
  for (const id of ['test', 'adr', 'final']) assert.strictEqual(await cap(t.page, id), 'Not run');
  assert.strictEqual(await text(t.page, '#overall'), 'Needs you');
  assert.strictEqual(await text(t.page, '#round'), '3 / 3');
  await t.close();
});

test('ui5: no page scroll at 1440 px; a narrow container scrolls inside itself; embed posts height only on change', async b => {
  const t = await open(b, TWO_FAILS);
  assert.ok(await t.page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth));
  await t.close();
  const n = await open(b, TWO_FAILS, null, { width: 745, query: '?embed=1' });
  assert.ok(await n.page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), 'the page scrolls sideways');
  assert.ok(await n.page.$eval('#scroller', e => e.scrollWidth > e.clientWidth), 'the diagram does not scroll inside its container');
  assert.ok(Math.abs(await n.page.$eval('#world', e => Number(/scale\(([\d.]+)\)/.exec(e.style.transform)[1])) - 0.6) < 1e-9, 'scale floor 0.6');
  await n.close();
  const { base, flowFile } = makeRun(TWO_FAILS, { status: 'completed', durationMs: 1, result: null, logs: [] });
  const srv = await B.start({ port: 0, projectDir: base, flowFile, pollMs: 50 });
  const host = await b.newPage();
  await host.setContent(`<iframe id="f" src="http://127.0.0.1:${srv.port}/?embed=1" width="900" height="400"></iframe>`);
  await host.evaluate(() => { window.msgs = []; window.addEventListener('message', e => window.msgs.push(e.data)); });
  await sleep(1500);
  const msgs = await host.evaluate(() => window.msgs);
  await host.close(); srv.server.close();
  assert.ok(msgs.length >= 1 && msgs.length <= 3, `height messages: ${msgs.length}`);
  assert.ok(msgs.every(m => m.type === 'afb-height' && Number.isFinite(m.height) && Object.keys(m).length === 2));
});

test('ui10: while an agent runs, its token text grows when the transcript grows', async b => {
  const { base, flowFile } = makeRun([['#9 implement · t', null, 40000, ['Read']]]);
  const srv = await B.start({ port: 0, projectDir: base, flowFile, pollMs: 50 });
  const page = await b.newPage({ viewport: { width: 1440, height: 1300 } });
  await page.goto(`http://127.0.0.1:${srv.port}/`);
  await page.waitForFunction(() => /k \/ /.test(document.querySelector('.node[data-node="impl"] .tkt').textContent));
  const before = await text(page, '.node[data-node="impl"] .tkt');
  const f = path.join(base, 's1', 'subagents', 'workflows', 'wf_ui', 'agent-a1.jsonl');
  fs.appendFileSync(f, jl([{ type: 'assistant', timestamp: '2026-11-16T08:09:00.000Z', message: { model: 'claude-sonnet-5-5', usage: { input_tokens: 5, cache_read_input_tokens: 70000, output_tokens: 5 }, content: [{ type: 'tool_use', name: 'Bash', input: {} }] } }]));
  await page.waitForFunction(x => document.querySelector('.node[data-node="impl"] .tkt').textContent !== x, before, { timeout: 4000 });
  assert.strictEqual(before, '40k / 200k');
  assert.strictEqual(await text(page, '.node[data-node="impl"] .tkt'), '70k / 200k');
  assert.strictEqual(await text(page, '.node[data-node="impl"] .act'), 'Using Bash');
  await page.close(); srv.server.close();
});

test('ui6: a stable finished run makes no DOM change in the diagram over 2 seconds', async b => {
  const t = await open(b, TWO_FAILS.slice(0, 6), { status: 'completed', durationMs: 1, result: null, logs: [] });
  const n = await t.page.evaluate(() => new Promise(res => {
    let c = 0; const o = new MutationObserver(m => { c += m.length; });
    o.observe(document.getElementById('world'), { subtree: true, childList: true, attributes: true, characterData: true });
    setTimeout(() => { o.disconnect(); res(c); }, 2000);
  }));
  assert.strictEqual(n, 0);
  await t.close();
});

test('ui7: the page and the event stream carry no prompt, answer or tool input', async b => {
  const t = await open(b, TWO_FAILS);
  const html = await t.page.content();
  const sse = JSON.stringify(await (await fetch(`http://127.0.0.1:${t.srv.port}/state.json`)).json());
  for (const bad of ['SECRET PROMPT TEXT', 'SECRET ANSWER', 'SECRET TOOL INPUT']) {
    assert.ok(!html.includes(bad) && !sse.includes(bad), bad);
  }
  await t.close();
});

test('ui8: no colour literal in the board CSS outside the :root token blocks', () => {
  const html = fs.readFileSync(path.join(root, 'plugins', 'harness', 'board', 'board.html'), 'utf8');
  const css = html.slice(html.indexOf('<style>'), html.indexOf('</style>'))
    .replace(/:root\{[^}]*\}/g, '').replace(/@media \(prefers-color-scheme: dark\)\{:root:not\(\[data-theme="light"\]\)\{[^}]*\}\}/g, '')
    .replace(/:root\[data-theme="dark"\]\{[^}]*\}/g, '');
  assert.ok(!/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/.test(css), 'a colour literal is outside the token blocks');
});

if (process.env.BOARD_PERF === '1') {
  test('ui9: smooth under a 6x slow CPU while a run plays and the page scrolls', async b => {
    const t = await open(b, TWO_FAILS);
    const cdp = await t.page.context().newCDPSession(t.page);
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 6 });
    await t.page.evaluate(() => {
      window.__long = 0; window.__frames = [];
      new PerformanceObserver(l => { window.__long += l.getEntries().length; }).observe({ entryTypes: ['longtask'] });
      let last = performance.now(); (function f(t) { window.__frames.push(t - last); last = t; requestAnimationFrame(f); })(last);
    });
    for (let i = 0; i < 10; i++) { await t.page.mouse.wheel(0, 120); await sleep(100); }
    const r = await t.page.evaluate(() => ({ long: window.__long, med: window.__frames.slice().sort((a, c) => a - c)[Math.floor(window.__frames.length / 2)], y: window.scrollY }));
    assert.ok(r.long <= 4, `long tasks: ${r.long}`);
    assert.ok(r.med <= 20, `median frame ${r.med}`);
    assert.ok(r.y > 0);
    await t.close();
  });
}

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { console.log('board-ui: skip — no chromium'); process.exit(0); }
  let failed = 0;
  for (const [name, fn] of cases) {
    try { await fn(browser); console.log(`PASS ${name}`); } catch (e) { failed++; console.log(`FAIL ${name}\n  ${e && e.stack ? e.stack.split('\n').slice(0, 4).join('\n  ') : e}`); }
  }
  await browser.close();
  console.log(failed ? `board-ui: ${failed} failed` : `board-ui: ${cases.length} passed`);
  process.exit(failed ? 1 : 0);
})();
