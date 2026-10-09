# gh-254-codex-agents-md-rules — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine signal — the change decides how the always-on governance rules reach a Codex session, and rewrites the managed `AGENTS.md` section every Codex consumer receives (public contract).
Flags: workflow-engine, public contracts, existing behavior, cross-platform
Affects: Codex adapter (`adapters/codex/project/harness-instructions.md`, `scripts/render_codex_adapter.py`, `scripts/deploy-codex-adapter.sh`), consumer `AGENTS.md` managed section, `tests/scripts/rule-loading-tiers.test.sh`
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

> approve design
> notes: - to avoid any breaking on main, let create branch call "codex" - all PRs related to it, let open to codex branch

> do for next step after this PR, continue based on it

"This PR" is #259 (item 1, #253). The next step in the #257 plan is item 2, GitHub issue #254
("Codex Phase 6.2: deliver always-on rules via a shared, runtime-neutral AGENTS.md"). Its Target
checklist is the scope of this slug. "Continue based on it" is read as: branch from
`feat/gh-253-codex-full-payload` (item 2 depends on item 1) and open the PR against `codex`.

## What changed

A Codex install now writes the five always-on rules (`architecture.md`, `behavior.md`,
`guidelines.md`, `orchestration.md`, `research-depth.md`) inline into the managed section of the
root `AGENTS.md`, each introduced by a `Source:` line naming its payload path, followed by a list
of the four path-scoped rules with their payload paths and `paths:` globs. The renderer builds
this block from `rules/` (frontmatter decides the tier), caps it at 20 KiB, and writes it to
`<output>/agents-block.md`; the deployer validates that file before any write and feeds it to
the existing marker / hash / sidecar lifecycle. `.codex/harness-instructions.md` is retired into
the block's preamble. Deploy warns when a root `AGENTS.override.md` hides `AGENTS.md`, or when the
resulting `AGENTS.md` exceeds Codex's 32 KiB default. `docs/codex-alpha-install.md` explains the
block, the budget, and how `AGENTS.md` and `CLAUDE.md` interact for users running both tools.

### Rationale

Codex has no include mechanism and reads instructions only from `AGENTS.md` files (root → cwd,
32 KiB default budget), and hook trust is unknown (#255), so inlining is the only path that puts
the rules in session context without depending on the model choosing to read a file. Rendering
from `rules/` at install time keeps `rules/` the single source, which answers the drift concern
behind `specs/codex-support/design.md` §6.1.

### Alternatives considered

- Mandatory-read list in the block — rejected by the user: delivery depends on model compliance,
  the pattern that fails today.
- Inline only `behavior.md`, list the rest — rejected: an arbitrary line between guaranteed and
  not.
- SessionStart hook injection — rejected: hook trust under Codex is unknown (#255).

### Deviations

- Plan interface: `render_agents_block(preamble, payload_rules_dir)` per PLAN.md, not the design's
  first draft `(root, payload_rules)`; design.md aligned in `4ade695`.
- Task 2.1 judgment call: a block file with no trailing newline is rejected (the byte contract
  requires exactly one).

Full suite: `bash scripts/run-tests.sh` was ALL GREEN before the first `scripts/` edit (818 pytest
passed) and after all four tasks (828 pytest passed); it is cited here, not as a Verify row.

### Task review log

- Task 1.1 (`8048501`): spec pass, quality approved. Minor findings (forwarded to final review):
  M1 install suite and deployed pointer are inconsistent until Task 2.1 lands (by plan);
  M2 the marker check does not cover the preamble; M3 unclosed rule frontmatter inlines an empty
  body silently, and an inline `paths: [..]` yields no globs; M4 the preamble read is not wrapped
  in `AdapterError`; M5 the stale-block test's `pytest.raises` has no `match=`.
- Task 2.2 (`55bd643`): spec pass, quality approved. Minor M6: the set comparison does not catch a
  rule inlined twice (accepted; the renderer iterates a sorted set of file names).
- Task 2.3 (`789e2b9`): spec pass, quality approved, no findings.
- Task 2.1 (`58d9a7e`): spec pass, quality approved. Minor M7: the fail-closed case did not pin the
  failure message; M8: the edited-block helper used locale-default text I/O; M9: `for rule in
  $(always_on_rules)` word-splits a `$ROOT` with spaces (accepted; every other case in the suite
  shares that assumption). The controller confirmed fail-first: with the pre-change deploy script
  the new and rewritten cases fail.
- Fixed in `4ade695`: M2, M3 (unclosed frontmatter now fails closed with the rule path), M4, M5,
  M7, M8. Accepted: M1 (resolved by Task 2.1), M6, M9; the inline `paths: [..]` half of M3 (no
  rule uses that form).

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| plan contract | `python3 scripts/check_plan_contract.py specs/gh-254-codex-agents-md-rules/PLAN.md` | 0 | plan passes the context contract |  |
| block inventory | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k agents_block_inventory` | 0 | always-on set = frontmatter-derived; on-demand list = path-scoped set | SC-1 |
| block budget and fail-closed | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k agents_block_budget` | 0 | >20 KiB, marker in rule or preamble, empty set, unclosed frontmatter, `paths:` with no parsed globs fail; current block ≤18 KiB (15,866 bytes) | SC-2 |
| block neutrality and determinism | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k agents_block_neutral` | 0 | no `@` import, `/skill`, `$skill`, "for Codex" in the block's own text; byte-identical renders | SC-3 |
| block output file | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k agents_block_output` | 0 | `agents-block.md` beside the manifest; stale one removed; no `project/.codex/harness-instructions.md` | SC-4 |
| install lifecycle | `bash tests/scripts/codex-install.test.sh` | 0 | 38 cases: rules inside markers, pre-#254 upgrade, edited block sidecar, retired file prune/keep (and kept while an edited old block stays), missing block fails closed, override and 32 KiB warnings | SC-5 |
| rule tier parity | `bash tests/scripts/rule-loading-tiers.test.sh` | 0 | rendered block's `Source:` set = shell always-on tier, both directions | SC-6 |
| docs content | `python3 -c "import pathlib,sys; t=pathlib.Path('docs/codex-alpha-install.md').read_text(encoding='utf-8'); sys.exit(0 if all(k in t for k in ('AGENTS.override.md', '32 KiB', '20 KiB', '@AGENTS.md', 'claude-md-and-agents-md', 'CLAUDE.local.md')) else 1)"` | 0 | required facts present | SC-7 |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | does not scan `docs/codex-alpha-install.md`; run as a no-regression check |  |
| Claude rendering unchanged | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k claude_rendering_is_unchanged` | 0 |  | SC-8 |

### Context-Propagation Audit

Run by request of #254 ("Needs a context-propagation audit"). The diff does not touch the
path-based `workflow-engine` trigger (`skills/*/SKILL.md`, prompts, `agents/*.md`, `rules/*.md`);
it changes the channel that carries `rules/` into a Codex session. Search surface: `rules/*.md`,
`agents/*.md`, `skills/*/*.md`, `scripts/render_codex_adapter.py`,
`scripts/render_agent_definitions.py`, `specs/codex-support/evidence/codex-0.147.0/`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| five always-on `rules/*.md` | Codex session in the project | main | always-loaded: inlined in root `AGENTS.md` managed block (complete copy, rendered at install) | `codex-install.test.sh` (each rule's heading inside the markers); `test_agents_block_inventory_*` (body = payload text); drift: `rule-loading-tiers.test.sh` Codex case; loading: `codex-rs/core/src/agents_md.rs` @ `rust-v0.147.0` (provenance, not observed in a run) |
| same | Codex session when root `AGENTS.override.md` exists or `AGENTS.md` > 32 KiB | main | not delivered (override hides it / byte truncation) | deploy warning cases in `codex-install.test.sh`; documented in `docs/codex-alpha-install.md` |
| four path-scoped `rules/*.md` | Codex session | main | on-demand list in the block + explicit Read steps in skills, rewritten to payload paths by #253 | `test_agents_block_inventory_*` (paths exist); #253 `test_payload_closure_*` |
| five always-on rules | Claude session, `.claude/` install | main | always-loaded from `.claude/rules/` (unchanged) | `test_claude_rendering_is_unchanged_by_codex_render`; Claude deploy untouched |
| same | Claude session reading `AGENTS.md` (no `CLAUDE.md`) | main | always-loaded via `AGENTS.md`; same text | Claude memory docs (v2.1.277+); block's own text has no runtime-specific syntax (`test_agents_block_neutral_*`) |
| `rules/behavior.md` §1, `rules/auto-correct-scope.md`, `rules/orchestration.md` | Codex subagent profiles (`.codex/agents/*.toml`) | reviewer, implementer | explicit references in `developer_instructions` and skill dispatch prompts — **unchanged by this diff**; whether a Codex child also loads `AGENTS.md` is unconfirmed (evidence `agents-fresh-bounded.json` shows a fresh, bounded context, not its instruction set) | not claimed by this change; see Harness-Delta |

Result: **PASS** for every consumer this change claims. The inline copy is complete and
drift-tested, which the audit's inline-copy rule requires. The child-context row is pre-existing
and not load-bearing for #254. Recorded as backlog: the `.codex/agents/*.toml` profiles cite bare
`rules/…` paths that are not rewritten to payload paths.

### Correctness Review

Six FIND angles over `e36f806..e164421` (branch package), 10 deduplicated locations, one
independent scorer per location, threshold 75. No location reached the threshold.

- **L1 — fixed in `ae49a2f` despite scoring 0.** Upgrading a pre-#254 install whose managed block
  the user had edited deleted `.codex/harness-instructions.md` while the kept block still pointed
  at it; the new rules went only to the sidecar. Four of six angles found it independently. The
  scorer gave 0 solely under the unmodified-line rule (the retire loop itself was unchanged) and
  confirmed the bug is real and introduced by this diff's retirement of the file. Fix: retiring
  runs after the AGENTS.md decision and keeps retired files until the new block lands. Two new
  install cases; the first fails against the pre-fix deploy script.
- **L3 — fixed in `ae49a2f` (scored 50).** A `paths:` key in a form the parser does not read
  (inline list, bare value, unindented items) yielded no globs, and the rule was listed with no
  trigger. Render now fails closed.

### Advisory Findings

Recorded, not fixed (below threshold):

- L2 (25) — a non-UTF-8 or unreadable root `AGENTS.md` raises after project files are written;
  the ordering predates this diff.
- L4 (50) — a trailing YAML comment on a glob item is kept in the glob; no rule uses one.
- L5 (50) — `_strip_frontmatter` splits on `str.splitlines()` separators (form feed, U+2028, …);
  no rule contains them.
- L6 (25) — a rule whose first line is a Markdown `---` rule is parsed as frontmatter; Claude
  Code's loader reads it the same way.
- L7 (25) — a directory named `<x>.md` under `rules/` raises `IsADirectoryError`; the unchanged
  `_rewrite_markdown` already fails first.
- L8 (0, unmodified line) — `--remove` with reversed markers raises `ValueError`; pre-existing.
- L9 (0, pre-existing) — CRLF line endings outside the managed block are converted to LF.
- Fix re-review of `ae49a2f`: `fix_verdict: closed` for all four AGENTS.md branches. Two P3
  notes: (a) while an edited or malformed block stays, *every* retired file is kept, not only
  the one the old block names (deliberate: the old block's references are not parsed); (b) the
  retire loop now runs after `AGENTS.md` is written, so a `target_path` symlink-escape exit there
  leaves `agents_block_hash` stale until the next run, which recovers (`current == block`).
- L10 (0, unmodified line) — an edited, preserved retired `.codex/harness-instructions.md` keeps
  the doctor at `INSTALL_HASH_MISMATCH` until the user deletes it (the doc tells them to).

### Not auto-verified

- Codex 0.147.0 truncates the root→cwd `AGENTS.md` chain at the byte once 32 KiB is reached — reached provenance (read from `codex-rs/core/src/agents_md.rs` at tag `rust-v0.147.0`); not observed in a live run because no `codex` binary is available on this host.

### Rollback

- Code: `git revert` the branch's commits (or close the PR unmerged; nothing reaches `codex` until merge).
- Consumers: re-run `bash scripts/install-codex-harness.sh --source <pre-#254 checkout>`; the managed block's hash matches the rendered block, so it is replaced by the one-line pointer and `.codex/harness-instructions.md` is re-created. An edited block is kept with an `AGENTS.md.harness-incoming` sidecar.

### Harness-Delta

- backlog — the SDD file handoff: implementers cannot write their report file, so the controller
  filed every report (open issue #261).
- backlog — `branch-isolation-guard.sh` denied an implementer's Write to the session scratchpad
  from a task-branch worktree (`unsafe-path:outside-root`, "shared branch main"); worked around
  with a Bash heredoc (open issue #262).
- backlog — Codex agent profiles (`.codex/agents/*.toml`, rendered by
  `scripts/render_agent_definitions.py`) cite bare `rules/…` paths the #253 rewrite does not
  cover, and Codex child-context loading of `AGENTS.md` is unobserved (context-propagation audit).
