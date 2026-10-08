# gh-253-codex-full-payload — Summary

Lane: high-risk
Confidence: high
Reason: hard gate high-blast — the change edits `hooks/commit-gate.sh` and the Codex installer/deployer scripts every Codex consumer runs.
Flags: high-blast, existing behavior, cross-platform, public contracts
Affects: Codex adapter (`scripts/render_codex_adapter.py`, `scripts/deploy-codex-adapter.sh`, `scripts/install-codex-harness.sh`), `hooks/commit-gate.sh` helper lookup
Input-type: spec slice
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> current the hook scripts are not available with codex
> and the claude code now support AGENTS.md file
> let review and checking if we can support user with codex if they want to install our harness-skill

> writing plan to the github first with seperate to each section with detail purpose and target
> after that, start for item 1 first

Item 1 is GitHub issue #253 ("Codex Phase 6.1: ship the full harness payload with the Codex
install"), tracked under #257. Its Target checklist is the scope of this slug.

## What changed

A Codex install now ships a derived harness payload at `.codex/.agent-harness/payload/`
(36 render-time files: rules, non-test runtime, templates, the six consumer scripts,
`harness-manifest.json`, each shipped skill's helpers, and the correctness-review prompt
fragments). In the installed plugin skills and the payload's own Markdown, helper paths are
rewritten to point there. The payload helpers resolve the consumer repo root. Both hooks probe
the payload as a last candidate. The deployer sweeps empty payload directories on prune and
remove, the installer appends `.codex/.agent-harness/` to `.gitignore`, and the doctor hashes
skills as rendered. Claude install output is unchanged.

The full `bash scripts/run-tests.sh` ran all green before the first edit (799 pytest), at each
wave boundary except the expected wave-1 red noted in the Status Log, and after the review fixes
(818 pytest, every shell suite passed).

### Rationale

Confidence is `high`: the issue's Target is concrete, and the design follows an existing
precedent — `scripts/deploy-harness.sh` already defines the canonical consumer subset
(`CONSUMER_SCRIPTS`/`CONSUMER_DATA`) and rewrites root-relative helper paths in derived Markdown.
The Codex adapter already owns `.codex/.agent-harness/` per `docs/codex-alpha-install.md`, so the
payload location has one interpretation that respects the existing ownership boundary.

### Alternatives considered

- To be recorded in `design.md`.

### Deviations

- Rule 1 — The controller fixed Task 1.3's review findings directly. The docs claimed `--remove` behaves "as the Claude installer does", but the Claude installers have no `--remove` path (`grep -c -- --remove` is 0 in both). The wording came from `design.md`, so it was corrected there too. The docs now also name the `.codex/*` and negated `!` skip forms the installer honours. Two pinned skip forms were added to `tests/scripts/codex-install-gitignore.test.sh`. Files: `docs/codex-alpha-install.md`, `tests/scripts/codex-install-gitignore.test.sh`, `specs/gh-253-codex-full-payload/design.md`.
- Process — Implementers left changes uncommitted; the controller committed each task separately so two parallel implementers in one worktree could not collide on git's index lock.

Minor review findings, carried to the final review:
- Task 1.2: the `codex_lane_repo` case in `tests/hooks/commit-gate-evidence.test.sh` does not assert that the source and `.claude/` copies of `verify_summary.py` are absent, so a future `new_repo` change could let it pass for the wrong reason.
- Task 1.1: until Task 2.1 lands, wave 1 leaves `codex-install.test.sh` red by plan ordering (closed by Task 2.1's Verify).
- Task 2.2: the `.gitignore` paragraph in `docs/codex-alpha-install.md` describes Task 1.3's behaviour before that code exists. The Task 1.3 implementer builds to that paragraph, and the Task 1.3 reviewer checks the two against each other. The controller accepted placing the `.gitignore` line in its own paragraph instead of the "adapter owns" list, because that list names only manifest-recorded paths.
- Task 2.1 (pre-existing): `deploy-codex-adapter.sh` runs its fixed rmdirs in the order `.codex/agents`, `.codex`, `.codex/.agent-harness`. An unedited `--remove` on a project that had no `.codex/` before install therefore leaves an empty `.codex/`. Forwarded to the final review.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane specs/gh-253-codex-full-payload/SUMMARY.md` | 0 | intake | |
| payload reference closure + helpers resolve the consumer root | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k closure` | 0 | 3 tests, incl. running payload helpers from a scratch consumer | SC-1 |
| consumer subset single-sourced from deploy-harness.sh | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k consumer_subset` | 0 | parity, removal, bogus, unparseable | SC-2 |
| rewrite idempotent, non-targets untouched, empty targets no-op | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k rewrite` | 0 | incl. frontmatter `allowed-tools` | SC-3 |
| required `payload` inventory accepted by schema | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k payload_inventory` | 0 | | SC-4 |
| commit-gate runs lane evidence from the Codex payload | `bash tests/hooks/commit-gate-evidence.test.sh` | 0 | `Lane evidence... FAILED` asserted for a placeholder lane | SC-5 |
| session-knowledge renders runtime mode from the payload | `bash tests/hooks/session-knowledge.test.sh` | 0 | | SC-6 |
| payload install / conflict / prune / remove lifecycle | `bash tests/scripts/codex-install.test.sh` | 0 | 29 cases | SC-7 |
| append-only .gitignore entry | `bash tests/scripts/codex-install-gitignore.test.sh` | 0 | 11 cases, incl. negated parent | SC-8 |
| Claude rendering unchanged by a Codex render | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k claude_rendering_is_unchanged` | 0 | | SC-9 |
| docs list payload + .gitignore; doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | | SC-10 |
| doctor hashes rendered skills (clean install not flagged) | `python3 -m pytest scripts/test_codex_harness_doctor.py -q` | 0 | review finding D | |

### Not auto-verified

- Live Codex CLI behaviour is unobserved for this change: no Codex binary ran. Plugin skill
  discovery of the rewritten text, an agent following the rewritten paths, and hook execution
  under real trust were exercised only by the fake-Codex harness and direct script runs
  (traceability + truth for the scripts themselves; the runtime path is unverified).
- Linux/WSL and Codex versions newer than 0.147.0 remain outside the evidence boundary
  (traceability).
- That the 36-file payload is the complete set every future skill needs is guarded only by the
  closure test over today's rendered text (truth for today's tree; future references are covered
  only if they use a payload-backed path form).
- The Task 1.2 mutation check (removing the third hook candidate fails the new cases) was run
  once by the implementer and not re-run by a gate (truth, one-time).

### Context-Propagation Audit

Not run. The diff does not trip the `workflow-engine` gate: `git diff --name-only e28e917..HEAD`
touches no `skills/*/SKILL.md`, skill prompt, `agents/*.md`, or `rules/*.md` source, and the skill
runs "only when the changed diff trips" that gate. The delivery question it would ask, whether
every rewritten reference in Codex-delivered skill and rule text reaches a real file, is instead
checked mechanically by `test_payload_closure_every_helper_reference_resolves` and
`test_payload_closure_helpers_resolve_the_consumer_root_not_the_payload`.

### Correctness Review

Six FIND angles ran over `e28e917..5305d13`. 10 locations were deduplicated and scored
independently (threshold 75).

Fixed (score >= 75; all Rule 1, no Rule 4 item touched):
- A (75) — `scripts/verify_summary.py` took `.codex/.agent-harness/payload` as the repo root, so
  skill-invoked `--lane/--check <slug>` failed, and commit-gate's `REQUIRE_VERIFY` re-run blocked
  valid commits. Root resolution now also unwraps the payload location.
- B (100) — `scripts/rebuild_solution_index.py` wrote `INDEX.md` inside the payload. Same root
  fix in `_default_root`.
- C (75) — correctness-review's prompt composer could not find its fragments under Codex. The
  payload now ships each skill's `prompts/` fragments, and `scripts/render_skill_prompt.py`
  resolves a relative fragment against `--root` when it is not found from the working directory.
- D (100) — the doctor hashed raw source skills, so every clean install reported
  `INSTALL_HASH_MISMATCH`. `codex_harness_doctor.py` now hashes skills as the renderer ships
  them (`render_codex_adapter.payload_targets` + `rewrite_payload_paths`), and the doctor fixture
  installs rendered skills.

Also fixed although advisory, because each was a one-line change in code this branch wrote:
- E (50) — the installer treated a negated parent (`!/.codex/`) as already deciding
  `.agent-harness`. Only an explicit `!.codex/.agent-harness` negation is respected now.
- G (50) — `rewrite_payload_paths` with an empty target list corrupted text. It now returns early.

### Advisory Findings

- F (25) — rendered skills name `.codex/.agent-harness/payload/harness-manifest.json` as the
  authority, while commit-gate reads modes from the indexed root manifest or embedded defaults.
  This matches the Claude deploy's existing rewrite to `.claude/harness-manifest.json`, so it is
  pre-existing design, not a regression. Relevant only to consumers that track a root manifest
  with non-default modes.
- H (0, unmodified line) — `skills/visual-planner/render_plan.py:1424`: the
  `TEMPLATE_PATH.parents[3]` fallback assumes the `.claude/skills/` depth. Run from a payload copy
  in a subdirectory without `specs/`, it searches `.codex/.agent-harness/specs`. Running from the
  repo root (the documented use) works. `render_plan.py` is a Rule-4 core engine, so this goes
  to a follow-up.
- I (25) — the `verify_summary.py` that commit-gate runs is an agent-writable, gitignored copy.
  This is the same trust model as the existing `.claude/scripts/` candidate (Gate verifiability
  negative scope: `Does not verify: verifier integrity`).
- J (0, refuted) — the reported leftover empty `.codex/` after `--remove` does not occur. The
  shell `--remove` path runs `rmdir "$STATE_DIR" "$TARGET_DIR/.codex"` in the right order after
  the Python cleanup.

### Rollback

- Revert the merge commit of this branch: `git revert -m 1 <merge-sha>`; no data migration is involved.
- Consumers who already installed the new adapter: re-run `bash scripts/install-codex-harness.sh --source <reverted checkout> --directory <project> --yes`. The prune step removes the payload paths the reverted manifest no longer owns; locally edited copies are preserved as conflicts, never deleted.

### Harness-Delta

- backlog — Claude consumers have the same latent gap for `runtime/…` and `rules/…` paths: `deploy-harness.sh` `rewrite_derived_paths` rewrites only `scripts/<consumer subset>`, `harness-manifest.json` and the `render_plan.py` command, so a deployed skill still says `python3 runtime/run_state.py`, `skills/subagent-driven-development/scripts/task_brief.py` and `bash skills/using-git-worktrees/scripts/detect-isolation.sh`, none of which exist at a consumer's root (the payload is under `.claude/`). Observed in a scratch Claude install on 2026-10-08. Out of scope here; file as its own issue.
