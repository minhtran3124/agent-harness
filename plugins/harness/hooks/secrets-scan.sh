#!/usr/bin/env bash
# PreToolUse(Bash): on `git commit`, block when the staged diff or staged filenames look like secrets.
# Fails open: no jq/git, a bad payload, or any other command passes. Exit 2 blocks.
command -v jq >/dev/null && command -v git >/dev/null || exit 0
cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
printf '%s' "$cmd" | grep -qE '(^|[;&|(]|[[:space:]])git[[:space:]]+([^;&|]*[[:space:]])?commit([[:space:]]|$)' || exit 0

# Same patterns the retired commit-gate used. Tests, examples and docs are excluded from the diff.
PATTERN='(sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|password\s*=\s*["'"'"'][^"'"'"']+|passwd\s*=|api_key\s*=\s*["'"'"'][^"'"'"']+|apikey\s*=\s*["'"'"'][^"'"'"']+|client_secret\s*=\s*["'"'"'][^"'"'"']+|\bsecret\s*=\s*["'"'"'][^"'"'"']+)'
if git diff --cached -U0 -- ':!*tests/*' ':!*__tests__/*' ':!*.example' ':!*.md' ':!docs/' 2>/dev/null | grep -qEi "$PATTERN"; then
  echo "BLOCKED: potential secret in the staged changes. Run 'git diff --cached', move the value to an env var, re-stage. If it is a fake test value, ask the owner." >&2
  exit 2
fi
if git diff --cached --name-only 2>/dev/null | grep -qE '\.env$'; then
  echo "BLOCKED: a .env file is staged. Unstage it (git restore --staged <file>), gitignore it, and commit a .env.example instead." >&2
  exit 2
fi
exit 0
