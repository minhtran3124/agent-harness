# blast-radius-stale-plan

Lane: high-risk
Confidence: high
Reason: Hard gate — edits a wired hook (`hooks/blast-radius-check.sh`, high-blast: auto-runs on every Write/Edit of every session). The defect and the fix are both unambiguous (the code contradicts its own documented contract), so confidence is high; the gate still requires high-risk ceremony.
Flags: high-blast file (hooks/*), existing behavior
Affects: hooks/blast-radius-check.sh (PostToolUse Edit|Write — fires in every session, in every repo the harness is deployed into)
Input-type: Harness improvement
Route: tiny-sized diff, high-risk lane — branch → direct patch + regression test → SUMMARY with Verify/Rollback
Escalate: no — the user authorized the hook edit after the finding was surfaced

### Intent

The user asked to close `specs/verify-substance/PLAN.md`, which I had told them was `status: active`
and causing spurious blast-radius warnings on every edit:

> "specs/verify-substance/PLAN.md vẫn status: active, gây cảnh báo blast-radius vu vơ mỗi lần edit.
> Nên đóng hoặc chuyển paused. ---> đóng"

**That premise was wrong.** `verify-substance` is `status: shipped` on every branch that has it
(`v2`, `feat/branch-per-lane`, `feat/correctness-review-altitude`), and no `PLAN.md` anywhere in the
repo or its two sibling worktrees is `active`. There was nothing to close. The warnings were real,
but the cause was a defect in the hook. The user then authorized fixing that instead.

### The defect

`hooks/blast-radius-check.sh` contradicted the contract stated in its own header:

> *"No-op (silent) when: no active PLAN.md exists ... This keeps it quiet outside of active plan
> execution."*

The code did the opposite. When no plan was `active`, line 37 fell back to the **most recently
modified** `PLAN.md` and enforced *its* `<files>` set:

```bash
[ -z "$PLAN" ] && PLAN=$(ls -t "$REPO_DIR"/specs/*/PLAN.md 2>/dev/null | head -1)
```

So a long-shipped plan kept policing every edit, forever. A shipped plan's `<files>` set is a
**record of what that work touched** — not a scope constraint on everything that comes after it.
This was live during the fix itself: the deployed hook fired on the very edit that removed it,
citing `specs/verify-substance/PLAN.md` (shipped since 2026-07-04).

The cost is worse than noise. A warning that fires when nothing is wrong trains the reader to
ignore it, so the hook stops working on the day it is finally right — a scope-creep warning during
a real wave would land in a channel everyone has learned to skip.

### What changed

- `hooks/blast-radius-check.sh` — dropped the stale-plan fallback (one line). `status: active` is
  now the only thing that arms the hook, matching the header contract. The comment above the loop
  now says why there is no fallback, so it does not get "helpfully" re-added.
- `tests/hooks/blast-radius-check.test.sh` — 6 → 8 cases. The two new ones cover the state that was
  never tested and is exactly where the bug lived: **a `PLAN.md` exists but none is `active`**
  (`shipped`, and `proposed`). The old case 1 only covered *no `PLAN.md` at all*, which is why six
  green tests never saw this.

### Deviations

- Rule 2 — Added a second regression case (`proposed`, not just `shipped`). The fallback keyed on
  "not active", so a not-yet-started plan armed the hook the same way a finished one did; one case
  would have locked half the fix.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| hook contract, incl. the closed hole | `bash tests/hooks/blast-radius-check.test.sh` | 0 | 8 passed |
| the new tests actually catch the bug | `bash -c 'd=$(mktemp -d); mkdir -p "$d/hooks" "$d/tests/hooks"; cp tests/lib.sh "$d/tests/"; cp tests/hooks/blast-radius-check.test.sh "$d/tests/hooks/"; git show d424183:hooks/blast-radius-check.sh > "$d/hooks/blast-radius-check.sh"; bash "$d/tests/hooks/blast-radius-check.test.sh"; rc=$?; rm -rf "$d"; exit $rc'` | 1 | **2 FAILED** (both new cases) — the new suite run against the pre-change hook (from `d424183`, the base this PR merges onto), so they are a real regression lock, not decoration |
| no plan is silently armed anymore | `grep -rn '^status: active' specs --include='*.md'` | 1 | NONE — and the hook is now correctly silent, where before it fell back to `verify-substance` |
| full suite | `bash scripts/run-tests.sh` | 0 | see below |

### Rollback

- Revert the whole change: `git revert <sha>` (single commit — hook + tests move together).
- The change is a **loosening**: it can only make the hook quieter, never noisier. Reverting
  restores the spurious warnings; it cannot restore lost protection, because the fallback protected
  nothing (it enforced a dead plan's file set against unrelated work).
- No break-glass needed. `BLAST_RADIUS_STRICT=1` still escalates a genuine in-plan violation to
  exit 2, unchanged.

### Blast radius / who this bites

`blast-radius-check.sh` is **wired** (PostToolUse on Edit|Write) and runs in every session, in this
repo and in every project the harness is deployed into. The behavior change is **strictly a
narrowing of when it fires**: edits made while a plan is `active` behave exactly as before
(in-scope → silent; out-of-scope → warn; `BLAST_RADIUS_STRICT=1` → exit 2). Edits made while **no**
plan is active are now silent, where they previously warned against a stale plan. Nobody loses a
warning they should have had.
