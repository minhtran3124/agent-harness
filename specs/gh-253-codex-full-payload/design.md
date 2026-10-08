---
slug: gh-253-codex-full-payload
status: approved
issue: 253
tracking: 257
---

# Ship the full harness payload with the Codex install — Design

## Purpose

A Codex-only consumer receives the plugin (13 skills, 3 hooks + `hooks/lib`), 4 agent profiles,
`.codex/harness-instructions.md`, and an `AGENTS.md` pointer. Nothing else. Rendered skills
contain 26 (skill → path) references to `rules/`, `runtime/`, `scripts/`, and `templates/` files,
covering 17 unique paths, and none of them exist in the project. Skills also run skill-local
helpers by project-root path (`python3 skills/visual-planner/render_plan.py`,
`skills/subagent-driven-development/scripts/task_brief.py`,
`bash skills/using-git-worktrees/scripts/detect-isolation.sh`). Under Codex the skills live only in
the plugin cache, so these fail as well. Two hooks
probe only `<root>/…` and `<root>/.claude/…` for their Python helpers, so under Codex:

- `commit-gate.sh` finds no `verify_summary.py`, skips lane evidence and the Verify re-run, and
  allows the commit with one stderr line (`commit-gate.sh:167`, `:291`);
- `session-knowledge.sh` finds no `runtime_mode.py`, so the Codex runtime-mode banner never
  renders (`session-knowledge.sh:121-122`).

Goal: after a Codex install, every helper path a shipped skill or hook names resolves inside the
project, under the same ownership and non-clobber guarantees the adapter already gives.

## Constraints

- Claude install output stays byte-identical. Its tests must pass untouched.
- One consumer subset. `scripts/deploy-harness.sh` `CONSUMER_SCRIPTS`/`CONSUMER_DATA` is the
  canonical list of helpers a consumer receives. The Codex renderer must read that list, not keep a
  second hand-written copy.
- The adapter owns only manifest-recorded paths (`docs/codex-alpha-install.md`). New paths go
  through the existing `project/` overlay, so they inherit refresh / `.harness-incoming` / prune /
  `--remove` without new lifecycle code.
- Source skill prose stays runtime-neutral (Phase 3). Path rewriting happens only in the rendered,
  derived copy, as the Claude deploy already does.
- No trust, config, or `AGENTS.md`-content changes. Those belong to #254 and #255.
- The hooks keep resolving the project root from the runtime (never from `SCRIPT_DIR`) and keep
  reading `harness-manifest.json` from the git index only.

## Chosen approach — project payload under `.codex/.agent-harness/payload/`

User-selected 2026-10-08 (alternatives below).

```text
<project>/
  .codex/.agent-harness/
    deployment-manifest.json      (existing — now also lists payload files)
    marketplace/…                 (existing — plugin: skills, hooks)
    payload/                      NEW, manifest-owned
      rules/*.md                  all rules (always-on + path-scoped)
      runtime/*.py                non-test runtime modules
      templates/**                SUMMARY/ESCALATIONS/receipt templates + structure/
      scripts/<CONSUMER_SCRIPTS>  the six consumer helpers
      harness-manifest.json       CONSUMER_DATA
      skills/<name>/…             non-Markdown, non-test helper files of each shipped skill
                                  (render_plan.py + template.html + view_plan.py +
                                  build_roadmap.py, task_brief.py, review_package.py,
                                  detect-isolation.sh, review-config.json)
```

### Components

1. **Renderer (`scripts/render_codex_adapter.py`)**
   - Read `CONSUMER_SCRIPTS`/`CONSUMER_DATA` from `scripts/deploy-harness.sh` with a regex over
     the bash source: a `NAME=(` line, then one double-quoted entry per line until `)`. Comment
     lines inside the array are skipped. "Cannot be parsed" means the array header is absent, the
     closing `)` is absent, or there are zero entries. Any of these, or an entry naming a missing
     file, raises `AdapterError`. This is deliberately stricter than `deploy-harness.sh
     copy_consumer_subset`, which warns and continues: a partial Codex payload would pass its own
     closure test only by accident.
   - The rewrite applies to the whole rendered file, frontmatter included. This is intended:
     `allowed-tools` entries such as `Bash(python3 skills/visual-planner/render_plan.py *)` must
     match the rewritten command, or the tool permission and the instruction disagree. Accepted
     side effect: `rules/auto-correct-scope.md:87` names `skills/visual-planner/render_plan.py` as
     an example high-blast file. In the Codex-derived copy, that example now shows the payload
     path. The sentence still names the same file, so its meaning holds.
   - Copy `rules/`, `runtime/` (excluding `test_*.py`, `__pycache__`), `templates/`, the consumer
     scripts, the consumer data, and each shipped skill's non-Markdown, non-test helper files
     (`skills/<name>/**` minus `*.md`, `test_*`, `__pycache__`) into
     `project/.codex/.agent-harness/payload/`.
   - Rewrite helper paths in rendered Markdown only: the plugin's `skills/**/*.md` and the
     payload's `rules/**/*.md` and `templates/**/*.md`. Bare `rules/<file>`, `runtime/<file>`,
     `templates/<file>`, `scripts/<consumer script>`, `skills/<name>/<helper>`, and
     `harness-manifest.json` become `.codex/.agent-harness/payload/<same>`. The rewrite is token-anchored like
     `deploy-harness.sh rewrite_derived_paths`: no match when preceded by `[\w./-]`, so it is
     idempotent and never rewrites `.claude/…` or already-prefixed paths. It rewrites only targets
     that exist in the payload, so a non-payload `scripts/foo` stays untouched.
   - Add a required `payload` inventory (sorted payload-relative file list) to
     `render-manifest.json` and to `adapters/codex/schema.json` `required` + `properties`. In the
     same edit, add `"payload"` to the hard-coded expected set in `_validate_schema`, which rejects
     any other `required` set. Otherwise the renderer fails closed on its own schema.
2. **Deployer (`scripts/deploy-codex-adapter.sh`)** — already syncs every file under the rendered
   `project/` overlay. Change only the empty-directory cleanup. On every `sync_project` run
   (install-time prune of retired files and `--remove` alike), delete empty directories under
   `payload/` deepest-first, before the existing three fixed rmdirs. Today it rmdirs only those
   three. File modes are not preserved (`atomic_write` uses a 0600 tempfile). That is acceptable
   because every payload helper is invoked through an interpreter (`python3 …` / `bash …`).
   `detect-isolation.sh` is already 100644 in source, so its bare `allowed-tools` form fails in
   every runtime today. Out of scope.
3. **Hooks** — add a third candidate, after the existing two, so source-checkout and Claude
   resolution order is unchanged. Relative candidates are project-relative because
   `commit-gate.sh` `cd`s to the runtime-resolved `$REPO_DIR` (`:145-152`) before probing, and
   `session-knowledge.sh` anchors on `$RUN_STATE_ROOT`. The new candidates follow each hook's
   existing anchoring:
   - `commit-gate.sh`: `.codex/.agent-harness/payload/scripts/verify_summary.py`, plus the stderr
     hint that lists where it looked;
   - `session-knowledge.sh`: `.codex/.agent-harness/payload/runtime/runtime_mode.py`.
4. **Installer `.gitignore` step (`scripts/install-codex-harness.sh`)** — ensure the project's
   `.gitignore` lists `.codex/.agent-harness/`. Append only, mirroring `install-harness.sh:249-297`:
   skip if a line already scopes it (`.codex`, `.codex/`, `/.codex/`, or any `.codex/.agent-harness`
   form, matching the Claude installer's directory-scoped pattern check), warn and skip if the directory is already tracked, and never
   rewrite the file. Without it, `commit-gate.sh`'s strict-profile untracked-`.py` deny
   (`:111`, excludes only `.claude/`) blocks every commit in a Codex consumer. That is already
   true for the plugin's own `.py` files under `marketplace/`, and the payload adds more. Skipped
   under `--dry-run`. Not undone by `--remove`, matching the Claude installer.
5. **Docs** — add the payload and the `.gitignore` entry to the "adapter owns" list in
   `docs/codex-alpha-install.md`, and state that `--remove` leaves the `.gitignore` line in place.

### Data flow

`install-codex-harness.sh` → `deploy-codex-adapter.sh` → `render_codex_adapter.py` writes
`plugin/` + `project/` (now including `payload/`) → `sync_project install` hashes each `project/`
file into `deployment-manifest.json` `project_files` → Codex skills, read from the plugin cache,
run `python3 .codex/.agent-harness/payload/scripts/…` from the project root → hooks find helpers
through their third candidate.

### Error behaviour

- If `CONSUMER_SCRIPTS` cannot be parsed or names a missing source, the render fails with an
  `AdapterError`. It never ships a partial payload.
- An edited payload file on reinstall is kept, the new copy is written beside it as
  `<file>.harness-incoming`, and the conflict is recorded. Existing semantics.
- On remove, an edited payload file is preserved and stays in the manifest. Existing semantics.
- If no helper resolves, the hooks keep their current fail-open warning. This item makes the
  helper resolvable; turning "unresolved" into a doctor reason belongs to #255.

### Tests

- **Reference-closure contract (the regression guard):** render, then scan every rendered
  `SKILL.md`/rule/template for `.codex/.agent-harness/payload/<path>` and for any remaining bare
  `rules|runtime|templates|scripts/<consumer>|skills/<name>/<helper>` reference. Assert each
  prefixed path exists in the payload and no bare reference to a payload-backed target is left.
  The miss set is computed from the rendered tree, never hard-coded, so the test fails on today's
  tree and on any future skill reference.
- **Single-source subset:** removing a name from `CONSUMER_SCRIPTS` changes the rendered payload,
  and a bogus name fails the render.
- **Rewrite safety:** rewriting is idempotent; `.claude/rules/x` and
  `.codex/.agent-harness/payload/rules/x` are untouched; prose mentioning a non-payload
  `scripts/test_x.py` is untouched. In a dual-candidate snippet such as `subagent-driven-development`'s
  `if [ -f runtime/resume_decision.py ] … else .claude/runtime/…`, only the bare branch is
  rewritten. The `.claude/` branch stays as a harmless dead fallback under Codex. A frontmatter
  `allowed-tools` entry is rewritten too (asserted).
- **Install lifecycle (fake Codex CLI, existing `codex-install.test.sh` harness):** after install
  the payload exists and is manifest-listed; an edited payload file produces `.harness-incoming`;
  `--remove` deletes unchanged payload files and empty directories and keeps edited ones; a
  reinstall that retires a payload file prunes it and its now-empty directory.
- **Hooks:** in a temp repo with only `.codex/.agent-harness/payload/scripts/verify_summary.py`,
  `commit-gate.sh` runs lane evidence (a failing SUMMARY is reported, not "skipped"). Existing
  Claude/source resolution tests stay green.
- **Gitignore step:** fresh repo gains the line once (idempotent on reinstall); an existing
  scoping line is left alone; `--dry-run` writes nothing.
- **Claude byte-identity:** existing deploy/install tests unchanged and passing.
- Full `bash scripts/run-tests.sh`.

## Alternatives considered

- **Ship the payload inside the plugin package** — rejected. Skills execute from the project
  directory, and Codex's plugin cache path is internal and unobserved in the 0.147.0 evidence, so
  skill-cited paths would rest on an unproven location.
- **Reuse the Claude deploy into `.claude/`** — rejected. A Codex-only install would write a Claude
  settings tree, and two installers would co-own one prune boundary.
- **Mirror `.claude/` as `.codex/{rules,scripts,…}`** — rejected. `.codex/` is Codex's own config
  namespace, and an unnamespaced `rules/` there risks colliding with Codex features. The
  `.agent-harness/` subdirectory is already ours.
- **Leave paths bare and tell the agent in prose to resolve them under the payload** — rejected.
  It depends on instruction-following where the Claude precedent uses a deterministic rewrite.

## Out of scope

- Loading the always-on rules into Codex session context (#254).
- Hook trust, doctor reasons, installer next-step messaging (#255).
- The latent Claude-side gap where `deploy-harness.sh` does not rewrite `runtime/…`, `rules/…`,
  or skill-local helper paths (`task_brief.py`, `detect-isolation.sh`). Recorded as a
  Harness-Delta backlog item in `SUMMARY.md`.
- Running `init-structure.sh` from the Codex installer. The #253 Target lists it, but it is a
  separate lifecycle concern. It moves to #255 or a follow-up so this diff stays one mechanism.
  The #253 checklist will be updated.
