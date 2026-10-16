# gh-308-deletion-test-ceiling — Design

Written 2026-10-16. Pins: repo 03e3555

## Goal

Give the 600-word skill ceiling a stated procedure that cannot drop a condition, and use it once to
free room in the three skills at or near the ceiling, so later roadmap items (#310, #312, #313,
#318) can add sentences safely.

## Current state

- `scripts/audit_skill_prompts.py` sets `SKILL_WORD_CEILING = 600` and, over it, reports only
  `skill exceeds 600-word progressive-disclosure ceiling: skills/<name>/SKILL.md (<count>)`. A
  skill with an `UPSTREAM.md` is exempt.
- Two recorded trims lost conditions with all tests green:
  `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md` (feature-intake Step 1 and Step 6).
- The guardrails that entry proposed already shipped on 2026-10-15 (commits up to `23438c1`):
  `scripts/check_scope_qualifiers.py` lists dropped condition words per hunk;
  `skills/subagent-driven-development/scripts/review_package.py` emits it as `## Scope qualifiers`;
  `task-reviewer-prompt.md` runs a meaning check on every changed `.md` under `skills/`, `rules/`,
  `agents/` and must resolve each listed word as "kept" with a cited HEAD line or as an Important
  finding. The two matching rows in `docs/harness-experimental/improvement-backlog.md` still read
  `open`.
- `scripts/test_check_scope_qualifiers.py` replays both recorded drops, but the script catches only
  one. `test_pilot_step6_cut_is_listed` shows the Step 6 word cut is listed.
  `test_pilot_step1_split_is_not_listed_known_limit` shows the Step 1 split is **not** listed: a
  split that keeps the condition word but moves later sentences out of its scope is a documented
  blind spot (`scripts/check_scope_qualifiers.py` docstring). Only the reviewer's free-form meaning
  check covers it.
- Word counts (measured 2026-10-16 `wc -w`): `session-retro` 600, `feature-intake` 598,
  `finishing-a-development-branch` 589. `session-retro` has no `references/` folder; the other two
  do.
- `skills/asd-ste100/` is a vendored upstream copy. `UPSTREAM.md` lists exactly three allowed
  differences and states there are no others. It is exempt from the ceiling.
- Four shell tests pin literal strings in the three skills:
  `tests/scripts/finishing-branch-contract.test.sh`,
  `tests/scripts/context-propagation-regression.test.sh`, `tests/scripts/consumer-subset.test.sh`,
  `tests/scripts/deploy-worktree-isolation.test.sh`.
- `scripts/check_ste_baseline.py` lints `skills/*/*.md` and `skills/*/*/*.md`, so it covers new
  `references/` files too. `scripts/ste-baseline.json` holds hard counts for the three SKILL.md files
  (`session-retro` 2, `feature-intake` 2, `finishing-a-development-branch` 0). From
  `scripts/run-tests.sh` it warns only.
- Python tests run through the shared venv that `tests/lib.sh` `ensure_pyenv` builds
  (`/tmp/harness-tests-venv/bin/python -m pytest`); the system `python3` has no pytest.

## Approaches considered

Where the canonical procedure lives (user chose A):

- **A — harness-owned reference, audit message points to it (chosen).** A `docs/solutions/` knowledge
  entry holds the full procedure; the audit message carries a two-line summary and the path.
  Upstream untouched; other skills and reviews can link to it.
- B — procedure only in the audit message. Smallest change, but the message grows and nothing can
  link to it.
- C — edit `asd-ste100` and record a fourth upstream difference. Keeps the issue's literal step 2
  but adds re-vendor work on every upstream change.

How to prove no condition was lost (user chose A):

- **A — existing machinery (chosen).** Scope-qualifier section resolved per file, reviewer
  `meaning: pass`, existing canary tests, audit counts, the four shell tests.
- B — A plus a new blind task-review eval fixture recorded beside the A/B in `rules/terminology.md`.
  Rejected: that file records controlled-language experiments, and it adds a workflow-engine file.

## Architecture

1. **Reference (new):** `docs/solutions/harness/deletion-test-for-word-ceiling.md`, with
   `problem_type: knowledge` (body sections Pattern and How_to_Use) and KB front-matter per
   `docs/solutions/README.md`. Content: the procedure; the condition-word list (if, unless, only,
   when, never, except, for a new, without), stated as the same list
   `scripts/check_scope_qualifiers.py` uses; the disclosure fallback; the "kept long on purpose"
   exit; the split-scope warning (when a sentence moves, any condition it depended on moves or is
   repeated with it); a link to `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`.
   `docs/solutions/INDEX.md` is rebuilt with `scripts/rebuild_solution_index.py`, never
   hand-edited.
2. **Procedure (as written in the reference):**
   1. List each sentence of the skill.
   2. Deletion test: delete a whole sentence when the model already does it by default, or when it
      restates a file the skill already points to.
   3. Disclosure: move a whole block that only some branches reach into the skill's `references/`,
      leaving a one-line pointer in the skill.
   4. Never shorten a sentence that holds a condition word. Keep it whole or move it whole. When a
      moved or deleted sentence sits under a leading condition ("If X, run these checks."), keep
      that condition in scope for every sentence that still depends on it.
   5. If the skill is still over budget, stop, keep the remaining sentences, and list them as
      "kept long on purpose" in the spec's SUMMARY.
3. **Audit message:** `scripts/audit_skill_prompts.py` appends to the existing over-ceiling problem
   string a two-line hint naming steps 2–4 and the reference path. The count, the ceiling and the
   vendored exemption do not change.
4. **Trims:** one task per skill, each to at most 540 words (budget). Moved material goes to that
   skill's `references/` (created for `session-retro`). Before deleting a line, grep it against the
   four shell tests. STE baseline, per trim, in this order:
   1. Ratchet guard: the skill's hard count at HEAD, summed over its `SKILL.md` and every file in
      its `references/`, is no higher than its summed hard count at the task base. Measure both
      sides with `skills/asd-ste100/scripts/ste-lint.py --json --disable synonym-rotation`, the
      same flags `review_package.py` uses.
   2. Only then run `python3 scripts/check_ste_baseline.py --update`, and keep from the rewritten
      `scripts/ste-baseline.json` only the entries for that skill's own files. Any other entry the
      update changed is reverted, so the update cannot absorb an unrelated regression.
5. **Backlog:** the two 2026-10-15 `ste-rewrite-drops-scope-qualifiers` rows in
   `docs/harness-experimental/improvement-backlog.md` (lines 24–25 at `03e3555`) change to `done`
   with commit `23438c1` noted.

Data flow at review time is unchanged: each trim task's diff passes through `review_package.py`,
whose `## Scope qualifiers` section feeds the task reviewer's meaning check.

## Error behavior

- A skill that cannot reach 540 words without shortening a condition sentence stops at its lowest
  safe count. The kept sentences are listed in SUMMARY as "kept long on purpose". The task is still
  done if the count dropped and no condition was lost; the shortfall is recorded, not hidden.
- A shell test that pins a sentence chosen for deletion: keep the sentence, or update the test and
  record why under `### Deviations`.
- `scope-qualifiers: unavailable` in a review package: the reviewer compares without it (existing
  behavior); the task's own Verify row re-runs `check_scope_qualifiers.py` directly so the proof
  does not depend on the package.

## Tests

- Truth tier: `scripts/audit_skill_prompts.py` re-run shows each of the three skills at ≤540 words.
- Truth tier: `check_scope_qualifiers.py --base <task base> --head <task head>` re-run per trim;
  every listed word is resolved "kept" with a cited line in the task review.
- Truth tier: existing pytest files (`test_check_scope_qualifiers.py`, `test_audit_skill_prompts.py`,
  `test_review_package.py`) through the shared venv, plus a new assertion in
  `test_audit_skill_prompts.py` that the over-ceiling message names the reference path.
- Truth tier: the four shell tests that pin these skills.
- Provenance tier: `grep` of `docs/harness-experimental/improvement-backlog.md` shows both
  `ste-rewrite-drops-scope-qualifiers` rows ending in `| done |` (SC-6).
- Truth tier: the per-skill ratchet guard re-run (SC-7). The base side is read without a checkout:
  `git show <base>:<path> | python3 skills/asd-ste100/scripts/ste-lint.py --json --disable
  synonym-rotation`, summed over the files that exist at the base. `session-retro` has no
  `references/` at the base, so its base sum is its `SKILL.md` count alone. Plus
  `git diff <base> -- scripts/ste-baseline.json` showing only entries under the three skills.
- Provenance tier: the task reviewer's `meaning: pass` per file (a model judgement on re-derived
  diff evidence, not a re-run behavior).

## Success criteria

- SC-1: the over-ceiling message names `docs/solutions/harness/deletion-test-for-word-ceiling.md`
  and the steps; a pytest asserts it.
- SC-2: the reference exists with valid KB front-matter and appears in the rebuilt `INDEX.md`.
- SC-3: `session-retro`, `feature-intake`, `finishing-a-development-branch` are each ≤540 words
  (budget), or each shortfall is listed as "kept long on purpose".
- SC-4: for each trim, every condition word that `check_scope_qualifiers.py` lists is resolved as
  "kept" with a cited HEAD line, and the reviewer's `meaning:` entry is `pass`. A word the reviewer
  resolves as a finding is fixed in a fix round by restoring the condition in scope. It is never
  closed by recording the sentence as "kept long on purpose"; that exit applies only to the word
  budget in SC-3.
- SC-5: the existing qualifier canaries, audit tests, review-package tests and the four shell tests
  pass.
- SC-6: the two backlog rows read `done`.
- SC-7: for each of the three skills, the summed hard count of `SKILL.md` plus `references/*.md` at
  the branch HEAD is no higher than the summed count at the branch base (measured with the
  §4 linter flags), and the diff of `scripts/ste-baseline.json` changes only entries under those
  three skills. The per-task guard in Architecture §4 uses the task base; when every task passes
  it, this branch-level check against the branch base passes too, so they are one check at two
  scopes.

## Non-goals

- Editing `skills/asd-ste100/` (vendored) or `UPSTREAM.md`.
- Changing the 600-word ceiling or the vendored exemption.
- Any `hooks/` change.
- Adding the sentences #310, #312, #313 and #318 need.
- Re-scoping #310; it is noted as largely done for a separate re-check.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | Each of the three skills holds at least 60 words (budget) that are either default behavior, a restatement of a pointed-to file, or branch-only material | none yet: Inference, 2026-10-16, reading of the three SKILL.md files | SC-3 | Stop at the lowest safe count and list kept sentences (Error behavior); #310/#312/#313/#318 get less room |
| A2 | `check_scope_qualifiers.py` lists every condition word a trim removes from a hunk; it does not list a split or move that keeps the word but narrows its scope | truth: Local, 2026-10-16, shared-venv pytest of `test_check_scope_qualifiers.py`: `test_pilot_step6_cut_is_listed` passes and `test_pilot_step1_split_is_not_listed_known_limit` passes | SC-4, SC-5 | A drop outside the word list, or a scope split, passes the script; the reviewer's free-form meaning check and procedure step 4 are the backstop |
| A3 | Moving a block to `references/` with a pointer keeps behavior, because the agent reads the reference when the branch applies | none yet: Inference, 2026-10-16, existing `references/` pointers in feature-intake and finishing | context-propagation-audit on the branch | A moved instruction is not delivered; the audit flags it and the block moves back |
| A4 | The four shell tests are the only tests that pin literal strings in the three skills | provenance: Local, 2026-10-16, `grep -rln` over `tests/`, `scripts/test_*`, `hooks/`, `skills/*/tests` | SC-5 | A missed test fails in `scripts/run-tests.sh`; fix as in Error behavior |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| A trim that passes cannot change agent behavior | The qualifier list and the reviewer catch dropped conditions; they do not measure comprehension. No blind behavioral eval runs (user chose proof A) |
| A scope split is caught mechanically | `check_scope_qualifiers.py` does not list a split that keeps the condition word but moves later sentences out of its scope (its documented known limit). Only the reviewer's meaning check covers it |
| The audit enforces the procedure | The audit still only counts words; the message describes the method but nothing checks that it was followed |
| Every future trim in the repo follows the procedure | Only the three trims here are reviewed against it |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | The canonical procedure lives in `docs/solutions/harness/deletion-test-for-word-ceiling.md`; the audit message points to it | `asd-ste100` stays an unmodified vendored copy; issue step 2 is replaced, not done literally | settled |
| D2 | Proof uses the existing qualifier section, reviewer meaning check and canary tests; no new eval and no `rules/terminology.md` entry | Issue's proof is narrowed; the gap is stated under What we do not claim | settled |
| D3 | Issue step 3 is bookkeeping only: mark the two backlog rows `done` | No new script or reviewer change in this work | settled |
| D4 | Trim budget is ≤540 words per skill, met by whole-sentence deletion or whole-block disclosure only | A shortfall is recorded as "kept long on purpose", never closed by shortening a condition sentence | settled |
