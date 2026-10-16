# onboarding-skill — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate (adds skills/onboarding/SKILL.md and edits skills/README.md); intake classifies workflow-as-code as high-risk even though the gate is warn-mode at commit time
Flags: external systems, multi-domain
Affects: skills/README.md (skill inventory and handoff map), skills/onboarding (new), harness-manifest.json / static skill checks if they register skills
Input-type: new spec
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/onboarding-skill/intent.md @ 5e8513c2792b8e5be9f5c29428c07897df1e0f8d

> I plan to create a skill that helps new team members onboard to an existing codebase quickly. The skill is not for the current project. It is for use when this harness is installed: a new team member uses the skill to onboard as fast as possible.

> I am thinking of using the langchain openwiki document for this project. The skill can review each topic or session. It can use knowledge from the openwiki built by langchain. We can show this to newcomers.

> check the folder openwiki/ now

> back to first my idea, the onboarding skill

### Intake notes

- Confidence high: the user approved intent.md after the design (wiki-backed sessions, verify-before-teaching, first-ticket mode, resumable progress, no-wiki fallback) was agreed in chat; one interpretation remains.
- `external systems` flag: the skill consumes LangChain OpenWiki 0.7.2 output (`openwiki/` layout observed in this repo at HEAD 996f50d). No SDK or dependency is added; the wiki is read as files.
- `multi-domain` flag: new skill plus README inventory plus whatever registration the static checks demand (to be settled by xia2).
- Branch `feat/onboarding-skill` cut from `sdlc`; the PR targets `sdlc`.
- 2026-10-16, after research: asked how progress should be saved, given the branch-isolation guard
  denies Write on `main` and consumers do not gitignore `.harness-state/`. The user answered
  "No saved progress". Intent outcome 4 (resumable progress under `.harness-state/onboarding/`)
  and design SC-6 are withdrawn by the user's decision, not omitted (design DC1).
- Same exchange: the user chose "Deployed path, no deploy change" for naming the script (design DC2).
- 2026-10-16, plan review: the deployed path fails the runtime-neutral scan. The user chose
  "Relative to the skill's directory" (design DC3).

## What changed

Adds the `onboarding` skill, a read-only, page-by-page tour of a consumer repo for a new team
member. When the repo has a generated OpenWiki, the skill walks it from `openwiki/quickstart.md`
and the section indexes. Before teaching each page, it re-verifies the page's grounded claims
against the cited source with `skills/onboarding/scripts/check_claims.py`. The script checks
`repo-lines-v1` and `repo-file-v1` hashes and reports wiki drift against `HEAD`. A focus mode
picks pages from the wiki's task-routing table. Without a wiki, the skill tours `CLAUDE.md`,
`techstacks/`, `docs/solutions/`, `rules/`, recently changed directories, and the
code-review-graph overview. The skill is registered in `harness-manifest.json`, `skills/README.md`,
the prompt-audit count, and the runtime-neutral inventory. It writes no file.

### Rationale

Hash recomputation makes "never teach a stale claim" a deterministic, unit-tested check instead
of agent judgment (design D1). The user cut saved progress (DC1), because the branch-isolation
guard denies the Write tool on `main` and consumers do not gitignore `.harness-state/`. The
script is named relative to the skill directory (DC3), because the runtime-neutral scan rejects
the derived `.claude/` path and the deploy script was out of scope.

### Alternatives considered

- Prose-only claim checks, with the agent reading each cited range: rejected as judgment-tier and slower per page (design approaches).
- `references/` per mode: not needed while the skill fits the 600-word ceiling.
- A deploy-script rewrite pattern for the script path, as for the asd-ste100 linter: rejected by the user to keep deploy out of scope (DC2, then DC3).
- Saving progress through the script with Bash, which bypasses the Write guard: offered, and the user chose no saved progress.

### Deviations

- Context-propagation audit repair: added the SKILL.md exit-table drift test (`beab618`).
- Intent fix round 1 (`b8e64e6`): added `docs/solutions/INDEX.md` to the fallback, built the session list from the quickstart and section indexes, ran the status check in every mode, and added a Skill Handoff Map line.

- Design change DC1 (reopens D3; new D7: no saved progress) — see `specs/onboarding-skill/design.md` `## Decision changes`.
- Design change DC2 (new D8: script named by deployed path) — see `specs/onboarding-skill/design.md` `## Decision changes`.
- Design change DC3 (reopens D8; new D9: script named relative to the skill directory) — see `specs/onboarding-skill/design.md` `## Decision changes`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intent pin unchanged since approval | `git diff --exit-code 5e8513c2792b8e5be9f5c29428c07897df1e0f8d -- specs/onboarding-skill/intent.md` | 0 | intake-time pin check | |
| openwiki was generated at the intake base | `test "$(python3 -c 'import json;print(json.load(open("openwiki/.last-update.json"))["gitHead"])')" = 996f50dcdade59defd11a406537b01c8354efb57` | 0 | wiki gitHead equals 996f50d, the sdlc tip this branch was cut from; pinned to the sha because sdlc moved during the run | |
| drift check reports behind | `python3 skills/onboarding/scripts/check_claims.py --status` | 1 | printed `behind 14`; needs the untracked `openwiki/` copy in this worktree | SC-1 |
| commit-gate page claims verify | `python3 skills/onboarding/scripts/check_claims.py enforcement/commit-gate.md` | 0 | 21 lines, all `ok` | SC-2 |
| checker unit tests | `/tmp/harness-tests-venv/bin/pytest -q skills/onboarding/scripts/test_check_claims.py` | 0 | 18 passed, including the exit-table drift test | SC-3 |
| focus rule present in SKILL.md | `grep -c "Then also" skills/onboarding/SKILL.md` | 0 | count 1 | SC-4 |
| no-wiki exits 2 in both modes | `/tmp/harness-tests-venv/bin/pytest -q skills/onboarding/scripts/test_check_claims.py -k no_wiki` | 0 | 2 passed | SC-5 |
| skill registered with valid frontmatter | `python3 scripts/check_manifest.py && python3 scripts/check_frontmatter_contract.py` | 0 | | SC-6 |
| allowed-tools conformance and word ceiling | `python3 scripts/check_skill_tool_conformance.py && python3 scripts/audit_skill_prompts.py` | 0 | 54 commands across 15 skills permitted; no audit problems | SC-7 |
| runtime-neutral scan | `python3 scripts/check_runtime_neutral_sources.py --root .` | 0 | `onboarding` is in `skill_names` | SC-8 |
| audit test counts 15 skills | `/tmp/harness-tests-venv/bin/pytest -q scripts/test_audit_skill_prompts.py` | 0 | 11 passed | SC-9 |
| deploy ships the script | `test -f .claude/skills/onboarding/scripts/check_claims.py` | 0 | run right after `bash scripts/deploy-harness.sh` (exit 0) | SC-10 |
| fallback instruction present | `grep -c "since=90.days" skills/onboarding/SKILL.md` | 0 | count 1 | SC-11 |

### Not auto-verified

- OpenWiki 0.7.2 layout (quickstart.md, per-section index.md, .claims/, .last-update.json, .page-manifest.json) was observed only in this repo — reached traceability; not re-run on a consumer project because none with a wiki is available at intake
- The agent's tour behavior (focus selection, newcomer layer, fallback tour) — reached traceability (grep for the instructions, SC-4 and SC-11); not re-run because no skill-eval run was made
- SC-1 and SC-2 depend on the untracked `openwiki/` copy in this worktree — reached truth locally; in CI or a fresh clone they exit 2, so CI cannot re-run them
- A7: the runtime reports the skill's base directory — reached provenance for Claude Code (observed at every skill load in this session); not observed for the Codex alpha

### Rollback

- `git revert b8e64e6 beab618 5bceaea 2bbff4a e3be7db` reverts the skill, its script, the drift test, and the four registration edits. It leaves the `specs/onboarding-skill/` record.
- Then run `bash scripts/deploy-harness.sh` so the derived `.claude/` tree drops the skill.

### Task review Minor findings (forwarded to final review)

- Task 1.1 — `check_claims.py:106-116`: a claim or evidence entry that is not a dict raises
  AttributeError (exit 1 with a traceback) instead of the exit-3 unparseable path.
- Task 1.1 — `check_claims.py:134-143`: an abbreviated `gitHead` that names HEAD prints
  `behind 0` (exit 1) instead of `current` (exit 0). The observed `.last-update.json` holds a
  full 40-character sha.
- Task 1.2 — the task's Verify did not read the unregistered skill; SC-7 was proven only after
  Task 2.1 (see Harness-Delta).
- Task 1.2 — the section list source `openwiki/index.md` is the implementer's choice; that file
  lists the nine wiki sections under `# Directories`.

### Advisory Findings

Correctness review over `996f50d..beab618`: six finders, 8 deduplicated locations, one
independent scorer each. Every location scored 50, which is below the threshold of 75. The
scorers judged each bug real and added by this diff, with a trigger that is rare in normal use.
None entered the fix loop. All are in `skills/onboarding/scripts/check_claims.py`.

| Location | Finding | Score |
| --- | --- | --- |
| `:82` | A claims file with the wrong shape (`{"claims": null}`, non-dict claims or evidence) or an unreadable claims file crashes with exit 1, which SKILL.md reads as "stale claims" instead of exit 3 | 50 |
| `:51` | An unreadable evidence file, or a path component over 255 bytes, raises OSError and aborts the page with exit 1 instead of rating one claim | 50 |
| `:122` | argparse usage errors exit 2, the documented `no-wiki` code, so a malformed call runs the fallback tour | 50 |
| `:36` | With no `git` on PATH, `--status` crashes with exit 1 (read as `behind`) instead of exit 3 | 50 |
| `:111` | An abbreviated `gitHead` equal to HEAD prints `behind 0` (exit 1) instead of `current`; the observed file holds a full sha | 50 |
| `:87` | `{"claims": []}` exits 0, so a page with no claims is shown as all `ok` | 50 |
| `:31` | `openwiki/` resolves against the working directory; a run from a subdirectory reports `no-wiki` | 50 |
| `:44` | `repo://` paths are not confined to the repository; an absolute or `../` path with a matching hash reports `ok` | 50 |

Correctness re-review of the intent fix delta `beab618..b8e64e6` (one focused finder,
enclosing-function angle, and one scorer per location), both in `skills/onboarding/SKILL.md`:

| Location | Finding | Score |
| --- | --- | --- |
| `:25` | "Start at `openwiki/quickstart.md`" has no mode qualifier, so a literal reading conflicts with the page-name and `status` modes | 50 |
| `:75` | The fallback "most commits" step counts file changes from `git log --name-only`, not commits; root files count unevenly (wording predates the delta) | 0 |

### Intent Findings

Intent review over `996f50d..beab618` (blind to PLAN.md), 8 findings:

- 1, 2 (gap; design drift): resumable progress under `.harness-state/onboarding/` is absent, and
  design SC-6 is withdrawn. Deferred by user decision: the user chose "No saved progress" (Intake
  notes; design DC1). Not a fix-loop item.
- Re-review at `b8e64e6`: findings 3, 5, 6 and the handoff-map advisory are closed. The fix
  added no new divergence.
- 3 (gap): the no-wiki fallback omitted `docs/solutions/INDEX.md`. Fixed in `b8e64e6`.
- 4 (gap): design SC-7, `bash scripts/run-tests.sh` prints `ALL GREEN`, has no Verify row. A
  whole-suite row is not allowed (`rules/plan-format.md` Guardrail 4); the suite runs at
  `finishing-a-development-branch`, which records its result. Closed at finish: at `ab908dc`,
  `bash scripts/run-tests.sh` exited 0 and printed `ALL GREEN` (1036 Python tests passed), and
  `bash scripts/ci-strict-gate.sh sdlc` exited 0.
- 5 (drift): the session list did not use each section's `index.md` page descriptions. Fix round 1.
- 6 (drift): the drift status ran only in the empty and `status` modes. Fix round 1.
- 7 (drift, ambiguous): focus "I will change a hook" also returns `testing/test-suite.md` from the
  row's "Then also" cell, while the intent says "the enforcement pages ... and nothing else". The
  user chose "Follow the routing row (Recommended)". Kept as built.
- 8 (excess, report-only): the `status`-only mode, the page-or-section jump mode, and exit 4.
- Advisory: the skill had no Skill Handoff Map entry in `skills/README.md`. Fix round 1.
- Advisory (equivalent drift): gotchas are matched by shared tags; the fallback tour and the
  `current` branch are proven at the script and grep tier only, not by a skill run.

### Context-Propagation Audit

Diff `996f50d..beab618`. The skill dispatches no subagent, so no fresh child context relies on it.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `skills/onboarding/SKILL.md` body | invoking agent | main (Claude Code) | explicit skill load from `.claude/skills/onboarding/` | deploy ships it (SC-10); `check_manifest.py` and `check_frontmatter_contract.py` exit 0 (SC-6) |
| SKILL.md `description:` | model skill list (routing) | main | always-loaded frontmatter | `check_frontmatter_contract.py` exit 0; no `disable-model-invocation` line |
| `check_claims.py` exit codes (D1, design Architecture) | SKILL.md Status and Each-page tables | main | complete inline copy | **was FAIL** (no drift test); repaired by `test_skill_exit_tables_match_script_codes` (beab618); a mutated copy fails the test |
| `rules/behavior.md` §1 (absence claims) | SKILL.md Rules | main | always-loaded rule (no `paths:` frontmatter) plus a named pointer | `tests/scripts/rule-loading-tiers.test.sh` keeps `behavior.md` in the always-on set |
| Untrusted-input rule (CLAUDE.md "Boundary of trust") | SKILL.md Rules | main, consumer repo | complete one-sentence statement in the skill; consumer CLAUDE.md is not assumed | inspected `skills/onboarding/SKILL.md:81` |
| Script location (D9, A7) | invoking agent | main | runtime base-directory line at skill load, Glob fallback | observed for Claude Code at every skill load in this session; Codex not observed (A7, accepted risk) |
| `harness-manifest.json` `skills` | Codex alpha adapter | Codex plugin | `scripts/render_codex_adapter.py:252-253` copies each manifest skill directory whole | inspected call site |
| `skills/README.md` row | humans and doc-truth lint | n/a | README inventory | `scripts/lint-doc-truth.sh` runs in `run-tests.sh` |
| `neutralization-inventory.json` `skill_names` | runtime-neutral scan | CI | registry | `check_runtime_neutral_sources.py --root .` exit 0 (SC-8) |

Result: **PASS** after repair. One row failed (an unanchored inline copy) and was repaired in beab618.

### Harness-Delta

- backlog — a task Verify that runs a manifest-driven check (`audit_skill_prompts.py`, `check_skill_tool_conformance.py`) on a skill that is not yet registered passes without reading the file. Task 1.2's Verify was green before Task 2.1 registered the skill (implementer and task reviewer both reported it).
