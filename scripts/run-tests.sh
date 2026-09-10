#!/bin/bash
# Harness test entry point — run everything CI runs:
#   L1  syntax (bash -n) + doc-truth lint
#   L2  hook contract tests          (tests/hooks/*.test.sh)
#   L3  script integration tests     (tests/scripts/*.test.sh)
# Usage: bash scripts/run-tests.sh
set -u
cd "$(dirname "$0")/.." || exit 1
FAILED=0

echo "== L1: syntax =="
for f in hooks/*.sh scripts/*.sh tests/lib.sh tests/*/*.test.sh; do
  bash -n "$f" || { echo "  ✗ syntax: $f"; FAILED=1; }
done
echo "  ✓ bash -n clean"

echo "== L1: doc-truth lint =="
bash scripts/lint-doc-truth.sh || FAILED=1

echo "== L1: skill-bash lint =="
bash scripts/lint-skill-bash.sh || FAILED=1

echo "== L1: hook repo-root source =="
bash scripts/check-hook-root-source.sh || FAILED=1

echo "== L1: plugin validate (skills + agents frontmatter) =="
bash scripts/check-plugin-validate.sh || FAILED=1

echo "== L1: skill allowed-tools =="
bash scripts/check-allowed-tools.sh || FAILED=1

echo "== L1: manifest consistency =="
if command -v python3 >/dev/null 2>&1; then
  python3 scripts/check_manifest.py || FAILED=1
  python3 scripts/check_frontmatter_contract.py || FAILED=1
  python3 scripts/check_gate_modes_smoke.py || FAILED=1
  python3 scripts/check_slim_surface.py || FAILED=1
else
  echo "  skip — no python3"
fi

echo "== L1: runtime-neutral sources =="
# The LIVE tree scan, not only the unit tests: the count-exact inventory only ratchets
# if something re-runs it on every change. A hook-test edit in one phase silently broke
# another phase's SC when this ran nowhere in CI (found in the phases-1-4 branch review).
if command -v python3 >/dev/null 2>&1 && [ -f scripts/check_runtime_neutral_sources.py ]; then
  python3 scripts/check_runtime_neutral_sources.py --root . || FAILED=1
else
  echo "  skip — no python3 or checker not present"
fi

echo "== L1: verify-row lint (changed SUMMARY/PLAN only) =="
# Lint only SUMMARY.md + PLAN.md files changed vs the base ref — new/edited Verify
# rows and SC-table Check cells must be pipe-free + <60s; shipped specs are
# grandfathered (scope matches ci-strict-gate's changed-file model).
#
# The base ref is resolved by scripts/resolve-base-ref.sh (which carries the rationale
# and is covered by tests/scripts/resolve-base-ref.test.sh); `fetch-depth: 0` on the CI
# `test` job is the other half of that fix. Every skip below names its reason —
# distinguishing "no base to compare against" from "compared and found nothing" is the
# whole point, since that ambiguity is what let the original bug report green.
TMP_POST_CUTOFF="$(mktemp)"; trap 'rm -f "$TMP_POST_CUTOFF"' EXIT
BASE_OUT="$(bash scripts/resolve-base-ref.sh 2>&1)"; BASE_RC=$?
if [ "$BASE_RC" -ne 0 ]; then
  echo "  skip — $BASE_OUT"
elif ! command -v python3 >/dev/null 2>&1; then
  echo "  skip — no python3"
else
  # Three-dot, matching scripts/ci-strict-gate.sh — two-dot also picks up files changed on
  # the BASE since the fork point, i.e. specs this branch never touched. Do not swallow
  # git's exit status: a failed diff and an empty diff both produce no output, and
  # reporting the first as the second is the exact confusion this block was rewritten to end.
  changed="$(git diff --name-only "$BASE_OUT"...HEAD -- 'specs/*/SUMMARY.md' 'specs/*/PLAN.md')"; diff_rc=$?
  if [ "$diff_rc" -ne 0 ]; then
    echo "  ✗ git diff against '$BASE_OUT' failed (rc=$diff_rc) — scope unknown, not treating as clean"
    FAILED=1
  elif [ -n "$changed" ]; then
    # GRANDFATHER CUTOFF. The changed-file set is the ONLY thing that keeps this lint off
    # already-shipped specs (check_verify_rows.py: "does not retroactively police
    # already-shipped specs"). That holds while the base ref is the integration branch —
    # each PR then changes only its own spec. It BREAKS on a release PR (simplify → main),
    # where the base is `main` and every spec accumulated since the fork looks new: 56 files,
    # including specs written while this lint was dead (wired 2026-07-17 at 7034d30, not
    # actually comparing anything until it was revived 2026-08-08 at $CUTOFF). Those never
    # had a chance to comply, so intersect with "changed since the lint went live" and the
    # grandfathering survives a change of base ref.
    CUTOFF=af869a9
    if git rev-parse -q --verify "$CUTOFF^{commit}" >/dev/null 2>&1; then
      git diff --name-only "$CUTOFF"...HEAD -- 'specs/*/SUMMARY.md' 'specs/*/PLAN.md' \
        > "$TMP_POST_CUTOFF"
      # -x -F: whole-line literal match. No match → grep exits 1 with empty output, which is
      # the correct answer (nothing changed since the cutoff), not an error.
      changed="$(printf '%s\n' "$changed" | grep -xF -f "$TMP_POST_CUTOFF" || true)"
    else
      echo "  note — grandfather cutoff $CUTOFF absent (shallow clone?); linting the full changed set"
    fi
    if [ -n "$changed" ]; then
      printf '%s\n' "$changed" | python3 scripts/check_verify_rows.py || FAILED=1
    else
      echo "  skip — no SUMMARY.md/PLAN.md changed since the grandfather cutoff"
    fi
  else
    echo "  skip — no changed SUMMARY.md/PLAN.md vs $BASE_OUT"
  fi
fi

for suite in tests/hooks/*.test.sh tests/scripts/*.test.sh; do
  echo ""
  echo "== $suite =="
  bash "$suite" || FAILED=1
done

echo ""
echo "== L2: python unit tests =="
# Prefer the shared venv lib.sh builds; else system python3; skip if pytest is unavailable.
PYBIN="${TMPDIR:-/tmp}/harness-tests-venv/bin/python"
[ -x "$PYBIN" ] || PYBIN="$(command -v python3 || true)"
if [ -n "$PYBIN" ] && "$PYBIN" -c 'import pytest' >/dev/null 2>&1; then
  # Engine unit tests that ship with the repo but nothing else runs.
  PYTESTS="scripts/test_check_manifest.py scripts/test_check_codex_capabilities.py scripts/test_check_codex_packaging.py scripts/test_codex_harness_doctor.py scripts/test_check_runtime_neutral_sources.py scripts/test_verify_summary.py scripts/test_check_verify_rows.py scripts/test_check_review_receipt.py scripts/test_audit_skill_prompts.py scripts/test_score_skill_eval.py scripts/test_generate_skill_eval_corpus.py scripts/test_record_skill_eval.py scripts/test_capture_skill_eval.py scripts/test_run_skill_eval_batch.py scripts/test_check_skill_eval_readiness.py scripts/test_invalidate_skill_eval_collection.py scripts/test_rebuild_solution_index.py scripts/test_resolve_finish_context.py scripts/test_render_skill_prompt.py scripts/test_render_agent_definitions.py scripts/test_render_codex_adapter.py scripts/test_render_runtime_entry.py scripts/test_check_plan_contract.py scripts/test_score_task_review_eval.py scripts/test_ste_terminology_experiment.py skills/subagent-driven-development/scripts/test_task_brief.py skills/visual-planner/test_render_plan.py runtime/test_runtime_mode.py runtime/test_run_state.py runtime/test_chain_guards_are_load_bearing.py runtime/test_resume_decision.py"
  # shellcheck disable=SC2086
  "$PYBIN" -m pytest $PYTESTS -q --no-header --no-cov -p no:cacheprovider || FAILED=1
else
  echo "  skip — no python3 with pytest available"
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "ALL GREEN"
else
  echo "FAILURES — see above"
fi
exit "$FAILED"
