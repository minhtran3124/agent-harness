# Break-Glass Log

Audit trail of hook overrides that let a normally-denied action proceed because a human recorded
a reason. Current writer: `hooks/branch-isolation-guard.sh` — when `BRANCH_ISOLATION_REASON` is
set and a code edit on a shared branch proceeds, it appends one row here, so every override is a
record rather than an invisible exception. Entry format: `- <iso8601> — branch-isolation
\`<path>\` on \`<branch>\` — <reason>`.

Former writer: `hooks/protected-path-guard.sh` (a dormant hook using `PROTECTED_PATH_REASON` and
the `- <iso8601> — \`<path>\` — <reason>` format below) was removed in PR #133 (2026-07-21, see
`docs/harness-experimental/trust-metrics.md`) and no longer writes to this file.

| When (UTC) | File | Reason |
|---|---|---|

<!-- rows are appended by branch-isolation-guard.sh as:
     `- <iso8601> — branch-isolation \`<path>\` on \`<branch>\` — <reason>` -->
