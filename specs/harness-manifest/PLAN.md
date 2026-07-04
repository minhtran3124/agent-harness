---
slug: harness-manifest
status: active
owner: Minh Tran
created: 2026-07-03
---

# Phase 2 — Harness manifest (single source for hard gates + inventory)

## 1. Motivation

DR-4: the hard-gate list diverges across feature-intake, auto-correct-scope, and
risk-corroboration.sh (feature-intake omits `public-contract` that the hook blocks on). Make one
machine-read source and enforce, in CI, that the enforcing hook matches it.

## 2. Non-goals

- No runtime YAML/JSON parsing inside risk-corroboration.sh (keep its tested regexes; CI checks consistency).
- No tool-registry product shape (ToolEntry/semver/SQLite) — per the 2026-06-09 research.
- No change to what the hook detects — only assert its category list == the manifest.

## 3. Success Criteria

1. `harness-manifest.json` is the single source: 8 detectable gates (+modes), 3 judgment gates, and the hook/skill/agent inventory.
2. `scripts/check_manifest.py` fails if manifest ↔ disk, manifest ↔ settings.json (wired), or manifest ↔ risk-corroboration.sh (add_cat + category_mode) diverge — bidirectional.
3. `check_manifest.py` exits 0 against the current repo; unit tests cover the drift cases.
4. feature-intake Step 3 includes `public-contract` and references the manifest; auto-correct-scope Rule 4 references it.
5. `bash scripts/run-tests.sh` green with the new test wired in.

## 4. Tasks

### Task 1.1 — Manifest + checker + tests

```xml
<task id="1.1" wave="1">
  <files>harness-manifest.json, scripts/check_manifest.py, scripts/test_check_manifest.py</files>
  <action>
Write harness-manifest.json (stdlib-parseable): keys __doc__, hard_gates {detectable:[{slug,desc,
mode}], judgment:[{slug,desc}]}, notes{}, hooks:[{name,wired}], skills:[names], agents:[names].
Populate from the current repo (13 hooks/11 wired, 15 skills, agents coding/reviewer/test-runner;
8 detectable gates = risk-corroboration add_cat set; judgment = remove-functionality/session-scope/
replace-service).
Write scripts/check_manifest.py (Python stdlib json/re only) asserting, with clear error lines:
  A. every manifest hook exists in hooks/ and every hooks/*.sh is in the manifest; each hook's
     `wired` matches whether settings.json references it.
  B. every manifest skill has skills/<name>/SKILL.md and vice versa; every manifest agent has
     agents/<name>.md (agents list excludes README/PROJECT*).
  C. hard_gates.detectable slugs == the set of `add_cat "X"` in risk-corroboration.sh == the set of
     category_mode branches; report any slug on one side but not the other.
Exit non-zero with a "manifest: <what> drift: <detail>" line on any mismatch; exit 0 clean.
Write scripts/test_check_manifest.py (pytest) driving check_manifest against tmp fixtures for: clean
pass; a hook on disk missing from manifest; a wired-flag mismatch; a detectable gate absent from the
hook; a hook add_cat absent from the manifest. Assert exit codes + messages.
  </action>
  <verify>python3 scripts/test_check_manifest.py && python3 scripts/check_manifest.py</verify>
  <done>Tests pass; checker green against the real repo; drift cases fail as asserted.</done>
</task>
```

### Task 2.1 — Wire checker into CI + align the doc consumers

```xml
<task id="2.1" wave="2">
  <files>scripts/run-tests.sh, skills/feature-intake/SKILL.md, rules/auto-correct-scope.md</files>
  <action>
Add scripts/test_check_manifest.py to run-tests.sh PYTESTS, and run `python3 scripts/check_manifest.py`
as an L1 step (alongside lint-doc-truth) so CI fails on manifest drift.
In feature-intake Step 3: add the missing `public-contract` gate to the hard-gate list and add a
line "Canonical list: harness-manifest.json (hard_gates) — do not diverge."
In auto-correct-scope Rule 4: add a pointer that the canonical detectable-gate list lives in
harness-manifest.json (the Rule-4 judgment items map to hard_gates.judgment).
  </action>
  <verify>bash scripts/run-tests.sh</verify>
  <done>CI runs check_manifest; feature-intake lists public-contract + points to the manifest; suite + lint green.</done>
</task>
```

## 5. Risks

- **Checker regex vs risk-corroboration.sh format.** If the hook's `add_cat "X"` / `category_mode`
  style changes, the checker's extraction could break. Mitigation: extract with a tolerant regex on
  the exact current tokens; unit tests pin both directions; the hook change itself would re-run CI.
- **Prose consumers not mechanically checked.** feature-intake/auto-correct-scope alignment is manual
  (prose); only the enforcing hook is mechanically tied to the manifest. Accepted: the hook is the
  load-bearing enforcer; lint-doc-truth already checks the manifest path is referenced.
- **JSON hand-edit friction** (no comments/trailing-comma). Mitigation: `__doc__`/`notes` keys carry
  guidance; the checker parses it so a malformed edit fails CI loudly.

## 6. Status Log

- 2026-07-03 — plan drafted + approved (Phase 2 of v0.3). Worktree feat/harness-manifest off v2.
