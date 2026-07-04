---
slug: verify-substance
status: active
owner: Minh Tran
created: 2026-07-04
---

# Phase 3 — Verify substance (evidence gates reject trivial proof)

## 1. Motivation

DR-6/7/18/19: the strict gate accepts `| x | true | 0 | |` as proof; an unedited rollback template
satisfies high-risk; the gate's own parser (`verify_summary.py`) has zero CI coverage; the
placeholder sets diverge; honest non-zero claims fail; `Verified:` stamps on failure; duplicate
check names collide; `Lane: not-normal` resolves as `normal`.

## 2. Non-goals

- No "command must reference a changed path" check (deferred — needs diff plumbing + allowlist).
- No change to ci-strict-gate.sh itself (it already delegates to verify_summary --check).
- No change to SUMMARY table format.

## 3. Success Criteria

1. A whole-command `true` / `:` / `exit 0` / bare `echo` row FAILS verify_summary (pinned by test).
2. A row claiming exit 1 whose command actually exits 1 PASSES (negative proof representable).
3. `Verified:` is written only when all checks pass; duplicate check names update by row order.
4. Placeholder sets identical across both checkers (`—`, `–`, `-`, `<command>`, empty).
5. Template-only Rollback fails high-risk; `Lane: not-normal` no longer resolves.
6. `bash scripts/run-tests.sh` runs test_verify_summary.py and stays green.

## 4. Tasks

### Task 1.1 — verify_summary.py substance + semantics

```xml
<task id="1.1" wave="1">
  <files>scripts/verify_summary.py, scripts/test_verify_summary.py</files>
  <action>
(1) _PLACEHOLDER_COMMANDS -> {"—", "–", "-", "&lt;command&gt;", ""}. (2) Add _TRIVIAL_RE matching a
whole command that proves nothing: `true`, `:`, `exit 0`, or echo-only (no pipe/&& into a real
tool); report `TRIVIAL [check] command is not evidence` and mark failed BEFORE running it.
(3) Pass/fail semantics: PASS when claimed == actual (any code, incl. non-zero); MISMATCH when
claimed != actual; FAIL when no claim and actual != 0. (4) Stamp `Verified:` in write mode ONLY
when failed == False. (5) _rewrite_table: consume results in row order (index queue), not a
name-keyed dict. Update/add tests: trivial variants fail; `echo x | grep x` is NOT trivial;
claimed-1/actual-1 passes; claimed-0/actual-1 mismatches; no Verified stamp on failure; duplicate
check names rewrite correctly; en-dash/hyphen rows skipped as placeholders.
  </action>
  <verify>python3 -m pytest scripts/test_verify_summary.py -q --no-header --no-cov -p no:cacheprovider</verify>
  <done>All listed behaviors pinned green.</done>
</task>
```

### Task 1.2 — check_lane_evidence.py exactness

```xml
<task id="1.2" wave="1">
  <files>scripts/check_lane_evidence.py, scripts/test_check_lane_evidence.py</files>
  <action>
(1) _resolve_lane: exact whole-value match `^(tiny|normal|high-risk)$` after strip/lower — the raw
template option line and `not-normal` return None. (2) _has_real_rollback: a content line equal to
the bare template `git revert &lt;sha&gt;` (with/without backticks/bullet) does not count; real =
at least one non-template content line. Add tests: template-only rollback fails high-risk; rollback
with real prose passes; `Lane: not-normal` -> unresolvable; template option line -> unresolvable.
  </action>
  <verify>python3 -m pytest scripts/test_check_lane_evidence.py -q --no-header --no-cov -p no:cacheprovider</verify>
  <done>Exactness behaviors pinned green; existing tests still pass.</done>
</task>
```

### Task 2.1 — Wire the parser's tests into CI

```xml
<task id="2.1" wave="2">
  <files>scripts/run-tests.sh</files>
  <action>Add scripts/test_verify_summary.py to the PYTESTS list (DR-7 one-line fix).</action>
  <verify>bash scripts/run-tests.sh</verify>
  <done>Suite green; test_verify_summary count appears in the pytest run.</done>
</task>
```

## 5. Risks

- **Semantics change ripples into ci-strict-gate**: rows in already-merged SUMMARYs re-run on future
  gate invocations — a legacy row claiming 0 that now exits non-zero fails as before (unchanged);
  the only behavior change is trivial-rows-fail and honest-nonzero-passes. Checked all 8 existing
  specs' Verify tables for trivial commands: none present.
- **Denylist false-positive** on a legitimate bare `echo` check — accepted: an echo-only command
  never validates repo behavior; a real check pipes/greps (not trivial by the regex).

## 6. Status Log

- 2026-07-04 — plan drafted (Phase 3 of v0.3); worktree fix/verify-substance off v2 @ 3294940.
