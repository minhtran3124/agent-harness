# refresh-stale-solutions — Summary

Lane: tiny
Confidence: high
Reason: Docs-only re-verification of 4 KB entries against ground truth; no hard gate (no hooks/settings.json/engine touched).
Flags: none
Affects: none
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> "merge #107 and fix the 4 stale solutions" — the 4 entries the post-merge audit
> flagged as `solutions_stale` (`confirmed_at` > 30 days). "Fix" = re-verify each against
> current ground truth, refresh `confirmed_at` if still accurate, correct stale references
> where the codebase moved.

## What changed

Re-verified the 4 audit-flagged KB entries against ground truth and refreshed
`confirmed_at` to 2026-07-17. Two were accurate as-is (`gap-closure-decisions`,
`hooks-addition-is-high-risk-even-dormant` — all referenced paths exist; `protected-path-guard`
still dormant with 0 `settings.json` refs; `risk-corroboration.sh` still keys on `^hooks/`).
Two referenced the now-deleted `skills/bootstrap-xia2` / `skills/xia2/PROJECT.md`
(xia2 is zero-config since this session): corrected their `module`/`affects`, added a dated
`Status` note that retires the specific bootstrap mechanism while preserving the durable
insight, and updated the matching `critical-patterns.md` `Module:` lines. Rebuilt `INDEX.md`.

### Rationale

`confirmed_at` means "last re-verified against ground truth", so a blind date-bump would be
dishonest for the two entries whose module was deleted — re-verification found real stale
references (`skills/bootstrap-xia2`, `skills/xia2/PROJECT.md`) that were corrected, not just
re-dated. The critical insight in both is still true and load-bearing (severity `critical`,
promoted to critical-patterns), so it was preserved with a Status note rather than deleted.

### Alternatives considered

- Blind `confirmed_at` bump on all 4. Rejected: two entries point at a deleted skill/file — re-dating without correcting would launder a false reference past the audit.
- Delete the two bootstrap-xia2 entries. Rejected: the core meta-repo signal-remapping insight remains valid and generalizes to any risk-classification config.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| all 4 refreshed to today | `grep -q "confirmed_at: 2026-07-17" docs/solutions/harness/gap-closure-decisions.md && grep -q "confirmed_at: 2026-07-17" docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md && grep -q "confirmed_at: 2026-07-17" docs/solutions/harness-bootstrap/meta-repo-signal-remapping.md && grep -q "confirmed_at: 2026-07-17" docs/solutions/harness-bootstrap/meta-repo-signal-remapping-decisions.md` | 0 | no June dates remain |
| no dangling bootstrap-xia2 module ref | `! grep -rq "module: skills/bootstrap-xia2" docs/solutions` | 0 | deleted-skill reference removed |
| INDEX rebuilt, 16 entries | `grep -q "16 total entries" docs/solutions/INDEX.md` | 0 | count unchanged, rows re-sorted by confirmed_at |

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
