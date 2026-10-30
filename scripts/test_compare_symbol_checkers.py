#!/usr/bin/env python3
"""Tests for scripts/compare_symbol_checkers.py and its fixtures (#523).

Runs with or without the optional tools (pyright, typescript-language-server, graphify,
code-review-graph): the PATH is emptied for the tool-absent checks. Set SYMCHECK_TOOLS_DIR to also
check the tool rows with the tools present.
Run: python3 -I scripts/test_compare_symbol_checkers.py   (or via pytest)
"""
import os
import re
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_symbol_checkers as m  # noqa: E402

REPO = os.path.dirname(HERE)
FIXTURES = os.path.join(REPO, "tests", "fixtures")
SRC_EXT = {"py": (".py",), "ts": (".ts",)}


def fixture_sources(lang):
    root = os.path.join(FIXTURES, m.LANGS[lang])
    text = ""
    for dirpath, _, names in os.walk(root):
        for n in names:
            if n.endswith(SRC_EXT[lang]):
                with open(os.path.join(dirpath, n), encoding="utf-8") as fh:
                    text += fh.read() + "\n"
    return text


def has_word(text, word):
    return re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(word), text) is not None


class EmptyPath:
    """Run a block with no tool on PATH and no tools dir."""

    def __enter__(self):
        self.old = os.environ.get("PATH")
        self.empty = tempfile.mkdtemp(prefix="nopath-")
        os.environ["PATH"] = self.empty
        return self

    def __exit__(self, *a):
        if self.old is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = self.old
        os.rmdir(self.empty)


class FixtureTests(unittest.TestCase):
    def test_claim_files_meet_the_ticket_minimums(self):
        for lang in m.LANGS:
            claims = m.load_claims(os.path.join(FIXTURES, m.LANGS[lang]))
            self.assertGreaterEqual(len(claims), 20, lang)
            self.assertGreaterEqual(sum(c["label"] == "wrong-pair" for c in claims), 5, lang)
            self.assertTrue(all(c["label"] in m.LABELS for c in claims), lang)
            self.assertEqual(len({c["claim"] for c in claims}), len(claims), "duplicate claim in " + lang)

    def test_labels_hold_against_the_fixture_sources(self):
        for lang in m.LANGS:
            src = fixture_sources(lang)
            for c in m.load_claims(os.path.join(FIXTURES, m.LANGS[lang])):
                q, mem = c["claim"].rsplit(".", 1)
                ctx = os.path.join(FIXTURES, m.LANGS[lang], c["context"])
                self.assertTrue(os.path.isfile(ctx), c["claim"])
                if c["label"] in ("exists", "wrong-pair"):
                    self.assertTrue(has_word(src, q) and has_word(src, mem), "both names in source: " + c["claim"])
                if c["label"] == "missing":
                    self.assertFalse(has_word(src, mem), "member absent from source: " + c["claim"])
                if c["label"] == "wrong-pair":
                    self.assertNotIn(c["claim"], src, "wrong-pair written as a real use: " + c["claim"])


class ScoreTests(unittest.TestCase):
    def test_score_counts_false_pass_and_false_fail(self):
        claims = [{"claim": "a.b", "label": "exists"}, {"claim": "a.c", "label": "exists"},
                  {"claim": "a.d", "label": "missing"}, {"claim": "a.e", "label": "wrong-pair"}]
        s = m.score(claims, {"a.b": True, "a.c": False, "a.d": True, "a.e": False})
        self.assertEqual(s["exists"], {"total": 2, "correct": 1, "wrong": 1})
        self.assertEqual(s["missing"], {"total": 1, "correct": 0, "wrong": 1})
        self.assertEqual(s["wrong-pair"], {"total": 1, "correct": 1, "wrong": 0})

    def test_graphify_pairs_use_contains_and_method_edges(self):
        import json
        g = {"nodes": [{"id": "c", "label": "Cart", "file_type": "code"},
                       {"id": "m", "label": ".total()", "file_type": "code"},
                       {"id": "f", "label": "pricing.py", "file_type": "code"},
                       {"id": "fn", "label": "format_price()", "file_type": "code"},
                       {"id": "j", "label": "json", "file_type": "concept"}],
             "links": [{"source": "c", "target": "m", "relation": "method"},
                       {"source": "f", "target": "fn", "relation": "contains"},
                       {"source": "fn", "target": "j", "relation": "calls"}]}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "graph.json")
            with open(p, "w") as fh:
                json.dump(g, fh)
            self.assertEqual(m.graphify_pairs(p), {("Cart", "total"), ("pricing", "format_price")})

    def test_crg_pairs_use_parent_name_or_file_stem(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "graph.db")
            con = sqlite3.connect(p)
            con.execute("create table nodes (kind text, name text, parent_name text, file_path text)")
            con.executemany("insert into nodes values (?,?,?,?)", [
                ("File", "/x/pricing.py", None, "/x/pricing.py"),
                ("Function", "format_price", None, "/x/pricing.py"),
                ("Function", "total", "Cart", "/x/pricing.py")])
            con.commit()
            con.close()
            self.assertEqual(m.crg_pairs(p), {("pricing", "format_price"), ("Cart", "total")})


class BaselineTests(unittest.TestCase):
    def test_baseline_known_counts_on_both_fixtures(self):
        opts = {"tools_dir": None, "ground_check": os.path.join(REPO, "plugins", "harness", "scripts", "ground-check.sh"),
                "timeout": 60}
        for lang in m.LANGS:
            fdir = os.path.join(FIXTURES, m.LANGS[lang])
            claims = m.load_claims(fdir)
            res = m.measure("baseline", lang, fdir, claims, opts)
            s = res["score"]
            # The baseline accepts every dotted symbol whose names each appear somewhere: it never rejects a
            # real claim and never catches a wrong pair.
            self.assertEqual(s["exists"], {"total": 15, "correct": 15, "wrong": 0}, lang)
            self.assertEqual(s["missing"], {"total": 6, "correct": 6, "wrong": 0}, lang)
            self.assertEqual(s["wrong-pair"], {"total": 7, "correct": 0, "wrong": 7}, lang)
            self.assertGreaterEqual(res["cold"], 0)
            self.assertGreaterEqual(res["repeat"], 0)


class TableTests(unittest.TestCase):
    def setUp(self):
        self.opts = {"tools_dir": None, "ground_check": os.path.join(REPO, "plugins", "harness", "scripts", "ground-check.sh"),
                     "timeout": 60}

    def test_absent_tools_are_could_not_run_never_zero_correct(self):
        with EmptyPath():
            rows = m.run_all(FIXTURES, self.opts)
        for r in rows:
            if r["method"] == "baseline":
                self.assertIn("score", r)
                continue
            self.assertIn("could_not_run", r, r["method"])
            self.assertIn("not installed", r["could_not_run"])
            self.assertNotIn("score", r, "an absent tool must not carry a score")
        table = m.format_table(rows)
        self.assertIn("could not run: not installed: graphify", table)
        self.assertIn("could not run: not installed: code-review-graph", table)
        self.assertIn("could not run: not installed: pyright-langserver", table)
        self.assertIn("could not run: not installed: typescript-language-server", table)

    def test_table_has_one_row_per_method_and_language(self):
        with EmptyPath():
            rows = m.run_all(FIXTURES, self.opts)
        data = [ln for ln in m.format_table(rows).splitlines() if ln.split(" | ")[0].strip() in m.METHODS]
        self.assertEqual(len(data), len(m.METHODS) * len(m.LANGS))
        for method in m.METHODS:
            for lang in m.LANGS:
                self.assertEqual(sum(1 for ln in data if ln.startswith(method) and (" | %s " % lang) in ln), 1, (method, lang))

    def test_tools_present_rows_are_scored_when_a_tools_dir_is_given(self):
        td = os.environ.get("SYMCHECK_TOOLS_DIR")
        if not td:
            self.skipTest("SYMCHECK_TOOLS_DIR not set")
        rows = m.run_all(FIXTURES, dict(self.opts, tools_dir=td))
        for r in rows:
            self.assertTrue(("score" in r) != ("could_not_run" in r), r["method"])
            if "score" in r:
                total = sum(v["total"] for v in r["score"].values())
                self.assertEqual(total, len(r["claims"]))


class CrgArgvTests(unittest.TestCase):
    def test_code_review_graph_is_not_given_the_rejected_quiet_flag(self):
        td = tempfile.mkdtemp(prefix="fakecrg-")
        os.makedirs(os.path.join(td, "venv-crg", "bin"))
        exe = os.path.join(td, "venv-crg", "bin", "code-review-graph")
        with open(exe, "w") as fh:
            fh.write("#!/bin/sh\nfor a in \"$@\"; do [ \"$a\" = -q ] && { echo 'no such option: -q' >&2; exit 2; }; done\n"
                     "mkdir -p .code-review-graph; python3 -c \"import sqlite3;sqlite3.connect('.code-review-graph/graph.db').close()\"\n")
        os.chmod(exe, 0o755)
        work = tempfile.mkdtemp(prefix="crgwork-")
        fdir = os.path.join(FIXTURES, m.LANGS["py"])
        opts = {"tools_dir": td, "timeout": 60}
        try:
            m.graph_method("code-review-graph", "py", fdir, [], work, opts, False)
        except m.CouldNotRun as exc:
            self.assertNotIn("exit 2", str(exc))
        except Exception:
            pass  # empty fake db has no schema; only the argv matters

    def test_repeat_run_does_a_real_build_not_a_noop_update(self):
        td = tempfile.mkdtemp(prefix="fakecrg-")
        os.makedirs(os.path.join(td, "venv-crg", "bin"))
        exe = os.path.join(td, "venv-crg", "bin", "code-review-graph")
        log = os.path.join(td, "argv.log")
        with open(exe, "w") as fh:
            fh.write("#!/bin/sh\necho \"$1\" >> \"%s\"\n"
                     "mkdir -p .code-review-graph; python3 -c \"import sqlite3;sqlite3.connect('.code-review-graph/graph.db').close()\"\n" % log)
        os.chmod(exe, 0o755)
        work = tempfile.mkdtemp(prefix="crgwork-")
        fdir = os.path.join(FIXTURES, m.LANGS["py"])
        opts = {"tools_dir": td, "timeout": 60}
        try:
            m.graph_method("code-review-graph", "py", fdir, [], work, opts, True)
        except Exception:
            pass  # empty fake db has no schema; only the argv matters
        with open(log) as fh:
            self.assertEqual(fh.read().split(), ["build"])


if __name__ == "__main__":
    unittest.main()
