---
slug: harness-tests-phase1
status: shipped
owner: minhtran
created: 2026-06-11
---

# Harness test suite — Phase 1

## 1. Motivation

All verification of harness changes is ad-hoc (this session proved both the value and the
waste: 11-case + 6-case matrices built, run once, discarded). Freeze them as regression
tests and mechanize the doc-truth audit.

## 2. Non-goals

- Fixing bugs the tests expose in hooks/ (hard gate — separate approval).
- Behavioral/LLM tests for skills (phase 3) and full hook coverage (phase 2).
- Wiring the lint into commit hooks (CI-only for now).

## 3. Success Criteria

`bash scripts/run-tests.sh` green locally; same command green on ubuntu + macos in CI;
the lint fails when a doc references a missing path or the hook table contradicts
settings.json.

## 4. Tasks

### Task 1.1 — Test framework + hook contract tests

```xml
<task id="1.1">
  <files>tests/lib.sh, tests/hooks/auto-test-on-change.test.sh, tests/hooks/risk-corroboration.test.sh, tests/hooks/commit-quality-gate.test.sh</files>
  <action>lib.sh: mktemp git repos with hooks copied in (hooks resolve repo root from their own location), stdin-JSON runner capturing OUT/RC, assert helpers, shared pytest venv, skip/xfail support. Port the session's matrices; commit-gate pytest-failure case is xfail (known || true bug).</action>
  <verify>bash tests/hooks/auto-test-on-change.test.sh && bash tests/hooks/risk-corroboration.test.sh && bash tests/hooks/commit-quality-gate.test.sh</verify>
  <done>All cases pass or explicit skip/xfail; zero writes outside mktemp dirs</done>
</task>
```

### Task 1.2 — Installer suite + doc-truth lint + runner

```xml
<task id="1.2">
  <files>tests/scripts/install-harness.test.sh, scripts/lint-doc-truth.sh, scripts/run-tests.sh</files>
  <action>Port the 6 installer cases (install --source into mktemp targets). Lint: extract repo-relative path refs from CLAUDE.md/README.md/HARNESS.md/skills/README.md (markdown links + backticked slash-tokens; skip URLs/placeholders/specs/; map .claude/ → root; allow skills/*/ resolution), assert existence; parse the CLAUDE.md hook table and cross-check each row's ✅/⬜ against settings.json registration. run-tests.sh = lint + all tests/**/*.test.sh, aggregate, nonzero on failure.</action>
  <verify>bash scripts/run-tests.sh</verify>
  <done>Green run; lint catches a synthetic phantom ref when one is injected (negative check)</done>
</task>
```

### Task 1.3 — CI workflow + docs

```xml
<task id="1.3">
  <files>.github/workflows/harness-ci.yml, CLAUDE.md, README.md</files>
  <action>Actions workflow: push/PR, matrix ubuntu-latest + macos-latest, run scripts/run-tests.sh. Add a short Testing note to README and a CLAUDE.md pointer.</action>
  <verify>bash scripts/run-tests.sh (local); workflow YAML parses (yq/python yaml or actionlint if available)</verify>
  <done>Workflow file valid; docs mention the runner</done>
</task>
```

## 5. Risks

- BSD/GNU divergence (macOS dev vs linux CI) — exactly what the CI matrix exists to catch.
- Lint false positives on prose paths — mitigated by placeholder/specs/URL filters; tune
  against the real docs until green, keep filters documented in the script.

## 6. Status Log

- 2026-06-11 — plan created; lane normal, additive-only.
- 2026-06-11 — all 3 tasks done; suite ALL GREEN (40 pass / 1 xfail); lane raised to high-risk at commit time (corroboration regex matches tests/hooks/ paths — false positive recorded).
