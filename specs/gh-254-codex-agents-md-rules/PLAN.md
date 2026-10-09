---
slug: gh-254-codex-agents-md-rules
status: proposed
owner: Minh Tran
created: 2026-10-09
---

# Deliver the always-on rules via a shared, runtime-neutral AGENTS.md

## 1. Motivation

Issue #254 (tracking #257), building on #253 / PR #259. A Codex session receives none of the five
always-on rules; the managed `AGENTS.md` block is a one-line pointer to a file that only mentions
rules. Design: `specs/gh-254-codex-agents-md-rules/design.md` (render the five rules inline into
the managed block, 20 KiB budget, retire `.codex/harness-instructions.md`). Research:
`specs/gh-254-codex-agents-md-rules/research-brief.md` (Codex 0.147.0 truncates the root→cwd
chain at the byte once 32 KiB is reached; a root `AGENTS.override.md` hides `AGENTS.md`).

## 2. Non-goals

- Rewriting rule content, or changing which rules are always-on vs path-scoped.
- Fixing the rules' source-name citations (`agents/reviewer.md`, `hooks/commit-gate.sh`, …).
- Hook trust, doctor reasons, installer next step (#255); a combined installer (#256).
- Reading a user's `project_doc_max_bytes` override (the size warning assumes the 32 KiB default
  and says so).

## Global Constraints

- Run `bash scripts/run-tests.sh` before the first `scripts/` edit and once after all tasks;
  record the result in SUMMARY prose, never as a Verify row.
- Claude install and deploy output stay byte-identical: no edit to `scripts/deploy-harness.sh`,
  `scripts/install-harness.sh`, or any `rules/*.md`.
- The always-on set is derived from frontmatter (no `paths:` key ⇒ always-on), exactly as
  `tests/scripts/rule-loading-tiers.test.sh` `has_paths_frontmatter` does; never a hand list.
- The managed-block lifecycle (insert / hash-gated replace / sidecar / remove) is reused, not
  rewritten. Root `AGENTS.md` outside the markers is never modified.
- Text is read and written as UTF-8 everywhere the block is handled; the budget is UTF-8 bytes.
- Bash stays macOS 3.2 compatible; Python 3 stdlib only. Tests use the fake-Codex harness and
  never touch the real `~/.codex` or the network.
- Verify commands are pipe-free, a single command, and finish in under 60 s.

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
| --- | --- | --- | --- |
| SC-1 | The rendered block inlines exactly the frontmatter-derived always-on rules (payload-rewritten text, `Source:` payload path each) and lists exactly the path-scoped rules with existing payload paths and their `paths:` globs | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k agents_block_inventory` | exit 0 |
| SC-2 | Render fails closed when the block exceeds 20 KiB, when a rule contains a marker string, or when the always-on set is empty; the current block is ≤ 18 KiB | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k agents_block_budget` | exit 0 |
| SC-3 | The block's own text carries no runtime-specific syntax (`@` import line, `/skill` or `$skill` invocation, "for Codex"), and two renders are byte-identical | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k agents_block_neutral` | exit 0 |
| SC-4 | Render writes `<output>/agents-block.md`, removes a stale one, and no longer emits `project/.codex/harness-instructions.md` | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k agents_block_output` | exit 0 |
| SC-5 | Install puts every always-on rule's text inside the markers; an install from the one-line block upgrades in place; an edited block gets an `AGENTS.md.harness-incoming`; an unchanged retired `.codex/harness-instructions.md` is pruned and an edited one kept; a missing block file fails before `AGENTS.md` changes; root `AGENTS.override.md` and an over-32-KiB `AGENTS.md` each print a warning; `--remove` strips the section | `bash tests/scripts/codex-install.test.sh` | exit 0 |
| SC-6 | The rendered block's inlined-rule inventory equals the shell-derived always-on tier, compared in both directions | `bash tests/scripts/rule-loading-tiers.test.sh` | exit 0 |
| SC-7 | Docs describe the block, the budget and truncation, the `AGENTS.override.md` caveat, and the `AGENTS.md`/`CLAUDE.md` interplay; the doc-truth lint passes | `bash scripts/lint-doc-truth.sh` | exit 0 |
| SC-8 | Claude rendering is unchanged by a Codex render | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k claude_rendering_is_unchanged` | exit 0 |

## 4. Tasks

### Task 1.1 — Render the managed AGENTS.md block (wave 1)

- **Files:** scripts/render_codex_adapter.py, adapters/codex/project/harness-instructions.md, scripts/test_render_codex_adapter.py
- **Action:** Write the failing tests first, named so the SC `-k` filters select them:
  `test_agents_block_inventory_*` (SC-1), `test_agents_block_budget_*` (SC-2: over 20 KiB, marker
  inside a rule, empty always-on set — each via a cloned render root — and current size
  ≤ 18 KiB), `test_agents_block_neutral_*` (SC-3), `test_agents_block_output_*` (SC-4). Then
  implement per `design.md` §Components 1–2:
  - `always_on_rules(rules_dir)` / `path_scoped_rules(rules_dir)` using the `has_paths_frontmatter`
    test (line 1 is `---`, a `paths:` line before the closing `---`); path-scoped returns the
    `paths:` globs;
  - `render_agents_block(preamble, payload_rules_dir)` → text with both markers: preamble; per
    always-on rule sorted by name, `Source: .codex/.agent-harness/payload/rules/<name>` then the
    rule text verbatim with leading frontmatter stripped and only trailing whitespace at file end
    removed; subsections joined by `\n\n---\n\n`; then the on-demand list. Raise `AdapterError`
    over `AGENTS_BLOCK_MAX_BYTES = 20 * 1024` UTF-8 bytes, on a marker inside a rule, or on an
    empty always-on set;
  - `render()`: delete a stale `<output>/agents-block.md` with the other owned outputs, write the
    new block (UTF-8) from the payload rules after the rewrite, and stop copying
    `harness-instructions.md` into `project/`.
  Edit `adapters/codex/project/harness-instructions.md` in place to be runtime-neutral: title
  "Agent Harness", no "for Codex", `agents/PROJECT.md` named as "if present", and a sentence that
  the rules below are always-on.
- **Verify:** `python3 -m pytest scripts/test_render_codex_adapter.py -q`
- **Done:** All tests in the file pass, including the four new groups and the existing
  byte-stability and Claude-unchanged tests.
- **Criteria:** SC-1, SC-2, SC-3, SC-4, SC-8
- **Interfaces:** Consumes the payload rules from #253's render and the preamble source; produces `<output>/agents-block.md` and `render_agents_block()` in `scripts/render_codex_adapter.py`.

### Task 2.1 — Deploy the rendered block (wave 2)

- **Files:** scripts/deploy-codex-adapter.sh, tests/scripts/codex-install.test.sh
- **Action:** Rewrite the assertions that encode the old behaviour first (`:84`, `:128`
  harness-instructions in installed files / `project_files`; `:148-157` update marker — now
  appended to a rule source copy and asserted inside the `AGENTS.md` block; `:169`, `:182`,
  `:189` literal one-line text), then add failing cases: every always-on rule's first heading
  inside the markers after a fresh install; upgrade from a seeded pre-#254 state (one-line block
  with its hash in the deployment manifest, plus a manifest-owned unchanged
  `.codex/harness-instructions.md`) replaces the block and prunes the file; the same with an
  edited file keeps it; a source whose render emits no block file fails with `AGENTS.md`
  byte-identical; root `AGENTS.override.md` prints `AGENTS.override.md`; a large user `AGENTS.md`
  pushing the result over 32768 bytes prints `32 KiB`. Then implement per `design.md`
  §Components 3: `sync_project` takes the block path as a third argument
  (`sync_project install "$WORK/rendered/project" "$WORK/rendered/agents-block.md"`), reads and
  validates it (exists, non-empty, starts with the begin marker, ends with the end marker) before
  the first write, reads `AGENTS.md` with `encoding="utf-8"`, and prints both non-fatal
  warnings after the write. Remove mode is unchanged.
- **Verify:** `bash tests/scripts/codex-install.test.sh`
- **Done:** The suite exits 0 with the new cases; `bash -n scripts/deploy-codex-adapter.sh`
  exits 0.
- **Criteria:** SC-5
- **Interfaces:** Consumes `<output>/agents-block.md` from Task 1.1; produces the managed section written by `scripts/deploy-codex-adapter.sh`.

### Task 2.2 — Codex path in the rule-tier inventory test (wave 2)

- **Files:** tests/scripts/rule-loading-tiers.test.sh
- **Action:** Add a case that renders the adapter into a temp directory
  (`python3 "$ROOT/scripts/render_codex_adapter.py" --root "$ROOT" --output <tmp>`), extracts the
  `Source: .codex/.agent-harness/payload/rules/<name>` lines from `agents-block.md`, and asserts
  the set equals the existing `$always` set in both directions (no extra, none missing). Write it
  to fail first by asserting against a deliberately wrong expected set, then correct it.
- **Verify:** `bash tests/scripts/rule-loading-tiers.test.sh`
- **Done:** The suite exits 0 with the new case.
- **Criteria:** SC-6
- **Interfaces:** Consumes `scripts/render_codex_adapter.py` from Task 1.1; produces the Codex-path case in `tests/scripts/rule-loading-tiers.test.sh`.

### Task 2.3 — Document the block and the AGENTS.md / CLAUDE.md interplay (wave 2)

- **Files:** docs/codex-alpha-install.md
- **Action:** Replace `.codex/harness-instructions.md` in the installed-file list (`:39`) with the
  managed block. Add a section: what the block contains (five always-on rules inline, on-demand
  list), why inline (no include mechanism in Codex), the 32 KiB default budget and byte
  truncation of the root→cwd chain with the 20 KiB block cap, the `AGENTS.override.md` caveat,
  and for users running both tools: Claude reads `AGENTS.md` only without a
  `CLAUDE.md`/`.claude/CLAUDE.md`/`CLAUDE.local.md` (v2.1.277+), the `@AGENTS.md` bridge, the
  `claude-md-and-agents-md` setting (user/managed settings only), and the ~14 KB double load
  when both `.claude/rules/` and the block are read.
- **Verify:** `bash scripts/lint-doc-truth.sh`
- **Done:** The lint exits 0; `grep -c "AGENTS.override.md" docs/codex-alpha-install.md` ≥ 1 and
  `grep -c "harness-instructions" docs/codex-alpha-install.md` = 0.
- **Criteria:** SC-7
- **Interfaces:** Consumes the design and research facts; produces the updated `docs/codex-alpha-install.md`.

## 5. Risks

- A rule grows past the budget: the ≤ 18 KiB test fails in that PR before any install fails.
- Upgrade path depends on the stored `agents_block_hash` matching the one-line block; the seeded
  pre-#254 test pins it.
- Truncation behaviour is read from Codex source, not observed in a run (no `codex` on this host).

## 6. Status Log

- 2026-10-09 — plan written from the approved design and research brief.
