# stack-profiles — Summary

Lane: high-risk
Confidence: high
Reason: Adds files under templates/ (the stack-profile bundle) — a hard-gate path per ci-strict-gate/PROJECT.md. Additive only (new profiles); no existing file changed.
Flags: high-blast (templates/)
Affects: templates/stacks/ (new bundled profiles consumed by bootstrap-xia2)
Input-type: harness improvement

### Intent

User request (this session): after MIN-25 made `rules/` stack-agnostic, add real bundled stack profiles so a Next.js (FE), Node/TS (BE), and Django (BE) repo init **fully** via `/bootstrap-xia2` — not just the generic `_skeleton` fallback. (Selected: nextjs, node, django.)

## What changed

Added three bundled stack profiles, each mirroring the `fastapi` profile's section structure:
`templates/stacks/{nextjs,node,django}/{architecture.md,guidelines.md}` (6 files). `bootstrap-xia2`
now renders a real profile for those detected stacks instead of the generic skeleton. Purely
additive — no existing file modified; unbundled stacks (e.g. go) still get the `_skeleton` fallback.

### Rationale

Closes the gap the post-MIN-25 dogfood exposed: only `fastapi` had a bundled profile, so FE/Node/Django repos fell back to the empty skeleton. Authored by three parallel subagents (file-disjoint), each told to mirror the fastapi profile's depth + structure for its stack.

### Alternatives considered

- Leave it at the `_skeleton` fallback (let humans fill per repo): rejected — the user explicitly wants FE/Node/Django to init fully out of the box.

### Deviations

- none

### Verify

<!-- Pipe-free + idempotent so ci-strict-gate's verify_summary --check re-runs clean. -->

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| full suite + doc-truth lint | `bash scripts/run-tests.sh` | 0 | ALL GREEN (102 passed, 1 skipped) |
| all 3 profiles present | `test -f templates/stacks/nextjs/architecture.md && test -f templates/stacks/node/guidelines.md && test -f templates/stacks/django/architecture.md` | 0 | 6 files authored |
| lane evidence (dogfood) | `python3 scripts/check_lane_evidence.py stack-profiles` | 0 | high-risk SUMMARY has Verify + Rollback |

Also dogfooded manually: detection for nextjs/node/django/fastapi → renders the real `templates/stacks/<stack>/` profile; `go` (unbundled) → `_skeleton` fallback (no wrong-stack).

### Rollback

- Additive only — remove the new dirs: `git rm -r templates/stacks/nextjs templates/stacks/node templates/stacks/django` (or `git revert <sha>`). No existing file changed; nothing else depends on them.

### Harness-Delta

- none — clean additive extension of MIN-25.
