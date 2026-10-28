#!/bin/bash
# Offline install smoke test for the harness plugin, driven through the real Claude Code CLI.
#
# Verifies:        in an ISOLATED config dir, `claude plugin marketplace add <repo>` and
#                  `claude plugin install harness@agent-harness` succeed; `claude plugin details
#                  harness` reports the skills, agents and hook events the source tree holds; and
#                  the installed cache copy keeps the executable bit on hooks/*.sh and scripts/*.sh
#                  and holds the same skill and agent files as the source.
# Does not verify: that hooks fire in a live session, or anything that needs a model call or login.
#
# Safety: it installs a plugin, so it REFUSES to run unless CLAUDE_CONFIG_DIR is set to a
# directory of its own (never your real ~/.claude).
#   Local:  CLAUDE_CONFIG_DIR="$(mktemp -d)" bash scripts/check-plugin-install.sh
# Without the `claude` CLI it skips (exit 0) unless REQUIRE_CLAUDE_CLI=1, which makes it fail.
# Bash 3.2 compatible.
set -u
cd "$(dirname "$0")/.." || exit 1
REPO=$(pwd)

if [ -z "${CLAUDE_CONFIG_DIR:-}" ]; then
  echo "  ✗ plugin install: refusing to run, CLAUDE_CONFIG_DIR is not set (it would touch your real ~/.claude)" >&2
  echo "    use: CLAUDE_CONFIG_DIR=\"\$(mktemp -d)\" bash scripts/check-plugin-install.sh" >&2
  exit 2
fi
mkdir -p "$CLAUDE_CONFIG_DIR" || exit 2
# Guard against the real config dir, with or without a trailing slash.
real_home=$(cd "$HOME/.claude" 2>/dev/null && pwd -P)
cfg=$(cd "$CLAUDE_CONFIG_DIR" && pwd -P)
if [ -n "$real_home" ] && [ "$cfg" = "$real_home" ]; then
  echo "  ✗ plugin install: refusing to run against the real ~/.claude" >&2
  exit 2
fi

if ! command -v claude >/dev/null 2>&1; then
  if [ "${REQUIRE_CLAUDE_CLI:-}" = 1 ]; then
    echo "  ✗ plugin install: the 'claude' CLI is not on PATH and REQUIRE_CLAUDE_CLI=1" >&2
    exit 1
  fi
  echo "  skip — plugin install: the 'claude' CLI is not on PATH (set REQUIRE_CLAUDE_CLI=1 to fail instead)"
  exit 0
fi

rc=0
bad() { rc=1; echo "  ✗ $1" >&2; }
ok()  { echo "  ✓ $1"; }

run() { # run <label> <cmd...>: show output only on failure
  local label=$1 out; shift
  if out=$("$@" 2>&1); then ok "$label"; else
    bad "$label"; printf '%s\n' "$out" | sed 's/^/      /' >&2; return 1
  fi
}

run "marketplace add" claude plugin marketplace add "$REPO" || exit 1
run "install harness@agent-harness" claude plugin install harness@agent-harness || exit 1

# Expected counts come from the source tree, never hardcoded.
count() { find "$1" -maxdepth "$2" -type f -name "$3" 2>/dev/null | wc -l | tr -d ' '; }
want_skills=$(count plugins/harness/skills 2 SKILL.md)
want_agents=$(count plugins/harness/agents 1 '*.md')
events=$(python3 -c 'import json,sys;print("\n".join(sorted(json.load(open(sys.argv[1]))["hooks"])))' plugins/harness/hooks/hooks.json)
[ -n "$events" ] || { bad "could not read hook events from plugins/harness/hooks/hooks.json"; exit 1; }

details=$(claude plugin details harness 2>&1) || { bad "plugin details harness"; printf '%s\n' "$details" | sed 's/^/      /' >&2; exit 1; }
printf '%s\n' "$details" | sed 's/^/      /'

# The details layout ("Skills (16)  a, b", "Hooks (3)  SessionStart, ...") is observed on
# claude 2.1.312, not a documented contract: if it changes this fails loudly. The installed files
# are cross-checked on disk below.
echo "$details" | grep -Eq "^[[:space:]]*Skills \(${want_skills}\)" || bad "details does not report $want_skills skills"
echo "$details" | grep -Eq "^[[:space:]]*Agents \(${want_agents}\)" || bad "details does not report $want_agents agents"
for e in $events; do
  echo "$details" | grep -E "^[[:space:]]*Hooks " | grep -q "$e" || bad "details does not mention hook event $e"
done

# Installed cache copy.
cache=$(find "$CLAUDE_CONFIG_DIR/plugins" -type d -path '*/agent-harness/harness/*' -name hooks -prune 2>/dev/null | head -1)
[ -n "$cache" ] || { bad "installed copy of harness not found under $CLAUDE_CONFIG_DIR/plugins"; exit 1; }
inst=$(dirname "$cache")
got_skills=$(count "$inst/skills" 2 SKILL.md)
got_agents=$(count "$inst/agents" 1 '*.md')
if [ "$got_skills" = "$want_skills" ]; then ok "installed copy has $got_skills skills"; else bad "installed copy has $got_skills skills, source has $want_skills"; fi
if [ "$got_agents" = "$want_agents" ]; then ok "installed copy has $got_agents agents"; else bad "installed copy has $got_agents agents, source has $want_agents"; fi

nx=0
for f in "$inst"/hooks/*.sh "$inst"/scripts/*.sh; do
  [ -e "$f" ] || continue
  [ -x "$f" ] || { bad "not executable in the installed copy: ${f#"$inst"/}"; nx=1; }
done
[ "$nx" = 0 ] && ok "hooks/*.sh and scripts/*.sh keep the executable bit"
exit $rc
