#!/usr/bin/env node
'use strict';
// Live run board for ship.js (autopilot) runs. One file, no dependencies, Node 18 or newer.
//
// It reads what Claude Code already writes for every Workflow run, and nothing else:
//   <project dir>/<session>/subagents/workflows/<run id>/journal.jsonl   one `started` and one `result` line per agent
//   <project dir>/<session>/subagents/workflows/<run id>/agent-<id>.jsonl  the agent transcript (timestamps, model, effort)
//   <project dir>/<session>/workflows/<run id>.json                        the run summary, written once when the run ends
// <project dir> is ~/.claude/projects/<the project path with every non-alphanumeric character as '-'>.
// That layout belongs to Claude Code and can change; a missing file is reported, never guessed.
//
// The server tails those files and pushes normalized events to the page over SSE (Server-Sent Events).
// It binds 127.0.0.1 only. It sends labels, phases, statuses, models, efforts, times and the agent's short
// summary; it never sends prompts, tool calls or file contents.
//
//   node board.js [--project <path>] [--run <run id | run dir>] [--port <n>] [--no-follow]
//
// Verifies: the page shows each agent of one run as it starts and ends, within about one poll interval (500 ms).
// Does not verify: anything the journal does not record (log() lines and phase() calls appear only in the end
// summary); runs of other projects; that Claude Code keeps this file layout.

const fs = require('fs');
const path = require('path');
const http = require('http');
const os = require('os');

const POLL_MS = 500;
const SUMMARY_CHARS = 200;
const HERE = __dirname;

// ---------------------------------------------------------------------------
// Pure helpers (exported for tests)
// ---------------------------------------------------------------------------

// Claude Code names a project dir after the absolute path, every character outside [A-Za-z0-9] as '-'.
const projectKey = p => path.resolve(p).replace(/[^A-Za-z0-9]/g, '-');

// "#321 QA check fix r2 · title" -> { ticket: '321', stage: 'QA check fix', round: 2, retry: false, subject: 'title' }
function parseLabel(label) {
  const s = String(label || '');
  const m = s.match(/^#(\d+)\s+(.*)$/);
  const ticket = m ? m[1] : null;
  const rest = m ? m[2] : s;
  const cut = rest.indexOf(' · ');
  let stage = (cut >= 0 ? rest.slice(0, cut) : rest).trim();
  const subject = cut >= 0 ? rest.slice(cut + 3).trim() : '';
  let retry = false, round = null;
  if (/\s+retry$/.test(stage)) { retry = true; stage = stage.replace(/\s+retry$/, ''); }
  const r = stage.match(/\s+r(\d+)(?:\.\d+)?$/);
  if (r) { round = Number(r[1]); stage = stage.slice(0, r.index); }
  return { ticket, stage: stage || '?', round, retry, subject };
}

// The node of flow.json whose `match` regex fits the stage; null when none does.
function nodeFor(flow, stage) {
  for (const n of flow.nodes) {
    for (const re of n.match || []) {
      if (new RegExp(re, 'i').test(stage)) return n.id;
    }
  }
  return null;
}

// Agent result -> board status. A check that returns passed_ac false is a failure even when the call itself was ok.
function statusOf(result) {
  if (!result || typeof result !== 'object') return 'done';
  const st = String(result.status || '').toLowerCase();
  if (st === 'blocked' || st === 'needs_review') return 'waiting';
  if (st === 'failed' || st === 'error' || st === 'killed') return 'failed';
  if (result.passed_ac === false) return 'failed';
  return 'done';
}

function cut(s, n) {
  const a = Array.from(String(s == null ? '' : s).replace(/\s+/g, ' ').trim());
  return a.length > n ? a.slice(0, n - 1).join('') + '…' : a.join('');
}

// Lines of a JSONL chunk; `carry` holds a torn last line until the rest arrives.
function splitLines(carry, chunk) {
  const text = carry + chunk;
  const parts = text.split('\n');
  const rest = parts.pop();
  const rows = [];
  for (const line of parts) {
    const t = line.trim();
    if (!t) continue;
    try { const v = JSON.parse(t); if (v && typeof v === 'object') rows.push(v); } catch (e) { /* skip a bad line */ }
  }
  return { rows, carry: rest };
}

// First and last timestamp, model and effort of one agent transcript (already parsed rows).
function agentFacts(rows, facts) {
  const f = facts || { first: null, last: null, model: null, effort: null };
  for (const d of rows) {
    if (typeof d.timestamp === 'string') {
      if (!f.first || d.timestamp < f.first) f.first = d.timestamp;
      if (!f.last || d.timestamp > f.last) f.last = d.timestamp;
    }
    const msg = d.message && typeof d.message === 'object' ? d.message : null;
    if (!f.model && d.type === 'assistant' && msg && typeof msg.model === 'string') f.model = msg.model;
    if (!f.effort && typeof d.effort === 'string') f.effort = d.effort;
  }
  return f;
}

// One journal row -> one board event (or null). `facts` is what the agent transcript showed so far.
function eventOf(row, ctx) {
  const { flow, agents, runId } = ctx;
  if (row.type === 'started' && row.agentId) {
    const p = parseLabel(row.label);
    const a = { agentId: row.agentId, label: String(row.label || ''), phase: row.phase || null, ...p, node: nodeFor(flow, p.stage) };
    agents.set(row.agentId, a);
    return { kind: 'started', run_id: runId, agent_id: a.agentId, ticket: a.ticket, stage: a.stage, node: a.node,
      round: a.round, retry: a.retry, phase: a.phase, label: cut(a.label, 120), status: 'running' };
  }
  if (row.type === 'result' && row.agentId) {
    const a = agents.get(row.agentId) || { agentId: row.agentId, label: '', ticket: null, stage: '?', node: null, round: null, retry: false, phase: null };
    const r = row.result && typeof row.result === 'object' ? row.result : null;
    const ev = { kind: 'result', run_id: runId, agent_id: a.agentId, ticket: a.ticket, stage: a.stage, node: a.node,
      round: a.round, retry: a.retry, phase: a.phase, label: cut(a.label, 120), status: statusOf(r),
      summary: r && r.summary ? cut(r.summary, SUMMARY_CHARS) : '' };
    if (r && typeof r.passed_ac === 'boolean') ev.passed_ac = r.passed_ac;
    if (r && typeof r.head_sha === 'string') ev.head_sha = r.head_sha.slice(0, 12);
    if (Array.isArray(r && r.scenarios)) {   // a UAT or QA check result (UAT_SCHEMA in ship.js)
      const rows = r.scenarios.filter(x => x && typeof x === 'object');
      ev.checks = { total: rows.length, passed: rows.filter(x => x.status === 'PASS').length,
        failed: rows.filter(x => x.status === 'FAIL').length,
        not_checkable: rows.filter(x => /not-(browser-)?checkable/.test(String(x.kind || ''))).length };
    }
    return ev;
  }
  return null;
}

// The run summary file -> one `run_end` event.
function endEventOf(summary, runId) {
  const s = summary && typeof summary === 'object' ? summary : {};
  const res = s.result && typeof s.result === 'object' ? s.result : {};
  const fin = res.final && typeof res.final === 'object' ? res.final : {};
  return { kind: 'run_end', run_id: runId, status: String(s.status || 'unknown'), duration_ms: typeof s.durationMs === 'number' ? s.durationMs : null,
    pr: fin.url || fin.pr || null, branch: fin.branch || null,
    logs: Array.isArray(s.logs) ? s.logs.slice(-20).map(x => cut(x, 200)) : [] };
}

// ---------------------------------------------------------------------------
// Finding runs
// ---------------------------------------------------------------------------

const projectsRoot = () => path.join(os.homedir(), '.claude', 'projects');

// Every run dir of one project dir, newest first by mtime of its journal.
function runsOf(projDir) {
  const out = [];
  let sessions = [];
  try { sessions = fs.readdirSync(projDir, { withFileTypes: true }).filter(d => d.isDirectory()); } catch (e) { return out; }
  for (const s of sessions) {
    const base = path.join(projDir, s.name, 'subagents', 'workflows');
    let runs = [];
    try { runs = fs.readdirSync(base, { withFileTypes: true }).filter(d => d.isDirectory()); } catch (e) { continue; }
    for (const r of runs) {
      const dir = path.join(base, r.name);
      let mtime = 0;
      try { mtime = fs.statSync(path.join(dir, 'journal.jsonl')).mtimeMs; } catch (e) { continue; }
      out.push({ id: r.name, dir, mtime, summary: path.join(projDir, s.name, 'workflows', `${r.name}.json`) });
    }
  }
  return out.sort((a, b) => b.mtime - a.mtime);
}

// --run <dir | id>: a directory as given, or an id looked up under every project.
function resolveRun(arg, root = projectsRoot()) {
  if (fs.existsSync(path.join(arg, 'journal.jsonl'))) {
    const dir = path.resolve(arg), id = path.basename(dir);
    return { id, dir, summary: path.join(dir, '..', '..', '..', 'workflows', `${id}.json`) };
  }
  if (!/^[A-Za-z0-9_-]+$/.test(arg)) throw new Error(`--run ${arg}: neither a run dir nor a run id`);
  const hits = [];
  let projs = [];
  try { projs = fs.readdirSync(root, { withFileTypes: true }).filter(d => d.isDirectory()); } catch (e) { /* none */ }
  for (const p of projs) for (const r of runsOf(path.join(root, p.name))) if (r.id === arg) hits.push(r);
  if (hits.length === 1) return hits[0];
  if (hits.length > 1) throw new Error(`run id ${arg} matches ${hits.length} directories; pass the directory:\n${hits.map(h => h.dir).join('\n')}`);
  throw new Error(`run id ${arg} not found under ${root}`);
}

// ---------------------------------------------------------------------------
// Tailing one run
// ---------------------------------------------------------------------------

class RunTail {
  constructor(run, flow, emit) {
    this.run = run; this.flow = flow; this.emit = emit;
    this.agents = new Map();          // agentId -> parsed label + node
    this.facts = new Map();           // agentId -> { first, last, model, effort }
    this.offsets = new Map();         // file -> { pos, carry }
    this.ended = false;
  }

  readNew(file) {
    let st;
    try { st = fs.statSync(file); } catch (e) { return []; }
    const o = this.offsets.get(file) || { pos: 0, carry: '' };
    if (st.size < o.pos) { o.pos = 0; o.carry = ''; }       // truncated or replaced: read again
    if (st.size === o.pos) return [];
    const fd = fs.openSync(file, 'r');
    try {
      const buf = Buffer.alloc(st.size - o.pos);
      fs.readSync(fd, buf, 0, buf.length, o.pos);
      o.pos = st.size;
      const { rows, carry } = splitLines(o.carry, buf.toString('utf8'));
      o.carry = carry;
      this.offsets.set(file, o);
      return rows;
    } finally { fs.closeSync(fd); }
  }

  // Model, effort and times of one agent, read from its transcript; emits `agent_facts` when they change.
  // Reads new transcript rows; returns the facts event to send when something changed, else null.
  poke(agentId) {
    const rows = this.readNew(path.join(this.run.dir, `agent-${agentId}.jsonl`));
    if (!rows.length) return null;
    const before = JSON.stringify(this.facts.get(agentId) || null);
    const f = agentFacts(rows, this.facts.get(agentId));
    this.facts.set(agentId, f);
    return JSON.stringify(f) !== before ? { kind: 'agent_facts', run_id: this.run.id, agent_id: agentId, ...f } : null;
  }

  tick() {
    const ctx = { flow: this.flow, agents: this.agents, runId: this.run.id };
    for (const row of this.readNew(path.join(this.run.dir, 'journal.jsonl'))) {
      const ev = eventOf(row, ctx);
      if (!ev) continue;
      const facts = this.poke(ev.agent_id);
      const f = this.facts.get(ev.agent_id);
      if (f) ev.ts = ev.kind === 'started' ? f.first : f.last;
      this.emit(ev);                       // the page learns the agent first, then its facts
      if (facts) this.emit(facts);
    }
    for (const id of this.agents.keys()) { const facts = this.poke(id); if (facts) this.emit(facts); }
    if (!this.ended && this.run.summary && fs.existsSync(this.run.summary)) {
      try {
        this.emit(endEventOf(JSON.parse(fs.readFileSync(this.run.summary, 'utf8')), this.run.id));
        this.ended = true;
      } catch (e) { /* written but not complete yet: try on the next tick */ }
    }
  }
}

// ---------------------------------------------------------------------------
// Server
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const a = { project: process.cwd(), run: null, port: 4317, follow: true, idleExit: 0 };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i], v = argv[i + 1];
    if (k === '--project') { a.project = v; i++; }
    else if (k === '--run') { a.run = v; i++; }
    else if (k === '--port') { a.port = Number(v); i++; }
    else if (k === '--no-follow') a.follow = false;
    else if (k === '--idle-exit') { a.idleExit = Number(v); i++; }
    else if (k === '-h' || k === '--help') a.help = true;
    else throw new Error(`unknown argument: ${k}`);
  }
  if (!Number.isInteger(a.port) || a.port < 0 || a.port > 65535) throw new Error('--port must be 0..65535');
  if (!(a.idleExit >= 0)) throw new Error('--idle-exit must be a number of minutes, 0 or more');
  return a;
}

function start(opts) {
  const flow = JSON.parse(fs.readFileSync(opts.flowFile || path.join(HERE, 'flow.json'), 'utf8'));
  const page = fs.readFileSync(path.join(HERE, 'board.html'));
  const clients = new Set();
  let history = [], tail = null;

  const emit = ev => {
    history.push(ev);
    const data = `data: ${JSON.stringify(ev)}\n\n`;
    for (const res of clients) res.write(data);
  };
  const open = run => {
    history = [];
    tail = new RunTail(run, flow, emit);
    emit({ kind: 'run', run_id: run.id, dir: run.dir });
    tail.tick();
  };
  const projDir = opts.projectDir || path.join(projectsRoot(), projectKey(opts.project));
  const pickNewest = () => { const r = runsOf(projDir)[0]; return r || null; };

  if (opts.run) open(resolveRun(opts.run, opts.root));
  else { const r = pickNewest(); if (r) open(r); }

  // idleExit (minutes): stop once no run has been going for that long (the run ended, or none started).
  const idleMs = (opts.idleExit || 0) * 60000;
  let lastBusy = Date.now(), server = null;
  const timer = setInterval(() => {
    if (!opts.run && opts.follow) {
      const r = pickNewest();
      if (r && (!tail || r.id !== tail.run.id)) open(r);      // a newer run started: switch to it
    }
    if (tail) tail.tick();
    if (tail && !tail.ended) lastBusy = Date.now();
    else if (idleMs && server && Date.now() - lastBusy >= idleMs) server.close();
  }, opts.pollMs || POLL_MS);

  server = http.createServer((req, res) => {
    const url = (req.url || '/').split('?')[0];
    if (url === '/' || url === '/index.html') {
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' });
      return res.end(page);
    }
    if (url === '/flow.json') {
      res.writeHead(200, { 'content-type': 'application/json' });
      return res.end(JSON.stringify(flow));
    }
    if (url === '/state.json') {
      res.writeHead(200, { 'content-type': 'application/json' });
      return res.end(JSON.stringify({ project_dir: projDir, run: tail ? tail.run.id : null, events: history }));
    }
    if (url === '/events') {
      res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-store', connection: 'keep-alive' });
      res.write(`data: ${JSON.stringify({ kind: 'hello', project_dir: projDir, run_id: tail ? tail.run.id : null })}\n\n`);
      for (const ev of history) res.write(`data: ${JSON.stringify(ev)}\n\n`);
      clients.add(res);
      req.on('close', () => clients.delete(res));
      return;
    }
    res.writeHead(404); res.end('not found');
  });
  const ping = setInterval(() => { for (const res of clients) res.write(': ping\n\n'); }, 15000);
  server.on('close', () => { clearInterval(timer); clearInterval(ping); for (const res of clients) res.end(); clients.clear(); });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(opts.port, '127.0.0.1', () => resolve({ server, port: server.address().port, projDir }));
  });
}

const USAGE = `usage: node board.js [--project <path>] [--run <run id | run dir>] [--port <n>] [--no-follow]
  --project  the project whose newest ship.js run to show (default: the current directory)
  --run      one run: its id (wf_...) or its directory
  --port     port on 127.0.0.1 (default 4317; 0 picks a free one)
  --no-follow  stay on the run shown at start; by default the board switches to a newer run of the project
  --idle-exit  stop after this many minutes with no run going (default 0: never)`;

if (require.main === module) {
  let a;
  try { a = parseArgs(process.argv.slice(2)); } catch (e) { console.error(`board: ${e.message}\n${USAGE}`); process.exit(2); }
  if (a.help) { console.log(USAGE); process.exit(0); }
  start(a).then(({ server, port, projDir }) => {
    console.log(`board: http://127.0.0.1:${port}  (runs of ${projDir})`);
    server.on('close', () => { console.log('board: stopped (no run going)'); process.exit(0); });
  }).catch(e => { console.error(`board: ${e.message}`); process.exit(1); });
}

module.exports = { projectKey, parseLabel, nodeFor, statusOf, splitLines, agentFacts, eventOf, endEventOf, runsOf, resolveRun, RunTail, parseArgs, start };
