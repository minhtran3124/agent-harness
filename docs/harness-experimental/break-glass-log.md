# Break-Glass Log

Audit trail of overrides to `hooks/protected-path-guard.sh` (a **dormant** hook — see the hook
table in `CLAUDE.md`). When that hook is wired and a write to a high-blast file proceeds because
`PROTECTED_PATH_REASON` was set, the hook appends one dated row here, so every override is a
record rather than an invisible exception.

| When (UTC) | File | Reason |
|---|---|---|

<!-- rows are appended by the hook as: `- <iso8601> — \`<path>\` — <reason>` -->
