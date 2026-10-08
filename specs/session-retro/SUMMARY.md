# session-retro — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine signal fired (new skills/session-retro/SKILL.md and a harness-manifest.json skill register entry); scripts/run-tests.sh is warn-tier gate logic
Flags: workflow-engine
Affects: skills inventory (harness-manifest.json skills register), scripts/run-tests.sh output contract
Input-type: harness improvement

### Intent

> make the review retro skill following link
> compare with our current workflow and thinking how we can learn/improve/distill from it?

> https://www.aihero.dev/skills-retro

> chạy thử /session-retro cho phiên này, sau đó review lại prompt của skill theo chuẩn của opus5.5. target của tôi là nó sẽ chạy vs model này.

> làm mục 1 và 2, rồi commit và mở PR

## What changed

Adds a user-invoked `session-retro` skill, adapted from the AI Hero "skills retro" method. It traces
the moments where a session struggled to a missing environment lever (check, pointer, scoped rule,
tool, or access), filters candidates for recurrence against `docs/solutions/` and the improvement
backlog, and proposes ranked fixes for the user to approve without editing anything. The prompt was
then reviewed against the Opus 5.5 prompting guidance. A trial run of the skill on its own authoring
session produced two fixes, both made here: `scripts/run-tests.sh` now reprints the name of every
failed step, shell-suite case, and pytest test at the end; and the codex-capability-probe
"missing tools" case links the real interpreter instead of a pyenv shim, which needs tools
outside the test's restricted PATH.

### Rationale

`compound` captures what a session learned; nothing in the chain asked what in the environment
let the agent stumble or whether a check could replace prose. The skill is propose-only and
user-invoked because each environment change taxes every later session. Both trial-run fixes
were chosen for recurrence: every `hooks/`/`scripts/` change runs the suite, and a permanently
red local test trains people to ignore red.

### Alternatives considered

- Fold the retro into `compound` — rejected: different question (environment levers vs. durable knowledge) and `compound` writes records without approval.
- Add `env` and `pyenv` to the probe test's tool list — rejected: the shim also needs further coreutils; linking `sys.executable` removes the shim from the picture.
- Derive the skill count in `scripts/test_audit_skill_prompts.py` from the manifest (retro candidate 3) — deferred; not approved for this PR.

### Deviations

- Rule 3 (blocking): `scripts/test_audit_skill_prompts.py` hard-codes the skill count; updated 12 → 13 so the new skill does not fail the suite.
- The chain ran out of order: no `feature-intake` SUMMARY before the first edit; this SUMMARY was written at commit time. `context-propagation-audit`, `correctness-review`, and `intent-review` were not run.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| probe test green on a pyenv host | `bash tests/scripts/codex-capability-probe.test.sh` | 0 | 40 passed (was 38 passed, 1 failed) | |
| skill registered in manifest | `python3 scripts/check_manifest.py` | 0 | | |
| skill frontmatter contract | `python3 scripts/check_frontmatter_contract.py` | 0 | | |
| skill under the 600-word ceiling | `python3 scripts/audit_skill_prompts.py --json` | 0 | | |
| run-tests.sh parses | `bash -n scripts/run-tests.sh` | 0 | | |

### Not auto-verified

- `run-tests.sh` end-of-run failure summary lists the failing suite and case — reached truth by one manual run (it printed `tests/scripts/codex-capability-probe.test.sh` / `missing tools degrade to explicit unknown` before the probe fix); no Verify row, because the behavior only shows on a full-suite run, which exceeds the Verify time budget.
- Full suite all green — reached truth locally (`bash scripts/run-tests.sh` → ALL GREEN, 638 pytest passed); not a Verify row for the same reason.
- `disable-model-invocation: true` stops Claude from auto-invoking the skill — reached traceability only; the field is not checked against Claude Code documentation, and no other skill in this repo uses it.
- The skill prompt follows the Opus 5.5 guidance — reached traceability (manual review against the claude-api `prompt-audit.md` guide); no eval of the skill's behavior was run.

### Rollback

- Revert the merge commit with `git revert -m 1 <merge-sha>`. That removes the skill directory, its manifest and README entries, and the test and `run-tests.sh` changes together. No state outside the repo is touched, and nothing is deployed until a consumer re-syncs.
- If a consumer has already re-synced, re-sync it after the revert. `scripts/deploy-harness.sh` prunes entries the previous harness manifest shipped but source no longer has, so the skill directory is removed.

### Harness-Delta

- backlog: adding a skill requires four coordinated edits (manifest register, `skills/README.md` row, hard-coded count in `scripts/test_audit_skill_prompts.py`, 600-word ceiling), discovered only through test failures — candidate: an "Adding a skill" checklist in `skills/README.md` and a manifest-derived count.
