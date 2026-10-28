#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
grep -q 'REVIEW_PACKAGE_PATH' "$root/skills/correctness-review/SKILL.md"
grep -q 'REVIEW_PACKAGE_PATH' "$root/skills/correctness-review/prompts/shared.md"
grep -q 'do not rebuild the same full diff' "$root/skills/correctness-review/prompts/shared.md"
echo 'final-review-package-contract: passed'
