#!/usr/bin/env node
'use strict';
// Start the run board for this project (or reuse the one already running) and open it in a browser.
// Autopilot runs this just before it launches the workflow. It never fails the launch: on any problem it
// prints one line and exits 0. Only a bad argument exits 2.
//
//   node open_board.js [--project <dir>] [--port <n>] [--idle-exit <minutes>] [--no-open]

const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

const BOARD = path.resolve(__dirname, '..', '..', '..', 'board', 'board.js');

function parseArgs(argv) {
  const a = { project: process.cwd(), port: 4317, idleExit: 30, open: true };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i], v = argv[i + 1];
    if (k === '--project') { a.project = v; i++; }
    else if (k === '--port') { a.port = Number(v); i++; }
    else if (k === '--idle-exit') { a.idleExit = Number(v); i++; }
    else if (k === '--no-open') a.open = false;
    else throw new Error(`unknown argument: ${k}`);
  }
  if (!a.project) throw new Error('--project needs a directory');
  if (!Number.isInteger(a.port) || a.port < 1 || a.port > 65535) throw new Error('--port must be 1..65535');
  if (!(a.idleExit >= 0)) throw new Error('--idle-exit must be 0 or more minutes');
  return a;
}

// The board on <port>, if one answers: { project_dir } from its /state.json, else null.
function probe(port, timeoutMs = 1000) {
  return new Promise(resolve => {
    const req = http.get({ host: '127.0.0.1', port, path: '/state.json', timeout: timeoutMs }, res => {
      let body = '';
      res.on('data', c => { body += c; });
      res.on('end', () => { try { const j = JSON.parse(body); resolve(j && 'events' in j ? j : null); } catch (e) { resolve(null); } });
    });
    req.on('timeout', () => { req.destroy(); resolve(null); });
    req.on('error', () => resolve(null));
  });
}

function canOpen(env = process.env, platform = process.platform) {
  if (env.HARNESS_BOARD_NO_OPEN === '1' || env.CI) return false;
  if (platform === 'darwin' || platform === 'win32') return true;
  return Boolean(env.DISPLAY || env.WAYLAND_DISPLAY);      // Linux with no desktop: nothing to open
}

function openBrowser(url, platform = process.platform) {
  const [cmd, args] = platform === 'darwin' ? ['open', [url]]
    : platform === 'win32' ? ['cmd', ['/c', 'start', '', url]]
    : ['xdg-open', [url]];
  try { spawn(cmd, args, { detached: true, stdio: 'ignore' }).on('error', () => {}).unref(); return true; } catch (e) { return false; }
}

// Start board.js detached; its first stdout line names the URL. Resolves the URL or null.
function startBoard(a, waitMs = 5000) {
  const log = path.join(os.tmpdir(), `harness-board-${process.pid}-${Date.now()}.log`);
  const fd = fs.openSync(log, 'a');
  const child = spawn(process.execPath, [BOARD, '--project', a.project, '--port', String(a.port), '--idle-exit', String(a.idleExit)],
    { detached: true, stdio: ['ignore', fd, fd] });
  child.on('error', () => {});
  child.unref();
  fs.closeSync(fd);
  return new Promise(resolve => {
    const t0 = Date.now();
    const look = () => {
      let text = '';
      try { text = fs.readFileSync(log, 'utf8'); } catch (e) { /* not written yet */ }
      const m = text.match(/board: (http:\/\/127\.0\.0\.1:\d+)/);
      if (m) return resolve({ url: m[1], log });
      if (/board: /.test(text) || Date.now() - t0 > waitMs) return resolve({ url: null, log, text: text.trim().split('\n').pop() });
      setTimeout(look, 100);
    };
    look();
  });
}

async function main(argv, env = process.env) {
  let a;
  try { a = parseArgs(argv); } catch (e) { console.error(`open_board: ${e.message}`); return 2; }
  const { projectKey } = require(BOARD);
  const want = projectKey(path.resolve(a.project));
  const running = await probe(a.port);
  let url;
  if (running && path.basename(running.project_dir || '') === want) {
    url = `http://127.0.0.1:${a.port}`;
    console.log(`board: ${url} (already running for this project)`);
  } else {
    if (running) a.port = 0;      // another project's board holds the port: take a free one
    const r = await startBoard(a);
    if (!r.url) { console.log(`board: not started (${r.text || 'no answer'}; log ${r.log}). The run goes on without it.`); return 0; }
    url = r.url;
    console.log(`board: ${url} (started; it stops ${a.idleExit ? `after ${a.idleExit} min with no run going` : 'when you stop it'})`);
  }
  if (!a.open) console.log('board: browser not opened (--no-open)');
  else if (!canOpen(env)) console.log(`board: no desktop here, so no browser opened; open ${url} yourself`);
  else if (!openBrowser(url)) console.log(`board: could not open a browser; open ${url} yourself`);
  return 0;
}

if (require.main === module) main(process.argv.slice(2)).then(code => process.exit(code), e => { console.log(`board: not started (${e.message}). The run goes on without it.`); process.exit(0); });

module.exports = { parseArgs, probe, canOpen, startBoard, main, BOARD };
