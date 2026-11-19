#!/usr/bin/env node
'use strict';
// Acceptance tests for #689: "Make the board easier to use on a phone".
// Blind tests: written from the owner's answers and the board's public interface (B.start, `/`, `?embed=1`),
// not from board.html or board.js. They open the page in Chromium and check what a user sees: visible text,
// sizes (getBoundingClientRect), computed font sizes and scroll widths. No class name or id is used.
// They need Playwright with a Chromium; without it the file prints "skip" and exits 0, like tests/board/board-ui.test.js.
// Run: node tests/acceptance/689/board-phone.test.js
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const root = path.join(__dirname, '..', '..', '..');
const B = require(path.join(root, 'plugins', 'harness', 'board', 'board.js'));
const FLOW = JSON.parse(fs.readFileSync(path.join(root, 'plugins', 'harness', 'board', 'flow.json'), 'utf8'));
const STEP_NAMES = FLOW.nodes.map(n => n.t);

let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { console.log('acceptance 689: skip — no playwright'); process.exit(0); }

const PHONES = [{ width: 390, height: 844 }, { width: 360, height: 800 }];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const jl = rows => rows.map(r => JSON.stringify(r)).join('\n') + '\n';
const transcript = (t0, t1, tokens, tools) => [
  { type: 'user', timestamp: t0, effort: 'medium', message: { role: 'user', content: 'prompt' } },
  { type: 'assistant', timestamp: t1, message: { id: 'm1', model: 'claude-sonnet-5-5',
    usage: { input_tokens: 1000, cache_read_input_tokens: tokens - 1050, output_tokens: 50 },
    content: [{ type: 'text', text: 'answer' }, ...tools.map(name => ({ type: 'tool_use', name, input: {} }))] } },
];

// Same run layout as the makeRun helper of tests/board/board-ui.test.js. Every call gets its own temp dir.
function makeRun(rows) {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'acc-689-'));
  const dir = path.join(base, 's1', 'subagents', 'workflows', 'wf_ui');
  fs.mkdirSync(dir, { recursive: true });
  const journal = [];
  rows.forEach(([label, result, tokens, tools], i) => {
    const id = `a${i + 1}`;
    journal.push({ type: 'started', agentId: id, label, phase: 'P' });
    if (result) journal.push({ type: 'result', agentId: id, result });
    const mm = String(Math.min(i + 1, 59)).padStart(2, '0');
    fs.writeFileSync(path.join(dir, `agent-${id}.jsonl`),
      jl(transcript('2026-11-16T08:00:00.000Z', `2026-11-16T08:${mm}:00.000Z`, tokens, tools)));
  });
  fs.writeFileSync(path.join(dir, 'journal.jsonl'), jl(journal));
  const flowFile = path.join(base, 'flow.json');
  fs.writeFileSync(flowFile, JSON.stringify({ ...FLOW, models: { 'claude-sonnet-5-5': 200000 } }));
  return { base, flowFile };
}

// Implement is done, the QA check failed, code review runs. Each summary carries a unique marker, so a
// step's handoff (the summary of the previous agent of the same ticket) can be told apart from its own summary.
// Tool names are chosen so they appear nowhere else on the page.
const RUN = [
  ['#9 implement · Add thing', { status: 'ok', summary: 'Built it HANDOFF-ALPHA' }, 58000, ['NotebookEdit', 'WebSearch']],
  ['#9 QA check · Add thing', { status: 'ok', passed_ac: false, summary: 'AC2 fails HANDOFF-BETA' }, 30000, ['KillShell']],
  ['#9 code-review · x', null, 90000, ['Glob', 'TodoWrite']],
];
// The same run plus 40 agents whose stage matches no box: they show only in the event log, so the log is long.
const LONG_LOG = [...RUN.slice(0, 2),
  ...Array.from({ length: 40 }, (_, i) => [`#9 lint pass ${i + 1} · x`, { status: 'ok', summary: `lint ${i + 1} ok` }, 1000, []]),
  RUN[2]];

const cases = [];
const test = (name, fn) => cases.push([name, fn]);

async function open(browser, rows, { width, height, query = '', mobile = true }) {
  const { base, flowFile } = makeRun(rows);
  const srv = await B.start({ port: 0, projectDir: base, flowFile, pollMs: 50 });
  const ctx = await browser.newContext({ viewport: { width, height }, isMobile: mobile, hasTouch: mobile });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(`http://127.0.0.1:${srv.port}/${query}`);
  // Ready when the run's summaries have arrived (visible text, no selector).
  await page.waitForFunction(() => document.body && /HANDOFF-BETA/.test(document.body.innerText), null, { timeout: 8000 });
  await sleep(700);
  return { page, errors, close: async () => { await ctx.close(); srv.server.close(); } };
}

// In-page helpers, injected as a string so every evaluate can use them.
const HELPERS = `
  window.__vis = el => {
    if (!el || !el.getBoundingClientRect) return false;
    if (el.checkVisibility && !el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  window.__own = el => [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
  // Visible elements whose own text is exactly a step name.
  window.__nameEls = names => [...document.querySelectorAll('body *')]
    .filter(e => names.includes(window.__own(e)) && window.__vis(e));
  // The block of one step: the largest ancestor of its name that holds no other step name.
  window.__item = (el, names) => {
    const all = window.__nameEls(names);
    let cur = el;
    while (cur.parentElement && cur.parentElement !== document.body &&
           all.filter(n => cur.parentElement.contains(n)).length <= 1) cur = cur.parentElement;
    return cur;
  };
`;
async function helpers(page) { await page.evaluate(HELPERS); }

// For each step name, the visible block of that step. A step block is the largest ancestor of the name that
// holds no other step name and that shows a token figure ("tokens n/a" or "58k"): that tells a step apart from
// the same name in a header or a summary line. A state word ("Done in 1:00", "Waiting") that sits just outside
// such a block (a badge under a card) belongs to the nearest block above or below it, within 60 px.
// Returns { name, text, left, right, top, bottom } (page coordinates) or { name, missing: true }.
async function stepItems(page, names) {
  await helpers(page);
  return page.evaluate(names => {
    const STATE = /^(Waiting|Running|Done|Failed|Needs you|Not run)\b/;
    const items = names.map(name => {
      const cands = window.__nameEls(names).filter(e => window.__own(e) === name).map(e => window.__item(e, names));
      const el = cands.find(c => /tokens|\d+(\.\d+)?k\b/.test(c.innerText)) || null;
      if (!el) return { name, missing: true };
      const r = el.getBoundingClientRect();
      return { name, el, text: el.innerText, left: r.left, right: r.right, top: r.top + window.scrollY, bottom: r.bottom + window.scrollY };
    });
    const found = items.filter(i => !i.missing);
    const loose = [...document.querySelectorAll('body *')].filter(e => STATE.test(window.__own(e)) && window.__vis(e) &&
      !found.some(i => i.el.contains(e)));
    for (const e of loose) {
      const r = e.getBoundingClientRect(); const cx = (r.left + r.right) / 2; const top = r.top + window.scrollY, bot = r.bottom + window.scrollY;
      let best = null, bestD = 61;
      for (const i of found) {
        if (cx < i.left || cx > i.right) continue;
        const d = top >= i.bottom ? top - i.bottom : (bot <= i.top ? i.top - bot : 0);
        if (d < bestD) { best = i; bestD = d; }
      }
      if (best) {
        best.text += '\n' + e.innerText;
        best.top = Math.min(best.top, top); best.bottom = Math.max(best.bottom, bot);
        best.left = Math.min(best.left, r.left); best.right = Math.max(best.right, r.right);
      }
    }
    return items.map(({ el, ...rest }) => rest);
  }, names);
}

const noPageHScroll = page => page.evaluate(() => {
  const d = document.documentElement;
  return { scrollWidth: Math.max(d.scrollWidth, document.body.scrollWidth), clientWidth: d.clientWidth };
});

// ---------------------------------------------------------------------------------------------
// Criterion 1 (owner): "Stacked step list" = Under ~600 px, show a vertical list of steps (name, state,
// model and effort, tokens, handoff text, tool names). Wide screens keep the diagram.
// ---------------------------------------------------------------------------------------------
for (const vp of PHONES) {
  test(`AC1: under 600 px (${vp.width}x${vp.height}) the steps are a vertical list, one step per row, inside the screen`, async b => {
    const t = await open(b, RUN, vp);
    const items = await stepItems(t.page, STEP_NAMES);
    const missing = items.filter(i => i.missing).map(i => i.name);
    assert.deepStrictEqual(missing, [], `steps not shown as a visible block: ${missing.join(', ')}`);
    for (const i of items) assert.match(i.text, /Waiting|Running|Done|Failed|Needs you|Not run/, `step "${i.name}" shows no state`);
    for (const i of items) {
      assert.ok(i.left >= -1 && i.right <= vp.width + 1, `step "${i.name}" is outside the screen width (${Math.round(i.left)}..${Math.round(i.right)})`);
    }
    // Vertical list: no two steps share a row.
    for (let x = 0; x < items.length; x++) for (let y = x + 1; y < items.length; y++) {
      const a = items[x], c = items[y];
      const overlap = Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top);
      assert.ok(overlap <= 1, `"${a.name}" and "${c.name}" sit side by side, not stacked`);
    }
    assert.deepStrictEqual(t.errors, []);
    await t.close();
  });

  test(`AC1: under 600 px (${vp.width}x${vp.height}) each step shows name, state, model and effort, tokens, handoff text and tool names without hover`, async b => {
    const t = await open(b, RUN, vp);
    const items = Object.fromEntries((await stepItems(t.page, ['Implement', 'UAT / QA check', 'Code review', 'Intent & plan']))
      .map(i => [i.name, i]));
    for (const n of Object.keys(items)) assert.ok(!items[n].missing, `no visible step block for "${n}"`);
    const impl = items['Implement'].text, qa = items['UAT / QA check'].text, rev = items['Code review'].text;
    // state
    assert.match(impl, /Done/, 'Implement: state');
    assert.match(qa, /Failed/, 'UAT / QA check: state');
    assert.match(rev, /Running/, 'Code review: state');
    assert.match(items['Intent & plan'].text, /Waiting/, 'Intent & plan: state');
    // model and effort
    for (const [n, s] of [['Implement', impl], ['UAT / QA check', qa], ['Code review', rev]]) {
      assert.match(s, /Sonnet 5\.5/, `${n}: model`);
      assert.match(s, /medium/, `${n}: effort`);
    }
    // tokens
    assert.match(impl, /58k/, 'Implement: tokens');
    assert.match(qa, /30k/, 'UAT / QA check: tokens');
    assert.match(rev, /90k/, 'Code review: tokens');
    // handoff text: the previous agent's summary, as visible text (not a tooltip)
    assert.match(qa, /HANDOFF-ALPHA/, 'UAT / QA check: handoff from Implement not visible');
    assert.match(rev, /HANDOFF-BETA/, 'Code review: handoff from the QA check not visible');
    // tool names, as visible text (not a tooltip or an icon only)
    for (const tool of ['NotebookEdit', 'WebSearch']) assert.ok(impl.includes(tool), `Implement: tool name ${tool} not visible`);
    assert.ok(qa.includes('KillShell'), 'UAT / QA check: tool name KillShell not visible');
    for (const tool of ['Glob', 'TodoWrite']) assert.ok(rev.includes(tool), `Code review: tool name ${tool} not visible`);
    await t.close();
  });
}

// "Wide screens keep the diagram." / "Desktop (>=1024 px) ... unchanged." (owner, criteria 1 and 2)
// Regression guard: this holds on the base and must still hold after the change.
for (const width of [1024, 1440]) {
  test(`AC1/AC2: at ${width} px (desktop) the flow diagram is still shown: steps side by side with arrows`, async b => {
    const t = await open(b, RUN, { width, height: 900, mobile: false });
    const items = await stepItems(t.page, STEP_NAMES);
    assert.deepStrictEqual(items.filter(i => i.missing).map(i => i.name), [], 'step boxes not visible');
    const sameRow = items.some((a, x) => items.some((c, y) => y > x && Math.abs(a.top - c.top) < 2 && Math.abs(a.left - c.left) > 20));
    assert.ok(sameRow, 'no two steps side by side: the diagram is gone');
    await helpers(t.page);
    const arrows = await t.page.evaluate(() => [...document.querySelectorAll('svg path')].filter(window.__vis).length);
    assert.ok(arrows >= 1, 'no visible arrow in the diagram');
    const w = await noPageHScroll(t.page);
    assert.ok(w.scrollWidth <= w.clientWidth, `page scrolls sideways at ${width} px`);
    await t.close();
  });
}

// ---------------------------------------------------------------------------------------------
// Criterion 2 (owner): "Recommended set" = Under 600 px: 44x44 px tap targets, text >=12 px, no horizontal
// page scroll, hover details reachable by tap or shown inline, full-height log with no nested scroll.
// Desktop (>=1024 px) and ?embed=1 unchanged. Tested by a 390x844 and 360x800 Playwright case.
// ---------------------------------------------------------------------------------------------
for (const vp of PHONES) {
  // The question named the problem: the diagram "scrolls sideways". So nothing visible may need a sideways
  // scroll: not the page, and not a box inside it.
  test(`AC2: no horizontal page scroll at ${vp.width}x${vp.height}`, async b => {
    const t = await open(b, RUN, vp);
    const w = await noPageHScroll(t.page);
    assert.ok(w.scrollWidth <= w.clientWidth, `page is ${w.scrollWidth} px wide in a ${w.clientWidth} px screen`);
    await helpers(t.page);
    const sideways = await t.page.evaluate(() => [...document.querySelectorAll('body *')].filter(e => {
      if (!window.__vis(e)) return false;
      const s = getComputedStyle(e);
      return /auto|scroll/.test(s.overflowX) && e.scrollWidth > e.clientWidth + 1;
    }).map(e => `<${e.tagName.toLowerCase()}> ${e.scrollWidth}/${e.clientWidth}: ${e.innerText.slice(0, 40).replace(/\s+/g, ' ')}`));
    assert.deepStrictEqual(sideways, [], `a box on the page scrolls sideways: ${sideways.join('; ')}`);
    await t.close();
  });

  test(`AC2: every tap target is at least 44x44 px at ${vp.width}x${vp.height}`, async b => {
    const t = await open(b, RUN, vp);
    await helpers(t.page);
    const small = await t.page.evaluate(() => {
      const sel = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=tab],' +
        '[role=checkbox],[role=switch],[role=option],[onclick],[tabindex]:not([tabindex="-1"])';
      const set = new Set([...document.querySelectorAll(sel)]);
      // Clickable elements that show a pointer cursor (the outermost one of a pointer group).
      for (const e of document.querySelectorAll('body *')) {
        if (getComputedStyle(e).cursor === 'pointer' && !(e.parentElement && getComputedStyle(e.parentElement).cursor === 'pointer')) set.add(e);
      }
      return [...set].filter(window.__vis).map(e => {
        const r = e.getBoundingClientRect();
        return { w: r.width, h: r.height, d: `<${e.tagName.toLowerCase()}> "${(e.getAttribute('aria-label') || e.innerText || e.title || '').slice(0, 30).replace(/\s+/g, ' ')}"` };
      }).filter(x => x.w < 44 - 0.5 || x.h < 44 - 0.5).map(x => `${x.d} ${Math.round(x.w)}x${Math.round(x.h)}`);
    });
    assert.deepStrictEqual(small, [], `tap targets smaller than 44x44 px: ${small.join('; ')}`);
    await t.close();
  });

  test(`AC2: all visible text is at least 12 px at ${vp.width}x${vp.height}`, async b => {
    const t = await open(b, RUN, vp);
    await helpers(t.page);
    const tiny = await t.page.evaluate(() => {
      const out = [];
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = walk.nextNode(); n; n = walk.nextNode()) {
        const s = n.textContent.trim();
        if (!s) continue;
        const el = n.parentElement;
        if (!el || !window.__vis(el)) continue;
        const range = document.createRange(); range.selectNodeContents(n);
        const r = range.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        // Rendered size: computed font size times any CSS scale on the way up (an SVG drawing scaled down counts).
        let px = parseFloat(getComputedStyle(el).fontSize);
        const box = el.getBoundingClientRect();
        // offsetWidth is a rounded layout width: only a scale of more than 2% counts as a CSS scale.
        if (el.offsetWidth >= 10 && box.width > 0 && Math.abs(box.width / el.offsetWidth - 1) > 0.02) px *= box.width / el.offsetWidth;
        else if (el.closest('svg') && el.closest('svg').getBoundingClientRect().width > 0) {
          const svg = el.closest('svg');
          const vb = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width;
          if (vb) px *= svg.getBoundingClientRect().width / vb;
        }
        if (px < 12 - 0.05) out.push(`${px.toFixed(1)} px: "${s.slice(0, 30)}"`);
      }
      return out;
    });
    assert.deepStrictEqual(tiny, [], `text smaller than 12 px (${tiny.length}): ${tiny.slice(0, 6).join('; ')}`);
    await t.close();
  });

  test(`AC2: hover details are shown inline or appear on tap at ${vp.width}x${vp.height}`, async b => {
    const t = await open(b, RUN, vp);
    await helpers(t.page);
    // Details that exist only as a hover tooltip (title attribute) on a visible element.
    const titled = await t.page.evaluate(() => [...document.querySelectorAll('body [title]')].filter(window.__vis)
      .map((e, i) => { e.setAttribute('data-acc689', String(i)); return { i, title: e.getAttribute('title').replace(/^[\s↳]+/, '').trim() }; })
      .filter(x => x.title));
    const hidden = [];
    for (const { i, title } of titled) {
      const shown = () => t.page.evaluate(s => document.body.innerText.includes(s), title);
      if (await shown()) continue;
      const h = await t.page.$(`[data-acc689="${i}"]`);
      if (h && await h.isVisible()) { try { await h.tap({ timeout: 2000 }); } catch (e) { /* not tappable */ } await sleep(200); }
      if (!(await shown())) hidden.push(title);
    }
    assert.deepStrictEqual(hidden, [], `details only reachable by hover: ${hidden.join('; ')}`);
    await t.close();
  });

  test(`AC2: the event log is full height with no nested scroll at ${vp.width}x${vp.height}`, async b => {
    const t = await open(b, LONG_LOG, vp);
    await t.page.waitForFunction(() => /lint 40 ok/.test(document.body.innerText) && /lint 1 ok/.test(document.body.innerText), null, { timeout: 8000 });
    await helpers(t.page);
    const r = await t.page.evaluate(() => {
      // The log entries, found by their visible text.
      const entries = [...document.querySelectorAll('body *')].filter(e => /lint \d+ ok/.test(window.__own(e)));
      if (!entries.length) return { error: 'no log entry found by its text' };
      const clipping = new Set();
      for (const e of entries) {
        for (let a = e.parentElement; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
          const s = getComputedStyle(a);
          if (/auto|scroll|hidden|clip/.test(s.overflowY) && a.scrollHeight > a.clientHeight + 1) {
            clipping.add(`<${a.tagName.toLowerCase()}> overflow-y:${s.overflowY} ${a.scrollHeight}/${a.clientHeight}`);
          }
        }
      }
      return { entries: entries.length, clipping: [...clipping] };
    });
    assert.ok(!r.error, r.error);
    assert.deepStrictEqual(r.clipping, [], `the event log sits in a box that scrolls or clips: ${r.clipping.join('; ')}`);
    await t.close();
  });
}

// "?embed=1 unchanged" (owner, criterion 2). Regression guard at desktop width, from the documented embed
// behaviour in plugins/harness/board/README.md: no own header and footer note, transparent background,
// the diagram shown, no sideways page scroll.
for (const width of [1024, 1440]) {
  test(`AC2: ?embed=1 unchanged at ${width} px: no header or footer note, transparent background, the diagram shown`, async b => {
    const t = await open(b, RUN, { width, height: 900, query: '?embed=1', mobile: false });
    await helpers(t.page);
    const r = await t.page.evaluate(() => {
      const textVisible = re => [...document.querySelectorAll('body *')].some(e => re.test(window.__own(e)) && window.__vis(e));
      return {
        header: textVisible(/^Agent Flow Board$/),
        footer: textVisible(/^Source: journal\.jsonl/),
        bgBody: getComputedStyle(document.body).backgroundColor,
        bgHtml: getComputedStyle(document.documentElement).backgroundColor,
      };
    });
    assert.strictEqual(r.header, false, 'embed shows the board header');
    assert.strictEqual(r.footer, false, 'embed shows the footer note');
    for (const bg of [r.bgBody, r.bgHtml]) assert.ok(bg === 'transparent' || /rgba\(0, 0, 0, 0\)/.test(bg), `background is ${bg}`);
    const items = await stepItems(t.page, STEP_NAMES);
    assert.deepStrictEqual(items.filter(i => i.missing).map(i => i.name), [], 'step boxes not visible');
    assert.ok(items.some((a, x) => items.some((c, y) => y > x && Math.abs(a.top - c.top) < 2 && Math.abs(a.left - c.left) > 20)),
      'no two steps side by side: the diagram is gone in embed mode');
    const w = await noPageHScroll(t.page);
    assert.ok(w.scrollWidth <= w.clientWidth, 'embed page scrolls sideways');
    await t.close();
  });
}

(async () => {
  let browser;
  try { browser = await chromium.launch(); } catch (e) { console.log('acceptance 689: skip — no chromium'); process.exit(0); }
  let failed = 0;
  for (const [name, fn] of cases) {
    try { await fn(browser); console.log(`PASS ${name}`); } catch (e) { failed++; console.log(`FAIL ${name}\n  ${e && e.stack ? e.stack.split('\n').slice(0, 3).join('\n  ') : e}`); }
  }
  await browser.close();
  console.log(failed ? `acceptance 689: ${failed} of ${cases.length} failed` : `acceptance 689: ${cases.length} passed`);
  process.exit(failed ? 1 : 0);
})();
