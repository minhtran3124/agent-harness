# mcp-install-wiring — Summary

Lane: normal
Confidence: high
Reason: Installer change approved by user with explicit design (merge-not-overwrite, warn-not-fail); touches scripts/ which is not in the hard-gate list, but is the public curl|bash entry point — treated with normal-lane proof (tests below).
Flags: none
Input-type: harness improvement

## What changed

`install-harness.sh` now wires the code-review-graph MCP server into the target project:
a dedicated `.mcp.json` step (create if missing; jq-merge the `code-review-graph` server
into an existing file; leave untouched if already wired or unparseable) plus a soft `uvx`
prerequisite check (warn + install hint, never fail). `deploy-harness.sh` warns if the
repo root lacks `.mcp.json` (anti-drift canary). README installation/MCP sections updated.

### Rationale

The harness docs mandate graph-first exploration, but the installer never shipped the MCP
config — consuming projects got the mandate without the wiring. `.mcp.json` is handled
outside PAYLOAD because it needs merge semantics and must survive the root-source prune
(Claude Code reads it at the project root, not in `.claude/`). The server entry is read
from the source repo's `.mcp.json` (single source of truth) with an inline fallback.

### Alternatives considered

- Add `.mcp.json` to PAYLOAD — rejected: PAYLOAD items are overwritten wholesale and
  pruned after the `.claude/` build; both behaviors are wrong for this file.
- Hard-fail when `uvx` is missing — rejected: breaks CI/container installs; harness has a
  documented Grep/Read fallback. (A `--require-graph` strict flag can be added later.)

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Syntax | `bash -n scripts/install-harness.sh && bash -n scripts/deploy-harness.sh` | 0 | |
| Dry-run reports MCP step | `install-harness.sh --source . --dry-run -d /tmp/h-t1` | 0 | "would create .mcp.json" |
| Fresh install creates file | `install-harness.sh --source . --yes -d /tmp/h-t2` | 0 | valid JSON, survives prune, no stale canary warning |
| Merge preserves other servers | pre-seed context7 entry → install → `jq '.mcpServers \| keys'` | 0 | `["code-review-graph","context7"]` + backup taken |
| Idempotent re-run | re-install into /tmp/h-t3 | 0 | "already wires — left unchanged" |
| Invalid JSON untouched | pre-seed garbage → install | 0 | warns, file byte-identical |
| uvx-missing warns, not fails | `env PATH=/usr/bin:/bin install-harness.sh --dry-run` | 0 | warning printed, install proceeds |

### Rollback

- `git revert ea3182f`

### Harness-Delta

- none
