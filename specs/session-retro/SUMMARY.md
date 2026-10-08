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
- The chain ran out of order. There was no `feature-intake` SUMMARY before the first edit, and this SUMMARY was written at commit time. The review chain (`context-propagation-audit`, `correctness-review`, `intent-review`) ran after PR #248 was opened, not before.
- Rule 3 (blocking), from correctness-review: registering `session-retro` without a skill-eval corpus entry broke `python3 scripts/score_skill_eval.py --validate-corpus` (`corpus: missing skill session-retro`, exit 1; scored 100). Fix: added a `session-retro` entry to `scripts/generate_skill_eval_corpus.py` and regenerated, which added only the two new `session-retro` files and the manifest entry. The hard-coded corpus count in `scripts/test_generate_skill_eval_corpus.py` was updated from 12 to 13.
- Review independence was enforced by instruction, not structurally. The scorer and intent-reviewer ran as `general-purpose` agents told to stay read-only, because the read-only `reviewer` agent type is not registered in this session.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| probe test green on a pyenv host | `bash tests/scripts/codex-capability-probe.test.sh` | 0 | 40 passed (was 38 passed, 1 failed) | |
| skill registered in manifest | `python3 scripts/check_manifest.py` | 0 | | |
| skill frontmatter contract | `python3 scripts/check_frontmatter_contract.py` | 0 | | |
| skill under the 600-word ceiling | `python3 scripts/audit_skill_prompts.py --json` | 0 | | |
| run-tests.sh parses | `bash -n scripts/run-tests.sh` | 0 | | |
| skill-eval corpus covers every registered skill | `python3 scripts/score_skill_eval.py --validate-corpus` | 0 | `skill-eval: valid` (was exit 1 before the corpus fix) | |

### Not auto-verified

- `run-tests.sh` end-of-run failure summary lists the failing suite and case — reached truth by one manual run (it printed `tests/scripts/codex-capability-probe.test.sh` / `missing tools degrade to explicit unknown` before the probe fix); no Verify row, because the behavior only shows on a full-suite run, which exceeds the Verify time budget.
- Full suite all green — reached truth locally (`bash scripts/run-tests.sh` → ALL GREEN, 638 pytest passed); not a Verify row for the same reason.
- `disable-model-invocation: true` stops Claude from auto-invoking the skill. Reached provenance: the Claude Code skills docs (`code.claude.com/docs/en/skills.md`) list it as a frontmatter field ("prevent Claude from automatically loading this skill… trigger manually with `/name`"; it also keeps the description out of context). It was not behavior-tested in a session. Under the Codex adapter it is unconfirmed: the skill is copied verbatim, and nothing in the repo shows that Codex honors the field.
- The skill prompt follows the Opus 5.5 guidance — reached traceability (manual review against the claude-api `prompt-audit.md` guide); no eval of the skill's behavior was run.

### Rollback

- Revert the merge commit with `git revert -m 1 <merge-sha>`. That removes the skill directory, its manifest and README entries, and the test and `run-tests.sh` changes together. No state outside the repo is touched, and nothing is deployed until a consumer re-syncs.
- If a consumer has already re-synced, re-sync it after the revert. `scripts/deploy-harness.sh` prunes entries the previous harness manifest shipped but source no longer has, so the skill directory is removed.

### Context-Propagation Audit

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `skills/session-retro/SKILL.md` body (propose-only, stop for approval) | Claude Code session invoking `/session-retro` | main | full skill loads on invocation | Claude Code skills docs ("full skill loads when invoked"); `check_frontmatter_contract.py` passes |
| `disable-model-invocation: true` | Claude Code skill routing | main | frontmatter, read by the runtime | Claude Code skills docs (frontmatter reference) |
| `skills/session-retro/SKILL.md` | subagents | implementer / reviewer / scorer | none: the field blocks preloading into subagents, and the skill dispatches no children | Claude Code skills docs; SKILL.md has no Agent or Task dispatch |
| `skills/session-retro/` | Codex adapter | Codex session | copied verbatim by `render_codex_adapter.py` `_copy_tree` | `test_render_codex_adapter.py` passes. Whether Codex honors `disable-model-invocation` is **unconfirmed** (advisory: the load-bearing propose-only rule is in the body, which is delivered) |
| `harness-manifest.json` `skills` register | `check_manifest.py`, `render_codex_adapter.py`, `audit_skill_prompts.py`, `score_skill_eval.py` corpus | CI / scripts | file read | each passes on HEAD; `--validate-corpus` passes after the Rule 3 fix |

Result: **PASS**, with one advisory row (Codex auto-invocation unconfirmed).

### Correctness Findings

Six FIND angles and an independent scorer per deduplicated location; threshold 75.

- `harness-manifest.json:236`: corpus entry missing, so `--validate-corpus` failed. Score 100, fixed (Rule 3, see Deviations).
- `scripts/run-tests.sh:136`: advisory, score 50. The pytest detail grep matches only `^FAILED `, so collection/import/fixture `ERROR` lines leave the summary saying just `pytest`. The step is still named and the exit code is correct.
- `scripts/run-tests.sh:119`: advisory, score 50. The suite detail grep matches only `  FAIL  ` lines, so the 7 suites that don't use `tests/lib.sh` are named without their failing case, and a nameless `fail` adds a blank entry.
- `scripts/run-tests.sh:116`: advisory, score 50. Piping suites through `tee` drops `tests/lib.sh`'s `[ -t 1 ]`-gated colour on interactive runs. The pipe-hang concern has no trigger: no suite backgrounds a process.

### Intent Findings

- none. The intent reviewer, in a fresh context and blind to plan and research documents, found no gap, drift, or excess against the verbatim intent.

### Harness-Delta

- backlog: adding a skill requires six coordinated edits, each found only through a failure: the manifest register, the `skills/README.md` row, the generator `SPECS` entry plus regenerated corpus, two hard-coded skill counts (`scripts/test_audit_skill_prompts.py`, `scripts/test_generate_skill_eval_corpus.py`), and the 600-word ceiling. Candidate: an "Adding a skill" checklist in `skills/README.md`, with counts derived from the manifest.
- backlog (missing guardrail): `scripts/run-tests.sh` never runs `score_skill_eval.py --validate-corpus`, which is why CI stayed green while the corpus was broken. Candidate: add it to the L1 manifest-consistency block.
