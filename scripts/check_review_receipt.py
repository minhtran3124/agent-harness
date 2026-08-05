#!/usr/bin/env python3
"""Validate a spec's review receipt against the exact reviewed HEAD.

A review receipt (`specs/<slug>/.review-receipt.json`) records that a review
passed at a specific commit. It is only valid while HEAD still points at that
commit: a fix committed after the review advances HEAD, makes the receipt stale,
and this checker fails — so a stale review can never silently authorize a newer
HEAD.

One exception: an advance that touches only receipt-neutral paths adds no
reviewable surface, so it does not stale the receipt — `specs/` bookkeeping, and
stored eval output under an `evals/**/<results|result|raw|transcripts>/**`
directory. See `_RECEIPT_NEUTRAL_CATEGORIES` and `_EVAL_OUTPUT_PARTS`.

Usage:
    python3 scripts/check_review_receipt.py <specs/slug-dir> [--require type1,type2]

    <specs/slug-dir>   Directory holding the receipt (e.g. specs/gh-143-...).
                       The receipt is <that-dir>/.review-receipt.json.
    --require t1,t2    Comma-separated review `type` values that must each be
                       present with result `pass`.

The reviewed HEAD is resolved with `git rev-parse HEAD` run in the repo that
contains the slug dir.

Exit codes:
    0  Receipt valid, and (if --require given) all required types present & pass.
    1  Any check failed — one line to stderr naming the failing check
       (missing / malformed / stale-sha / review-failed / blocking-open /
       missing-required-type).
    2  Bad invocation.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RECEIPT_NAME = ".review-receipt.json"

# reviewed_head_sha MUST be a resolved full commit sha. A symbolic ref (e.g. the
# literal "HEAD", "@", or a branch name) would make `git diff <ref>..<HEAD>`
# resolve the ref to the current commit and diff the repo against itself —
# always empty — silently defeating the stale-sha gate. Require 40 hex chars.
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# check_claude_simplify.py is a sibling script in this same directory; load it
# by explicit path (not a bare `import`) so this module works correctly
# regardless of the caller's sys.path/cwd — matching this repo's existing
# import-by-path convention for cross-script reuse (see the test files under
# scripts/ that load their target module the same way).
_CCS_SPEC = importlib.util.spec_from_file_location(
    "check_claude_simplify",
    Path(__file__).resolve().parent / "check_claude_simplify.py",
)
assert _CCS_SPEC and _CCS_SPEC.loader, "could not load check_claude_simplify.py"
check_claude_simplify = importlib.util.module_from_spec(_CCS_SPEC)
_CCS_SPEC.loader.exec_module(check_claude_simplify)

_SIMPLIFY_TYPE = "simplify"

# Categories from check_claude_simplify.classify_path that carry no reviewable
# surface, so a commit touching only these must not stale an otherwise valid
# receipt. Deliberately narrower than that module's full exclusion set:
# `documentation` is prose a human reads (intent drift hides there),
# and `vendor`/`generated` can carry a dependency bump or a regenerated
# lockfile — real shipped behavior that must not ride an old receipt.
_RECEIPT_NEUTRAL_CATEGORIES = frozenset({"specs_bookkeeping", "evaluation"})


# Exact-case spellings of the neutral authorities. classify_path matches its
# authority tokens case-insensitively (fine for the simplify policy, whose
# lenient direction merely skips a cleanup); this gate's lenient direction is
# a review bypass, so a case-variant `Specs/` or `evals/Raw/` — a different
# directory on a case-sensitive filesystem — must stay reviewable.
_EVAL_OUTPUT_PARTS = frozenset({"results", "result", "raw", "transcripts"})


def _carries_reviewable_surface(path: str) -> bool:
    """True when `path` carries reviewable surface, failing closed on garbage.

    A path that classify_path cannot parse is treated as reviewable: an
    unclassifiable path is unknown, not exempt. A path whose neutral category
    was matched only through case folding is likewise treated as reviewable.
    """
    try:
        category = check_claude_simplify.classify_path(path)
    except ValueError:
        return True
    if category not in _RECEIPT_NEUTRAL_CATEGORIES:
        return True
    parts = path.split("/")
    if category == "specs_bookkeeping":
        return parts[0] != "specs"
    # category == "evaluation": corroborate the exact-case spelling of the
    # authority components classify_path matched case-insensitively.
    return not (
        parts[0] == "evals" and any(part in _EVAL_OUTPUT_PARTS for part in parts[1:-1])
    )


_SIMPLIFY_OUTCOMES = frozenset({"changed", "no_op"})
_SIMPLIFY_RESULTS = frozenset({"pass", "fail"})
_SPEC_VERDICTS = frozenset({"pass", "fail", "cannot_verify"})
_QUALITY_VERDICTS = frozenset({"approved", "needs_fixes"})

# Workflow-engine path signal — the surfaces whose changes require a passing
# /context-propagation-audit before push. This is a literal copy of the signal in
# hooks/risk-corroboration.sh (add_cat "workflow-engine"); the two are kept
# byte-identical by tests/scripts/workflow-engine-regex-parity.test.sh, so this
# copy cannot drift silently. Include, then subtract the prose exclusions.
_WF_INCLUDE = re.compile(
    r"^skills/[^/]+/SKILL\.md$|^skills/[^/]+/.*prompt[^/]*\.md$|^agents/[^/]+\.md$|^rules/[^/]+\.md$"
)
_WF_EXCLUDE = re.compile(r"(^|/)(README\.md|[A-Za-z0-9_-]+\.template\.md)$")
_WF_AUDIT_TYPE = "context-propagation-audit"


def _touches_workflow_engine(changed: list[str] | None) -> bool | None:
    """True if the base..HEAD changed set touches a workflow-engine surface.

    None if the range was undiffable (bad ref) — the caller fails closed.
    """
    if changed is None:
        return None
    return any(_WF_INCLUDE.match(p) and not _WF_EXCLUDE.search(p) for p in changed)


def _git_head(slug_dir: Path) -> str | None:
    """Return the current HEAD sha of the repo containing slug_dir, or None."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=slug_dir,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _changed_files(slug_dir: Path, a: str, b: str) -> list[str] | None:
    """File paths changed between commits a and b, or None if the range is undiffable.

    Used to distinguish a review-neutral advance (bookkeeping or stored eval
    evidence) from an unreviewed code change after review.

    `-z` is load-bearing: without it Git quotes any path with a non-ASCII or
    control character (`"src/caf\\303\\251.py"`), and classify_path rejects the
    backslash spelling — which would fail the whole gate closed on a valid
    branch, blaming the base ref. NUL-delimited output is never quoted.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "-z", f"{a}..{b}"],
            cwd=slug_dir,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return [path for path in proc.stdout.split("\0") if path.strip()]


def is_ancestor(slug_dir: Path, ancestor: str, descendant: str) -> bool | None:
    """True if ancestor is an ancestor of (or identical to) descendant.

    None if ancestry cannot be determined (bad ref) — the caller fails closed.
    """
    try:
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=slug_dir,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None


def _simplify_required(changed: list[str] | None) -> bool | None:
    """True if the base..HEAD changed set touches any reviewable path.

    None if the range was undiffable, or a changed path cannot be classified —
    the caller fails closed in either case.
    """
    if changed is None:
        return None
    try:
        return any(
            check_claude_simplify.classify_path(p) == "reviewable" for p in changed
        )
    except ValueError:
        return None


def simplify_shape_error(entry: dict) -> str | None:
    """Pure structural validation of a `type: simplify` receipt entry.

    Checks SHA format, the Claude Code capability version floor, bounded
    reason/outcome/result vocabulary, and internal changed/no_op
    evidence-shape consistency (empty evidence for a no-op, well-formed
    evidence for a change). Returns a one-line failure reason, or None if the
    entry is internally well-formed.

    Does not perform git ancestry checks or cross-check against
    `reviewed_head_sha` — the caller (which holds the repo) does that
    separately, since this function has no filesystem/git access.
    """
    for field in ("base_sha", "pre_sha", "post_sha"):
        value = entry.get(field)
        if not isinstance(value, str) or not SHA_RE.match(value):
            return (
                f"malformed: simplify entry {field} {value!r} is not a resolved "
                f"40-char hex commit sha"
            )

    version = entry.get("claude_code_version")
    capability = check_claude_simplify.capability_status(
        version if isinstance(version, str) else None
    )
    if capability["status"] != "supported":
        return (
            f"malformed: simplify entry claude_code_version {version!r} is "
            f"{capability['status']} (minimum {capability['minimum']})"
        )

    if entry.get("reason") not in check_claude_simplify.POLICY_REASONS:
        return (
            f"malformed: simplify entry reason {entry.get('reason')!r} is not a "
            f"recognized policy reason"
        )

    if entry.get("result") not in _SIMPLIFY_RESULTS:
        return (
            f"malformed: simplify entry result {entry.get('result')!r} must be "
            f"'pass' or 'fail'"
        )

    outcome = entry.get("outcome")
    if outcome not in _SIMPLIFY_OUTCOMES:
        return f"malformed: simplify entry outcome {outcome!r} must be 'changed' or 'no_op'"

    changed_files = entry.get("changed_files")
    if (
        not isinstance(changed_files, list)
        or any(not isinstance(p, str) or not p for p in changed_files)
        or len(changed_files) != len(set(changed_files))
    ):
        return (
            "malformed: simplify entry changed_files must be a list of unique "
            "non-empty paths"
        )

    pre_sha = entry.get("pre_sha")
    post_sha = entry.get("post_sha")
    verification_result = entry.get("verification_result")
    delta_verdict = entry.get("delta_verdict")

    if outcome == "no_op":
        if pre_sha != post_sha or changed_files:
            return (
                "malformed: simplify entry outcome no_op contradicts identical "
                "pre/post sha or empty changed_files"
            )
        if verification_result is not None or delta_verdict is not None:
            return (
                "malformed: simplify entry outcome no_op must carry empty "
                "verification/delta evidence"
            )
        return None

    # outcome == "changed"
    if pre_sha == post_sha or not changed_files:
        return (
            "malformed: simplify entry outcome changed contradicts distinct "
            "pre/post sha or non-empty changed_files"
        )
    if verification_result not in {"pass", "fail"}:
        return (
            f"malformed: simplify entry verification_result "
            f"{verification_result!r} must be 'pass' or 'fail'"
        )
    if not isinstance(delta_verdict, dict):
        return "malformed: simplify entry delta_verdict must be an object for a changed outcome"
    if delta_verdict.get("spec_verdict") not in _SPEC_VERDICTS:
        return (
            f"malformed: simplify entry delta_verdict.spec_verdict "
            f"{delta_verdict.get('spec_verdict')!r} is not a recognized verdict"
        )
    if delta_verdict.get("quality_verdict") not in _QUALITY_VERDICTS:
        return (
            f"malformed: simplify entry delta_verdict.quality_verdict "
            f"{delta_verdict.get('quality_verdict')!r} is not a recognized verdict"
        )
    return None


def simplify_entry_passes(entry: dict) -> bool:
    """Whether the recorded evidence indicates a passing simplify outcome.

    Deliberately ignores the entry's own self-reported `result` field — an
    entry that claims `result: "pass"` while its verification/delta evidence
    says otherwise must not be trusted. Assumes `simplify_shape_error` already
    returned None for this entry.
    """
    if entry["outcome"] == "no_op":
        return True
    delta_verdict = entry["delta_verdict"]
    return (
        entry["verification_result"] == "pass"
        and delta_verdict.get("spec_verdict") == "pass"
        and delta_verdict.get("quality_verdict") == "approved"
    )


def check_receipt(
    slug_dir: Path,
    require: list[str],
    require_audit_if: str | None = None,
    require_simplify_if: str | None = None,
) -> str | None:
    """Validate the receipt. Return a one-line failure reason, or None if valid.

    require_audit_if: a base ref. When the base..HEAD diff touches a
    workflow-engine surface, `context-propagation-audit` is added to `require`,
    so a workflow-engine change cannot be pushed on a receipt that omits (or did
    not pass) the audit it is meant to trigger.

    require_simplify_if: a base ref. When the base..HEAD diff touches any
    reviewable (non-excluded) path, a passing `type: simplify` entry is
    required and deeply validated: resolved-SHA format, ancestry
    (base_sha -> pre_sha -> post_sha), the Claude Code version floor, a
    bounded policy reason, changed/no_op evidence-shape consistency, passing
    verification and spec/quality delta verdicts for a changed outcome, and
    that post_sha is the exact commit covered by `reviewed_head_sha` (so
    post-simplify code cannot ship unreviewed).
    """
    receipt_path = slug_dir / RECEIPT_NAME
    if not receipt_path.is_file():
        return f"missing: no review receipt at {receipt_path}"

    try:
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return f"malformed: {receipt_path} is not valid JSON ({exc})"

    if not isinstance(data, dict):
        return f"malformed: {receipt_path} is not a JSON object"

    reviewed = data.get("reviewed_head_sha")
    if not isinstance(reviewed, str) or not reviewed.strip():
        return f"malformed: {receipt_path} has no reviewed_head_sha"
    if not SHA_RE.match(reviewed.strip()):
        return (
            f"malformed: reviewed_head_sha {reviewed.strip()!r} is not a resolved "
            f"40-char hex commit sha (symbolic refs like 'HEAD' are rejected)"
        )

    head = _git_head(slug_dir)
    if head is None:
        return f"stale-sha: cannot resolve git HEAD for {slug_dir}"
    reviewed = reviewed.strip()
    if reviewed != head:
        # HEAD moved since review. Tolerate a review-neutral advance — the
        # plan-`shipped` transition (finishing-a-development-branch Step 4)
        # commits only `specs/`, and re-collected eval evidence under
        # `evals/**/results|transcripts/` is recorded output, not reviewable
        # source. Neither carries code, so neither must stale a valid receipt.
        # Any change in a reviewable category since the review stays fatal.
        changed = _changed_files(slug_dir, reviewed, head)
        if changed is None:
            return (
                f"stale-sha: receipt reviewed {reviewed[:12]} but HEAD is "
                f"{head[:12]} and the range is undiffable — re-review at current HEAD"
            )
        unreviewed = [p for p in changed if _carries_reviewable_surface(p)]
        if unreviewed:
            return (
                f"stale-sha: receipt reviewed {reviewed[:12]} but HEAD {head[:12]} "
                f"adds unreviewed reviewable changes (e.g. {unreviewed[0]}) — "
                f"re-review at current HEAD"
            )
        # else: review-neutral advance (bookkeeping/eval evidence) — receipt valid.

    reviews = data.get("reviews")
    if not isinstance(reviews, list):
        return f"malformed: {receipt_path} has no reviews list"

    for review in reviews:
        if not isinstance(review, dict):
            return f"malformed: {receipt_path} has a non-object review entry"
        rtype = review.get("type", "<unknown>")
        # Every recorded review must have passed. `fail`, `pending`, `skipped`, a
        # typo, or an absent result are all non-pass and fatal — an incomplete or
        # unrecorded outcome must never authorize a push (a recorded audit that was
        # skipped/pending would otherwise slip through the --require pass check).
        result = review.get("result")
        if result != "pass":
            return (
                f"review-failed: review '{rtype}' has result {result!r} — every "
                f"recorded review must be 'pass'"
            )
        blocking = review.get("blocking_open", 0)
        if isinstance(blocking, bool) or not isinstance(blocking, int):
            return f"malformed: review '{rtype}' has non-integer blocking_open"
        if blocking > 0:
            return f"blocking-open: review '{rtype}' has {blocking} blocking open"

    required = list(require)
    # Both conditional requirements diff the same base..HEAD range in the
    # documented invocation (finishing passes one base to both flags) — run
    # the diff once per distinct base and share the changed set.
    changed_since: dict[str, list[str] | None] = {}

    def _changed_since_base(base_ref: str) -> list[str] | None:
        if base_ref not in changed_since:
            changed_since[base_ref] = _changed_files(slug_dir, base_ref, "HEAD")
        return changed_since[base_ref]

    if require_audit_if is not None:
        touched = _touches_workflow_engine(_changed_since_base(require_audit_if))
        if touched is None:
            return (
                f"stale-sha: cannot diff workflow-engine base {require_audit_if!r} "
                f"— re-check with a valid base ref"
            )
        if touched and _WF_AUDIT_TYPE not in required:
            required.append(_WF_AUDIT_TYPE)

    if require_simplify_if is not None:
        needed = _simplify_required(_changed_since_base(require_simplify_if))
        if needed is None:
            return (
                f"stale-sha: cannot diff simplify base {require_simplify_if!r} "
                f"— re-check with a valid base ref"
            )
        if needed and _SIMPLIFY_TYPE not in required:
            required.append(_SIMPLIFY_TYPE)

    passed_types = {
        r.get("type")
        for r in reviews
        if isinstance(r, dict) and r.get("result") == "pass"
    }
    for req in required:
        if req not in passed_types:
            suffix = (
                " (diff touches the workflow-engine inventory)"
                if req == _WF_AUDIT_TYPE
                else " (diff touches a reviewable path)"
                if req == _SIMPLIFY_TYPE
                else ""
            )
            return (
                f"missing-required-type: required review '{req}' not present with "
                f"result pass{suffix}"
            )

    if require_simplify_if is not None:
        # A resumed session appends a fresh `type: simplify` entry each time the
        # stage re-runs (references/simplify-stage.md), so `reviews` may contain
        # superseded entries whose post_sha no longer matches reviewed_head_sha.
        # Every entry's own shape/ancestry is still checked (a malformed entry
        # is corruption regardless of whether it's superseded), but only an
        # entry that actually covers current HEAD is required to be present
        # and passing — older, non-matching entries are historical, not errors.
        simplify_entries = [
            review
            for review in reviews
            if isinstance(review, dict) and review.get("type") == _SIMPLIFY_TYPE
        ]
        for review in simplify_entries:
            shape_error = simplify_shape_error(review)
            if shape_error is not None:
                return shape_error
            base_sha, pre_sha, post_sha = (
                review["base_sha"],
                review["pre_sha"],
                review["post_sha"],
            )
            base_ancestor = is_ancestor(slug_dir, base_sha, pre_sha)
            if base_ancestor is None:
                return (
                    f"stale-sha: cannot verify simplify ancestry for base_sha "
                    f"{base_sha[:12]}"
                )
            if not base_ancestor:
                return (
                    f"malformed: simplify entry pre_sha {pre_sha[:12]} is not a "
                    f"descendant of its declared base_sha {base_sha[:12]}"
                )
            post_ancestor = is_ancestor(slug_dir, pre_sha, post_sha)
            if post_ancestor is None:
                return (
                    f"stale-sha: cannot verify simplify ancestry for pre_sha "
                    f"{pre_sha[:12]}"
                )
            if not post_ancestor:
                return (
                    f"malformed: simplify entry post_sha {post_sha[:12]} is not a "
                    f"descendant of its own pre_sha {pre_sha[:12]}"
                )
        if simplify_entries:
            current_entries = [
                review for review in simplify_entries if review["post_sha"] == reviewed
            ]
            if not current_entries:
                return (
                    "stale-sha: no simplify entry's post_sha matches "
                    f"reviewed_head_sha {reviewed[:12]} — post-simplify code "
                    "was not reviewed"
                )
            for review in current_entries:
                if not simplify_entry_passes(review):
                    return (
                        "review-failed: simplify entry does not indicate a "
                        "passing outcome (verification/delta evidence)"
                    )

    return None


def _self_test_simplify() -> int:
    """Exercise the --require-simplify-if gate against a throwaway git repo.

    Mirrors check_claude_simplify.py's `_self_test_policy` shape: a compact
    positive + representative-negative sweep, not the full matrix (that lives
    in scripts/test_check_review_receipt.py).
    """
    with tempfile.TemporaryDirectory(
        prefix="check-review-receipt-simplify-self-test-"
    ) as tmp:
        repo = Path(tmp)

        def run(*args: str) -> None:
            subprocess.run(
                ["git", *args], cwd=repo, check=True, capture_output=True, text=True
            )

        def head() -> str:
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            )
            return proc.stdout.strip()

        run("init", "-q", "-b", "main")
        run("config", "user.email", "self-test@example.invalid")
        run("config", "user.name", "Self Test")
        (repo / "src.py").write_text("x = 1\n", encoding="utf-8")
        run("add", "-A")
        run("commit", "-q", "-m", "base")
        base = head()
        (repo / "src.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
        run("add", "-A")
        run("commit", "-q", "-m", "pre-simplify checkpoint")
        pre = head()
        (repo / "src.py").write_text("x = 1\ny = 2\nz = 3\n", encoding="utf-8")
        run("add", "-A")
        run("commit", "-q", "-m", "post-simplify")
        post = head()

        slug_dir = repo / "specs" / "demo"
        slug_dir.mkdir(parents=True)
        receipt_path = slug_dir / RECEIPT_NAME

        def entry(**overrides):
            base_entry = {
                "type": "simplify",
                "result": "pass",
                "blocking_open": 0,
                "base_sha": base,
                "pre_sha": pre,
                "post_sha": post,
                "claude_code_version": "2.1.154",
                "reason": "non_tiny_source_change",
                "outcome": "changed",
                "changed_files": ["src.py"],
                "verification_result": "pass",
                "delta_verdict": {
                    "spec_verdict": "pass",
                    "quality_verdict": "approved",
                },
            }
            base_entry.update(overrides)
            return base_entry

        def write(review: dict, reviewed_head_sha: str = post) -> None:
            data = {"reviewed_head_sha": reviewed_head_sha, "reviews": [review]}
            receipt_path.write_text(json.dumps(data), encoding="utf-8")

        write(entry())
        good = check_receipt(slug_dir, [], require_simplify_if=base) is None

        write(entry(pre_sha="HEAD"))
        symbolic_sha_rejected = (
            check_receipt(slug_dir, [], require_simplify_if=base) is not None
        )

        write(entry(claude_code_version="2.1.153"))
        old_version_rejected = (
            check_receipt(slug_dir, [], require_simplify_if=base) is not None
        )

        write(
            entry(
                outcome="no_op",
                post_sha=pre,
                changed_files=["src.py"],
                verification_result=None,
                delta_verdict=None,
            ),
            reviewed_head_sha=pre,
        )
        no_op_contradiction_rejected = (
            check_receipt(slug_dir, [], require_simplify_if=base) is not None
        )

        write(entry(verification_result="fail"))
        failing_verification_rejected = (
            check_receipt(slug_dir, [], require_simplify_if=base) is not None
        )

        write(entry(), reviewed_head_sha=pre)
        unreviewed_post_simplify_rejected = (
            check_receipt(slug_dir, [], require_simplify_if=base) is not None
        )

        data = {"reviewed_head_sha": post, "reviews": []}
        receipt_path.write_text(json.dumps(data), encoding="utf-8")
        missing_entry_rejected = (
            check_receipt(slug_dir, [], require_simplify_if=base) is not None
        )

        passed = (
            good
            and symbolic_sha_rejected
            and old_version_rejected
            and no_op_contradiction_rejected
            and failing_verification_rejected
            and unreviewed_post_simplify_rejected
            and missing_entry_rejected
        )
    if not passed:
        print("check-review-receipt: simplify self-test failed", file=sys.stderr)
        return 1
    print("check-review-receipt: simplify self-test passed")
    return 0


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="check_review_receipt.py", add_help=True)
    parser.add_argument("slug_dir", nargs="?", default=None)
    parser.add_argument("--require", default="")
    parser.add_argument(
        "--require-audit-if",
        default=None,
        metavar="BASE_REF",
        help="also require context-propagation-audit when BASE_REF..HEAD touches "
        "a workflow-engine surface (skills/*/SKILL.md, dispatch prompts, agents/, rules/)",
    )
    parser.add_argument(
        "--require-simplify-if",
        default=None,
        metavar="BASE_REF",
        help="also require a passing type:simplify entry when BASE_REF..HEAD touches "
        "a reviewable (non-excluded) path; deeply validates its SHAs, ancestry, "
        "version, reason, changed/no_op evidence, and coverage of reviewed_head_sha",
    )
    parser.add_argument("--self-test-simplify", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test_simplify:
        return _self_test_simplify()

    if args.slug_dir is None:
        parser.error("slug_dir is required unless --self-test-simplify is given")

    require = [t.strip() for t in args.require.split(",") if t.strip()]

    slug_dir = Path(args.slug_dir)
    if not slug_dir.is_dir():
        print(f"missing: {slug_dir} is not a directory", file=sys.stderr)
        return 1

    reason = check_receipt(
        slug_dir,
        require,
        require_audit_if=args.require_audit_if,
        require_simplify_if=args.require_simplify_if,
    )
    if reason is not None:
        print(reason, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
