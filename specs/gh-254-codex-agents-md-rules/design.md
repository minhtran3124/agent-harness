---
slug: gh-254-codex-agents-md-rules
status: approved
issue: 254
tracking: 257
depends_on: 253
---

# Deliver the always-on rules via a shared, runtime-neutral AGENTS.md — Design

## Purpose

Claude Code auto-loads five always-on rules (`behavior.md`, `architecture.md`, `guidelines.md`,
`orchestration.md`, `research-depth.md`) from `.claude/rules/` every session. A Codex session
gets none of them. Today the Codex install writes a one-line managed block into the root
`AGENTS.md` (`deploy-codex-adapter.sh:140-146`):

```
<!-- agent-harness:begin -->
Read `.codex/harness-instructions.md` before using the Agent Harness.
<!-- agent-harness:end -->
```

and `.codex/harness-instructions.md` only *mentions* rules. So the harness skills run under Codex
without the governance they assume. #253 (PR #259) installed the rule files under
`.codex/.agent-harness/payload/rules/`; this item makes their content reach the session.

Goal: a Codex session receives the five always-on rules as part of its instruction chain, within
Codex's project-doc size cap, through an `AGENTS.md` section that reads correctly whether Codex or
Claude Code loads it.

## Facts this design rests on

- Codex builds its instruction chain once per run from `AGENTS.override.md` / `AGENTS.md` /
  fallback names, one file per directory, root → current directory, and **stops adding files once
  the combined size reaches `project_doc_max_bytes` (32 KiB default)**; the 0.147.0 source
  truncates the file that crosses the budget at the byte (`research-brief.md`). It has no import or
  include mechanism ([Codex AGENTS.md docs](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
  read 2026-10-09). Not yet observed against the pinned CLI 0.147.0 — recorded as unverified.
- Claude Code reads `AGENTS.md` only when no `CLAUDE.md` exists (default); `@AGENTS.md` inside
  `CLAUDE.md` is the documented bridge (https://code.claude.com/docs/en/memory).
- The five always-on rules total 13,980 bytes. They contain no `.claude/`-only instruction
  (`grep -n '\.claude/' rules/{behavior,architecture,guidelines,orchestration,research-depth}.md`
  finds one prose mention of "a `.claude/` copy", true in either runtime). They do cite harness
  component paths by their **source** name — `agents/reviewer.md`, `hooks/commit-gate.sh`,
  `skills/feature-intake/SKILL.md`, `skills/README.md`, `techstacks/` — which do not exist at a
  consumer's project root under Codex (plugin / `.codex/agents/*.toml`) **or under Claude**
  (`.claude/…`). That is pre-existing and runtime-independent; this item does not change it
  (rule content is out of scope).
- The tier is decided by the file: a rule **without** `paths:` frontmatter is always-on
  (`CLAUDE.md`; `tests/scripts/rule-loading-tiers.test.sh` `has_paths_frontmatter`).
- The SessionStart hook could inject the rules, but hook trust under Codex is `unknown` (#255),
  so it may not fire. Not a delivery path.

## Decision

**Render the five always-on rules inline into the managed block** (user-approved 2026-10-09 over
a mandatory-read list and an inline-`behavior.md`-only hybrid).

`specs/codex-support/design.md` §6.1 rejected "duplicated inline policy". That rejection targeted
hand-maintained copies that drift from the source. This block is *derived*: rendered from
`rules/` on every install, so it cannot drift, and the source of truth stays `rules/`. A
mandatory-read list was rejected because delivery would depend on the model choosing to read —
the pattern that fails today.

## Constraints

- Claude install output stays byte-identical; its tests pass untouched.
- Rule content is not rewritten and the always-on / path-scoped split does not change (issue
  out-of-scope).
- The always-on set is derived from frontmatter, never a hand list.
- The block is owned by the existing marker / hash / sidecar logic. No new lifecycle code: an
  upgrade from the one-line block is an ordinary "block changed, hash matches old" replace.
- Root `AGENTS.md` stays user-owned outside the markers (`specs/codex-support/design.md` D6).

## Architecture

```
rules/*.md ──(#253 payload copy + path rewrite)──► project/.codex/.agent-harness/payload/rules/
                                                        │
render_codex_adapter.render_agents_block() ◄────────────┘   + adapters/codex/project/harness-instructions.md (preamble)
        │
        ▼
<output>/agents-block.md   (beside render-manifest.json, outside project/ → never deployed as a file)
        │
deploy-codex-adapter.sh sync_project reads it ──► root AGENTS.md managed section
```

### Components

1. **`render_agents_block(preamble, payload_rules_dir)`** in `scripts/render_codex_adapter.py`. Deterministic
   function returning the block text including both markers:
   - preamble: the source file `adapters/codex/project/harness-instructions.md` is **edited in
     place** to be runtime-neutral (title "Agent Harness"; no "for Codex"; `agents/PROJECT.md`
     named as "if present") and keeps its name and location as a render input only;
   - one subsection per always-on rule, sorted by filename: a
     `Source: .codex/.agent-harness/payload/rules/<name>` line, then the payload-rewritten text
     verbatim (any leading YAML frontmatter stripped; headings **not** demoted);
   - subsections separated by a blank line, `---`, blank line; only trailing whitespace at the
     end of each rule file is stripped (rule lines are kept byte-for-byte), so the output is
     deterministic;
   - an on-demand list: each path-scoped rule's payload path plus its `paths:` globs as the
     "read when" trigger.
   The always-on set uses the same test as `rule-loading-tiers.test.sh` `has_paths_frontmatter`:
   line 1 is `---` and a `paths:` line appears before the closing `---`.
   Fails closed (`AdapterError`) when a rule contains either marker string, when the always-on
   set is empty, or when the block exceeds the **20 KiB budget** (`AGENTS_BLOCK_MAX_BYTES`,
   counted as UTF-8 bytes). 20 KiB leaves ≥12 KiB of the 32 KiB cap for the user's own
   `AGENTS.md` and nested files. A render-test asserts the current block is ≤18 KiB, so CI fails
   in the PR that grows a rule toward the limit, before any install fails.
2. **`render()`** deletes any stale `<output>/agents-block.md` with the other owned outputs,
   writes the new one (UTF-8), and stops copying `.codex/harness-instructions.md` into `project/`.
3. **`deploy-codex-adapter.sh`** `sync_project` gains a third argument, the block file path
   (`sync_project install "$WORK/rendered/project" "$WORK/rendered/agents-block.md"`). In install
   mode a missing or empty block file exits non-zero before any write; remove mode does not need
   it. `AGENTS.md` is read with `encoding="utf-8"` so the hash compare does not depend on the
   locale. When a root `AGENTS.override.md` exists, deploy prints a warning that Codex will load
   it instead of `AGENTS.md`, so the rules will not reach the session. Everything else
   (insert / replace / sidecar / remove) is unchanged.
4. **Retired file.** `.codex/harness-instructions.md` leaves the rendered `project/`, so the
   existing retired-file prune removes it when unchanged and keeps it when edited.

### Runtime neutrality

The block's own text (preamble, `Source:` lines, on-demand list) uses no runtime-specific syntax
(no `@` imports, no `/skill` or `$skill` invocation, no "for Codex" title) and names only paths
that exist after a Codex install. The inlined rule bodies are the rules as written; their
source-name citations (see Facts) resolve under Claude by the `.claude/` prefix and under Codex
only via the plugin or the `.codex/agents/*.toml` profiles — unchanged by this item. A Claude session that
loads `AGENTS.md` therefore reads the same governance it already has. A user with both runtimes
and the `@AGENTS.md` bridge loads the rules twice (`.claude/rules/` and the block), about 14 KB
of duplicated context per Claude session; documented, not prevented.

## Error behavior

| Condition | Result |
| --- | --- |
| Block over budget, marker inside a rule, empty always-on set | render exits 1 with `codex-adapter: …`; deploy aborts before writing (existing render-failure path) |
| User edited the block | kept; full incoming copy in `AGENTS.md.harness-incoming` (existing) |
| Upgrade from the one-line block | replaced, since its hash matches `agents_block_hash` (existing) |
| Edited `.codex/harness-instructions.md` on upgrade | preserved as an edited retired file (existing) |
| Rendered block file missing/empty at deploy | deploy exits non-zero before writing |
| Root `AGENTS.override.md` exists | block still written; deploy warns the rules will not load |
| Root `AGENTS.md` > 32 KiB after the write | block still written; deploy warns that Codex truncates at the 32 KiB default (`agents_md.rs:119-120`), cutting the rules at the file's end |

## Tests

- `scripts/test_render_codex_adapter.py`: block rule set equals the frontmatter-derived
  always-on set; on-demand list equals the path-scoped set with payload paths that exist;
  budget (fail above 20 KiB; current block ≤18 KiB), marker and empty-set failures; no
  runtime-specific syntax in the block's own text; deterministic output; stale block removed.
- `tests/scripts/codex-install.test.sh`: fresh install puts every always-on rule's text in
  `AGENTS.md`; upgrade from the one-line block; edited-block sidecar; retired
  `harness-instructions.md` pruned; removal still strips the section; `AGENTS.override.md`
  warning; missing block file fails closed. Existing assertions that encode the old behaviour are
  **rewritten**: `:84` and `:128` (harness-instructions in installed files / `project_files`),
  `:148-157` (update marker now asserted inside the `AGENTS.md` block), `:169`, `:182`, `:189`
  (literal one-line block text). The upgrade cases (one-line block → rendered block; retired
  `harness-instructions.md` pruned) start from a real pre-#254 state seeded into the target and
  its deployment manifest. The interrupted-update rollback case must still show `AGENTS.md`
  untouched when the block file is missing.
- `tests/scripts/rule-loading-tiers.test.sh`: a Codex-path case — the rendered block's rule
  inventory equals the shell-derived always-on tier, compared in both directions.

The explicit Read steps in consuming skills (`rules/plan-format.md` etc.) already resolve to the
payload through #253's render-time rewrite and its closure test; no new check here.

## Docs

`docs/codex-alpha-install.md`: replace `.codex/harness-instructions.md` in the installed-file
list (`:39`) with the block; what the block contains and why, the 32 KiB budget, the
`AGENTS.override.md` caveat, and the `AGENTS.md` / `CLAUDE.md` interplay for users running both tools (default precedence,
`@AGENTS.md` bridge, `claude-md-and-agents-md`, double loading).

## Out of scope

Rewriting rule content; changing tiers; hook trust (#255); a combined installer (#256).
