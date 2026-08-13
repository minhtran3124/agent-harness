# ste-terminology-evidence — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine signal — adds a rule file that enters agent context and edits two skill prompts; `skills/context-propagation-audit/SKILL.md` states workflow-engine changes are high-risk at intake and must not be lowered to bypass the delivery proof. No hooks, settings, or templates touched.
Flags: workflow-engine
Affects: rules/ (agent-loaded prose), CLAUDE.md rule-loading contract
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

check link https://claude.ai/share/367af290-6ee1-4a2a-b2db-4a6301ef1df4 và cho tôi biết suy nghĩ của bạn

check again link https://claude.ai/share/367af290-6ee1-4a2a-b2db-4a6301ef1df4

- fix dòng rule-loading trong CLAUDE.md
- clone file terminology.md về
- run testing với những trường hợp assume ở trên, lấy kết quả, đo metrics, reports + so sánh
- chạy nhiều lần để test vs những kết quả khác nhau
- tổng hợp và tạo decision documents theo kết quả đo dc

## What changed

`CLAUDE.md` now states the rule-loading *mechanism* (`paths:` present → contextual, absent →
always-on) instead of a hand-maintained list that had drifted and omitted `research-depth.md`.
`rules/terminology.md` is added as a path-scoped controlled-language rule, reconstructed from
the shared conversation's specification and then cut down to what a 76-trial A/B measurement
justified: §3 (machine-decidable acceptance criteria) required, §1 and §2 advisory.
`specs/ste-terminology-evidence/` holds the decision record and the reproducible experiment.
`skills/writing-plans/SKILL.md` and `skills/writing-plans/plan-document-reviewer-prompt.md` each
gain an explicit Read of the new rule, mirroring the `plan-format.md` Read already present in both
for the same reason — `paths:` does not fire on write. The reviewer also gains a `Decidable
Criteria` rubric row, and `tests/scripts/context-propagation-regression.test.sh` gains an assertion
plus a mutation case so removing either Read fails CI.

### Rationale

The proposal's central claim — that one-concept-one-word is load-bearing for LLM-executed
prose — was unmeasured, and `CLAUDE.md` "Gate verifiability" forbids shipping a gate whose
value proposition is unverified. Measurement reversed the priority: §1 showed zero effect
(40/40 both arms, two difficulty levels) while §3 showed a large one (1/8 vs 8/8, p=0.0014,
two models). So §3 is adopted, §1 is kept as readability guidance only, and the proposed
`scripts/lint_ste.py` + `PostToolUse` hook are not built.

### Alternatives considered

- Build `lint_ste.py` first as the shared conversation proposed — rejected: it would enforce
  §1/§2, the two sections with no measured or no reliable effect, and add a `PostToolUse` hook
  (block-tier `ci-strict-gate.sh` surface) for a gate proving nothing about behaviour.
- Put the terminology table in `CLAUDE.md` — rejected: +20% always-on context for a rule
  relevant to a minority of runs.
- Scope the rule via `paths:` to `skills/`/`agents/`/`rules/` as drafted — rejected on
  evidence: `paths:` fires on read and write-flows do not trigger it, so it could not have
  fired in the case it was designed for.

### Deviations

- Rule 1 (scope correction): the shared conversation's proposed fix for `research-depth.md`
  (add `paths:` frontmatter) was not applied — direct observation showed the file already
  auto-loads, and adding `paths:` would have removed it from the always-on set. Fixed the
  stale `CLAUDE.md` prose instead.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| full suite after CLAUDE.md edit | `bash scripts/run-tests.sh` | 0 | ALL GREEN; 569 pytest + shell tests | |
| experiment metrics reproduce | `python3 specs/ste-terminology-evidence/experiment/final.py` | 0 | H1 0/10 vs 4/10 p=0.0867; H2 1/8 vs 8/8 p=0.0014; H3 40/40 vs 40/40 | |
| rule-loading tiers as documented | `for f in .claude/rules/*.md; do head -1 "$f"; done` | 0 | 5 files without `paths:` (always-on), 3 with (contextual) — matches the corrected CLAUDE.md line | |
| context-propagation drift tests | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | 8 passed, including the new mutation case: deleting the reviewer's `terminology.md` Read is detected | |
| writing-plans delivery contract | `bash tests/scripts/writing-plans-contract.test.sh` | 0 | 3 passed; caught a real regression first — the added Read broke the literal ``Read `rules/plan-format.md` `` the test greps for, fixed by keeping it contiguous | |
| round-2 fixture traps are real | `grep -vc '^ok$' p.txt; sort -u q.txt \| wc -l; awk -F, 'NF!=3' s.csv \| wc -l` | 0 | 1 bad line, 499/500 distinct, 1 malformed row — reading cannot answer, only a command can | |

### Context-Propagation Audit

**Verdict: PASS after one repair.**

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `terminology.md` §3 | `skills/writing-plans/SKILL.md` (plan author) | main | explicit Read | `tests/scripts/context-propagation-regression.test.sh` (new assertion + mutation) |
| `terminology.md` §3 | `skills/writing-plans/plan-document-reviewer-prompt.md` | isolated plan reviewer | explicit Read — **added by this audit** | same test; mutation deleting the Read is detected |
| `terminology.md` §3 | `skills/subagent-driven-development/implementer-prompt.md` | implementer subagent | not delivered, and not needed | inspected call site: the prompt **pastes** task text (line 105 says so) and the report contract returns a `Verify` *result*; the implementer consumes a criterion, never authors one |
| `terminology.md` §3 | `skills/intent-review/intent-reviewer-prompt.md` | intent reviewer | deliberately **not** delivered | inspected: it pastes `### Intent` and `### Verify` verbatim and never Reads the SUMMARY file, so `paths:` cannot fire — hard exclusion #1 (never touch `### Intent`) holds by construction |
| `terminology.md` §3 | any context Reading `specs/**/PLAN.md` or `specs/**/SUMMARY.md` | reviewer / new session | `paths:`-triggered | frontmatter inspected; matches the `specs/**` glob shape used by all three existing contextual rules |
| `terminology.md` §3 | `SUMMARY.md ### Verify` authoring (`feature-intake`) | main | `paths:` read-side only | accepted without repair: those rows are already structurally constrained to `Command \| Exit` by `templates/SUMMARY.template.md` and `scripts/verify_summary.py`, so §3 adds only the Notes column |
| `CLAUDE.md` rule-loading line | every session | all | always-loaded | `for f in .claude/rules/*.md` frontmatter scan: 5 without `paths:`, 3 with — matches the corrected prose |

**Failed row and repair.** The isolated plan reviewer judges whether each `Verify:`/`Done:` field
is acceptable but could not receive §3: it inherits no path-scoped rule, and `paths:` fires on read
rather than on write. Repaired with an explicit Read (mirroring the `plan-format.md` Read already
there for the same reason) plus a `Decidable Criteria` rubric row, and anchored by a drift test with
a mutation case so deleting either Read fails CI.

### Not auto-verified

- `rules/terminology.md` and `specs/ste-terminology-evidence/*` are untracked, and
  `scripts/run-tests.sh:62` scopes its SUMMARY/PLAN lint to `git diff BASE...HEAD` — the
  committed diff. The ALL GREEN above therefore did **not** lint these new files — reached
  traceability; re-run the suite after the first commit
  (`docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md`).
- "`research-depth.md` auto-loads" — reached provenance from this session's startup context,
  a single observation; there is no regression test asserting the tier of each rule file.
- §3 of `rules/terminology.md` is enforced by **no gate**. It is prose that agents read —
  reached traceability (the file exists and is path-scoped); its effect on real `PLAN.md`
  authoring is not measured, only its effect on the synthetic H2 task is.
- The experiment's per-trial agent outputs are archived, not regenerable: re-running the
  agents draws fresh samples. `final.py` re-derives the statistics from the archived
  outcomes (truth tier for the arithmetic, not for the sampling).
- No `/context-propagation-audit` has run. Touching `rules/` raises the `workflow-engine`
  signal, which asks for that audit — required before this branch ships, not done here.

### Rollback

- `git checkout CLAUDE.md && rm -rf rules/terminology.md specs/ste-terminology-evidence/`
- after commit: `git revert <sha>`

### Harness-Delta

- backlog → `/compound`: two reusable learnings. (a) A wording/prose change proposal should be
  A/B-measured against filesystem ground truth before a gate is built for it; ceiling effects
  mean easy fixtures will always report "no difference" and must be hardened before a null is
  believed. (b) `paths:` frontmatter fires on read only, so any rule intended for a *write*
  flow needs an explicit Read step — a rule scoped to the directory it governs is a silent
  no-op for the authors of that directory.
