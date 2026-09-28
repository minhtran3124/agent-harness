#!/bin/bash
# Every skills/*/SKILL.md must declare `allowed-tools` — least privilege at the skill level,
# enforced by the runtime rather than by prose.
#
# Verifies:        the field is PRESENT and non-empty in every skill.
# Does not verify: that the list is CORRECT. `claude plugin validate` does not check tool names
#                  (verified: a bogus name passes), and no test exercises a skill under its
#                  declared list — so an under-granted skill breaks only at runtime. Adding or
#                  narrowing a list is a change that needs a human read of the skill's body.
set -u
cd "$(dirname "$0")/.." || exit 1

MISSING=""
for f in skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  # Only the frontmatter block counts (between the first two --- lines).
  if ! awk 'NR==1&&/^---$/{inb=1;next} inb&&/^---$/{exit} inb' "$f" \
       | grep -qE '^allowed-tools:[[:space:]]*[^[:space:]]'; then
    MISSING="$MISSING $f"
  fi
done

if [ -n "$MISSING" ]; then
  echo "  ✗ skills missing a non-empty allowed-tools in frontmatter:" >&2
  for f in $MISSING; do echo "      $f" >&2; done
  echo "      Derive the list from the skill's own body; under-granting breaks it at runtime." >&2
  exit 1
fi
echo "  ✓ all $(ls -d skills/*/ | wc -l | tr -d ' ') skills declare allowed-tools"
exit 0
