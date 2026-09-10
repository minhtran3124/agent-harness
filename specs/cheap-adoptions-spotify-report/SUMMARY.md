# cheap-adoptions-spotify-report — Summary

Lane: high-risk
Confidence: high
Reason: **Corrected from `normal` during review.** The original reasoning conflated two different things: a gate's block/warn mode governs commit-time blocking, not lane assignment. `harness-manifest.json`'s own `workflow-engine` entry says "intake still classifies it high-risk", and feature-intake Step 3 assigns high-risk for ANY manifest hard gate. Independently corroborated: `risk-corroboration.sh` blocked the review-fix commit with "Staged diff trips hard-gate categories: authorization ... But specs SUMMARY declares Lane: normal" — changing a skill's `allowed-tools` IS an authorization surface
Flags: existing-behavior, multi-domain, weak-proof
Affects: skill frontmatter contract (`allowed-tools`, `description`), agents/ validation surface, rules/behavior.md
Input-type: harness improvement
Route: normal — PLAN.md (4 items, >2 files) → direct execution on this branch
Escalate: no — no hard gate in block mode; the one ambiguous item (#2) was narrowed to a pilot before work started

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- verbatim -->

> lam 4 viec re tu bao cao di

The four items, as ranked in `docs/research/2026-09-09-spotify-portal-ai-plugins.md` §7 and
re-verified on disk before any edit (per `docs/solutions/harness/gap-closure-decisions.md`, which
records that most "gaps" named by a research doc turn out already shipped):

| # | Item | Verified still open |
|---|---|---|
| 1 | Fix `claude plugin validate --strict .`, add to CI | ✅ fails on 3 files in `agents/`; `grep -c 'plugin validate' harness-ci.yml` = 0 |
| 8 | "Run `--help` before relying on a flag" rule | ✅ no `--help` rule anywhere in `rules/*.md` |
| 9 | Extend `allowed-tools` to the skills lacking it | ✅ 3 of 12 have it (feature-intake, visual-planner, xia2); 9 lack it |
| 2 | Rewrite `description:` in user vocabulary | ✅ still mechanism-voiced — scoped to a 3-skill pilot |

## What changed

Four adoptions from the Spotify comparison. Item #1 was **rescoped after investigation** — the
report's proposed fix was wrong; the rest landed as specified, with #2 deliberately a pilot.

| # | Delivered |
|---|---|
| 1 | `scripts/check-plugin-validate.sh` — fails on any validator error, and on any warning outside a justified 3-file allowlist. Wired into `run-tests.sh` L1. **Not** the report's fix (see Deviations). |
| 8 | `rules/behavior.md` §3 — confirm a command's interface before depending on it. |
| 9 | `allowed-tools` on the 9 skills lacking it (12/12 now), each list derived from that skill's own body; `scripts/check-allowed-tools.sh` ratchet wired into L1. |
| 2 | `description:` rewritten for `brainstorming`, `xia2` (mutual anti-triggers) and `correctness-review` (control, voice only). The other 9 are out of scope. |

### Rationale

All four are adoptions from the Spotify comparison, chosen because they are independent of the
plugin-packaging decision (report item #3), which is an escalation. Items 1, 8 and 9 are mechanical
and carry no eval cost. Item 2 is **not** cheap in its full form and is deliberately not done in
full here: rewriting all 12 `description:` fields invalidates the 192-case activation baseline in
`evals/skills/prompt-refactor/activation/`, and `scripts/score_skill_eval.py` enforces
non-regression against it, so the honest cost is a manual re-run of 192 LLM dispatches. The report
itself recommends a 3-skill pilot first; that is what this does.

### Alternatives considered

- **Do all 12 descriptions now** — rejected: perturbs the eval baseline every other skill change is
  measured against, for a change whose benefit is unproven. The pilot exists to produce that proof.
- **Four separate PRs** — rejected: items 1, 8, 9 touch disjoint files and share one review; the
  overhead of four intake/plan/review cycles exceeds the change itself.
- **Skip `allowed-tools` on review skills** — considered, then rejected: the reviewer skills are
  exactly where an over-broad tool grant matters most.

### Deviations

- **Item #1 rescoped — the report's fix would have made things worse.** It proposed adding
  frontmatter to `agents/README.md`, `agents/PROJECT.md`, `agents/PROJECT.template.md` so
  `claude plugin validate --strict .` passes. The validator classifies every `*.md` under `agents/`
  as an agent, so frontmatter would **register those three as dispatchable agents** — Claude Code
  ignores them today precisely because they lack it (they are absent from the available-agent
  list). The report's alternative, moving them, is also not free: `agents/PROJECT.md` is in
  `deploy-harness.sh`'s `BOOTSTRAP_OWNED_FILES` and is referenced by path from `agents/coding.md`
  and `agents/test-runner.md`. Delivered a checker with a justified allowlist instead. Caught by
  reading the files before editing them, per `docs/solutions/harness/gap-closure-decisions.md`.
- **Rule 2 (missing prerequisite, auto-added):** SC-2 named `scripts/check-allowed-tools.sh`, which
  did not exist. Written and wired into `run-tests.sh` L1.
- **Rule 1 (auto-fix):** the first draft of `rules/behavior.md` §3 cited `skills/setup/SKILL.md` —
  a path in the *Spotify* repo, not this one. `scripts/lint-doc-truth.sh` blocked the suite and
  named it ("does not exist in a consuming repo"). Reworded to name the external repo explicitly.
  The gate caught a doc defect in the very rule about not trusting recalled paths.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Plugin validator gate | `bash scripts/check-plugin-validate.sh` | 0 | Proven to bite: removing `description:` from a SKILL.md in a temp copy exits 1 and names that skill | SC-1 |
| Every skill declares allowed-tools | `bash scripts/check-allowed-tools.sh` | 0 | 12/12; proven to bite when the field is removed in a temp copy | SC-2 |
| scope-gate contract suite | `bash tests/hooks/scope-gate.test.sh` | 0 | 11 passed; representative hook suite unaffected by the frontmatter changes | SC-3 |
| Doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | Blocked the first draft of the §3 rule for citing a Spotify path; passes after rewording | |
| Skill prompt audit | `python3 scripts/audit_skill_prompts.py` | 0 | Frontmatter parses on all 12 after the edits | |

Full suite, cited not tabled: `bash scripts/run-tests.sh` -> `ALL GREEN`. Not a row — at ~3.5
minutes it exceeds the strict gate's 60s per-command cap
(`docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`).

### Not auto-verified

- **No `allowed-tools` list is verified to be CORRECT — only present.** I measured this rather than
  assumed it: putting `TotallyBogusTool` into a skill's `allowed-tools` in a temp copy made
  `claude plugin validate --strict --json` report **nothing**. So the validator does not check tool
  names, no test exercises a skill under its declared list, and an under-granted skill would fail
  only at runtime, in the middle of a real task. Reached **traceability**; the 9 new lists are my
  reading of each skill's body, not a measured result. This is the largest risk in the change.
- **The plugin-validate gate is local-only today.** GitHub runners do not ship the `claude` CLI, so
  the check skips there — with a named reason, never silently. Its CI value is zero until a runner
  has the CLI. Reached **truth** locally, **not observed** in CI.
- **The 3 rewritten descriptions are unmeasured.** The whole point of item #2 was to improve
  activation, and nothing here demonstrates that it did. The 192-case corpus in
  `evals/skills/prompt-refactor/activation/` is the instrument, and it was deliberately not re-run:
  the pilot exists to decide whether a full re-baseline is worth paying for. Reached
  **traceability** (the text changed); the claim that it routes better is **unmeasured**.
- **The anti-trigger pair is asserted, not tested.** `brainstorming` and `xia2` now each name the
  other as a non-trigger. Whether the model actually respects that is exactly what the unrun corpus
  would measure.

### Rollback

- `git revert <sha>` — single branch, docs/frontmatter/CI only; no migration, no external state.

### Harness-Delta

- **fix-direct:** none of the four items needed a workflow change.
- **backlog (-> compound):** the report's item #1 was wrong in a way worth recording — a research
  doc read a validator's failure as a defect in the repo, when the validator was mis-classifying
  three files. *A tool reporting a failure is evidence about the tool's model of your repo, not
  only about your repo.* The generic version already exists as
  `docs/solutions/harness/gap-closure-decisions.md` ("verify each named gap on disk first"), and
  this run is its second confirmation in two days — the entry may warrant a `confirmed_at` bump
  rather than a new record.
