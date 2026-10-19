# core-docs-refresh — Summary

Lane: high-risk
Confidence: high
Reason: Docs-only truth-sync, but the diff touches `templates/structure/`, which `scripts/ci-strict-gate.sh` gates (block tier) and which needs a high-risk SUMMARY with re-runnable Verify rows. No hook, script, skill, or rule logic changes.
Flags: none
Affects: README.md, HARNESS.md, CLAUDE.md, AGENTS.md, skills/README.md, skill and agent READMEs, consumer scaffold READMEs in templates/structure/
Input-type: maintenance

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Review the @README.md and @CLAUDE.md files and other related doc files. Check them against the recent code changes and update them.
The whole skill, the skill overview, and the instructions must be covered.
Spawn sub-agents to do research, to reduce the time needed.

### Intake notes

- Scope reading: "the whole skill" = every `skills/*/SKILL.md` is checked, with SKILL.md treated as the source of truth; only docs are edited. SKILL.md inconsistencies are reported, not fixed.
- Recent changes = PRs #290–#331 (`git log 7ef3579..c3d09c0`), but docs were checked against the full current code.
- The uncommitted OpenWiki sections in `CLAUDE.md` / `AGENTS.md` are the user's separate work and are not part of this commit.

## What changed

Four parallel research agents checked the docs against the code, each on its own files. Fixes:
`README.md` (installer `--profile` flag, `python3` requirement, consumer `scripts/` subset,
current test-suite contents, warn-mode gates); `HARNESS.md` (bug-fix route via
`diagnosing-bugs`, red/green proof, `workflow engine` hard gate, block vs warn mode);
`CLAUDE.md` (bug-fix route + tiny-lane STE rule, red/green check in the commit-gate row,
`hooks/lib/gate-modes.default.sh`); `AGENTS.md` (pytest command matches the `find` in
`run-tests.sh`); `skills/README.md` (diagram, minimum path, bug-fix path, triggers, outputs,
handoff map for all 15 skills incl. `diagnosing-bugs` and `asd-ste100`); the compound, xia2,
feature-intake/tests and agents READMEs; `docs/solutions/README.md`, `evals/README.md`,
`techstacks/README.md`, `docs/codex-alpha-install.md`; and the matching consumer scaffold
copies in `templates/structure/`.

### Rationale

Every changed claim was checked against the file that implements it before the edit. The
`templates/structure/` copies are what `scripts/init-structure.sh` installs into consumer
projects, so fixing only the in-repo copy would leave consumers with the stale text.

### Alternatives considered

- Drop the `templates/structure/` edits to stay off the CI strict gate — rejected: consumers would keep stale scaffold docs.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Doc-truth lint (paths + hook table vs settings.json) | `bash scripts/lint-doc-truth.sh` | 0 | all referenced paths exist |  |
| Rule loading tiers unchanged | `bash tests/scripts/rule-loading-tiers.test.sh` | 0 | 3/3 |  |
| Manifest consistency | `python3 scripts/check_manifest.py` | 0 | 15 skills, 3 hooks match disk |  |
| Red/green opt-in env exists (backs CLAUDE.md/HARNESS.md wording) | `grep -q REQUIRE_RED_TEST scripts/verify_summary.py` | 0 |  |  |
| Gate-mode defaults file exists (backs CLAUDE.md gotcha) | `test -f hooks/lib/gate-modes.default.sh` | 0 |  |  |

`bash scripts/run-tests.sh` was also run before commit: exit 0, ALL GREEN, 1060 python passed. It is not a Verify row because it runs longer than a Verify row should (`docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`).

### Not auto-verified

- That every prose claim in the edited docs matches the code — reached traceability (paths exist, hook table matches); semantic accuracy rests on the agents' file reads and human review.
- That no remaining drift exists in docs outside the edited set (e.g. `specs/README.md`, `rules/orchestration.md` 8-gate list) — not checked by any gate; listed as follow-ups in the PR.

### Rollback

- `git revert <sha>` — prose-only; no schema, script, or hook behavior change.

### Harness-Delta

- backlog — source inconsistencies found but out of scope: normal lane has no plan author (`feature-intake` normal route → SDD, which needs a `PLAN.md`); `install-harness.sh` `REPO_URL` names `harness-skills` while the repo is `agent-harness`; `rules/orchestration.md` lists 8 hard gates (manifest has 9); xia2 structural test still reads `PROJECT.md`; `specs/README.md` drifted from its template; prompt-refactor corpus manifest lacks the two new skills; no bookkeeping PR for #331.
