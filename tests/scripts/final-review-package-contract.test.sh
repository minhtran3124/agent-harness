#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
chain="$root/skills/subagent-driven-development/references/review-chain.md"
grep -q 'branch review package' "$chain"
grep -q 'oracle inputs and blindness rules remain unchanged' "$chain"
grep -q 'REVIEW_PACKAGE_PATH' "$root/skills/correctness-review/SKILL.md"
grep -q 'REVIEW_PACKAGE_PATH' "$root/skills/intent-review/SKILL.md"
grep -q 'FORBIDDEN from reading.*PLAN.md' "$root/skills/intent-review/intent-reviewer-prompt.md"
echo 'final-review-package-contract: passed'
