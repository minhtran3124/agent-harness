#!/usr/bin/env python3
"""Compare ways to check a `qualifier.member` claim against code (spike for #523).

Methods: the baseline plugins/harness/scripts/ground-check.sh, a language server (pyright for Python,
typescript-language-server for TS), graphify, code-review-graph and codegraph. The codegraph row uses the
same (container, member) rule as the other graph tools; the alias-aware row also reads the import aliases
and `instantiates` edges of the context file, the best this index can do. Every method answers only
"found" or "not found" for a claim; the runner scores that answer against the label in claims.tsv.
The output of every tool is untrusted: a tool is never trusted past that one bit.

Usage:
  python3 -I scripts/compare_symbol_checkers.py --fixtures tests/fixtures [--tools-dir DIR]
                                                [--details] [--json]

Fixtures: <fixtures>/ground-check-py and <fixtures>/ground-check-ts, each with claims.tsv
(claim, label, context file, note). Labels: exists, missing, wrong-pair.

Tool lookup: --tools-dir (or env SYMCHECK_TOOLS_DIR) is searched first, then PATH. A method whose tool
is absent or does not start prints `could not run: <reason>` and is never scored as 0 correct.
Stdlib only. The fixtures are copied to a temp dir, so no tool writes into the repo.
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

LABELS = ("exists", "missing", "wrong-pair")
LANGS = {"py": "ground-check-py", "ts": "ground-check-ts"}
METHODS = ("baseline", "language server", "graphify", "code-review-graph", "codegraph", "alias-aware codegraph")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BASE_PATH = "/usr/local/bin:/usr/bin:/bin"


class CouldNotRun(Exception):
    """A method that cannot run: tool absent, did not start, or gave no usable answer."""


class NoReply(CouldNotRun):
    """One request got no reply in time. The server may only be slow, unlike a server that exited."""


# ---------------------------------------------------------------- claims and tools

def load_claims(fixture_dir):
    claims = []
    with open(os.path.join(fixture_dir, "claims.tsv"), encoding="utf-8") as fh:
        rows = [ln.rstrip("\n").split("\t") for ln in fh if ln.strip()]
    for row in rows[1:]:
        claims.append({"claim": row[0], "label": row[1], "context": row[2], "note": row[3] if len(row) > 3 else ""})
    return claims


def find_tool(rel_candidates, names, tools_dir):
    """Return an absolute path or None. tools_dir first, then PATH."""
    if tools_dir:
        for rel in rel_candidates:
            p = os.path.join(tools_dir, rel)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        for n in names:
            p = os.path.join(tools_dir, "bin", n)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def run(cmd, cwd=None, env=None, timeout=120):
    try:
        return subprocess.run(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CouldNotRun("timed out after %ss: %s" % (timeout, os.path.basename(cmd[0])))
    except OSError as exc:
        raise CouldNotRun("did not start: %s" % exc)


def tool_version(path, flag="--version"):
    try:
        out = subprocess.run([path, flag], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        return (out.stdout or out.stderr).strip().splitlines()[-1] if (out.stdout or out.stderr).strip() else "?"
    except (OSError, subprocess.TimeoutExpired):
        return "?"


# ---------------------------------------------------------------- baseline: ground-check.sh

def baseline(lang, fixture_dir, claims, work, opts):
    gc = opts["ground_check"]
    if not os.path.isfile(gc):
        raise CouldNotRun("ground-check.sh not found at %s" % gc)
    repo = os.path.join(work, "repo")
    env = dict(os.environ, PATH=BASE_PATH + ":" + os.environ.get("PATH", ""),
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    if not os.path.isdir(repo):
        shutil.copytree(fixture_dir, repo, ignore=shutil.ignore_patterns("claims.tsv"))
        for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                    ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "fixture"]):
            r = run(cmd, cwd=repo, env=env)
            if r.returncode != 0:
                raise CouldNotRun("git fixture setup failed: %s" % r.stderr.strip()[:120])
    md = os.path.join(work, "claims.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write("# Claims\n\n")
        for c in claims:
            fh.write("- `%s`\n" % c["claim"])
    r = run(["bash", gc, "--repo", repo, "--ref", "HEAD", "--mode", "full", md], env=env)
    if r.returncode not in (0, 1):
        raise CouldNotRun("ground-check.sh exit %s: %s" % (r.returncode, r.stderr.strip()[:120]))
    failed = set()
    for line in r.stdout.splitlines():
        # Any FAIL kind rejects the claim it names (path, line, quote, command, pins as well as symbol).
        m = re.match(r"FAIL (?:path|line|quote|symbol|command|pins): (\S+) \(", line)
        if m:
            failed.add(m.group(1))
    return {c["claim"]: c["claim"] not in failed for c in claims}


# ---------------------------------------------------------------- language server (LSP over stdio)

class Lsp:
    def __init__(self, cmd, cwd, env):
        try:
            self.proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL)
        except OSError as exc:
            raise CouldNotRun("did not start: %s" % exc)
        self.next_id = 1
        self.replies = {}
        self.abandoned = set()  # ids of requests that timed out: a late reply to one is dropped
        self.cv = threading.Condition()
        self.closed = False
        threading.Thread(target=self._read, daemon=True).start()

    def _send(self, obj):
        body = json.dumps(obj).encode()
        try:
            self.proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
            self.proc.stdin.flush()
        except (OSError, ValueError):
            raise CouldNotRun("server closed its stdin")

    def _read(self):
        out = self.proc.stdout
        try:
            while True:
                length = None
                while True:
                    line = out.readline()
                    if not line:
                        return
                    line = line.strip()
                    if not line:
                        break
                    if line.lower().startswith(b"content-length:"):
                        length = int(line.split(b":")[1])
                if length is None:
                    continue
                msg = json.loads(out.read(length))
                if "method" in msg and "id" in msg:  # a request from the server: answer with an empty result
                    res = None
                    if msg["method"] == "workspace/configuration":
                        res = [None] * len(msg.get("params", {}).get("items", []))
                    try:
                        self._send({"jsonrpc": "2.0", "id": msg["id"], "result": res})
                    except CouldNotRun:
                        return
                elif "id" in msg:
                    with self.cv:
                        if msg["id"] in self.abandoned:
                            self.abandoned.discard(msg["id"])
                        else:
                            self.replies[msg["id"]] = msg
                        self.cv.notify_all()
        except (OSError, ValueError):
            return
        finally:
            with self.cv:
                self.closed = True
                self.cv.notify_all()

    def request(self, method, params, timeout):
        rid = self.next_id
        self.next_id += 1
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.time() + timeout
        with self.cv:
            while rid not in self.replies:
                left = deadline - time.time()
                if left <= 0:
                    self.abandoned.add(rid)
                    raise NoReply("no reply to %s within %ss" % (method, timeout))
                if self.closed and rid not in self.replies:
                    raise CouldNotRun("server exited during %s" % method)
                self.cv.wait(min(left, 1.0))
            return self.replies.pop(rid)

    def notify(self, method, params):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def close(self):
        try:
            self.request("shutdown", None, 5)
            self.notify("exit", None)
        except CouldNotRun:
            pass
        try:
            self.proc.kill()
            self.proc.wait(timeout=5)
            self.proc.stdin.close()
            self.proc.stdout.close()
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass


def lsp_cmd(lang, tools_dir):
    if lang == "py":
        p = find_tool(["venv-pyright/bin/pyright-langserver"], ["pyright-langserver"], tools_dir)
        if not p:
            raise CouldNotRun("not installed: pyright-langserver")
        return [p, "--stdio"], "pyright"
    p = find_tool(["npm/node_modules/.bin/typescript-language-server"], ["typescript-language-server"], tools_dir)
    if not p:
        raise CouldNotRun("not installed: typescript-language-server")
    return [p, "--stdio"], "typescript-language-server"


def lsp_probe_files(lang, root, claims):
    """Write one probe file per context file: the context source plus one line per claim.
    Returns {claim: (probe relpath, line, column of the member)}."""
    by_ctx = {}
    for c in claims:
        by_ctx.setdefault(c["context"], []).append(c)
    where = {}
    ext = ".py" if lang == "py" else ".ts"
    for ctx, cl in by_ctx.items():
        with open(os.path.join(root, ctx), encoding="utf-8") as fh:
            src = fh.read().rstrip("\n").split("\n")
        probe_rel = ctx[: -len(ext)] + "__probe" + ext
        lines = list(src)
        for i, c in enumerate(cl):
            text = ("_p%d = %s" if lang == "py" else "void (%s);") % ((i, c["claim"]) if lang == "py" else (c["claim"],))
            lines.append(text)
            col = text.index(c["claim"]) + c["claim"].rfind(".") + 1
            where[c["claim"]] = (probe_rel, len(lines) - 1, col)
        with open(os.path.join(root, probe_rel), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return where


def language_server(lang, fixture_dir, claims, work, opts):
    cmd, name = lsp_cmd(lang, opts["tools_dir"])
    root = os.path.join(work, "proj")
    if os.path.isdir(root):
        shutil.rmtree(root)
    shutil.copytree(fixture_dir, root, ignore=shutil.ignore_patterns("claims.tsv"))
    where = lsp_probe_files(lang, root, claims)
    timeout = opts["timeout"]
    lsp = Lsp(cmd, root, dict(os.environ))
    try:
        uri = "file://" + root
        init = lsp.request("initialize", {"processId": os.getpid(), "rootUri": uri,
                                          "capabilities": {"textDocument": {"definition": {"linkSupport": False}}},
                                          "workspaceFolders": [{"uri": uri, "name": "fx"}]}, timeout)
        if "error" in init:
            raise CouldNotRun("initialize failed: %s" % str(init["error"])[:120])
        lsp.notify("initialized", {})
        opened = set()
        for probe_rel, _, _ in where.values():
            if probe_rel in opened:
                continue
            opened.add(probe_rel)
            with open(os.path.join(root, probe_rel), encoding="utf-8") as fh:
                text = fh.read()
            lsp.notify("textDocument/didOpen", {"textDocument": {
                "uri": "file://" + os.path.join(root, probe_rel),
                "languageId": "python" if lang == "py" else "typescript", "version": 1, "text": text}})
        def definition(claim, wait=timeout):
            probe_rel, line, col = where[claim]
            return lsp.request("textDocument/definition", {
                "textDocument": {"uri": "file://" + os.path.join(root, probe_rel)},
                "position": {"line": line, "character": col}}, wait)

        # Readiness gate: a server answers [] until its project has loaded. Poll the last `exists` claim
        # until it resolves (or the gate timeout passes) so no scored claim is asked before the project is
        # ready. Each gate request waits at most the time left, so the total wait stays near the gate
        # timeout. A server that never becomes ready is not a failed run: it is scored as it answers, so the
        # row keeps its measured misses. Every scored claim is then asked once; the gate claim is asked
        # once more in that pass, and a late reply to a timed-out gate request is dropped by Lsp.
        gate = [c["claim"] for c in claims if c["label"] == "exists"][-1]
        gate_timeout = opts.get("gate_timeout", 30)
        deadline = time.time() + gate_timeout
        while True:
            left = deadline - time.time()
            if left <= 0:
                break
            try:
                if definition(gate, min(timeout, left)).get("result"):
                    break
            except NoReply:
                pass  # a slow load: a request that timed out before the gate deadline is polled again
            except CouldNotRun:
                raise  # server died or closed its stdin: a real failure, not a slow load
            time.sleep(min(0.3, max(0.0, deadline - time.time())))
        found = {}
        answered = 0
        for c in claims:
            rep = definition(c["claim"])
            if "error" in rep:
                found[c["claim"]] = False
                continue
            answered += 1
            res = rep.get("result")
            found[c["claim"]] = bool(res) and (not isinstance(res, list) or len(res) > 0)
        if answered == 0:
            raise CouldNotRun("%s answered no definition request" % name)
        return found
    finally:
        lsp.close()


# ---------------------------------------------------------------- graph tools: (container, member) pairs

def stem(label):
    return re.sub(r"\.(py|ts|tsx|js|jsx)$", "", label)


def graphify_pairs(graph_json):
    with open(graph_json, encoding="utf-8") as fh:
        g = json.load(fh)
    nodes = {n["id"]: n for n in g.get("nodes", [])}
    pairs = set()
    for e in g.get("links", g.get("edges", [])):
        if e.get("relation") not in ("contains", "method"):
            continue
        a, b = nodes.get(e.get("source")), nodes.get(e.get("target"))
        if not a or not b or a.get("file_type") != "code" or b.get("file_type") != "code":
            continue
        container = stem(re.sub(r"\(\)$", "", a.get("label", "")).lstrip("."))
        member = re.sub(r"\(\)$", "", b.get("label", "")).lstrip(".")
        pairs.add((container, member))
    return pairs


def crg_pairs(db_path):
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    try:
        pairs = set()
        for kind, name, parent, fpath in con.execute("select kind, name, parent_name, file_path from nodes"):
            if kind == "File":
                continue
            container = parent if parent else stem(os.path.basename(fpath or ""))
            pairs.add((container, name))
        return pairs
    finally:
        con.close()


def codegraph_pairs(db_path):
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    try:
        pairs = set()
        for kind, name, qualified, fpath in con.execute("select kind, name, qualified_name, file_path from nodes"):
            if kind in ("file", "import"):
                continue
            container = qualified.rsplit("::", 1)[0] if "::" in (qualified or "") else stem(os.path.basename(fpath or ""))
            pairs.add((container, name))
        return pairs
    finally:
        con.close()


def codegraph_aliases(db_path, context):
    """{local name: real name} for one file: import aliases, then instances from `instantiates` edges."""
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    try:
        aliases = {}
        for (sig,) in con.execute("select signature from nodes where kind = 'import' and file_path = ?", (context,)):
            sig = sig or ""
            star = re.match(r"import \* as (\w+) from [\"'](.+?)[\"']", sig)
            if star:
                aliases[star.group(1)] = star.group(2).rsplit("/", 1)[-1]
            for real, local in re.findall(r"([\w.]+) as (\w+)", sig if not star else ""):
                aliases[local] = real.rsplit(".", 1)[-1]
        for name, target in con.execute(
                "select s.name, t.name from edges e join nodes s on s.id = e.source join nodes t on t.id = e.target "
                "where e.kind = 'instantiates' and s.file_path = ? and s.kind != 'function'", (context,)):
            aliases[name] = target
        return aliases
    finally:
        con.close()


def graph_method(tool, lang, fixture_dir, claims, work, opts, repeat):
    root = os.path.join(work, "proj")
    if not os.path.isdir(root):
        shutil.copytree(fixture_dir, root, ignore=shutil.ignore_patterns("claims.tsv"))
    env = dict(os.environ)
    if tool == "graphify":
        exe = find_tool(["venv-graphify/bin/graphify"], ["graphify"], opts["tools_dir"])
        if not exe:
            raise CouldNotRun("not installed: graphify")
        # Same rule as code-review-graph below: every run is a full build. Drop the previous
        # output so a repeat run cannot be an incremental no-op and the cold/repeat columns match.
        shutil.rmtree(os.path.join(root, "graphify-out"), ignore_errors=True)
        r = run([exe, "update", "."], cwd=root, env=env, timeout=opts["timeout"])
        out = os.path.join(root, "graphify-out", "graph.json")
        if r.returncode != 0 or not os.path.isfile(out):
            raise CouldNotRun("graphify update exit %s: %s" % (r.returncode, (r.stderr or r.stdout).strip()[-120:]))
        pairs = graphify_pairs(out)
    elif tool in ("codegraph", "alias-aware codegraph"):
        exe = find_tool(["npm/node_modules/.bin/codegraph"], ["codegraph"], opts["tools_dir"])
        if not exe:
            raise CouldNotRun("not installed: codegraph")
        # Every run is a full build, as above. No daemon: a watcher must not outlive the temp dir.
        shutil.rmtree(os.path.join(root, ".codegraph"), ignore_errors=True)
        r = run([exe, "init", "--yes"], cwd=root, env=dict(env, CODEGRAPH_NO_DAEMON="1", CODEGRAPH_TELEMETRY="0"),
                timeout=opts["timeout"])
        db = os.path.join(root, ".codegraph", "codegraph.db")
        if r.returncode != 0 or not os.path.isfile(db):
            raise CouldNotRun("codegraph exit %s: %s" % (r.returncode, (r.stderr or r.stdout).strip()[-120:]))
        pairs = codegraph_pairs(db)
        if tool == "alias-aware codegraph":
            result = {}
            for c in claims:
                q, member = c["claim"].rsplit(".", 1)
                aliases = codegraph_aliases(db, c["context"])
                result[c["claim"]] = (aliases.get(q, q), member) in pairs
            return result
    else:
        exe = find_tool(["venv-crg/bin/code-review-graph"], ["code-review-graph"], opts["tools_dir"])
        if not exe:
            raise CouldNotRun("not installed: code-review-graph")
        # Always a full build: "update" does nothing on an unchanged non-git fixture, so a repeat
        # run through it would carry no timing or determinism information.
        r = run([exe, "build", "--repo", root], cwd=root, env=env, timeout=opts["timeout"])
        db = os.path.join(root, ".code-review-graph", "graph.db")
        if r.returncode != 0 or not os.path.isfile(db):
            raise CouldNotRun("code-review-graph exit %s: %s" % (r.returncode, (r.stderr or r.stdout).strip()[-120:]))
        pairs = crg_pairs(db)
    result = {}
    for c in claims:
        q, m = c["claim"].rsplit(".", 1)
        result[c["claim"]] = (q, m) in pairs
    return result


# ---------------------------------------------------------------- scoring and table

def score(claims, found):
    """Per label: total, correct, wrong. wrong is a false pass for missing/wrong-pair, a false fail for exists."""
    out = {l: {"total": 0, "correct": 0, "wrong": 0} for l in LABELS}
    for c in claims:
        s = out[c["label"]]
        s["total"] += 1
        accepted = found[c["claim"]]
        ok = accepted if c["label"] == "exists" else not accepted
        s["correct" if ok else "wrong"] += 1
    return out


def timed(fn):
    t0 = time.time()
    res = fn()
    return res, time.time() - t0


def measure(method, lang, fixture_dir, claims, opts):
    work = tempfile.mkdtemp(prefix="symcheck-")
    try:
        if method == "baseline":
            fn = lambda rep: baseline(lang, fixture_dir, claims, work, opts)
        elif method == "language server":
            fn = lambda rep: language_server(lang, fixture_dir, claims, work, opts)
        else:
            tool = method
            fn = lambda rep: graph_method(tool, lang, fixture_dir, claims, work, opts, rep)
        cold, t_cold = timed(lambda: fn(False))
        rep, t_rep = timed(lambda: fn(True))
        if cold != rep:
            raise CouldNotRun("cold and repeat run gave different answers")
        return {"found": cold, "score": score(claims, cold), "cold": t_cold, "repeat": t_rep}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_all(fixtures, opts):
    rows = []
    for method in METHODS:
        for lang, sub in LANGS.items():
            fdir = os.path.join(fixtures, sub)
            row = {"method": method, "lang": lang, "claims": load_claims(fdir)}  # a bad claims.tsv must surface
            try:
                row.update(measure(method, lang, fdir, row["claims"], opts))
            except CouldNotRun as exc:
                row["could_not_run"] = str(exc)
            except (sqlite3.Error, OSError, ValueError) as exc:  # tool database, IO or unreadable output (JSON, UTF-8): keep the rows already done; bugs (KeyError) must surface
                row["could_not_run"] = "%s: %s" % (type(exc).__name__, str(exc)[:120])
            rows.append(row)
    return rows


def format_table(rows):
    head = ["method", "lang", "exists ok", "exists FF", "missing ok", "missing FP", "wrong-pair ok", "wrong-pair FP",
            "cold s", "repeat s"]
    lines = []
    for r in rows:
        if "could_not_run" in r:
            lines.append([r["method"], r["lang"], "could not run: " + r["could_not_run"]])
            continue
        s = r["score"]
        lines.append([r["method"], r["lang"],
                      "%d/%d" % (s["exists"]["correct"], s["exists"]["total"]), str(s["exists"]["wrong"]),
                      "%d/%d" % (s["missing"]["correct"], s["missing"]["total"]), str(s["missing"]["wrong"]),
                      "%d/%d" % (s["wrong-pair"]["correct"], s["wrong-pair"]["total"]), str(s["wrong-pair"]["wrong"]),
                      "%.2f" % r["cold"], "%.2f" % r["repeat"]])
    widths = [len(h) for h in head]
    for ln in lines:
        for i, cell in enumerate(ln[: len(head)] if len(ln) == len(head) else ln[:2]):
            widths[i] = max(widths[i], len(cell))
    fmt = lambda cells: " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells)).rstrip()
    out = [fmt(head), "-+-".join("-" * w for w in widths)]
    out += [" | ".join([ln[0].ljust(widths[0]), ln[1].ljust(widths[1]), ln[2]]) if len(ln) == 3 else fmt(ln) for ln in lines]
    out.append("")
    out.append("ok = correct/total. FF = false fail (a good claim rejected). FP = false pass (a bad claim accepted).")
    return "\n".join(out)


def format_details(rows):
    out = []
    for r in rows:
        if "could_not_run" in r:
            continue
        for c in r["claims"]:
            accepted = r["found"][c["claim"]]
            ok = accepted if c["label"] == "exists" else not accepted
            if not ok:
                kind = "false fail" if c["label"] == "exists" else "false pass"
                out.append("%s/%s: %s %s [%s] in %s" % (r["method"], r["lang"], kind, c["claim"], c["label"], c["context"]))
    return "\n".join(out)


def versions(opts):
    td = opts["tools_dir"]
    probes = [("pyright", ["venv-pyright/bin/pyright"], ["pyright"]),
              ("typescript-language-server", ["npm/node_modules/.bin/typescript-language-server"], ["typescript-language-server"]),
              ("graphify", ["venv-graphify/bin/graphify"], ["graphify"]),
              ("code-review-graph", ["venv-crg/bin/code-review-graph"], ["code-review-graph"]),
              ("codegraph", ["npm/node_modules/.bin/codegraph"], ["codegraph"])]
    out = []
    for name, rel, names in probes:
        p = find_tool(rel, names, td)
        out.append("%s: %s" % (name, tool_version(p) if p else "not installed"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fixtures", required=True, help="directory holding ground-check-py and ground-check-ts")
    ap.add_argument("--tools-dir", default=os.environ.get("SYMCHECK_TOOLS_DIR"), help="where the optional tools are installed")
    ap.add_argument("--ground-check", default=os.path.join(REPO, "plugins", "harness", "scripts", "ground-check.sh"))
    ap.add_argument("--timeout", type=int, default=90, help="seconds per tool call")
    ap.add_argument("--gate-timeout", type=float, default=30, help="seconds a language server may take to load its project")
    ap.add_argument("--details", action="store_true", help="list every misjudged claim")
    ap.add_argument("--json", action="store_true", help="print the rows as JSON instead of the table")
    a = ap.parse_args(argv)
    opts = {"tools_dir": a.tools_dir, "ground_check": a.ground_check, "timeout": a.timeout,
            "gate_timeout": a.gate_timeout}
    rows = run_all(a.fixtures, opts)
    if a.json:
        print(json.dumps(rows, indent=1))
        return 0
    print(format_table(rows))
    print("")
    print("\n".join(versions(opts)))
    if a.details:
        print("")
        print(format_details(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
