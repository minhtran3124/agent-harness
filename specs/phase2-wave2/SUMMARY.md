# phase2-wave2 — Summary

Lane: high-risk
Confidence: high
Reason: Diff edits CI-contract/high-blast files (scripts/run-tests.sh, harness-manifest.json, scripts/harness-audit.sh) — high-risk by judgment. Note ci-strict-gate does NOT mechanically fire (no settings/hooks/render_plan/templates path), verified; the lane is declared on judgment, not the gate. Direction unambiguous (user-directed wave 2 of the merged deep review).
Flags: high-blast (run-tests.sh, harness-manifest.json)
Affects: harness-manifest.json (plan-schema consumers), scripts/run-tests.sh (PYTESTS), scripts/harness-audit.sh (--json emitter), create-pr output contract
Input-type: harness improvement

### Intent

"merge v3 to main and start wave after that" — Phase 2 Wave 2 (coordinated deletes) per docs/research/harness-review-improvements/reviews/phase-2-deep-review-2026-07-16.md.

## What changed

Three coordinated deletions, each with its manifest/CI/skill wire updated atomically: check_plan_format.py + test (unwired from manifest:68 consumers and run-tests.sh PYTESTS — it is XML-only and unwireable since PR #69 made markdown the authoring syntax); harness-audit.sh check #4 verify_never_rerun (monotonic alarm-fatigue, 20→29 findings; the JSON emitter shrunk from 10→9 positional args); PR_TEMPLATE.md (tracked scratch file holding PR #2's body) with create-pr repointed to a gitignored `.pr-body.md`.

### Rationale

Wave 2 is the "coordinated" tier: each item is dead but coupled, so the value is doing the multi-file transaction atomically (delete + manifest + CI + skill wires in one commit) so the tree never goes inconsistent. The strict-gate finding (does NOT fire here) is why this is a judgment high-risk, not a mechanical one.

### Alternatives considered

- Rework check_plan_format to validate markdown: rejected — duplicates render_plan.py + executing-plans Step-0.
- Keep audit check #4 behind a flag: rejected — noise by construction, not a tunable.
- create-pr output to specs/<slug>/: rejected — specs/ is now tracked, would just relocate the pollution.

### Deviations

- none (execution matched the plan exactly)

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| plan parses (markdown, 4 tasks / 2 waves) | `bash -c 'python3 skills/visual-planner/render_plan.py specs/phase2-wave2/PLAN.md /tmp/p2w2.html > /tmp/p2w2.out 2>&1 && grep -q "tasks=4 waves=2" /tmp/p2w2.out'` | 0 | |
| 1.1 check_plan_format gone + unwired | `bash -c 'test ! -f scripts/check_plan_format.py && test ! -f scripts/test_check_plan_format.py && ! grep -q check_plan_format harness-manifest.json scripts/run-tests.sh && python3 scripts/check_manifest.py'` | 0 | manifest consistent |
| 1.2 audit check #4 gone, JSON valid | `bash -c 'test -z "$(grep VERIFY_NEVER_RERUN scripts/harness-audit.sh)" && bash scripts/harness-audit.sh --json > /tmp/p2w2audit.json && python3 -c "import json; json.load(open(\"/tmp/p2w2audit.json\"))"'` | 0 | emitter shrink parses (no pipe) |
| 1.2 audit test suite | `bash tests/scripts/harness-audit.test.sh` | 0 | 3 cases removed |
| 1.3 PR_TEMPLATE gone + repointed | `bash -c 'test ! -f PR_TEMPLATE.md && ! grep -rq "PR_TEMPLATE" skills/ && grep -q ".pr-body.md" .gitignore'` | 0 | create-pr → .pr-body.md |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | clean |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

### Rollback

- `git revert <wave commit>` — restores all three files and their wires from history; no data/schema migration. harness-audit emitter and manifest changes are self-contained.

### Harness-Delta

- none
