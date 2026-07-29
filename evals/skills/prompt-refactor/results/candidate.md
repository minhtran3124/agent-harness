# Candidate live-evaluation status

Run date: 2026-07-29
Environment: `claude` (`CLAUDE_CONFIG_DIR=~/.claude`), `claude-sonnet-5`, Claude Code `2.1.220`,
reasoning `low`, one clean no-tools session per observation, stdin closed.

**Arms.** Both arms are deployed worktrees running the identical probe; the only variable is the
prompt surface each session loads.

| arm | worktree | commit |
|---|---|---|
| baseline (pre-refactor) | `/private/tmp/harness-skills-baseline-ab` | `924af147e9721c0e09fb5d3f25a71e4465ea9b10` |
| candidate (post-refactor) | `/tmp/harness-skills-candidate-ab` | `dbdd2b70afd5d76637f0a87d6014c8dff9ae4763` |

`candidate.json` pins `commit_sha` at `edc89b6bae449eccc36b98086da4c89119ff0642`, the commit the
first candidate behavior observations were taken at. The prompt surface is byte-identical between
`edc89b6` and the worktree HEAD — only eval tooling and docs changed in between:

```bash
git diff --stat edc89b6..dbdd2b7 -- skills/ rules/ agents/ templates/ hooks/ \
  harness-manifest.json CLAUDE.md HARNESS.md settings.json   # empty
```

Raw responses for every case in this run are committed to
`transcripts/2026-07-29-baseline-run.json` and `transcripts/2026-07-29-candidate-run.json`.

## Coverage

| suite | corpus | baseline observed | candidate observed |
|---|---:|---:|---:|
| activation | 192 | 192 | 192 |
| behavior | 36 | 36 | 36 |
| end-to-end | 5 | 5 | 5 |

The strict canonical comparison now runs for real — the partial-collection failure recorded at
handoff is cleared.

## Activation results

Activation is graded on **which skill the response names as the handler**, not on the
TRIGGER/NO-TRIGGER token. That token proved unreliable in both arms: responses routinely answer
`NO-TRIGGER` while naming the correct skill (`"this is a knowledge-capture request (/compound
territory)"`), and near-miss queries routinely answer `TRIGGER` while naming a *different* skill —
which is correct behavior, since a near-miss for skill X may legitimately route to skill Y. So a
should-trigger case passes when the expected skill is named as handler, and a near-miss case is a
false positive only when the expected skill is named as handler.

| metric | baseline | candidate |
|---|---:|---:|
| pass | 152 / 192 | **162 / 192** |
| missed | 39 | 29 |
| false-positive | 1 | **0** |
| blocked (no decision returned) | 0 | 1 |

- **11 cases improved**, 1 regressed.
- **Zero new false positives.** The candidate also eliminated the baseline's only false positive
  (`correctness-review-near-miss-2`).
- The largest single gain is `context-propagation-audit`, whose should-trigger misses fell from
  **8 to 2** — six cases now route to the audit that previously did not.

### The one regression

`intent-review-trigger-4`: baseline `pass` → candidate `blocked`. The candidate response returned
no TRIGGER/NO-TRIGGER decision at all; it asked for the diff and emitted `git diff` / `git log`
command text instead. No activation judgement was observed, so the honest verdict is `blocked`, not
`missed`. It is recorded as a first-run result and **not** re-run to a better outcome.

### Misses that are probe or fixture artifacts, not description defects

Several should-trigger misses are shared by **both** arms at the same rate and reflect the fixture
or probe wording rather than the skill description:

- **`visual-planner` — 8/8 missed in both arms.** The responses are substantively correct: "rendering
  happens automatically via `hooks/render-plan-on-write.sh` on save; no skill needed." The corpus
  positive ("Render this PLAN.md as HTML…") was written before the render hook made manual
  invocation unnecessary. The fixture, not the description, is stale.
- **`feature-intake` (5–6 missed per arm).** The probe appends "Decide whether a repository skill
  should handle this request", which collides with a query that *is itself* a classification
  request; the model answers `NO-TRIGGER — this is a classification-only request, no edits`.
- **`xia2` (5–7 missed per arm).** Same shape: "research-only request, no implementation."

`finishing-a-development-branch` (5 missed in the candidate, 6 in the baseline) looks like a genuine
activation weakness in both arms — "pushing a branch and opening a PR is a plain git/gh operation,
not something a repository skill governs" — and is not explained by probe wording.

## Behavior results

36 / 36 pass in both arms. The baseline's eight earliest golden-path observations are preserved as
originally recorded; the recorder correctly refused to overwrite them with this run's repeats.

## End-to-end canary results

The canaries had no runnable probe in the corpus (only a `lane` and an `expectation` label). A
`prompt` field was added per case, the generator was updated to reproduce the fixture byte-for-byte,
and `run_skill_eval_batch.py` learned the `end-to-end` suite so the canaries are reproducible from
one documented command.

| case | baseline | candidate |
|---|---|---|
| e2e-tiny | pass | pass |
| e2e-normal | pass | pass |
| e2e-high-risk | **missed** | **missed** |
| e2e-resume | pass | pass |
| e2e-workflow-engine | **missed** | **pass** |

- `e2e-workflow-engine` is a candidate improvement: the baseline ordered correctness → intent and
  never named `context-propagation-audit` for a diff touching `skills/`, dispatch prompts, and
  `rules/`. The candidate ordered audit → correctness → intent.
- `e2e-high-risk` is missed by **both** arms for the same reason: each named design, research, plan,
  isolation, execution, and review, but neither named the **review receipt** required before ship.
  Recorded as a miss on both sides rather than rounded up.

## Review-chain and context-boundary results

Recorded separately under their own manual protocols:

- `evals/skills/review-chain/results/2026-07-29-prompt-refactor-ab.md` — 7 fixtures × 2 arms. On the
  5 fixtures whose expected oracle is correctness or intent: **4/5 both arms, identical miss**. No
  recall regression. Two open items are recorded there: a pre-declared false positive whose
  confidence crossed the 75 fix-loop threshold in the candidate arm only (65 → 75, n=1), and the
  `soft-delete-filter` fixture being unanswerable since its answer key cites the removed
  `templates/stacks/fastapi/` profile.
- `evals/context-boundaries/results/2026-07-29-prompt-refactor.md` — all four probes clean on the
  escape-relevant negative control. The main-session row, `unconfirmed` in the 2026-07-22 baseline
  because of context contamination, is now cleanly observed in both directions.

## Gate status

| criterion | check | result |
|---|---|---|
| SC-2 | `score_skill_eval.py --compare baseline.json candidate.json --suite activation` | pass |
| SC-3 | `score_skill_eval.py --suite behavior --candidate` | pass |
| SC-6 | `score_skill_eval.py --suite review-chain --candidate` | pass (schema gate; substantive evidence in the review-chain result file) |
| SC-9 | `score_skill_eval.py --compare baseline.json candidate.json` | pass |

Both comparison gates print one **unmeasured coverage** line for `intent-review-trigger-4` and exit
0. That is deliberate: the case is reported on every run so it cannot be mistaken for proven parity.

### How SC-2 got here

SC-2 originally required **192/192** activation cases to pass. This run measured that bar and it is
met by **neither** arm — the baseline scores 152/192 against the same corpus, and several misses are
fixture artifacts shared by both arms (most clearly `visual-planner`, 8/8 in both). That is a finding
about the criterion and the fixture set, not only about the candidate. Per Task 7.1's Done clause
("…or the plan is revised rather than declaring success") and `rules/orchestration.md` (a change that
would redefine validation requirements must escalate), it was escalated as `ESCALATIONS.md` E001 and
**decided by a human on 2026-07-29**: SC-2 becomes a non-regression bar — no case falls from pass,
the suite pass count does not drop, and no new false positive appears. Fixture re-grounding and the
corpus case-versioning it requires are filed as separate work.

The SC-9 sub-decision was to **fix the scorer** rather than waive the case. `blocked` means no
observation was collected, so counting `pass → blocked` as a measured regression contradicted this
repo's `not_observed != absent` rule — and the safety-critical check in the same function already
drew that distinction by excluding `blocked`. It now reports as unmeasured coverage. The first-run
record for `intent-review-trigger-4` is unchanged and was not re-run.

## Limitations

- **One first-run observation per case.** The protocol's "three runs where declared" was not
  executed: the corpus encodes no repetition count and the recorder rejects duplicate first-run
  records by design. Every number here is n=1 per cell, one model, one client version. No variance
  estimate.
- Both arms share the same user-level `~/.claude` profile (user memories and global instructions).
  It is identical across arms, so it does not confound the differential, but these are not
  clean-room numbers — one baseline response visibly cites a user memory.
- Activation grading is deterministic from the transcript text, then reviewed for the cases where
  the polarity token and the naming signal disagree. It measures whether the right skill is
  *named as handler*, which is a proxy for real dispatch, not a measurement of dispatch itself.
- Coverage is bounded by the corpus. A behavior with no fixture is unmeasured, not proven safe.
