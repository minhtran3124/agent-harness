# Prompt audit: Claude Code configuration for `agent-harness`

## Assumptions

**Target model:** Sonnet 5.5, the model running this session. Agent files that pin a model (`claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`) are all current-generation, so none counts as a retired-model fossil.

**Scope, as found:**
- Project instruction files: `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`.
- `~/.claude/CLAUDE.md`.
- Project `.claude/`: 10 rule files, 6 agent files, 16 skills plus `skills/README.md`.
- User-level skills: `autopilot`, `create-pr`, `ink-artifact`.
- The `harness` plugin (`plugins/harness/`): 8 agents and 23 skills. It is report-only.

**Nothing found for:**
- Ancestor `CLAUDE.md` or `AGENTS.md`: none in the three parent directories.
- Managed-policy `CLAUDE.md`: `/etc/claude-code` does not exist.
- `@`-imports in `CLAUDE.md`: none.
- Commands or output styles: none, at either level.

**Not read, as the brief requires:**
- Settings files (`settings*.json`), `hooks.json`, `.mcp.json` and `~/.claude.json`.
- The symlinked skills `~/.claude/skills/wednesday-pulse` and `weekly-digest` (they point into another repo).
- Third-party plugin skills (vercel, compound-engineering, cloudflare and others), which are outside what I could audit here.

**Read only partly:**
- The legacy `.claude/` rules `plan-format`, `wave-parallelism`, `review-policy`, `auto-correct-scope`, `terminology` and `research-depth`.
- The legacy `.claude/` skills and the `harness` plugin skills. For these I used diffs, greps for the signal patterns, and a path-existence check. I did not read them end to end.

**Edits to `~/.claude/` files affect every project.** They are marked below.

## Summary

**1. The gitignored `.claude/` copy is a stale deployed copy of the harness, and it loads next to the plugin.**
- `.gitignore:23` ignores `.claude/`, and `.claude/.harness-deployed` is its manifest.
- Ten skills have the same name in both places but different content: `brainstorming`, `xia2`, `writing-plans`, `finishing-a-development-branch`, `using-git-worktrees`, `intent-review`, `compound`, `diagnosing-bugs`, `session-retro` and `asd-ste100` (4 lines differ).
- `.claude/agents/task-reviewer.md` is byte-identical to the plugin's copy. `coding` and `test-runner` duplicate `harness:implementer` and `harness:test-runner`.
- The legacy rules use a different vocabulary from `CLAUDE.md`: `PLAN.md`, `SUMMARY.md`, `feature-intake`, and lanes `tiny|normal|high-risk` against `plan.md`, `summary.md`, `intake` and depth `S|M|L`. `skills/README.md:10-14` describes a "Codex advisory alpha" and a `docs/codex-alpha-install.md` that does not exist, while `CLAUDE.md:3` says Claude Code is the only supported runtime.
- Both copies of `behavior.md` load into every session, and they differ.

**2. `AGENTS.md` and `CLAUDE.md` disagree with the repository.**
- `AGENTS.md` says "six subagent role files" (there are eight) and "four Bash hooks" (there are six).
- `CLAUDE.md:77` says every hook except `merge-guard.sh` fails open, but its own `stop-evidence.sh` row says it blocks on the risk floor.
- `CLAUDE.md:65` says "Every skill above exists … now", but `qa-writer` and `security-reviewer` are agents and `/code-review` is not a plugin skill.

**3. `CLAUDE.local.md:38-52` points at skills and terms that exist only in the legacy copy.** Examples are `feature-intake`, lanes, `Evidence Ledger`, `visual-planner --review` and `context-propagation-audit`. The current workflow in `CLAUDE.md:52-63` has none of them. The user-level `autopilot` and `create-pr` skills also carry broken or project-specific references.

**Counts**

| Group | Findings |
|---|---|
| 1. Dated prompt text | 0 high or medium; 2 low flags. Pressure language is sparse and the `MUST`/`NEVER` hits encode real contracts. |
| 2. Brittle configuration files | 11 |
| 3. Tool descriptions | 1 |
| 4. Roster | 1 (agent duplicates) |

By confidence: 7 high, 6 medium and 5 low or flag-only findings.

## Findings

### High confidence

| # | Location | Evidence | Pattern | Why obsolete | Action |
|---|---|---|---|---|---|
| H1 | `AGENTS.md:11` | "the six subagent role files" | G2 volatile specifics | `plugins/harness/agents/` holds 8 files: advisor, implementer, intent-reviewer, qa-writer, researcher, security-reviewer, task-reviewer, test-runner. | rewrite |
| H2 | `AGENTS.md:12` | "plus four Bash hooks: rule delivery …, secrets scan …, PR-opened reminder, merged-worktree cleanup" | G2 stale fact and self-conflict | `plugins/harness/hooks/` has six Bash hooks, adding `merge-guard.sh` and `stop-evidence.sh`. `AGENTS.md:39` itself names `merge-guard.sh`, and `CLAUDE.md:79-86` lists six. | rewrite |
| H3 | `.claude/rules/behavior.md:37` (also `:17-19`) | "`render_plan.py` lives under `skills/visual-planner/`"; "`agents/reviewer.md` and `skills/correctness-review/…`" | G2 volatile specifics, conflict | `find . -name render_plan.py` outside `.claude/` and `.git/` returns nothing. The copy lacks the "workflow stopped early" and "Done needs real command output" text and §6. `CLAUDE.md:69` names `plugins/harness/rules/behavior.md` as the single source of truth, and the session-start hook already delivers it. | remove |
| H4 | `.claude/agents/PROJECT.md:11,13,27` | "`techstacks/` is empty by design"; "`AGENTS.md` → *Coding Style & Naming Conventions* and *Testing Guidelines*"; mapping to `scripts/install-harness.sh`, `tests/scripts/install-harness.test.sh`, `skills/visual-planner/test_render_plan.py` | G2 volatile specifics | There is no `techstacks/` directory. `AGENTS.md` has no such headings (they are Layout, Commands, Style and tests, Commits and pull requests). The three mapped paths do not exist. Its readers are the legacy `coding` and `test-runner`, while the plugin `test-runner` reads `CLAUDE.md` → `## Run and test` (which exists, `CLAUDE.md:5`). | remove, together with M3 |
| H5 | `.claude/skills/README.md:10-14` | "**Codex advisory alpha** … `docs/codex-alpha-install.md`" | G2 conflict, stale fact | The doc does not exist. `CLAUDE.md:3` says Claude Code is the only supported runtime. | covered by F1 |
| H6 | `~/.claude/skills/create-pr/SKILL.md:77` (all projects) | `python3 .claude/skills/create-pr/scripts/check_pr_body.py …` | G2 volatile specifics | The script lives at `~/.claude/skills/create-pr/scripts/check_pr_body.py`. The project-relative path does not exist here. | rewrite |
| H7 | `.claude/rules/*`, `.claude/skills/*` against `CLAUDE.md` | `PLAN.md`, `SUMMARY.md`, `feature-intake`, lanes against `plan.md`, `summary.md`, `intake`, depth S/M/L | G2 contradictory instruction files | Two vocabularies for the same artifacts and gates load together. | see F1 |

### Medium confidence

| # | Location | Evidence | Pattern | Why obsolete | Action |
|---|---|---|---|---|---|
| M1 | `CLAUDE.md:65` | "Every skill above exists in `plugins/harness/skills/` now" | G1d migration-relative phrasing, inaccurate | The sentence is a diff against an earlier state. `qa-writer` and `security-reviewer` are agents, and `/code-review` is not in that directory. | rewrite |
| M2 | `CLAUDE.md:77` against `CLAUDE.md:85` | "all hooks fail open except `merge-guard.sh`" and "fails open, except on the risk floor" | G2 conflict inside one file | The `stop-evidence.sh` row says it blocks on the risk floor. `docs/hooks.md:10` repeats the "all except `merge-guard.sh`" wording, so it needs the same fix. That file is not instruction text, so it is outside the diff. | rewrite |
| M3 | `.claude/agents/coding.md`, `test-runner.md`, `task-reviewer.md` | `coding` is pinned to `claude-opus-5-5` and defers to `agents/PROJECT.md`; `task-reviewer` is identical to the plugin copy | G4 redundant specialist agents | `harness:implementer` has the same description at Sonnet 5.5, and `CLAUDE.md:23` assigns coding to Sonnet 5.5. The plugin `test-runner` replaced the PROJECT.md pointer with `CLAUDE.md`. Direction is an assumption: the tracked plugin wins over the untracked deploy. | remove |
| M4 | `CLAUDE.local.md:38-52` | "feature-intake … lane … `multi-domain` / high-blast flags"; "Evidence Ledger"; "visual-planner `--review` … `.plan-review.json`"; "context-propagation-audit"; "same-wave overlap" | G2 stale and conflicting | These terms occur only in the legacy `.claude/` skills (0 plugin matches in skills, agents and templates). The workflow in `CLAUDE.md:52-63` uses `intake`, depth and `/code-review`. | rewrite |
| M5 | `CLAUDE.local.md:24-34` | Table of nine `mcp__code-review-graph__*` tools with "Use when" cells | G3 prose lists shadow the real tool list | The MCP server already lists these tools and their descriptions. Keep the guidance on which questions need the graph. | rewrite |
| M6 | `~/.claude/skills/autopilot/SKILL.md:28` against `:23,:29,:32,:26,:64` (all projects) | Rule 7: "the project's CLAUDE.md / AGENTS.md apply and win over this skill"; rule 8: "not blindly `main` even if CLAUDE.md says…"; rule 10: "this overrides a project default"; Mode B merges PRs | G2 conflict inside one file | "Project wins" is stated, then three places override it. | rewrite |
| M7 | `~/.claude/skills/autopilot/SKILL.md:11,23,30,34,39,41,46,53` (all projects) | "Vietnamese in most past runs"; "past runs hit the 25-watched-artifact cap…"; "`apps/api/.env`"; "(past run: #46 was skipped…)"; "tokscope: `pr-assets`"; "~20 minutes"; "travel-pi's Anthropic milestone" | G2 history narratives, volatile specifics | A rule's authority is the behavior it prescribes. Keep the reasons and drop the incident IDs and project names. | rewrite |

### Low confidence or flag only (not in the diff)

| # | Location | Note |
|---|---|---|
| F1 | `.claude/` tree against the plugin | Tree-level conflict. `.claude/` has no git history, so blame cannot say which side is newer. Assumed direction: the tracked plugin and `CLAUDE.md` are current. **You decide:** remove the stale deploy or redeploy it. Other files depend on it. `create-pr/SKILL.md:90` and `:167` resolve here only through the legacy `asd-ste100` and `finishing-a-development-branch/references/pr-body.md`. `finishing-a-development-branch` has no `references/` in the plugin, so that pointer would break if the tree went. The `branch-isolation-guard.sh` hook that blocked writing this report also comes from this legacy deploy. |
| F2 | `~/.claude/skills/autopilot` against the project | `/autopilot` ("never ask, never use AskUserQuestion", Mode B merges PRs) conflicts with `/harness:autopilot` (asks first) and with `merge-guard.sh`, which denies merges in subagents. This is a cross-scope conflict, so no edit is proposed. |
| F3 | `~/.claude/skills/create-pr/SKILL.md:161` | "Tone: `CLAUDE.local.md` §11". This repo's `CLAUDE.local.md` has no numbered sections. Written for another project, so flag only. |
| F4 | `CLAUDE.md:28-31, 36-38` | "It thinks for itself … Effort is not fixed" repeats `:20-22`, and the parallel-spawn rule restates a tool default. The copies agree, so keep-list item 8 applies. |
| F5 | `CLAUDE.local.md:56-58` | "even a familiar one" repeats the Context7 server's own instruction. Low confidence that it over-triggers. |
| F6 | Plugin, report only | `plugins/harness/agents/test-runner.md:16`: "Legacy fallback (one release)" is a time-sensitive clause. `plugins/harness/skills/tickets/SKILL.md:13`: a `## NEVER` list, which reads as a real constraint. `asd-ste100/SKILL.md` is about 2,660 words. |

**Clean:**
- `~/.claude/CLAUDE.md` (one line, consistent with the `cloudflare:cf-cli` skill).
- `ink-artifact`, apart from provenance asides ("taken from the user's tokscope dashboard screenshots").

## Proposed diff

Nothing is applied. Take hunks one at a time.

```diff
--- AGENTS.md
@@ H1 (line 11)
-- `plugins/harness/agents/` - the six subagent role files (model, effort and tools are in their frontmatter).
+- `plugins/harness/agents/` - the subagent role files (model, effort and tools are in their frontmatter).
@@ H2 (line 12)
-- `plugins/harness/hooks/` - `hooks.json` plus four Bash hooks: rule delivery at session start, secrets scan on commit, PR-opened reminder, merged-worktree cleanup.
+- `plugins/harness/hooks/` - `hooks.json` plus the Bash hooks listed in the `CLAUDE.md` Hooks table.

--- CLAUDE.md
@@ M1 (line 65)
-Decisions made on the way are recorded as ADRs in `docs/adr/`. Every skill above exists in `plugins/harness/skills/` now, and runs as `/harness:<name>`.
+Decisions made on the way are recorded as ADRs in `docs/adr/`. The skills above live in `plugins/harness/skills/` and run as `/harness:<name>`; `qa-writer` and `security-reviewer` are agents in `plugins/harness/agents/`.
@@ M2 (line 77)
-all hooks fail open except `merge-guard.sh`, which fails closed.
+all hooks fail open except `merge-guard.sh`, which fails closed, and `stop-evidence.sh` on its risk floor.

--- CLAUDE.local.md
@@ M4 (lines 38-52, replace the "Where it fits" list)
-- **feature-intake** — before assigning the lane, run `get_impact_radius_tool` … `multi-domain` / high-blast flags.
-- **xia2** — … cite the graph query in the research brief's Evidence Ledger as `Local` evidence, then confirm by reading the file.
-- **writing-plans** — … spot a file two tasks would both touch (same-wave overlap).
-- **visual-planner `--review`** — fill the `.plan-review.json` sidecar …
-- **correctness-review / task review** — …
-- **context-propagation-audit** — …
+- **intake** — run `get_impact_radius_tool` on the files the request names; a wide radius is evidence for depth M or L.
+- **xia2** — map local reuse and consumers with `semantic_search_nodes_tool` and `query_graph_tool` (`callers_of`, `tests_for`) before reading files one by one, then confirm by reading the file.
+- **writing-plans** — use `get_impact_radius_tool` per planned file to size the Files list and to spot a file two steps would both touch.
+- **/code-review, task-reviewer** — `detect_changes_tool` and `get_review_context_tool` on the diff; `query_graph_tool` (`callers_of`) for every changed public function before claiming "no caller breaks".
@@ M5 (lines 24-34, replace the tool table)
-| Tool | Use when |
-| `build_or_update_graph_tool` | Refresh … |
- … (nine rows)
+Refresh the graph with `build_or_update_graph_tool` at session start or after a pull or merge. Use `query_graph_tool` for callers, callees, imports and tests, and `get_impact_radius_tool` for blast radius.

--- .claude/rules/behavior.md        # H3: delete the file
--- .claude/agents/coding.md         # M3: delete (superseded by harness:implementer)
--- .claude/agents/task-reviewer.md  # M3: delete (identical to harness:task-reviewer)
--- .claude/agents/test-runner.md    # M3: delete (superseded by harness:test-runner)
--- .claude/agents/PROJECT.md        # H4: delete (readers removed; points at missing paths)
```

**Edits to `~/.claude/` (affect all projects):**

```diff
--- ~/.claude/skills/create-pr/SKILL.md
@@ H6 (line 77)
-python3 .claude/skills/create-pr/scripts/check_pr_body.py --title "<title>" <body.md>
+python3 ~/.claude/skills/create-pr/scripts/check_pr_body.py --title "<title>" <body.md>

--- ~/.claude/skills/autopilot/SKILL.md
@@ M6 (rule 7)
-7. Repo conventions: the project's CLAUDE.md / AGENTS.md apply and win over this skill.
+7. Repo conventions: the project's CLAUDE.md / AGENTS.md apply and win over this skill, except where rules 8 and 10 and Mode B state an override.
@@ M7 (rules 9, 11, 12, 17 and the Mode A references)
-(Vietnamese in most past runs)
+(match the owner's language)
-(past run: #46 was skipped on a data scan, and the owner had to say "do it yourself")
+(a skipped repro leaves the issue open and says so)
-Never one artifact per assumption: past runs hit the 25-watched-artifact cap and flooded the session with notices.
+Never one artifact per assumption: watched artifacts are capped at 25.
-using keys in `apps/api/.env`
+using the project's documented key file
-(tokscope: `pr-assets`, per `uat.md`)
+(the project's asset branch, per its UAT rule)
-(tokscope: `REVIEW.md` "Pick the reviewers first": …)
+(the project's review rules, if it has them)
-(written for travel-pi's Anthropic milestone, so replace its repo, …)
+(replace its repo, test and lint commands, issue numbers, tasks, base branch and phase titles)
-It can take ~20 minutes, so
+It can be slow, so
```

## Verification notes

- I checked paths with `ls` and `find`. I ran no commands from the audited files.
- The H1, H2 and M1 hunks match the file listings above. The M3 and H3 removals depend on F1's direction, so take them together with that decision. Back up `.claude/` first, because it is untracked and git cannot restore it.
- Before applying M4 or the removals, grep the wider system for the exact text. `scripts/lint-doc-truth.sh` checks documented paths, and `AGENTS.md:25` says to run it.
