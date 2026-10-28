#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
grep -q 'REVIEW_PACKAGE_PATH' "$root/skills/correctness-review/SKILL.md"
grep -q 'REVIEW_PACKAGE_PATH' "$root/skills/intent-review/SKILL.md"
grep -q 'REVIEW_PACKAGE_PATH' "$root/skills/correctness-review/prompts/shared.md"
grep -q 'do not rebuild the same full diff' "$root/skills/correctness-review/prompts/shared.md"
grep -q 'REVIEW_PACKAGE_PATH' "$root/skills/intent-review/intent-reviewer-prompt.md"
grep -q 'do not rebuild the same full diff' "$root/skills/intent-review/intent-reviewer-prompt.md"
grep -q 'FORBIDDEN from reading.*PLAN.md' "$root/skills/intent-review/intent-reviewer-prompt.md"
echo 'final-review-package-contract: passed'
