# simplify-prompt-instructions — Summary

Lane: high-risk
Confidence: high
Reason: the diff edits `hooks/commit-quality-gate.sh`, `scripts/deploy-harness.sh`, `scripts/verify_summary.py`, `rules/*.md` and `templates/structure/` — workflow-engine and high-blast paths, so the hard-gate signal forces high-risk regardless of size.
Flags: workflow-engine, high-blast-file, public-contract
Affects: harness deploy surface (`deploy-harness.sh`), commit gate (`commit-quality-gate.sh` Checks 1.6/2.5), doc-truth lint, scaffold templates
Input-type: harness improvement

### Intent

Not captured verbatim. The originating request predates this session's transcript, so no
verbatim quote exists to paste here; recording a paraphrase in this slot would fake the
intent-review oracle. Reconstructed scope, from the commit bodies that are the actual record:

- `062c5aa refactor(prompts): cut guidance a frontier model already applies`
- `dc77415 fix(deploy): ship the helper subset a consuming repo's gates actually run`
- `568893f fix(docs): make consumer-facing references true, and lint the derived tree for it`

An intent review against this section is therefore **not** available for this branch; see
`### Not auto-verified`.

## What changed

Three related fixes to what a *consuming* repo actually receives. `deploy-harness.sh` now ships an
allow-listed subset of `scripts/` (plus `harness-manifest.json`) into `.claude/`, rewrites
`scripts/X` → `.claude/scripts/X` in derived Markdown, and strips harness-only tests and
maintenance docs from the derived tree — so gates that were prose-only downstream (lane evidence
Check 1.6, the SDD ship gate, `finishing-a-development-branch`'s opening command) now execute.
`lint-doc-truth.sh` gained Check 4, which deploys into a scratch target and re-checks every path
the *derived* docs name from there, catching references that resolve only in this repo; the 45
dangling references it found are fixed, including three wrong lessons in the `specs-README`
scaffold (`plan.md` casing, "XML tasks", missing `SUMMARY.md`). Prompt/rule files drop guidance a
frontier model already applies.

### Rationale

A gate is only true when it runs where it is meant to protect. `lint-doc-truth.sh` reported exit 0
while every consuming repo had broken references, because it normalized `.claude/x` back to the
source it derives from and ran in the one repo where `scripts/` exists. The fix is to verify from
the deployed vantage point, not the source one. The scripts subset is an explicit allow-list rather
than `scripts/` wholesale (70+ files, including its own tests); hooks deliberately keep their own
path resolution so `risk-corroboration.sh` still reads the manifest from the git index rather than
a derived file an unstaged edit could loosen.

### Alternatives considered

- Deploy `scripts/` wholesale — rejected: ships 70+ files including harness CI tests and
  `render_runtime_entry.py`, whose source-time adapter inputs are pinned never to deploy.
- Rewrite paths in hooks as well as Markdown — rejected: would move gate policy onto an
  agent-writable derived file (`docs/solutions/harness/gate-config-must-read-index.md`).

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| consumer subset boundary | `bash tests/scripts/consumer-subset.test.sh` | 0 | 15 assertions: allow-list boundary, path rewrite + idempotency, hooks-untouched, both strips, deployed root resolution | |
| resync conflict guard | `bash tests/scripts/resync-conflict.test.sh` | 0 | 18s | |
| derived-tree doc truth | `bash scripts/lint-doc-truth.sh` | 0 | Check 4 clean after the 45 reference fixes | |
| commit gate behavior | `bash tests/hooks/commit-quality-gate.test.sh` | 0 | 23s; covers Checks 1.6 / 2.5 helper resolution | |
| rule loading tiers | `bash tests/scripts/rule-loading-tiers.test.sh` | 0 | always-on vs path-scoped inventory still matches `rules/*.md` | |
| verify_summary unit | `python3 -m pytest scripts/test_verify_summary.py -q` | 0 | 72 passed | |
| solution index unit | `python3 -m pytest scripts/test_rebuild_solution_index.py -q` | 0 | 4 passed | |

Full suite (`scripts/run-tests.sh`) also ran clean on this branch — 575 python tests plus the shell
suites, `ALL GREEN`. It is cited in prose, not as a row, because it exceeds the strict gate's 60s
per-command cap.

### Not auto-verified

- **Intent fidelity** — reached *none*; no verbatim request exists in this session, so the
  intent-review oracle could not run against `### Intent`. The commit bodies are the record.
- **Correctness review** — reached *none*; no `.review-receipt.json` exists for this slug. This
  branch was not executed through subagent-driven-development, so no correctness or context-
  propagation audit was pinned at base.
- **The allow-list is the right six helpers** — reached *traceability*; `consumer-subset.test.sh`
  asserts the boundary it was written against, not that a consuming repo's gates need exactly
  those six and no seventh.
- **The 45 reference fixes are semantically correct** — reached *truth* for resolvability (Check 4
  re-runs and passes) but only *traceability* for the "harness repo" labelling convention: the
  lint checks a three-line window for the phrase, not that the label is honest.
- **`task-reviewer-readonly.test.sh` reports `passed` with `rg: command not found`** — reached
  *none*; the assertions it names did not execute on this machine. Pre-existing, not introduced
  here, and logged below.

### Rollback

- `git revert 568893f dc77415 062c5aa`

### Harness-Delta

- backlog — `tests/scripts/task-reviewer-readonly.test.sh` prints `passed` after `rg: command not
  found`, so a missing binary is indistinguishable from a satisfied assertion. Same class as
  `docs/solutions/harness/green-can-mean-skipped`; should fail or explicitly SKIP.
- backlog — `scripts/resolve_finish_context.py` resolved base `main` for a branch cut from
  `simplify` (359 commits behind), and matched `specs/skill-prompt-refactor` by `token-overlap:2`
  to a plan this branch never touches. Both are the `stale-active-plan-misaims-blast-radius`
  pattern; a token-overlap match should be reported as unresolved, not as a plan.
