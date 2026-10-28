#!/bin/bash
# Harness test entry point — run everything CI runs:
#   L1  syntax (bash -n) + doc-truth lint
#   L2  hook contract tests          (tests/hooks/*.test.sh)
#   L3  script integration tests     (tests/scripts/*.test.sh)
# Usage: bash scripts/run-tests.sh
set -u
cd "$(dirname "$0")/.." || exit 1
FAILED=0
# Every failure is also recorded here and reprinted at the end, so a red run names what
# failed instead of leaving it to be found in ~1000 lines of output.
FAILED_STEPS=()
fail() { FAILED=1; FAILED_STEPS+=("$1"); }
STEP_LOG="$(mktemp)"
# Suites and pytest run through tee, so their stdout is a pipe; keep colour on a terminal.
if [ -t 1 ]; then export HARNESS_TEST_COLOR=1; PYTEST_COLOR=--color=yes; else PYTEST_COLOR=--color=no; fi
ESC="$(printf '\033')"
# record_details <ERE>: add each STEP_LOG line matching the marker <ERE>, minus the marker, to
# the summary. Colour codes are removed first so they cannot hide a marker.
record_details() {
  local line found=0
  while IFS= read -r line; do
    found=1
    FAILED_STEPS+=("    ${line:-(unnamed case)}")
  done < <(sed "s/${ESC}\[[0-9;]*m//g" "$STEP_LOG" | grep -E "$1" | sed -E "s/$1//")
  [ "$found" -eq 1 ] || FAILED_STEPS+=("    (no case names found; see the log above)")
}

echo "== L1: syntax =="
for f in plugins/harness/hooks/*.sh plugins/harness/scripts/*.sh scripts/*.sh tests/lib.sh tests/*/*.test.sh; do
  bash -n "$f" || { echo "  ✗ syntax: $f"; fail "syntax: $f"; }
done
echo "  ✓ bash -n clean"

echo "== L1: doc-truth lint =="
bash scripts/lint-doc-truth.sh || fail "scripts/lint-doc-truth.sh"

echo "== L1: skill-bash lint =="
bash scripts/lint-skill-bash.sh || fail "scripts/lint-skill-bash.sh"

echo "== L1: hook repo-root source =="
bash scripts/check-hook-root-source.sh || fail "scripts/check-hook-root-source.sh"

echo "== L1: plugin validate (skills + agents frontmatter) =="
bash scripts/check-plugin-validate.sh || fail "scripts/check-plugin-validate.sh"

echo "== L1: markdown links =="
bash scripts/check-md-links.sh || fail "scripts/check-md-links.sh"

echo "== L1: skill allowed-tools =="
bash scripts/check-allowed-tools.sh || fail "scripts/check-allowed-tools.sh"

echo "== L1: skill and agent registry (scanned from disk) =="
if command -v python3 >/dev/null 2>&1; then
  python3 scripts/check_frontmatter_contract.py || fail "scripts/check_frontmatter_contract.py"
  python3 scripts/check_skill_tool_conformance.py || fail "scripts/check_skill_tool_conformance.py"
else
  echo "  skip — no python3"
fi

echo "== L1: STE linter self-test and prose baseline =="
# The self-test can fail the suite. The baseline check reports only and always exits 0.
if command -v python3 >/dev/null 2>&1; then
  python3 plugins/harness/skills/asd-ste100/scripts/ste-lint.py --selftest || fail "ste-lint.py --selftest"
  python3 scripts/check_ste_baseline.py
else
  echo "  skip — no python3"
fi

# Build the shared pytest venv once, before anything runs concurrently: on a fresh machine
# (every CI run) parallel suites calling ensure_pyenv would race on venv creation + pip.
# pytest-xdist is best-effort — the pytest step below uses it only when it imports.
PYENV_BIN="$(bash -c 'source tests/lib.sh; ensure_pyenv && rm -rf "$PYSHIM" && echo "$PYENV_DIR/bin"' 2>/dev/null)"
if [ -n "$PYENV_BIN" ] && ! "$PYENV_BIN/python" -c 'import xdist' 2>/dev/null; then
  "$PYENV_BIN/pip" install -q pytest-xdist >/dev/null 2>&1 || true
fi

# Suites are hermetic (each works in its own mktemp repo — see tests/lib.sh), so they run
# in parallel. Each writes its own log, replayed below in glob order so output reads as if
# serial. HARNESS_TEST_JOBS=1 restores a serial run; HARNESS_SKIP_SUITES (space-separated
# paths) skips suites the caller already ran.
SUITE_JOBS="${HARNESS_TEST_JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"
SUITE_OUT="$(mktemp -d)"; trap 'rm -rf "$STEP_LOG" "$SUITE_OUT"' EXIT
SUITES=()
for suite in tests/hooks/*.test.sh tests/scripts/*.test.sh; do
  case " ${HARNESS_SKIP_SUITES:-} " in
    *" $suite "*) echo ""; echo "== $suite =="; echo "  skip — listed in HARNESS_SKIP_SUITES" ;;
    *) SUITES+=("$suite") ;;
  esac
done
echo ""
echo "== L2/L3: ${#SUITES[@]} suites, $SUITE_JOBS parallel jobs =="
# shellcheck disable=SC2016
printf '%s\n' "${SUITES[@]}" | xargs -P "$SUITE_JOBS" -I{} bash -c \
  'key=$(printf %s "$1" | tr / _); bash "$1" >"$2/$key.log" 2>&1; echo $? >"$2/$key.rc"' _ {} "$SUITE_OUT"
for suite in "${SUITES[@]}"; do
  key="$(printf %s "$suite" | tr / _)"
  echo ""
  echo "== $suite =="
  cat "$SUITE_OUT/$key.log" 2>/dev/null
  cp "$SUITE_OUT/$key.log" "$STEP_LOG" 2>/dev/null || : > "$STEP_LOG"
  if [ "$(cat "$SUITE_OUT/$key.rc" 2>/dev/null)" != 0 ]; then
    fail "$suite"
    record_details '^  (FAIL  |not ok )'
  fi
done

echo ""
echo "== L2: python unit tests =="
# Prefer the shared venv lib.sh builds; else system python3; skip if pytest is unavailable.
PYBIN="${TMPDIR:-/tmp}/harness-tests-venv/bin/python"
[ -x "$PYBIN" ] || PYBIN="$(command -v python3 || true)"
if [ -n "$PYBIN" ] && "$PYBIN" -c 'import pytest' >/dev/null 2>&1; then
  # Every unit test under scripts/ and plugins/harness/ — collected, not hand-listed: the
  # hand list drifted and left four test files running nowhere.
  PYTESTS="$(find scripts plugins/harness -name 'test_*.py' -not -path '*/__pycache__/*' | LC_ALL=C sort | tr '\n' ' ')"
  XDIST=""
  "$PYBIN" -c 'import xdist' >/dev/null 2>&1 && XDIST="-n $SUITE_JOBS"
  # shellcheck disable=SC2086
  "$PYBIN" -m pytest $PYTESTS $XDIST -q --no-header --no-cov -p no:cacheprovider "$PYTEST_COLOR" 2>&1 | tee "$STEP_LOG"
  if [ "${PIPESTATUS[0]}" -ne 0 ]; then
    fail "pytest"
    record_details '^(FAILED|ERROR) '
  fi
else
  echo "  skip — no python3 with pytest available"
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "ALL GREEN"
else
  echo "FAILURES:"
  printf '  %s\n' "${FAILED_STEPS[@]}"
fi
exit "$FAILED"
