---
slug: auto-test-multi-lang
status: shipped
owner: minhtran
created: 2026-06-11
---

# Multi-ecosystem auto-test-on-change hook

## 1. Motivation

The harness is applied across projects, but `hooks/auto-test-on-change.sh` is hard-coded to
pytest and a fixed `../..` project-root assumption. It must detect the ecosystem of the
edited test file and run the matching runner.

## 2. Non-goals

- Registering the hook (stays dormant in `settings.json`).
- A config-file rule map (env override only, until ≥2 projects need more).
- Rust/Java/other ecosystems (add when a real project needs them).

## 3. Success Criteria

Editing a test file triggers the right runner from the right directory for Python, JS/TS
(vitest / jest / npm test), and Go; unknown files skip silently; `AUTO_TEST_CMD` overrides
everything; contract unchanged (never blocks, always exit 0).

## 4. Tasks

### Task 1.1 — Rewrite the hook ecosystem-aware

```xml
<task id="1.1">
  <files>hooks/auto-test-on-change.sh</files>
  <action>Classify file by basename/path (test_*.py|*_test.py → python; *.test.*|*.spec.*|__tests__/*.{js,jsx,ts,tsx} → js; *_test.go → go). Walk up to the nearest ecosystem marker (pyproject.toml/pytest.ini/setup.cfg/requirements.txt; package.json; go.mod — go runs from the file's dir). Resolve runner: AUTO_TEST_CMD override first ({file} placeholder); js from package.json deps (vitest → npx vitest run, jest → npx jest, else scripts.test → npm test --silent --). python3 fallback; --no-cov only when pytest-cov importable. Keep: stderr feedback, tail -15, always exit 0.</action>
  <verify>bash -n hooks/auto-test-on-change.sh</verify>
  <done>Script parses; all legacy behavior (python pass/fail reporting) preserved</done>
</task>
```

### Task 2.1 — Test matrix

```xml
<task id="2.1">
  <files>(none — /tmp fixtures only)</files>
  <action>Run the hook against fixtures: python pass+fail (real venv), go pass+fail (real go test), js vitest/jest resolution (PATH shim npx), npm-script fallback (real npm + trivial scripts.test), AUTO_TEST_CMD override, non-test file skip, missing-runner failure report.</action>
  <verify>each case prints the expected [AUTO-TEST] line; skip cases silent with exit 0</verify>
  <done>All matrix rows recorded in SUMMARY ### Verify</done>
</task>
```

### Task 3.1 — Docs + deploy + commit

```xml
<task id="3.1">
  <files>CLAUDE.md</files>
  <action>Update the auto-test-on-change row in the CLAUDE.md hook table (pytest-only → multi-runner + override). Re-run deploy-harness.sh; commit hook + CLAUDE.md (+ ledger row).</action>
  <verify>diff -q hooks/auto-test-on-change.sh .claude/hooks/auto-test-on-change.sh</verify>
  <done>Clone in sync; commit passes risk-corroboration with Lane: high-risk</done>
</task>
```

## 5. Risks

- `eval` on the composed command — inputs are repo file paths + fixed templates; quoted in
  composition. Override env is user-supplied by definition.
- Runner detection wrong in monorepos (nearest package.json wins — documented behavior).

## 6. Status Log

- 2026-06-11 — plan created; lane high-risk (hooks/*), human-directed.
- 2026-06-11 — tasks 1.1–3.1 done; 11-case matrix green; shipped as `3bfb96e`.
