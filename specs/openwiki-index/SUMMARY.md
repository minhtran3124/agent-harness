# openwiki-index — Summary

Lane: high-risk
Confidence: high
Reason: Docs-only, but the commit-gate risk corroboration trips auth and authorization on the generated openwiki/ pages, which describe the harness's own auth hard gates in prose; declared high-risk per the gate rather than loosening it. No hook, script, skill, rule, or template change.
Flags: auth, authorization (keyword hits in generated wiki prose)
Affects: AGENTS.md, CLAUDE.md, README.md, openwiki/, .github/workflows/openwiki-update.yml
Input-type: maintenance

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

i want to add it under section  "Optional MCP servers (local setup)"
i want to commit changes for wiki

### Intake notes

- "it" read as OpenWiki (the user's answer to the clarifying question): commit the user's existing OpenWiki work and add an OpenWiki entry to README's "Optional MCP servers (local setup)".
- Unrelated untracked paths stay out of this commit: `.agents/`, `reports/`, `research_notes/`, `skills-lock.json`.

## What changed

Commits the generated `openwiki/` index (OpenWiki 0.7.2, `init` at 996f50d), the scheduled
`.github/workflows/openwiki-update.yml` refresh workflow, and the OpenWiki sections in `AGENTS.md`
and `CLAUDE.md` (the user's existing edits, unchanged). README gains an OpenWiki entry under
"Optional MCP servers (local setup)" with the local install command for the retrieval tools.

### Rationale

The wiki is a committed artifact that a workflow refreshes, while the retrieval tools are a
per-user MCP install. So the README entry sits with the other optional local servers, and the
agent instructions fall back to reading `openwiki/quickstart.md` when the tools are absent.

### Alternatives considered

- `openwiki integrations install claude --project` in the README — not used: it writes the integration into the repo, which contradicts the section's "install it yourself" model; not checked what files it writes.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 |  |  |
| README has the OpenWiki entry under the MCP section | `grep -q "openwiki integrations install claude" README.md` | 0 |  |  |
| Quickstart fallback named in AGENTS.md exists | `test -f openwiki/quickstart.md` | 0 |  |  |

### Not auto-verified

- `openwiki integrations install claude` makes `openwiki_search` / `openwiki_read` available in Claude Code — reached traceability only (`openwiki --help` names the subcommand); not run, to avoid changing the user's global config.
- The scheduled workflow runs green — needs `ANTHROPIC_API_KEY` (and LangSmith) repo secrets; not run.

### Rollback

- Revert the commit after merge: `git revert -m 1 <merge sha>` (removes `openwiki/`, the workflow, and the doc sections).
- Stop the scheduled refresh without reverting: `gh workflow disable openwiki-update.yml`.

### Harness-Delta

- none
