#!/bin/bash
# Clone the Claude Code setup from the repo root (the source) into .claude/, which is where
# Claude Code actually loads project skills, agents, and hooks. The root dirs stay the source
# of truth; .claude/ is a derived copy (gitignored).
#
# Idempotent — supports both a FIRST-TIME install and a RE-SYNC (update). Re-run after editing
# anything under skills/ agents/ hooks/ rules/ settings.json.
#
# Usage:  bash scripts/deploy-harness.sh [--target <dir>] [--yes] [--overwrite-conflicts] [--dry-run]
#   --target <dir>          Build .claude/ inside <dir> instead of next to the sources
#                            (used by install-harness.sh to deploy into a consuming project).
#   --yes, --non-interactive  Never prompt on a protected-file conflict; keep the local copy
#                            (incoming saved to <file>.harness-incoming for review).
#   --overwrite-conflicts    Never prompt; overwrite protected files with the incoming source.
#   --dry-run                Report what would sync (incl. protected-file conflicts) and exit
#                            0 before anything under .claude/ is written.
set -e

# Sources live one level above this script — resolve by path, NOT via git: when this script
# runs from a staged copy inside another project, git would resolve to that project's root,
# which has no harness sources.
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"

# bootstrap-xia2 writes these files per-consuming-repo (generated stack profile / convention
# index); a re-sync must never silently clobber them with the meta-repo's generic skeleton.
# Source of truth for this list: skills/bootstrap-xia2/SKILL.md (Init steps 6-7 + Scaffolding
# table). Deliberately NOT named PROTECTED_* — that prefix already denotes the unrelated
# hooks/protected-path-guard.sh / PROTECTED_PATH_REASON set.
BOOTSTRAP_OWNED_FILES=(
  "rules/architecture.md"
  "rules/guidelines.md"
  "agents/PROJECT.md"
  "skills/xia2/PROJECT.md"
)

OUT_BASE="$ROOT"
YES=0
OVERWRITE_CONFLICTS=0
DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    -t|--target) OUT_BASE="${2:?--target needs a path}"; shift 2 ;;
    --yes|--non-interactive) YES=1; shift ;;
    --overwrite-conflicts) OVERWRITE_CONFLICTS=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; exit 1 ;;
  esac
done
mkdir -p "$OUT_BASE"
OUT_BASE="$(cd "$OUT_BASE" && pwd -P)"
OUT="$OUT_BASE/.claude"
cd "$ROOT"

# ---------- styling (colors only on a TTY) ----------
if [ -t 1 ]; then
  B=$'\033[1m'; D=$'\033[2m'; R=$'\033[0m'
  G=$'\033[32m'; C=$'\033[36m'; Y=$'\033[33m'; M=$'\033[35m'
else
  B=; D=; R=; G=; C=; Y=; M=
fi
SPIN=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)

# step "label" command...  → animate a spinner, run the work, replace with a ✓
step() {
  local label="$1"; shift
  if [ -t 1 ]; then
    local i frame
    for i in 1 2 3 4 5 6 7 8; do
      frame="${SPIN[$(((i-1)%${#SPIN[@]}))]}"
      printf "\r  ${C}%s${R}  %s" "$frame" "$label"
      sleep 0.045
    done
    "$@"
    printf "\r  ${G}✓${R}  %s%*s\n" "$label" 6 ""
  else
    "$@"
    printf "  - %s\n" "$label"
  fi
}
trap 'printf "\r  '"$([ -t 1 ] && printf '\033[31m')"'✗'"$([ -t 1 ] && printf '\033[0m')"'  step failed\n" >&2' ERR

# ---------- protected-file helpers (bootstrap-xia2 owned files) ----------
is_protected() {
  local rel="$1" f
  for f in "${BOOTSTRAP_OWNED_FILES[@]}"; do
    [ "$rel" = "$f" ] && return 0
  done
  return 1
}

# True if any BOOTSTRAP_OWNED_FILES entry lives under dir entry $1 (e.g. "skills/xia2"
# holds "skills/xia2/PROJECT.md"). Needed because copy_dir wholesale rm+cp's whole
# directories, not individual files.
protected_under() {
  local rel="$1" f
  for f in "${BOOTSTRAP_OWNED_FILES[@]}"; do
    case "$f" in
      "$rel"/*) return 0 ;;
    esac
  done
  return 1
}

CONFLICTS=()
POLICY=""
BACKUP_TS=""

# Scan BOOTSTRAP_OWNED_FILES for local-vs-incoming conflicts and resolve ONE batch policy
# for all of them. Runs ONCE, before prep_dir and before the `for d in ...` copy loop —
# never inside copy_dir, which runs once per top-level dir and would prompt (and could
# abort) only after e.g. skills/ had already been destructively re-synced. Harmless on a
# first install / non-update run: $OUT/$f can't exist yet, so no conflicts are found.
preflight_protected() {
  local f
  for f in "${BOOTSTRAP_OWNED_FILES[@]}"; do
    [ -e "$OUT/$f" ] || continue
    [ -e "$f" ] || continue
    if ! cmp -s "$OUT/$f" "$f"; then
      CONFLICTS+=("$f")
    fi
  done

  if [ "$DRY_RUN" -eq 1 ]; then
    if [ "${#CONFLICTS[@]}" -eq 0 ]; then
      printf "  %sNo protected-file conflicts — dry run, nothing written.%s\n\n" "$D" "$R"
    else
      printf "  %s⚠ %d protected file(s) would conflict %s(dry run — nothing written)%s:\n" "$Y" "${#CONFLICTS[@]}" "$D" "$R"
      for f in "${CONFLICTS[@]}"; do
        printf "    - %s\n" "$f"
      done
      printf "\n"
    fi
    exit 0
  fi

  [ "${#CONFLICTS[@]}" -eq 0 ] && return 0

  if [ "$OVERWRITE_CONFLICTS" -eq 1 ]; then
    POLICY="overwrite"
  elif [ "$YES" -eq 1 ] || [ ! -r /dev/tty ]; then
    POLICY="keep"
    printf "  %s⚠ %d protected file(s) differ from the harness source — keeping your local copy;%s\n" "$Y" "${#CONFLICTS[@]}" "$R"
    printf "  %s  incoming saved as <file>.harness-incoming for review.%s\n" "$Y" "$R"
  else
    printf "\n  %s⚠ %d protected file(s) differ from the harness source:%s\n" "$Y" "${#CONFLICTS[@]}" "$R"
    for f in "${CONFLICTS[@]}"; do
      printf "    - %s\n" "$f"
    done
    printf "  ${B}[k]${R} keep mine (default)  ${B}[o]${R} overwrite with incoming  ${B}[b]${R} back up mine then overwrite  ${B}[a]${R} abort\n"
    printf "  Choice: "
    local ans=""
    read -r ans < /dev/tty || true
    case "$ans" in
      o|O) POLICY="overwrite" ;;
      b|B) POLICY="backup"; BACKUP_TS="$(date +%Y%m%d-%H%M%S)" ;;
      a|A) printf "\n  Aborted — nothing written.\n\n"; exit 1 ;;
      *)   POLICY="keep" ;;
    esac
  fi
}

# ---------- work units ----------
prep_dir()        { mkdir -p "$OUT"; }

# Apply the resolved POLICY to a top-level protected FILE entry (e.g. rules/architecture.md)
# instead of copy_dir's blind rm -rf + cp.
sync_protected_file() {
  local rel="$1" entry="$2" dst="$OUT/$1"

  if [ ! -e "$dst" ]; then
    cp -R "$entry" "$dst"          # fresh copy — nothing to protect yet
    return 0
  fi

  local conflict=0 f
  for f in "${CONFLICTS[@]}"; do
    [ "$f" = "$rel" ] && conflict=1 && break
  done
  if [ "$conflict" -eq 0 ]; then
    rm -f "$dst.harness-incoming"   # identical — clean any stale sidecar from a past conflict
    return 0
  fi

  case "$POLICY" in
    overwrite)
      rm -f "$dst.harness-incoming"
      rm -rf "$dst"; cp -R "$entry" "$dst"
      ;;
    backup)
      mkdir -p "$OUT/.harness-backup-$BACKUP_TS/$(dirname "$rel")"
      cp -R "$dst" "$OUT/.harness-backup-$BACKUP_TS/$rel"
      rm -f "$dst.harness-incoming"
      rm -rf "$dst"; cp -R "$entry" "$dst"
      ;;
    *)
      cp -R "$entry" "$dst.harness-incoming"
      ;;
  esac
}

# Wholesale-copy a DIR entry that HOLDS a protected file (skills/xia2/) — copy_dir's
# per-entry rm -rf + cp -R semantics apply to the whole dir (preserves stale-removal for
# everything else inside it), but nested protected file(s) are snapshotted first —
# including the never-shipped `.proposed` sidecar, unconditionally, since it can never
# conflict — and reconciled per POLICY after the dir copy lands.
sync_protected_dir() {
  local rel="$1" entry="$2" topdir="$3" tmp f nested
  tmp="$(mktemp -d)"

  for f in "${BOOTSTRAP_OWNED_FILES[@]}"; do
    case "$f" in
      "$rel"/*)
        nested="${f#"$rel"/}"
        mkdir -p "$tmp/$(dirname "$nested")"
        [ -e "$OUT/$rel/$nested" ] && cp -R "$OUT/$rel/$nested" "$tmp/$nested"
        [ -e "$OUT/$rel/$nested.proposed" ] && cp -R "$OUT/$rel/$nested.proposed" "$tmp/$nested.proposed"
        ;;
    esac
  done

  rm -rf "$OUT/$rel"
  cp -R "$entry" "$OUT/$topdir/"

  for f in "${BOOTSTRAP_OWNED_FILES[@]}"; do
    case "$f" in
      "$rel"/*)
        nested="${f#"$rel"/}"

        if [ -e "$tmp/$nested.proposed" ]; then
          mkdir -p "$OUT/$rel/$(dirname "$nested")"
          cp -R "$tmp/$nested.proposed" "$OUT/$rel/$nested.proposed"
        fi

        if [ ! -e "$tmp/$nested" ]; then
          continue    # nothing local pre-existed — fresh copy, nothing to reconcile
        fi

        local conflict=0 cf
        for cf in "${CONFLICTS[@]}"; do
          [ "$cf" = "$f" ] && conflict=1 && break
        done
        if [ "$conflict" -eq 0 ]; then
          rm -f "$OUT/$rel/$nested.harness-incoming"   # identical — stale-sidecar cleanup
          continue
        fi

        case "$POLICY" in
          overwrite)
            rm -f "$OUT/$rel/$nested.harness-incoming"   # incoming already at dst — no-op
            ;;
          backup)
            mkdir -p "$OUT/.harness-backup-$BACKUP_TS/$(dirname "$rel/$nested")"
            cp -R "$tmp/$nested" "$OUT/.harness-backup-$BACKUP_TS/$rel/$nested"
            rm -f "$OUT/$rel/$nested.harness-incoming"
            ;;
          *)
            cp -R "$OUT/$rel/$nested" "$OUT/$rel/$nested.harness-incoming"
            cp -R "$tmp/$nested" "$OUT/$rel/$nested"
            ;;
        esac
        ;;
    esac
  done

  rm -rf "$tmp"
}

# Merge-sync source dir $1 into $OUT/$1. Only entries the harness ships are
# removed + recopied; foreign entries already in $OUT/$1 (e.g. skills the user
# installed separately) are left untouched. A wholesale `rm -rf $OUT/$1` would
# delete those non-harness entries — this is deliberately per-entry instead.
# Protected files/dirs (BOOTSTRAP_OWNED_FILES) skip that blind rm+cp — see
# sync_protected_file / sync_protected_dir.
copy_dir()        {
  mkdir -p "$OUT/$1"
  for entry in "$1"/* "$1"/.[!.]*; do
    [ -e "$entry" ] || continue
    local base rel
    base="$(basename "$entry")"
    rel="$1/$base"

    if [ -d "$entry" ] && protected_under "$rel"; then
      sync_protected_dir "$rel" "$entry" "$1"
      continue
    fi
    if [ -f "$entry" ] && is_protected "$rel"; then
      sync_protected_file "$rel" "$entry"
      continue
    fi

    rm -rf "$OUT/$1/$base"
    cp -R "$entry" "$OUT/$1/"
  done
}
strip_archive()   { rm -rf "$OUT/skills/_archive"; }   # archived skills must not register as live
derive_settings() {
  # Point relative hook commands at the deployed .claude/ copies via $CLAUDE_PROJECT_DIR so they
  # resolve from any launch directory. Absolute / $-prefixed commands are left untouched.
  local derived
  derived="$(jq '.hooks |= with_entries(.value |= map(.hooks |= map(.command |= (
        if (startswith("$") or startswith("/")) then . else "$CLAUDE_PROJECT_DIR/.claude/" + . end
      ))))' settings.json)"

  # Merge, never replace. A consuming project's .claude/settings.json may carry its own
  # top-level keys (permissions, env, statusLine, enabledPlugins) AND its own hooks. Preserve
  # all of them: foreign top-level keys pass through untouched; per event, foreign hook
  # commands are kept while any prior-sync copy of a harness command is stripped and re-added
  # fresh (dedup by command — re-sync stays idempotent, no double-registration).
  if [ -f "$OUT/settings.json" ] && jq -e . "$OUT/settings.json" >/dev/null 2>&1; then
    local cur tmp
    cur="$(cat "$OUT/settings.json")"
    tmp="$(mktemp)"
    jq -n --argjson cur "$cur" --argjson new "$derived" '
      # all harness-owned command strings (the dedup key set)
      ([$new.hooks | .. | objects | select(has("command")) | .command] | unique) as $hcmds
      | ($cur.hooks // {}) as $curh
      | ($new.hooks // {}) as $newh
      | $cur
      | .hooks = (
          (($curh | keys) + ($newh | keys) | unique)
          | reduce .[] as $ev ({};
              # foreign blocks for this event: drop harness commands, then drop now-empty blocks
              ( ($curh[$ev] // [])
                | map(.hooks |= map(select(.command as $c | $hcmds | index($c) | not)))
                | map(select((.hooks | length) > 0)) ) as $foreign
              | .[$ev] = ($foreign + ($newh[$ev] // []))
            )
        )
    ' > "$tmp"
    mv "$tmp" "$OUT/settings.json"
  elif [ -f "$OUT/settings.json" ]; then
    # Exists but is NOT valid JSON — it cannot be merged. Never silently overwrite it:
    # back it up first, warn, then write a fresh valid settings.json the harness can load.
    local bak="$OUT/settings.json.invalid-bak-$(date +%Y%m%d-%H%M%S)"
    cp "$OUT/settings.json" "$bak"
    printf '  %s⚠ existing .claude/settings.json is not valid JSON — cannot merge.%s\n' "$Y" "$R" >&2
    printf '  %s  backed up to %s; wrote a fresh harness settings.json.%s\n' "$D" "${bak#"$OUT_BASE"/}" "$R" >&2
    printf '%s' "$derived" | jq . > "$OUT/settings.json"
  else
    # First install — no existing file to preserve.
    printf '%s' "$derived" | jq . > "$OUT/settings.json"
  fi
}

# ---------- mode detection: first install vs re-sync ----------
if [ -d "$OUT" ] && [ -e "$OUT/settings.json" ]; then
  MODE="update";  MODE_LABEL="Re-syncing harness (update)"; MODE_EMOJI="🔄"
else
  MODE="install"; MODE_LABEL="First-time install";          MODE_EMOJI="✨"
fi

printf "\n  ${B}${M}🧙 claude-skills harness${R} ${D}→ %s${R}\n" "$OUT"
printf "  ${MODE_EMOJI}  ${B}%s${R}\n\n" "$MODE_LABEL"

# Own labeled step, outside step()'s spinner — a batch prompt (or --dry-run exit) doesn't
# fight the spinner animation, and --dry-run must exit before prep_dir/copy_dir/derive_settings.
preflight_protected

# ---------- pipeline ----------
step "Preparing ${B}.claude/${R}"            prep_dir
for d in skills agents hooks rules templates; do
  [ -e "$d" ] || continue
  step "Syncing ${B}$d/${R}"                 copy_dir "$d"
done
step "Stripping archived skills"             strip_archive
step "Deriving ${B}settings.json${R} ${D}(hook paths)${R}" derive_settings

# ---------- summary ----------
SK=$(ls -d "$OUT"/skills/*/ 2>/dev/null | wc -l | tr -d ' ')
AG=$(ls "$OUT"/agents/*.md 2>/dev/null | wc -l | tr -d ' ')
HK=$(ls "$OUT"/hooks/*.sh 2>/dev/null | wc -l | tr -d ' ')
RL=$(ls "$OUT"/rules/*.md 2>/dev/null | wc -l | tr -d ' ')

printf "\n  ${G}${B}✓ Harness deployed${R}  ${D}(%s)${R}\n" "$MODE"
printf "  ${D}├─${R} 🎯 skills    ${B}%s${R}\n" "$SK"
printf "  ${D}├─${R} 🤖 agents    ${B}%s${R}\n" "$AG"
printf "  ${D}├─${R} 🪝 hooks     ${B}%s${R}\n" "$HK"
printf "  ${D}└─${R} 📜 rules     ${B}%s${R}  ${D}(+ settings.json)${R}\n" "$RL"
if [ "${#CONFLICTS[@]}" -gt 0 ]; then
  printf "  ${Y}⚠ protected-file conflicts (%s): %s${R}\n" "$POLICY" "$(IFS=,; echo "${CONFLICTS[*]}")"
  case "$POLICY" in
    keep)      printf "  ${D}  kept your local copies; incoming saved as <file>.harness-incoming${R}\n" ;;
    backup)    printf "  ${D}  backed up your local copies to .claude/.harness-backup-%s/ and applied incoming${R}\n" "$BACKUP_TS" ;;
    overwrite) printf "  ${D}  overwrote with incoming harness source${R}\n" ;;
  esac
fi
[ -f "$OUT_BASE/.mcp.json" ] || printf "  ${Y}⚠ No .mcp.json at project root — the code-review-graph MCP server is not wired (see README → MCP servers).${R}\n"
printf "\n  ${Y}↻ Restart Claude Code in this repo so it loads them.${R}\n\n"
