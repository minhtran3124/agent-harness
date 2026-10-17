#!/bin/bash
# Contract: deploy-harness.sh applies the target's harness-models.json (SC-13) and refuses an
# invalid one before it writes anything under .claude/, also under --dry-run (SC-14).
source "$(dirname "$0")/../lib.sh"

DEPLOY="$ROOT/scripts/deploy-harness.sh"
new_target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); printf '%s' "$d"; }
deploy() { bash "$DEPLOY" --target "$@" </dev/null 2>&1; }
# Every path plus a checksum of every file: a change, an addition or a removal shows up.
state() { [ -e "$1" ] || { echo absent; return; }; (cd "$1" && find . | LC_ALL=C sort && find . -type f -exec cksum {} + | LC_ALL=C sort); }

# ---------- SC-13: valid file is applied; consumer skill untouched ----------
BASE=$(new_target)
deploy "$BASE" >/dev/null; rc_base=$?

T=$(new_target)
printf '{"agents":{"coding":{"effort":"high"}}}\n' > "$T/harness-models.json"
mkdir -p "$T/.claude/skills/my-skill"
printf -- '---\nname: my-skill\ndescription: consumer skill\nmodel: sonnet\n---\n\nBody.\n' > "$T/.claude/skills/my-skill/SKILL.md"
cp "$T/.claude/skills/my-skill/SKILL.md" "$T/my-skill.orig"
deploy "$T" >/dev/null; rc=$?

t "default deploy and deploy with a valid harness-models.json both exit 0"
if [ "$rc_base" = 0 ] && [ "$rc" = 0 ]; then pass; else fail "base rc=$rc_base, configured rc=$rc"; fi

t "configured coding.md holds 'effort: high'"
if grep -qx 'effort: high' "$T/.claude/agents/coding.md"; then pass
else fail "frontmatter: $(sed -n '1,8p' "$T/.claude/agents/coding.md" | tr '\n' '|')"; fi

t "coding.md differs from the default deploy by exactly the effort line"
d=$(diff "$BASE/.claude/agents/coding.md" "$T/.claude/agents/coding.md" | grep '^[<>]')
if [ "$(printf '%s\n' "$d" | wc -l | tr -d ' ')" = 2 ] \
   && printf '%s\n' "$d" | grep -qx '< effort: [a-z]*' && printf '%s\n' "$d" | grep -qx '> effort: high'; then pass
else fail "diff: $(printf '%s' "$d" | tr '\n' '|')"; fi

t "other agent files are identical to the default deploy"
ok=1; for f in "$BASE"/.claude/agents/*.md; do
  n=$(basename "$f"); [ "$n" = coding.md ] && continue
  cmp -s "$f" "$T/.claude/agents/$n" || { ok=0; fail "$n differs"; break; }
done; [ "$ok" = 1 ] && pass

t "consumer tree holds scripts/apply_model_config.py and harness-models.defaults.json"
if [ -f "$T/.claude/scripts/apply_model_config.py" ] && [ -f "$T/.claude/harness-models.defaults.json" ]; then pass
else fail "$(ls "$T/.claude" "$T/.claude/scripts" 2>&1 | tr '\n' ' ')"; fi

t "consumer tree holds no agents/*.json"
if ! ls "$T"/.claude/agents/*.json >/dev/null 2>&1; then pass
else fail "$(ls "$T"/.claude/agents/*.json | tr '\n' ' ')"; fi

t "consumer skill with 'model: sonnet' is byte-identical after the deploy"
if cmp -s "$T/my-skill.orig" "$T/.claude/skills/my-skill/SKILL.md"; then pass
else fail "$(diff "$T/my-skill.orig" "$T/.claude/skills/my-skill/SKILL.md" | tr '\n' '|')"; fi

t "a second deploy with the same file leaves coding.md unchanged"
cp "$T/.claude/agents/coding.md" "$T/coding.1"
deploy "$T" >/dev/null
if cmp -s "$T/coding.1" "$T/.claude/agents/coding.md"; then pass; else fail "second deploy changed coding.md"; fi

# ---------- SC-14: invalid file stops deploy before any write ----------
INVALID='{"agents":{"coding":{"effort":"bogus"}}}'

T=$(new_target)
deploy "$T" >/dev/null
# Make a harness-owned file stale: a deploy that wrote anything would restore it.
printf 'stale marker\n' >> "$T/.claude/skills/xia2/SKILL.md"
printf '%s\n' "$INVALID" > "$T/harness-models.json"
before=$(state "$T/.claude")
out=$(deploy "$T"); rc=$?

t "re-sync with an invalid harness-models.json exits non-zero"
if [ "$rc" != 0 ]; then pass; else fail "rc=0"; fi

t "re-sync prints the applier's error"
if printf '%s' "$out" | grep -q "invalid effort 'bogus'"; then pass; else fail "output: $out"; fi

t "re-sync with an invalid file changes no file under .claude/"
if [ "$(state "$T/.claude")" = "$before" ]; then pass; else fail "$(diff <(printf '%s\n' "$before") <(state "$T/.claude") | head -5)"; fi

T=$(new_target)
printf '%s\n' "$INVALID" > "$T/harness-models.json"
out=$(deploy "$T"); rc=$?

t "first deploy with an invalid file exits non-zero, prints the error and creates no .claude/"
if [ "$rc" != 0 ] && printf '%s' "$out" | grep -q "invalid effort 'bogus'" && [ ! -e "$T/.claude" ]; then pass
else fail "rc=$rc .claude=$([ -e "$T/.claude" ] && echo present || echo absent) output: $out"; fi

T=$(new_target)
printf '%s\n' "$INVALID" > "$T/harness-models.json"
out=$(deploy "$T" --dry-run); rc=$?

t "--dry-run with an invalid file and no prior .claude/ exits non-zero, prints the error, writes nothing"
if [ "$rc" != 0 ] && printf '%s' "$out" | grep -q "invalid effort 'bogus'" && [ ! -e "$T/.claude" ]; then pass
else fail "rc=$rc .claude=$([ -e "$T/.claude" ] && echo present || echo absent) output: $out"; fi

finish
