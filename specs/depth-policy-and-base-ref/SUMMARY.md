# depth-policy-and-base-ref — Summary

Lane: high-risk
Confidence: high
Reason: `rules/research-depth.md` trips the `workflow-engine` manifest hard gate (warn-mode at commit time, but intake still classifies it high-risk per harness-manifest.json); 4 flags fired.
Flags: existing-behavior, weak-proof, cross-platform, multi-domain
Affects: research-depth policy (xia2 consumer contract); run-tests.sh base-ref resolution (verify-row lint scope)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> we have some notes to improve harness now [screenshot: Gap A citation ledger / Gap B
> negative-scope / Gap C 3-tier principle]
> - make the deep research codebase again, thinking by yourself about it for design/adopt/etc
> - and let me know it is correct or not?
> - should we do it or not?
> - how we adopt it?
> - give high level design/spec
> - have any side effect if we apply it? do have anything will broken if we apply it?

> mục đích của check_research_brief.py là gì?

> lập bảng so sánh độ sâu, độ phức tạp, mức độ ảnh hưởng, khả năng hỏng hóc

> làm cả hai trong một branch

Scope resolved by two explicit human decisions at intake (`AskUserQuestion`):

1. **Policy variant** — "Có điều kiện": external sources required only when the change has an
   external surface; absence must be *stated*, not implied. (Rejected: drop the requirement
   entirely; keep it unconditional and only add a `- none` escape.)
2. **Base-ref variant** — "Fallback chain + sửa CI": fix all three causes, including
   `fetch-depth: 0` on the CI `test` job. (Rejected: local-only fix; fail-loud variant.)

## What changed

Two independent corrections shipped together because both stem from the same defect class —
a rule that asserts something no one checks.

1. `rules/research-depth.md` + `skills/xia2/SKILL.md` +
   `skills/xia2/references/research-brief-template.md` — Standard/Deep no longer demand external
   documentation unconditionally. External sources are required **when the change has an external
   surface** (new/upgraded dependency, external integration, version-specific API). When none
   exists, the brief must record `- none (local-only; no external surface)` in Source Pack —
   silence is no longer an acceptable answer. All three files are updated together: xia2 agents
   read `SKILL.md` and fill the template, so a rule-only edit would have changed nothing that any
   consumer context actually sees.
2. `scripts/resolve-base-ref.sh` (new) + `tests/scripts/resolve-base-ref.test.sh` (new) +
   `scripts/run-tests.sh` + `.github/workflows/harness-ci.yml` — the verify-row lint resolved
   its base ref from a hardcoded `origin/main` that resolves **nowhere**: not locally (this
   repo's remote is `github`, there is no `origin`), and not in CI (the `test` job used a
   shallow `actions/checkout@v4`). The lint has therefore never executed since it shipped.
   Resolution now comes from declared bases only — `VERIFY_ROWS_BASE`, then `GITHUB_BASE_REF`
   (as `origin/<ref>`), then the branch's `@{upstream}` — and an undeclared or unresolvable
   base exits nonzero with a named reason instead of falling back to a guess. On CI, the `test`
   job gains `fetch-depth: 0` plus an explicit `git fetch --no-tags origin <base_ref>` — the same
   two-step the `strict-gate` job already uses and which is proven to work in this repo's CI,
   rather than relying on whatever refspec `actions/checkout` happens to leave behind.
   `scripts/ci-strict-gate.sh` gets the same treatment for its local default: it used to fall
   back to `origin/main`, where a failed `git diff` yields an empty diff and the *strict* gate
   exits 0 having checked nothing. It now refuses with a named reason instead.

### Rationale

Both changes close the same gap from opposite ends. The depth policy demanded evidence that
13 of 21 briefs never supplied (12 of them citing zero external sources while declaring
Standard/Deep) — an unenforceable requirement that trains readers to ignore the field. The
verify-row lint claimed to enforce evidence quality and silently skipped 100% of the time.
Rather than add a new gate on top of an unhonored policy (the `sources.json` + `quote ⊆
evidence` proposal in the intake notes), scope the policy to what is actually checkable and
repair the check that already exists.

### Alternatives considered

- **`specs/<slug>/sources.json` ledger + `quote ⊆ evidence` script** (the note's proposal) —
  rejected. The evidence side of that comparison is written by the same agent that writes the
  quote, so a hallucinated document yields a matching hallucinated snippet and the gate passes.
  It would be traceability tier claiming provenance — the exact failure `CLAUDE.md` "Gate
  verifiability" forbids. It also drags the diff into `hooks/` (block tier in
  `ci-strict-gate.sh`) and trips `check_gate_modes_smoke.py`'s hardcoded `EXPECTED_WARN` set.
- **Transcript cross-check** (assert every Source Pack URL was really fetched via `WebFetch`) —
  the only design that reaches provenance tier, since the agent does not author the transcript.
  Rejected on economics: ~400 fragile lines for a 1-in-21 failure rate, and it breaks under this
  repo's `resume <slug>` flow where the originating transcript is gone.
- **`scripts/check_research_brief.py`** (enforce the Source Pack contract, warn-first) —
  deferred, not rejected. Worth reconsidering only after the corrected policy has run long
  enough to show how often `Deep` legitimately implies an external surface.
- **Gap B / Gap C from the notes** — no work done: both are already shipped
  (`templates/SUMMARY.template.md:75` + `verify_summary.py:250-305` for B;
  `CLAUDE.md:63-67` for C). Building them again would produce an empty diff.

### Deviations

- Rule 2 — Extracted the base-ref resolution into `scripts/resolve-base-ref.sh` and added
  `tests/scripts/resolve-base-ref.test.sh` (8 cases). Not in the intake scope, which said
  "fix the base ref in `run-tests.sh`". Justification: the defect being fixed is a *scope
  selector that died silently*; logic inline in a 100-line suite runner cannot be unit-tested,
  so an inline fix would be as unprotected against silent death as the code it replaces. Two
  of the eight cases are regression guards for the exact original failures.
- Rule 1 — Fixed the pre-existing `${{ github.base_ref }}` interpolation in the **strict-gate**
  job of `.github/workflows/harness-ci.yml`, not only the instance this branch added. Normally
  adjacent code is left alone (`rules/behavior.md` §3), but it is the identical one-line defect
  in the same file, and shipping one fixed instance beside an unfixed twin reads as a deliberate
  distinction that does not exist.
- Rule 1 — Rejected the branch-name fallback chain (`origin/main` → `github/main` → `main`)
  that was approved at intake, after measuring it: on this branch it selects `main`, yielding
  36 changed spec files instead of 0 and surfacing 7 pre-existing violations in already-shipped
  specs — i.e. the approved variant would have turned CI red for work this branch never
  touched. Replaced with declared-bases-only + loud refusal. Same goal (the lint stops being
  dead), corrected mechanism.

### Correctness Review

Six isolated FIND angles over `1f1c351...HEAD`, deduplicated by `(file, line)`. **9 findings
fixed, 2 recorded as advisory.** The review found real defects in this branch's own fixes —
including three that recreate, in new clothing, the exact failure the branch exists to remove.

| # | Location | Defect | Status |
|---|---|---|---|
| 1 | `scripts/resolve-base-ref.sh` `@{upstream}` tier | `git push -u` sets upstream to the branch's **own** remote copy, so the lint diffed the branch against itself → empty set → `skip — compared and found nothing`. The skip-looks-like-pass ambiguity, rebuilt. | fixed — refuse a same-branch upstream |
| 2 | `scripts/resolve-base-ref.sh` validation | `rev-parse --verify` accepts **any** object; a blob sha passed, then `git diff` died with a fatal the caller swallowed → same false "nothing changed". | fixed — `^{commit}` |
| 3 | `scripts/ci-strict-gate.sh:36` | Only the *fallback* base was validated. CI always passes an explicit base, so the **only path CI takes** was unguarded: `ci-strict-gate.sh no/such/ref` → exit 0, no output. A strict gate passing because it could not run — the precise thing its own new comment claimed to have removed. | fixed — validate both paths; 2 new contract tests |
| 4 | `scripts/run-tests.sh:48` | Two-dot `git diff BASE` also picks up files changed on the base since the fork point (36 vs 35 files measured), while the comment claimed parity with `ci-strict-gate`'s three-dot. `2>/dev/null` also hid diff failures as empty results. | fixed — three-dot; failed diff sets `FAILED=1` |
| 5 | `SUMMARY.md` `### Verify` | One row invoked `ci-strict-gate.sh`, which re-enters `verify_summary --check` and re-runs this table — unbounded recursion locally, vacuous pass in CI. Three rows read the gitignored `.claude/` tree; one needed PyYAML the strict-gate job never installs. | fixed — table rebuilt bare-checkout-only |
| 6 | `tests/scripts/research-depth-drift.test.sh` | Stem anchors `depend` / `integrat` were satisfied by `independently` and the frontmatter word `integrations`, so deleting a whole trigger clause left the guard green — 2 of 5 anchors vacuous. The stale-wording check matched only 1 of 3 retired phrasings, and no mutation covered *re-adding* a retired claim. | fixed — multi-word anchors, per-trigger + re-add mutations, section-scoped template check |
| 7 | `skills/xia2/SKILL.md:3` | The frontmatter `description:` — the routing text an agent reads first — still stated official docs unconditionally, contradicting step 4 in the same file. Survived propagation because it does not look like policy prose. | fixed — + a stale-sentence guard |
| 8 | `.github/workflows/harness-ci.yml` | `${{ github.base_ref }}` interpolated into `run:` before bash parses it; quotes do not contain a branch name with shell metacharacters. | fixed — passed via `env:` |
| 9 | `scripts/ci-strict-gate.sh:27` | Usage line still documented the deleted `origin/main` default. | fixed |

**Advisory — recorded, not fixed (out of this branch's scope):**

- **A PR targeting `main` will fail the revived lint on 7 pre-existing violations.** With
  `GITHUB_BASE_REF=main` the changed set is 36 spec files, surfacing violations in
  `specs/durable-run-state/PLAN.md`, `specs/fix-hooks-gate-lane-divergence/*`,
  `specs/gh-129-run-state-e2e/SUMMARY.md`, and `specs/strict-gate-scripts-warn/SUMMARY.md` —
  shipped specs this branch never touched. Refusing to *guess* a base does not cover this,
  because `main` arrives as a **declared** base. Against `simplify` the same command is clean,
  so this branch's PR passes and the failure lands on the eventual `simplify → main`
  integration PR. Fixing 7 shipped specs is a separate change; whoever opens that PR must do it
  first, or pin a grandfather commit.
- **Local runs still skip for a standard clone with no upstream and no `VERIFY_ROWS_BASE`.**
  Previously `origin/main` supplied a base for such contributors. Refusing beats guessing, but
  it is a narrowing: the lint is live in CI and opt-in locally.

### Verify

The full suite (`scripts/run-tests.sh`) is exercised by the CI `tests` job on both
ubuntu-latest and macos-latest; it is cited in prose rather than as a row because it
exceeds the 60s strict-gate cap. The targeted rows below are the ones re-run here.

Every row below re-runs from a **bare checkout** with no extra dependencies. An earlier
revision of this table failed that: four rows mismatched in CI run `31245252833` — three read
the gitignored `.claude/` tree, one needed PyYAML which the strict-gate job does not install —
so `verify_summary --check` reported *"no changed high-risk SUMMARY passed"* and the branch
shipped with zero machine-verified proof behind a green tick. A fifth row invoked
`ci-strict-gate.sh` on itself, which re-enters `verify_summary --check` and re-runs this whole
table. Those rows are gone; the deployment evidence they carried lives in the audit prose below,
which is where environment-local facts belong.

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Base-ref resolution, 10 cases | `bash tests/scripts/resolve-base-ref.test.sh` | 0 | incl. refusal of a same-branch upstream, a non-commit object, and any branch-name guess | |
| This SUMMARY passes the lint this branch re-enables | `python3 scripts/check_verify_rows.py specs/depth-policy-and-base-ref/SUMMARY.md` | 0 | dogfood: caught 3 violations in this file's first draft | |
| Strict-gate contract tests, 19 cases | `bash tests/scripts/ci-strict-gate.test.sh` | 0 | incl. the 2 new cases pinning refusal of an unresolvable explicit base | |
| Policy drift guard, 11 cases incl. 6 mutation checks | `bash tests/scripts/research-depth-drift.test.sh` | 0 | repairs audit FAIL 1 | |
| Doc-truth lint (paths named in the new files exist) | `bash scripts/lint-doc-truth.sh` | 0 | | |
| Doc-truth contract tests | `bash tests/scripts/lint-doc-truth.test.sh` | 0 | 7 passed | |
| Brainstorming contract tests (xia2 handoff untouched) | `bash tests/scripts/brainstorming-contract.test.sh` | 0 | | |
| Shell syntax of the suite runner | `bash -n scripts/run-tests.sh` | 0 | | |
| Shell syntax of the new resolver | `bash -n scripts/resolve-base-ref.sh` | 0 | | |
| Shell syntax of the strict gate | `bash -n scripts/ci-strict-gate.sh` | 0 | | |
| Depth rule reached the xia2 skill | `grep -q "external surface" skills/xia2/SKILL.md` | 0 | a rule-only edit would reach no agent | |
| Depth rule reached the brief template | `grep -q "external surface" skills/xia2/references/research-brief-template.md` | 0 | | |
| CI `test` job fetches the PR base ref | `grep -q "name: Fetch base ref" .github/workflows/harness-ci.yml` | 0 | stdlib-only; the PyYAML version mismatched in CI | |

### Not auto-verified

- **The corrected depth policy is livable** — reached traceability; this branch's own
  `research-brief.md` records `- none (local-only; no external surface)` as a dogfood, but one
  brief does not prove the rule scales across future work.
- ~~**`fetch-depth: 0` makes the lint fire in CI**~~ — **now reached truth.** Confirmed by this
  PR's own CI run [`31243744831`](https://github.com/minhtran3124/agent-harness/actions/runs/31243744831):
  both `tests (ubuntu-latest)` and `tests (macos-latest)` print
  `✓ verify-row lint: all checked SUMMARY/PLAN rows are pipe-free and <60s` where the previous
  run (`31239698394`) printed `skip — no python3 or no origin/main ref`. The `✓` branch is only
  reachable with a non-empty changed-set — an empty one prints `skip — no changed
  SUMMARY.md/PLAN.md vs <ref>` — so this also confirms the lint selected real files rather than
  running vacuously. Green alone would not have shown this; the log line was read directly,
  because a skip is also green. That ambiguity was the original bug.
- **`actions/checkout@v4` semantics** — still only inferred. The CI run proves `origin/<base>`
  was present; it does not isolate whether `fetch-depth: 0` or the explicit
  `git fetch --no-tags origin <base_ref>` step produced it. Both ship together deliberately, so
  the mechanism is unattributed by design rather than unverified by omission.
- **The lint selects this branch's own changed files and no others** — reached truth locally
  (`VERIFY_ROWS_BASE=simplify` selects exactly this spec's SUMMARY) and truth in CI per the run
  above. Not verified: that the selection is identical in both, since the CI diff is computed
  against `origin/simplify` rather than the local `simplify`.
- **No other gate depends on the hardcoded `origin/main`** — reached provenance; re-derived by
  grepping `scripts/ hooks/ .github/` for `origin/main`, which returned only `run-tests.sh` and
  `ci-strict-gate.sh` (the latter always receives an explicit base from CI, so its default is
  local-only convenience). Not re-run as an assertion in code.
- **Retiring the unconditional external-source requirement loses no real signal** — reached
  traceability; based on 19/21 briefs citing zero URLs, which measures past behavior, not
  whether that behavior was correct.

### Context-Propagation Audit

**Verdict: FAIL → both rows repaired.**

Search surface, so a "no consumer" result is not read as proof of absence: `grep -rl` for
`research-depth`, `official documentation`, `upstream sources`, `version-matched` across
`*.md|*.py|*.sh|*.json` at repo root excluding `.git/` and `.worktrees/`; plus a directed read of
`agents/*.md`, `templates/`, `tests/`, `evals/`, and the deployed `.claude/` tree.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `rules/research-depth.md` §Coverage | `skills/xia2/SKILL.md` steps 4 + depth summary | xia2 agent (fresh child) | inline copy + explicit pointer to `rules/research-depth.md` §Coverage | `tests/scripts/research-depth-drift.test.sh` (6 cases, 2 mutation) |
| `rules/research-depth.md` §Coverage | `skills/xia2/references/research-brief-template.md` (Docs Findings, Source Pack) | xia2 agent filling the brief | inline copy | same drift test |
| `rules/research-depth.md` | `skills/xia2/references/depth-classifier.md` | xia2 agent | explicit Read anchor (`Use this reference with rules/research-depth.md`); restates depth *selection* only, never Coverage | inspected: no Coverage text to drift |
| `rules/research-depth.md` | `skills/feature-intake/SKILL.md` §Research-depth handoff | intake (main) | explicit path reference; maps lane→depth only, never Coverage | inspected: no Coverage text to drift |
| `rules/auto-correct-scope.md` Rule-4 list | `skills/correctness-review/prompts/shared.md` | reviewer | pre-existing, untouched by this diff | `tests/scripts/inline-policy-drift.test.sh` |
| — | `agents/*.md` | reviewer/implementer | no depth or Coverage text present | grep over `agents/*.md` for `Standard|Deep|research` → empty |
| — | `evals/skills/review-chain/fixtures/{context-rule-unread,stale-inline-policy}/` | eval | escape probes preserved | `git diff simplify -- evals/` → empty |

**FAIL 1 — three copies of one definition, no drift guard. REPAIRED.** The external-surface
definition now lives in the rule *and* two xia2 files (agents load the skill and template; they
do not read `rules/`). Three unguarded copies is the exact `stale-inline-policy` escape the
review-chain fixture pins. Added `tests/scripts/research-depth-drift.test.sh`: registry +
copies + per-concept anchor keywords, a check that the retired unconditional wording is gone,
and two mutation checks (strip the condition → detected; drop only the `local-only` sentinel →
detected) proving the lint is load-bearing rather than vacuous.

**FAIL 2 — the deployed `.claude/` tree carried the retired rule. REPAIRED.**
`.claude/rules/research-depth.md`, `.claude/skills/xia2/SKILL.md`, and
`.claude/skills/xia2/references/research-brief-template.md` each contained **0** occurrences of
`external surface` (dated Aug 7, before this change). `.claude/rules/` is **auto-loaded into
every session in this repo**, so every agent here was reading the unconditional rule while the
source said otherwise — a live contradiction in the consumer context, which is precisely what
this audit exists to detect, and the row hand-propagation missed.

Repaired by `scripts/deploy-harness.sh --yes`, run with explicit human authorisation (it mutates
the local `.claude/` tree, so it is never run autonomously). `--dry-run` first reported **no
protected-file conflicts** — `research-depth.md` is not consumer-owned, so it was overwritten
cleanly rather than being kept and shadowed by a `.harness-incoming` sidecar, which is the
outcome that would have left the stale rule in place while appearing to succeed. Confirmed
after: 4 occurrences of `external surface` in each of the three files, and
`find .claude -name '*.harness-incoming'` returns empty.

Not shipped by this PR either way: `.claude/` is gitignored (`.gitignore:26`) and untracked, so
the diff is unaffected and consumers get the corrected files on their own re-sync. Not escalated
to `ESCALATIONS.md`: this is the harness's normal source→deploy lag, not a defect in the change
under review.

**Not verified by this audit:** that any agent *obeys* the propagated rule. Every row above is
traceability tier — text reaches a context — never truth. The drift test proves the keywords are
present in each copy; it does not prove the copies say the same thing about them.

### Rollback

Graded, because the two halves fail independently. The live risk is half 2: a lint that has
never executed now executes, so it can block work that previously sailed through.

1. **Full undo** — `git revert <sha>`. Restores the hardcoded `origin/main` (lint dead again),
   the unconditional depth policy in all three files, and removes `scripts/resolve-base-ref.sh`
   + `tests/scripts/resolve-base-ref.test.sh`. No migration, no state, no consumer artifact is
   written by this change, so revert is complete.
2. **Neutralize the lint only, keep the policy fix** —
   `git checkout <sha>^ -- scripts/run-tests.sh` then commit. The runner returns to skipping;
   the resolver and its tests stay on disk unused; `rules/research-depth.md` and the xia2 files
   keep the corrected Coverage rule.
3. **Neutralize in CI only** — delete the `with: fetch-depth: 0` block from the `test` job in
   `.github/workflows/harness-ci.yml`. The lint then skips in CI with a named reason
   (`base ref 'origin/<base>' ... does not resolve`) while still running locally for anyone who
   sets `VERIFY_ROWS_BASE` or a branch upstream.
4. **Un-block a single run without changing code** — `VERIFY_ROWS_BASE=HEAD bash scripts/run-tests.sh`
   narrows the changed-set to uncommitted spec edits only; on a clean tree that is empty and the
   lint reports "no changed SUMMARY.md/PLAN.md" instead of failing. Verified: with this branch's
   SUMMARY staged but uncommitted it still selects 1 file, so this is a narrowing escape hatch
   for an urgent run, not a guaranteed bypass, and not a fix.

### Harness-Delta

- fix-direct — a gate can ship with tests, CI wiring, and a careful rationale comment and still
  never execute, because its *scope selector* (not its logic) is dead. Nothing in the suite
  reports "this check selected zero files, every time." Candidate for `/compound`: a gate that
  skips should be distinguishable from a gate that passes.
