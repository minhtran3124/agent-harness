"""Tests for check_review_receipt.py.

Run:

    python -m pytest scripts/test_check_review_receipt.py -x -q

Hermetic: each test builds a throwaway git repo in tmp_path, writes a
.review-receipt.json under a slug dir inside it, and invokes the checker with
HEAD resolved from that repo.
"""

import importlib.util
import json
import subprocess
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "check_review_receipt", Path(__file__).resolve().parent / "check_review_receipt.py"
)
assert _SPEC and _SPEC.loader, "could not load check_review_receipt.py"
crr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(crr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def make_repo(tmp_path: Path) -> Path:
    """Init a throwaway repo with one commit; return the repo root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    # Pin the initial branch name: two ancestry tests below check out `main` by
    # name after an orphan branch. `git init` alone uses the host's
    # init.defaultBranch, so those tests passed only on machines configured for
    # `main` and failed on CI runners defaulting to `master`. Matches the idiom
    # already used in skills/subagent-driven-development/scripts/test_simplify_record.py.
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def head_sha(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD")


def new_commit(repo: Path) -> None:
    (repo / "seed.txt").write_text("changed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "second")


def new_specs_commit(repo: Path, slug: str) -> None:
    """Advance HEAD with a specs/-only bookkeeping commit (the plan-shipped kind)."""
    plan = repo / "specs" / slug / "PLAN.md"
    plan.write_text("status: shipped\n", encoding="utf-8")
    _git(repo, "add", str(plan.relative_to(repo)))
    _git(repo, "commit", "-q", "-m", "chore: mark plan shipped")


def commit_file(repo: Path, relpath: str, content: str = "x\n") -> None:
    """Create/overwrite relpath and commit it; return nothing."""
    p = repo / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    _git(repo, "add", relpath)
    _git(repo, "commit", "-q", "-m", f"add {relpath}")


def audit_data(sha: str, audit_result: str = "pass") -> dict:
    d = valid_data(sha)
    d["reviews"].append(
        {
            "type": "context-propagation-audit",
            "reviewer": "sonnet",
            "result": audit_result,
            "blocking_open": 0,
            "advisory_open": 0,
        }
    )
    return d


def write_receipt(repo: Path, slug: str, data) -> Path:
    slug_dir = repo / "specs" / slug
    slug_dir.mkdir(parents=True)
    receipt = slug_dir / crr.RECEIPT_NAME
    if isinstance(data, str):
        receipt.write_text(data, encoding="utf-8")
    else:
        receipt.write_text(json.dumps(data), encoding="utf-8")
    return slug_dir


def valid_data(sha: str) -> dict:
    return {
        "reviewed_head_sha": sha,
        "reviews": [
            {
                "type": "correctness",
                "reviewer": "opus",
                "result": "pass",
                "blocking_open": 0,
                "advisory_open": 1,
            },
            {
                "type": "intent",
                "reviewer": "opus",
                "result": "pass",
                "blocking_open": 0,
                "advisory_open": 0,
            },
        ],
        "created": "2026-07-22T00:00:00",
    }


# ---------------------------------------------------------------------------
# Test cases (mapped to the task's required 6)
# ---------------------------------------------------------------------------


def test_fresh_receipt_with_required_types_passes(tmp_path):
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    assert crr.main([str(slug_dir), "--require", "correctness,intent"]) == 0


def test_new_commit_makes_receipt_stale(tmp_path, capsys):
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    new_commit(repo)
    assert crr.main([str(slug_dir)]) == 1
    assert "stale-sha" in capsys.readouterr().err


def test_specs_only_advance_stays_valid(tmp_path):
    # The plan-shipped bookkeeping commit touches only specs/ — it must NOT stale
    # a valid receipt (Codex P1 on PR #155): finishing validates, commits the
    # shipped status, then pushes; the pushed SHA differs only by that commit.
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    new_specs_commit(repo, "gh-x")
    assert crr.main([str(slug_dir), "--require", "correctness,intent"]) == 0


def test_eval_evidence_only_advance_stays_valid(tmp_path):
    # Re-collecting stored shadow-eval evidence advances HEAD but adds no
    # reviewable surface — rules/simplify-stage.md excludes evals/ results and
    # transcripts, and the branch review package scopes them out as pure data.
    # Such a commit must not stale an otherwise valid receipt.
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    commit_file(repo, "evals/skills/s/results/candidate.json", "{}\n")
    assert crr.main([str(slug_dir), "--require", "correctness,intent"]) == 0


def test_eval_evidence_plus_code_advance_still_stale(tmp_path, capsys):
    # The exemption is per-path, not per-commit: real code riding along with
    # eval evidence is still unreviewed.
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    (repo / "evals" / "skills" / "s" / "results").mkdir(parents=True)
    (repo / "evals" / "skills" / "s" / "results" / "candidate.json").write_text(
        "{}\n", encoding="utf-8"
    )
    (repo / "seed.txt").write_text("sneaky code change\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "eval evidence + code")
    assert crr.main([str(slug_dir)]) == 1
    assert "stale-sha" in capsys.readouterr().err


def test_docs_only_advance_is_still_stale(tmp_path, capsys):
    # `documentation` is excluded from *simplify* scope but is NOT receipt
    # neutral: prose is where intent drift hides, so it must still stale.
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    commit_file(repo, "docs/guide.md", "new prose\n")
    assert crr.main([str(slug_dir)]) == 1
    assert "stale-sha" in capsys.readouterr().err


def test_vendored_advance_is_still_stale(tmp_path, capsys):
    # A vendored dependency bump is shipped behavior — never receipt neutral.
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    commit_file(repo, "vendor/lib/thing.py", "payload\n")
    assert crr.main([str(slug_dir)]) == 1
    assert "stale-sha" in capsys.readouterr().err


def test_unclassifiable_path_fails_closed(tmp_path, capsys):
    # classify_path raises on a non-canonical spelling; an unclassifiable path
    # is unknown, not exempt, so it must count as reviewable.
    assert (
        crr._carries_reviewable_surface("evals/skills/s/results/../../../etc/passwd")
        is True
    )
    assert crr._carries_reviewable_surface("") is True


def test_root_singleton_files_are_not_exempt():
    # A root FILE named for a directory authority has no child component, so it
    # is not that authority — it stays reviewable, matching classify_path's rule.
    # Asserted at unit level: a `specs` file cannot coexist with the slug dir.
    assert crr._carries_reviewable_surface("specs") is True
    assert crr._carries_reviewable_surface("evals") is True


def test_case_variant_neutral_paths_stay_reviewable():
    # classify_path folds case when matching authorities; the staleness gate
    # must not. `Specs/` or `evals/Raw/` is a different directory on a
    # case-sensitive filesystem — honoring the folded match would let unreviewed
    # code ship under a case-variant spelling (removed-behavior finding at
    # ac161a0). Exact-lowercase spellings stay neutral; variants stay fatal.
    assert crr._carries_reviewable_surface("Specs/x/PLAN.md") is True
    assert crr._carries_reviewable_surface("SPECS/anything.sh") is True
    assert crr._carries_reviewable_surface("specs/x/PLAN.md") is False
    assert crr._carries_reviewable_surface("evals/skills/s/Results/x.json") is True
    assert crr._carries_reviewable_surface("Evals/skills/s/results/x.json") is True
    assert crr._carries_reviewable_surface("evals/skills/s/results/x.json") is False


def test_case_variant_specs_commit_stales_receipt(tmp_path, capsys):
    # End-to-end: a post-review commit under `Specs/` (not `specs/`) must stale.
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    commit_file(repo, "Specs/payload.py", "code\n")
    assert crr.main([str(slug_dir)]) == 1
    assert "stale-sha" in capsys.readouterr().err


def test_eval_fixtures_are_not_exempt():
    # Only stored results/transcripts are recorded output. Eval *fixtures* and
    # harness code under evals/ are real source and must still stale a receipt.
    assert (
        crr._carries_reviewable_surface("evals/skills/s/fixtures/case/app.py") is True
    )
    assert (
        crr._carries_reviewable_surface("evals/skills/s/results/candidate.json")
        is False
    )
    assert (
        crr._carries_reviewable_surface("evals/skills/s/transcripts/run/log.txt")
        is False
    )


def test_symbolic_reviewed_sha_is_rejected(tmp_path, capsys):
    # A symbolic ref (e.g. literal "HEAD") must NOT be accepted: git diff HEAD..HEAD
    # is always empty and would fail-open. Require a resolved 40-hex sha.
    repo = make_repo(tmp_path)
    data = valid_data("HEAD")
    slug_dir = write_receipt(repo, "gh-x", data)
    new_commit(repo)  # land unreviewed code after review
    assert crr.main([str(slug_dir), "--require", "correctness,intent"]) == 1
    assert "malformed" in capsys.readouterr().err


def test_mixed_advance_with_code_still_stale(tmp_path, capsys):
    # A specs/ change AND a code change after review is unreviewed code → stale.
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    (repo / "specs" / "gh-x" / "PLAN.md").write_text(
        "status: shipped\n", encoding="utf-8"
    )
    (repo / "seed.txt").write_text("sneaky code change\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "shipped + code")
    assert crr.main([str(slug_dir)]) == 1
    assert "stale-sha" in capsys.readouterr().err


def test_non_pass_result_is_rejected(tmp_path, capsys):
    # A recorded review with result 'pending' (or skipped/typo/absent) must fail —
    # not only 'fail'. An incomplete outcome cannot authorize a push.
    repo = make_repo(tmp_path)
    data = audit_data(head_sha(repo), audit_result="pending")
    slug_dir = write_receipt(repo, "gh-x", data)
    assert crr.main([str(slug_dir), "--require", "correctness,intent"]) == 1
    assert "review-failed" in capsys.readouterr().err


def test_missing_result_is_rejected(tmp_path, capsys):
    repo = make_repo(tmp_path)
    data = valid_data(head_sha(repo))
    del data["reviews"][0]["result"]  # absent result
    slug_dir = write_receipt(repo, "gh-x", data)
    assert crr.main([str(slug_dir)]) == 1
    assert "review-failed" in capsys.readouterr().err


def test_require_audit_if_workflow_engine_change_missing_audit(tmp_path, capsys):
    # A workflow-engine diff with a receipt that omits context-propagation-audit
    # must be blocked when --require-audit-if is given.
    repo = make_repo(tmp_path)
    base = head_sha(repo)
    commit_file(repo, "skills/demo/SKILL.md", "# demo skill\n")
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    rc = crr.main(
        [str(slug_dir), "--require", "correctness,intent", "--require-audit-if", base]
    )
    assert rc == 1
    assert "context-propagation-audit" in capsys.readouterr().err


def test_require_audit_if_workflow_engine_change_with_audit_passes(tmp_path):
    repo = make_repo(tmp_path)
    base = head_sha(repo)
    commit_file(repo, "skills/demo/subagents/worker-prompt.md", "# nested prompt\n")
    slug_dir = write_receipt(repo, "gh-x", audit_data(head_sha(repo)))
    rc = crr.main(
        [str(slug_dir), "--require", "correctness,intent", "--require-audit-if", base]
    )
    assert rc == 0


def test_require_audit_if_non_workflow_change_does_not_require_audit(tmp_path):
    # A prose-only / code-only diff that does NOT touch a workflow-engine surface
    # must not demand the audit.
    repo = make_repo(tmp_path)
    base = head_sha(repo)
    commit_file(repo, "app/service.py", "x = 1\n")
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    rc = crr.main(
        [str(slug_dir), "--require", "correctness,intent", "--require-audit-if", base]
    )
    assert rc == 0


def test_require_audit_if_readme_excluded(tmp_path):
    # agents/README.md is prose — excluded from the workflow-engine signal.
    repo = make_repo(tmp_path)
    base = head_sha(repo)
    commit_file(repo, "agents/README.md", "# agents inventory\n")
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    rc = crr.main(
        [str(slug_dir), "--require", "correctness,intent", "--require-audit-if", base]
    )
    assert rc == 0


def test_require_audit_if_bad_base_fails_closed(tmp_path, capsys):
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    rc = crr.main(
        [
            str(slug_dir),
            "--require-audit-if",
            "0000000000000000000000000000000000000000",
        ]
    )
    assert rc == 1
    assert "stale-sha" in capsys.readouterr().err


def test_blocking_open_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    data = valid_data(head_sha(repo))
    data["reviews"][0]["blocking_open"] = 2
    slug_dir = write_receipt(repo, "gh-x", data)
    assert crr.main([str(slug_dir)]) == 1
    assert "blocking-open" in capsys.readouterr().err


def test_review_result_fail_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    data = valid_data(head_sha(repo))
    data["reviews"][1]["result"] = "fail"
    slug_dir = write_receipt(repo, "gh-x", data)
    assert crr.main([str(slug_dir)]) == 1
    assert "review-failed" in capsys.readouterr().err


def test_missing_required_type_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    assert (
        crr.main([str(slug_dir), "--require", "correctness,context-propagation-audit"])
        == 1
    )
    assert "missing-required-type" in capsys.readouterr().err


def test_malformed_json_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    slug_dir = write_receipt(repo, "gh-x", "{not valid json,,,")
    assert crr.main([str(slug_dir)]) == 1
    assert "malformed" in capsys.readouterr().err


def test_missing_receipt_fails(tmp_path, capsys):
    repo = make_repo(tmp_path)
    slug_dir = repo / "specs" / "gh-x"
    slug_dir.mkdir(parents=True)
    assert crr.main([str(slug_dir)]) == 1
    assert "missing" in capsys.readouterr().err


def test_require_present_but_failed_is_not_satisfied(tmp_path, capsys):
    repo = make_repo(tmp_path)
    data = valid_data(head_sha(repo))
    data["reviews"][1]["result"] = "fail"  # intent present but failed
    slug_dir = write_receipt(repo, "gh-x", data)
    # review-failed is caught before the --require check
    assert crr.main([str(slug_dir), "--require", "intent"]) == 1
    assert "review-failed" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# --require-simplify-if (Task 3.1, SC-3/SC-5/SC-6)
# ---------------------------------------------------------------------------


def make_simplify_repo(tmp_path):
    """Build base -> pre -> post commit chain touching a reviewable path.

    Returns (repo, base_sha, pre_sha, post_sha). base..HEAD contains a
    reviewable (non-excluded) source path, so simplify is "required" per
    check_claude_simplify.classify_path.
    """
    repo = make_repo(tmp_path)
    commit_file(repo, "src/app.py", "x = 1\n")
    base = head_sha(repo)
    commit_file(repo, "src/app.py", "x = 1\ny = 2\n")
    pre = head_sha(repo)
    commit_file(repo, "src/app.py", "x = 1\ny = 2\nz = 3\n")
    post = head_sha(repo)
    return repo, base, pre, post


def simplify_entry(base, pre, post, **overrides):
    entry = {
        "type": "simplify",
        "result": "pass",
        "blocking_open": 0,
        "base_sha": base,
        "pre_sha": pre,
        "post_sha": post,
        "claude_code_version": "2.1.154",
        "reason": "non_tiny_source_change",
        "outcome": "changed",
        "changed_files": ["src/app.py"],
        "verification_result": "pass",
        "delta_verdict": {"spec_verdict": "pass", "quality_verdict": "approved"},
    }
    entry.update(overrides)
    return entry


def receipt_data(reviewed_head_sha, review):
    return {"reviewed_head_sha": reviewed_head_sha, "reviews": [review]}


def test_require_simplify_if_passing_entry_unblocks(tmp_path):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    slug_dir = write_receipt(
        repo, "gh-x", receipt_data(post, simplify_entry(base, pre, post))
    )
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 0


def test_require_simplify_if_superseded_entry_from_a_resume_cycle_does_not_block(
    tmp_path,
):
    # references/simplify-stage.md appends a fresh entry each time the stage
    # re-runs on resume, so a receipt can legitimately hold a stale entry
    # (post_sha1) alongside the current one (post_sha2 == reviewed_head_sha).
    # The stale entry must not fatally block validation of the current one.
    repo, base, pre1, post1 = make_simplify_repo(tmp_path)
    commit_file(repo, "src/app.py", "x = 1\ny = 2\nz = 3\nw = 4\n")
    post2 = head_sha(repo)
    stale_entry = simplify_entry(base, pre1, post1)
    current_entry = simplify_entry(base, post1, post2)
    slug_dir = write_receipt(
        repo,
        "gh-x",
        {"reviewed_head_sha": post2, "reviews": [stale_entry, current_entry]},
    )
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 0


def test_require_simplify_if_malformed_superseded_entry_still_rejected(
    tmp_path, capsys
):
    # A stale/superseded entry is not re-validated for freshness, but a
    # structurally corrupt one is still a fatal error — "historical" does not
    # mean "unvalidated".
    repo, base, pre1, post1 = make_simplify_repo(tmp_path)
    commit_file(repo, "src/app.py", "x = 1\ny = 2\nz = 3\nw = 4\n")
    post2 = head_sha(repo)
    malformed_stale_entry = simplify_entry(base, pre1, post1[:12])
    current_entry = simplify_entry(base, post1, post2)
    slug_dir = write_receipt(
        repo,
        "gh-x",
        {
            "reviewed_head_sha": post2,
            "reviews": [malformed_stale_entry, current_entry],
        },
    )
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "malformed" in capsys.readouterr().err


def test_require_simplify_if_missing_entry_fails(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    slug_dir = write_receipt(
        repo,
        "gh-x",
        receipt_data(
            post,
            {
                "type": "correctness",
                "result": "pass",
                "blocking_open": 0,
            },
        ),
    )
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "missing-required-type" in capsys.readouterr().err


def test_require_simplify_if_wrong_type_is_treated_as_missing(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    wrong = simplify_entry(base, pre, post)
    wrong["type"] = "not-simplify"
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, wrong))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "missing-required-type" in capsys.readouterr().err


def test_require_simplify_if_non_reviewable_diff_does_not_require_entry(tmp_path):
    repo = make_repo(tmp_path)
    base = head_sha(repo)
    commit_file(repo, "docs/guide.md", "# guide\n")
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 0


def test_require_simplify_if_case_variant_excluded_dir_still_requires_entry(
    tmp_path, capsys
):
    # The staleness exemption was taught exact-case at ed77172, but the
    # requirement trigger still folded case, so real source under `Docs/` or
    # `Evals/Raw/` — different directories on a case-sensitive filesystem —
    # answered "no reviewable path" and skipped the required stage entirely.
    repo = make_repo(tmp_path)
    base = head_sha(repo)
    commit_file(repo, "Docs/mod.py", "def f():\n    return 1\n")
    commit_file(repo, "Evals/Raw/mod.py", "def g():\n    return 2\n")
    slug_dir = write_receipt(repo, "gh-x", valid_data(head_sha(repo)))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "missing-required-type" in capsys.readouterr().err


def test_require_simplify_if_symbolic_sha_is_rejected(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    entry = simplify_entry(base, pre, post, pre_sha="HEAD")
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "malformed" in capsys.readouterr().err


def test_require_simplify_if_short_sha_is_rejected(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    entry = simplify_entry(base, pre, post, post_sha=post[:12])
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "malformed" in capsys.readouterr().err


def test_require_simplify_if_non_hex_sha_is_rejected(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    bogus = "g" * 40
    entry = simplify_entry(base, pre, post, base_sha=bogus)
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "malformed" in capsys.readouterr().err


def test_require_simplify_if_old_version_is_rejected(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    entry = simplify_entry(base, pre, post, claude_code_version="2.1.153")
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "malformed" in capsys.readouterr().err


def test_require_simplify_if_minimum_version_boundary_accepted(tmp_path):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    entry = simplify_entry(base, pre, post, claude_code_version="2.1.154")
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 0


def test_require_simplify_if_no_op_with_nonempty_changed_files_rejected(
    tmp_path, capsys
):
    # Real git HEAD must stay at `pre` here (no third commit) so the entry's
    # claimed no_op (pre_sha == post_sha, nothing further happened) matches
    # reviewed_head_sha == actual current HEAD, isolating the contradiction
    # under test (no_op outcome with non-empty changed_files) from the
    # unrelated top-level stale-sha check.
    repo = make_repo(tmp_path)
    commit_file(repo, "src/app.py", "x = 1\n")
    base = head_sha(repo)
    commit_file(repo, "src/app.py", "x = 1\ny = 2\n")
    pre = head_sha(repo)
    entry = simplify_entry(
        base,
        pre,
        pre,
        outcome="no_op",
        changed_files=["src/app.py"],
        verification_result=None,
        delta_verdict=None,
    )
    slug_dir = write_receipt(repo, "gh-x", receipt_data(pre, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "malformed" in capsys.readouterr().err


def test_require_simplify_if_changed_with_empty_changed_files_rejected(
    tmp_path, capsys
):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    entry = simplify_entry(base, pre, post, changed_files=[])
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "malformed" in capsys.readouterr().err


def test_require_simplify_if_failing_verification_rejected(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    entry = simplify_entry(base, pre, post, verification_result="fail")
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "review-failed" in capsys.readouterr().err


def test_require_simplify_if_pending_spec_verdict_rejected(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    entry = simplify_entry(
        base,
        pre,
        post,
        delta_verdict={"spec_verdict": "cannot_verify", "quality_verdict": "approved"},
    )
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "review-failed" in capsys.readouterr().err


def test_require_simplify_if_needs_fixes_quality_verdict_rejected(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    entry = simplify_entry(
        base,
        pre,
        post,
        delta_verdict={"spec_verdict": "pass", "quality_verdict": "needs_fixes"},
    )
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "review-failed" in capsys.readouterr().err


def test_require_simplify_if_forged_pass_result_does_not_bypass_failing_evidence(
    tmp_path, capsys
):
    # Mutation guard: self-reported result="pass" must not be trusted when the
    # underlying verification/delta evidence actually failed.
    repo, base, pre, post = make_simplify_repo(tmp_path)
    entry = simplify_entry(base, pre, post, result="pass", verification_result="fail")
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "review-failed" in capsys.readouterr().err


def test_require_simplify_if_pre_sha_not_descendant_of_base_rejected(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    # Build an unrelated commit to stand in as a forged "pre_sha" that never
    # descended from `base`.
    _git(repo, "checkout", "-q", "--orphan", "unrelated")
    (repo / "other.py").write_text("q = 1\n", encoding="utf-8")
    _git(repo, "add", "other.py")
    _git(repo, "commit", "-q", "-m", "unrelated root")
    unrelated = head_sha(repo)
    _git(repo, "checkout", "-q", "main")
    entry = simplify_entry(base, unrelated, post)
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "malformed" in capsys.readouterr().err


def test_require_simplify_if_post_sha_not_descendant_of_pre_rejected(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    _git(repo, "checkout", "-q", "--orphan", "unrelated")
    (repo / "other.py").write_text("q = 1\n", encoding="utf-8")
    _git(repo, "add", "other.py")
    _git(repo, "commit", "-q", "-m", "unrelated root")
    unrelated = head_sha(repo)
    _git(repo, "checkout", "-q", "main")
    # Real current HEAD is still `post` (checking out main did not move it) —
    # keep reviewed_head_sha == post so the top-level stale-sha check does not
    # preempt the ancestry check under test.
    entry = simplify_entry(base, pre, unrelated)
    slug_dir = write_receipt(repo, "gh-x", receipt_data(post, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "malformed" in capsys.readouterr().err


def test_require_simplify_if_post_sha_not_covered_by_reviewed_head_rejected(
    tmp_path, capsys
):
    # The simplify entry's post_sha must be the exact commit the final review
    # package covered — a receipt claiming a different reviewed_head_sha means
    # post-simplify code was never reviewed.
    repo, base, pre, post = make_simplify_repo(tmp_path)
    entry = simplify_entry(base, pre, post)
    slug_dir = write_receipt(repo, "gh-x", receipt_data(pre, entry))
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 1
    assert "stale-sha" in capsys.readouterr().err


def test_require_simplify_if_specs_only_bookkeeping_advance_stays_valid(tmp_path):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    slug_dir = write_receipt(
        repo, "gh-x", receipt_data(post, simplify_entry(base, pre, post))
    )
    new_specs_commit(repo, "gh-x")
    assert crr.main([str(slug_dir), "--require-simplify-if", base]) == 0


def test_require_simplify_if_bad_base_fails_closed(tmp_path, capsys):
    repo, base, pre, post = make_simplify_repo(tmp_path)
    slug_dir = write_receipt(
        repo, "gh-x", receipt_data(post, simplify_entry(base, pre, post))
    )
    rc = crr.main(
        [
            str(slug_dir),
            "--require-simplify-if",
            "0000000000000000000000000000000000000000",
        ]
    )
    assert rc == 1
    assert "stale-sha" in capsys.readouterr().err


def test_self_test_simplify_cli_passes():
    assert crr.main(["--self-test-simplify"]) == 0
