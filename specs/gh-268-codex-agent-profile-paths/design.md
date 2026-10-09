---
slug: gh-268-codex-agent-profile-paths
status: approved
issue: 268
tracking: 257
depends_on: 253, 254, 255
---

# Codex agent profiles cite paths a Codex install has — Design

## Purpose

`scripts/render_agent_definitions.py` `render_codex` embeds each `agents/<role>.md` body in the
rendered `.codex/agents/<role>.toml` `developer_instructions`. Those bodies cite harness files by
bare source paths. #253's render-time rewrite (`rewrite_payload_paths`) covers rendered skills and
payload Markdown, not the agent TOML, so in a Codex-only install:

| Profile | Cited path | Resolves today? |
|---|---|---|
| `coding.toml` | `rules/orchestration.md`, `rules/auto-correct-scope.md` | no — the files live under `.codex/.agent-harness/payload/rules/` |
| `reviewer.toml` | `rules/behavior.md` | no — same |
| `coding.toml`, `test-runner.toml` | `agents/PROJECT.md` | no — nothing creates it for a Codex-only project |
| all four | `agents/runtime-bindings.json` | provenance comment only ("generated from …"); not an instruction to read |

`auto-correct-scope.md` is path-scoped, so #254's inlined `AGENTS.md` block does not carry it
either: an implementer told to "classify against `rules/auto-correct-scope.md`" is pointed at a
missing file.

Goal: every file a rendered Codex profile tells an agent to read exists in a Codex install.

## Decision (user-approved 2026-10-09)

`agents/PROJECT.md`: **the Codex installer creates it from `agents/PROJECT.template.md` when it is
missing** (over adding it to the shared `init-structure.sh`, which would give Claude installs a
second, unread copy, and over an "if present" wording that leaves agents without test-command
guidance). The file is user-owned and meant to be committed by the user (the installer does not
`git add` it; the payload directory is gitignored, so the payload is the wrong home for a file the
team fills in), never overwritten, not recorded in the
deployment manifest, and left in place by `--remove`.

## Constraints

- Source `agents/*.md` and Claude render output stay unchanged; the rewrite happens only in the
  rendered Codex TOML (same rule as #253: derived copies only).
- The rewrite reuses `rewrite_payload_paths` and its existence gate (`payload_targets`), so only
  paths that the payload actually ships are prefixed; `agents/PROJECT.md` and
  `agents/runtime-bindings.json` are not payload targets and stay bare.
- Rendered profiles still pass `parse_codex_profile` and stay byte-deterministic.
- No step edits trust; installer additions follow the #255 tail rules (only after a successful
  deploy, never under `--dry-run`/`--remove`, never failing the install).

## Components

1. **Profile rewrite** (`scripts/render_codex_adapter.py` `render()`): after
   `render_agent_definitions.render_codex(root, agents_dir)` and once the payload targets are
   known, for each `agents_dir/*.toml` rewrite the value of the `developer_instructions` line:
   decode it with `json.loads` (it is emitted by `_toml_string` = `json.dumps(…,
   ensure_ascii=False)`), apply `rewrite_payload_paths`, re-encode with
   `json.dumps(…, ensure_ascii=False)`, and re-validate the file with
   `render_agent_definitions.parse_codex_profile`. Rewriting the decoded string matters: on the
   encoded text, a path after a `\n` escape is preceded by `n`, which the token anchor
   `(?<![\w./-])` treats as part of a word, so it would be skipped.
2. **`agents/PROJECT.md` on install** (`scripts/install-codex-harness.sh` tail, inside the
   `GI_RUN` block, after the `init-structure.sh` call and before the doctor). Guarded so it cannot
   fail the install. The two copy branches run `mkdir -p "$TARGET_DIR/agents"` first (an
   unrelated existing `agents/` directory simply receives the file); the other two branches write
   nothing. Exactly one line is printed:
   - `$TARGET_DIR/agents/PROJECT.md` exists (tested with `[ -e ]`, so a directory or symlink of
     that name is also left alone): `codex-install: agents/PROJECT.md exists; left as is.`
   - else, `$TARGET_DIR/.claude/agents/PROJECT.md` is a file (a Claude install that may already be
     filled in): copy it and print
     `codex-install: created agents/PROJECT.md from .claude/agents/PROJECT.md; Codex agents read the root copy, so keep the two in step.`
   - else, `$SOURCE_DIR/agents/PROJECT.template.md` is a file: copy it and print
     `codex-install: created agents/PROJECT.md from the template; fill in its Test execution section.`
   - else (older `--source`): `codex-install: agents/PROJECT.template.md not in this source checkout; skipping agents/PROJECT.md.`
   The copy is verbatim: the file is user-owned, so its own bare pointers (e.g. "lives in
   `rules/research-depth.md`") are not rewritten.
3. **Docs** (`docs/codex-alpha-install.md`): `agents/PROJECT.md` joins the list of files written
   outside `.codex/` (the "writes three things" sentence becomes four) and the installer-output
   section, with the four lines above and what to fill in; the dual-runtime note says the root
   copy is seeded from `.claude/agents/PROJECT.md` once and the two are separate files after.
4. **Closure test**: extend the payload closure check to the rendered agent TOML (decoded
   `developer_instructions`): no bare payload-eligible path is left, and every prefixed path
   exists in the payload.

## Error behavior

| Condition | Result |
| --- | --- |
| A rewritten profile fails `parse_codex_profile` | render raises; deploy aborts before any write |
| `agents/PROJECT.md` exists | left untouched; "exists; left as is" line |
| `.claude/agents/PROJECT.md` exists, root copy missing | seeded from the `.claude` copy |
| Template missing in `--source`, no `.claude` copy | skip line; install exits 0 |
| `--dry-run` / `--remove` | no `agents/PROJECT.md` created; `--remove` leaves an existing one |

## Tests

- `scripts/test_render_codex_adapter.py`: rendered `coding.toml` / `reviewer.toml` cite
  `.codex/.agent-harness/payload/rules/…` and no bare `rules/…`; `agents/PROJECT.md` and
  `agents/runtime-bindings.json` stay bare; every profile still parses; two renders are
  byte-identical; Claude rendering unchanged (existing test); closure extended to TOML.
- `tests/scripts/codex-install-next-step.test.sh`: fresh install creates `agents/PROJECT.md`
  equal to the template and prints its line; an existing one is byte-identical after install and
  prints the "exists" line; a target with `.claude/agents/PROJECT.md` gets a root copy equal to
  it; the existing stub `--source` (no template) prints the skip line; `--dry-run` creates none;
  `--remove` leaves it.

## Out of scope

- The optional live evidence of whether a Codex child session loads root `AGENTS.md` (needs a
  Codex binary; folded into #269's live capture).
- Rewriting the copied `agents/PROJECT.md` (user-owned; its bare "lives in" pointers stay).
- Keeping a root copy and `.claude/agents/PROJECT.md` in sync after the first seed.
- The Claude-side equivalent (Claude profiles also cite bare `agents/PROJECT.md` and `rules/…`
  while the files live under `.claude/`; pre-existing, unchanged here).
