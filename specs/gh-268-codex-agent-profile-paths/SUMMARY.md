# gh-268-codex-agent-profile-paths — Summary

Lane: high-risk
Confidence: medium
Reason: workflow-engine delivery — the change rewrites what isolated Codex subagent contexts (`.codex/agents/*.toml` `developer_instructions`) are told and adds a consumer-owned file at install; one material choice (how a Codex-only consumer gets `agents/PROJECT.md`) needs the user.
Flags: workflow-engine, public contracts, existing behavior, cross-platform
Affects: `scripts/render_codex_adapter.py` (agent profile render), Codex installer, `docs/codex-alpha-install.md`
Input-type: spec slice
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: yes (agents/PROJECT.md delivery has three materially different options; asked at brainstorming)

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> current the hook scripts are not available with codex
> and the claude code now support AGENTS.md file
> let review and checking if we can support user with codex if they want to install our harness-skill

> approve design
> notes: - to avoid any breaking on main, let create branch call "codex" - all PRs related to it, let open to codex branch

> ok, let check sub-agent profile issue. and go to next phase 6 itme

> 268 first

This slug is GitHub issue #268 ("Codex Phase 6: agent profiles cite bare rules/ paths that a
Codex install does not have"), filed from the #254 context-propagation audit. Its Target checklist
is the scope. The branch stacks on `feat/gh-255-codex-hook-trust` (PR #271); the PR targets
`codex`.

## What changed

The rendered Codex agent profiles now point at files a Codex install has. The renderer rewrites
the decoded `developer_instructions` of each `.codex/agents/*.toml` with #253's
`rewrite_payload_paths`, so `coding.toml` cites `.codex/.agent-harness/payload/rules/orchestration.md`
and `…/auto-correct-scope.md`, and `reviewer.toml` cites `…/rules/behavior.md`; a malformed
profile line fails the render closed. The Codex installer now creates `agents/PROJECT.md` when it
is missing — seeded from `.claude/agents/PROJECT.md` when a Claude install has one, else from
`agents/PROJECT.template.md` — and prints exactly one line saying what it did (including a
failed copy). The file is user-owned, meant to be committed, not in the manifest, never
overwritten, and left by `--remove`. `docs/codex-alpha-install.md` documents both.

### Rationale

Rewriting only the derived Codex render (the same rule #253 applied to skills) fixes the paths
without touching the shared `agents/*.md` sources or Claude output; rewriting the decoded string
is required because, on encoded text, a path after a `\n` escape is skipped by the token anchor.
`agents/PROJECT.md` is a team-maintained file, so it belongs at the project root (committable),
not in the gitignored payload; the user chose the installer as its creator.

### Alternatives considered

- Create `agents/PROJECT.md` from the shared `init-structure.sh` — rejected by the user: Claude
  installs would get a second, unread copy.
- Have the profiles say "read agents/PROJECT.md if present" — rejected: agents in a project
  without it get no test-command guidance.
- Pass a rewrite callback into `render_codex` — rejected: changes a Claude-shared function's
  signature; the post-render decode/re-encode keeps Claude code untouched.
- Always seed from the blank template — the user approved seeding from an existing
  `.claude/agents/PROJECT.md` instead.

### Deviations

- Rule 2 (Task 1.1) — the profile rewrite raises `AdapterError` when a profile lacks exactly one
  `developer_instructions` line (`b81095a`); hardened for non-JSON values in `1608b6a`.
- Rule 2 (Task 2.1) — also added `agents/PROJECT.md` to the doc's "Remove and recover" list so it
  agrees with the new install step (`43ec345`).

### Task review log

- Task 1.1 (`b81095a`): spec pass, quality approved. Minor M1 (non-JSON `developer_instructions`
  raised a bare `JSONDecodeError`) and M2 (the one-line guard was untested) fixed in `1608b6a`.
- Task 1.2 (`d925da2`): spec pass, quality approved. Minor M3 (a failed `mkdir`/`cp` printed
  no installer line) fixed in `126c794` with a fifth line and a test (`agents` pre-created as a
  file).
- Task 2.1 (`43ec345`): spec pass, quality approved. Minor M4: the inserted profile sentence made
  "Because the manifest lists it" read as if `agents/PROJECT.md` were manifest-owned, plus line
  wrap; fixed in `10903f6`.

Full suite: `bash scripts/run-tests.sh` was ALL GREEN before the first `scripts/` edit and after
all tasks (845 pytest passed); cited here, not as a Verify row.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane gh-268-codex-agent-profile-paths` | 0 | intake |  |
| profiles cite payload rules | `python3 -m pytest scripts/test_render_codex_adapter.py -q -k agent_profile` | 0 | 4 agent_profile tests + 3 fail-closed cases | SC-1 |
| renderer suite | `python3 -m pytest scripts/test_render_codex_adapter.py -q` | 0 | 52 tests incl. Claude rendering unchanged and payload closure | SC-2 |
| installer agents/PROJECT.md step | `bash tests/scripts/codex-install-next-step.test.sh` | 0 | 24 cases: template, customized .claude seed, untouched current and older-version .claude copies fall back to the template, exists, dangling symlink left alone, skip, failed copy, dry-run, remove | SC-3 |
| codex install suite | `bash tests/scripts/codex-install.test.sh` | 0 | 38 cases | SC-4 |
| docs content | `python3 -c "import pathlib,sys; t=pathlib.Path('docs/codex-alpha-install.md').read_text(encoding='utf-8'); sys.exit(0 if all(k in t for k in ('agents/PROJECT.md', 'four things', 'created agents/PROJECT.md from the template', 'created agents/PROJECT.md from .claude/agents/PROJECT.md', 'agents/PROJECT.md exists; left as is', 'four more steps', 'skipping agents/PROJECT.md')) else 1)"` | 0 | required lines present | SC-5 |
| .gitignore suite unchanged | `bash tests/scripts/codex-install-gitignore.test.sh` | 0 | 14 cases |  |

### Context-Propagation Audit

Requested by #268 (it changes what isolated Codex subagent contexts are told). Search surface:
`agents/{coding,reviewer,task-reviewer,test-runner}.md`, a fresh render of
`.codex/agents/*.toml` decoded through `parse_codex_profile`, `scripts/render_codex_adapter.py`,
`scripts/install-codex-harness.sh`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `rules/orchestration.md`, `rules/auto-correct-scope.md` | Codex `coding` profile | implementer (child) | explicit Read path in `developer_instructions`, now `.codex/.agent-harness/payload/rules/…` | `test_agent_profile_cites_payload_copies_of_rules`; fresh-render check: both paths are files in the payload |
| `rules/behavior.md` §1 | Codex `reviewer` profile | reviewer, scorer, intent (child) | explicit Read path, now payload path | same test and render check |
| `agents/PROJECT.md` *Test execution* | Codex `coding`, `test-runner` profiles | implementer, test runner (child) | explicit Read path at the project root; the installer creates the file when missing | `codex-install-next-step.test.sh` cases (template, `.claude` seed, exists, skip, failed copy) |
| `agents/runtime-bindings.json` | all four profiles | — | provenance note ("generated from …"), not a read instruction | inspected in the rendered text |

Result: **PASS** — every file a rendered Codex profile tells an agent to read exists after a Codex
install. Not observed: whether a Codex child session also loads root `AGENTS.md` (#269).

### Correctness Review

Six FIND angles over `3b47767..04038a1`, 6 deduplicated locations, one independent scorer each,
threshold 75. No location reached the threshold.

- **Fixed anyway in `e7444b1` (scored 50; introduced by this diff):** P — an untouched
  `.claude/agents/PROJECT.md` is the harness repo's own file, so seeding from it gave Codex
  agents harness test commands (two angles); Q — a dangling `agents/PROJECT.md` symlink failed
  `[ -e ]` and `cp` wrote through it (five angles); R — a partly failed copy left a truncated
  file. New tests for P and Q fail on the pre-fix installer.
- Fix re-review of `e7444b1`: `fix_verdict: closed`; follow-on P2 (an untouched copy from an
  older harness version differs byte-wise) and P3 (PID-suffixed temp name) fixed in the next
  commit with the "harness repo itself" marker check, `mktemp`, and a test.

### Advisory Findings

- S (25) — the copied `agents/PROJECT.md` keeps bare "lives in `rules/…`" pointers; user-owned,
  deliberately not rewritten (design Out of scope).
- T (0, refuted) — the claimed locale encoding mismatch cannot occur (single-byte locales
  round-trip the UTF-8 bytes; multibyte non-UTF-8 locales fail earlier).
- U (0, unmodified hook line) — committing the new root `agents/PROJECT.md` in a consumer
  matches `hooks/commit-gate.sh`'s `workflow-engine` pattern `^agents/[^/]+\.md$` (warn-mode
  by default: a note, not a block; denied only under `RISK_CORROBORATION_STRICT=1` or a
  block-mode manifest). Excluding it means editing a hook — a Rule-4 high-blast change left for
  the user to decide.
- R has no direct test (a `cp` shim that fails mid-write would cover it).

### Not auto-verified

- That a live Codex subagent follows the rewritten Read paths — reached traceability (the
  rendered text and payload files are checked); not run in Codex (no binary on this host).
- `agents/PROJECT.md` seeded from `.claude/agents/PROJECT.md` stays useful only while the two
  copies agree — not checked; documented as the user's to keep in step.

### Rollback

- Code: `git revert` the branch's commits, or close the PR unmerged; nothing reaches `codex` until merge.
- Consumers: re-run `bash scripts/install-codex-harness.sh --source <pre-#268 checkout>`; the agent profiles are manifest-owned and are re-rendered (an edited profile is kept with a `.harness-incoming` sidecar).

### Harness-Delta

- none
