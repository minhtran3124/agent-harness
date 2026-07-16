# auto-test-multi-lang — Summary

Lane: high-risk
Confidence: high
Reason: Touches hooks/* (hard-gate high-blast file) — change explicitly requested and scoped by the human; direction unambiguous (multi-ecosystem auto-test).
Flags: none (hard gate only)
Input-type: harness improvement

## What changed

Rewrote `hooks/auto-test-on-change.sh` from pytest-only to ecosystem-aware: classifies the
edited file (Python `test_*.py`/`*_test.py` → pytest; JS/TS `*.test.*`/`*.spec.*`/`__tests__/`
→ vitest/jest/npm-test resolved from the nearest `package.json`; Go `*_test.go` → `go test .`),
walks up to the right project root per ecosystem, and supports a per-project
`AUTO_TEST_CMD='<cmd> {file}'` override for anything else. Same contract as before:
non-blocking, always exit 0, stderr feedback, dormant (not registered).

### Rationale

The harness is a framework applied across projects; a hook hard-coded to pytest +
`SCRIPT_DIR/../..` only worked for one repo shape. Detection-by-convention with an
override env matches the repo's portability pattern (xia2: universal logic, swappable
project config). Robustness fixes folded in from P3's observed failures: `python3`
fallback when `python` is absent, `--no-cov` only added when pytest-cov is installed.

### Alternatives considered

- Config-file rule map (glob → command) — rejected for now: more machinery than needed;
  the override env covers the escape hatch. Revisit if ≥2 projects need custom rules.
- Reading the test command from `agents/PROJECT.md` — rejected: that file is prose for
  agents, not machine config; parsing it from bash is brittle.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Syntax | `bash -n hooks/auto-test-on-change.sh` | 0 | |
| Python pass/fail (real pytest venv) | hook + `pytest.ini` root | 0 | PASSED / FAILED(1), root via find_up |
| Go pass/fail (real `go test`) | hook + `go.mod` fixture | 0 | PASSED / FAILED(1), runs from file dir |
| vitest resolution | shim `npx` + devDependencies.vitest | 0 | `npx vitest run <file>` |
| jest resolution via `__tests__/` | shim `npx` + devDependencies.jest | 0 | `npx jest <file>` |
| npm scripts.test fallback (real npm) | `scripts.test` only | 0 | PASSED |
| No detectable JS runner | empty package.json | 0 | silent skip |
| Custom ecosystem | `AUTO_TEST_CMD='echo … {file}' AUTO_TEST_PATTERN='*_spec.rb'` | 0 | `(custom)` ran with expanded {file} |
| Override on recognized file | `AUTO_TEST_CMD` only, py test | 0 | override replaces pytest |
| Non-test file skip | `pytest.ini` via hook | 0 | silent |
| Plain .ts outside `__tests__/` skip | `src/util.ts` | 0 | silent |

### Rollback

- `git revert 3bfb96e` (single hook file + CLAUDE.md row; hook remains dormant)

### Harness-Delta

- none
