#!/usr/bin/env bash
# Fetch or use a local harness checkout, then deploy its Codex adapter.
set -euo pipefail

REPO_URL="${CS_REPO_URL:-https://github.com/minhtran3124/agent-harness}"
BRANCH="${CS_BRANCH:-simplify}"
TARGET_DIR="$PWD"
SOURCE_DIR=""
# Not named CODEX_BIN: assigning that would blank an exported CODEX_BIN that the deploy reads.
CODEX_BIN_ARG="${CODEX_BIN:-}"
CODEX_HOME_ARG=""
FORWARD_ARGS=()

usage() {
  cat <<EOF
Usage: install-codex-harness.sh [options]

Options:
  -d, --directory <path>   Target project (default: current directory)
  -b, --branch <name>      Git branch when fetching (default: $BRANCH)
  --source <path>          Use a local harness checkout instead of cloning
  --codex-bin <path>       Codex executable
  --codex-home <path>      Explicit Codex state root
  --yes                    Non-interactive; keep local files on conflict
  --overwrite-conflicts    Replace edited harness-managed files/AGENTS.md block
  --dry-run                Validate and report without writing
  --remove                 Remove this Codex harness deployment
  -h, --help               Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -d|--directory) TARGET_DIR="${2:?--directory needs a path}"; shift 2 ;;
    -b|--branch) BRANCH="${2:?--branch needs a name}"; shift 2 ;;
    --source) SOURCE_DIR="${2:?--source needs a path}"; shift 2 ;;
    --codex-bin) CODEX_BIN_ARG="${2:?$1 needs a path}"; FORWARD_ARGS+=("$1" "$2"); shift 2 ;;
    --codex-home) CODEX_HOME_ARG="${2:?$1 needs a path}"; FORWARD_ARGS+=("$1" "$2"); shift 2 ;;
    --yes|--overwrite-conflicts|--dry-run|--remove) FORWARD_ARGS+=("$1"); shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'codex-install: unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

mkdir -p "$TARGET_DIR"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd -P)"
WORK=""
cleanup() { [ -z "$WORK" ] || rm -rf "$WORK"; }
trap cleanup EXIT HUP INT TERM

if [ -n "$SOURCE_DIR" ]; then
  SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd -P)"
else
  command -v git >/dev/null 2>&1 || {
    printf 'codex-install: git is required unless --source is provided\n' >&2
    exit 1
  }
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/codex-harness-install.XXXXXX")"
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$WORK/source" >/dev/null 2>&1 || {
    printf 'codex-install: clone failed; use --source for an offline install\n' >&2
    exit 1
  }
  SOURCE_DIR="$WORK/source"
fi

[ -f "$SOURCE_DIR/scripts/deploy-codex-adapter.sh" ] || {
  printf 'codex-install: invalid source checkout\n' >&2
  exit 1
}
bash "$SOURCE_DIR/scripts/deploy-codex-adapter.sh" \
  --source "$SOURCE_DIR" --target "$TARGET_DIR" ${FORWARD_ARGS[@]+"${FORWARD_ARGS[@]}"}

# ---------- ensure .codex/.agent-harness/ is gitignored (append-only; never rewrites) ----------
# The payload and plugin copies under .codex/.agent-harness/ carry .py files; untracked, they
# deny every commit under the strict commit-gate untracked-.py check. Mirrors the .claude/ step
# in install-harness.sh: runs only after a successful deploy (set -e exits above otherwise),
# never under --dry-run or --remove, skips a tracked directory, a directory git already ignores,
# or an explicit !.codex/.agent-harness rule, and is never fatal. The line is not recorded in the deployment manifest.
GI_RUN=1
for arg in ${FORWARD_ARGS[@]+"${FORWARD_ARGS[@]}"}; do
  case "$arg" in --dry-run|--remove) GI_RUN=0 ;; esac
done
if [ "$GI_RUN" -eq 1 ]; then
  GI="$TARGET_DIR/.gitignore"
  gi_skip=""
  if git -C "$TARGET_DIR" ls-files --error-unmatch -- .codex/.agent-harness >/dev/null 2>&1; then
    gi_skip="tracked"
  else
    # Ask git, not a regex: the last matching rule wins, and a re-include under an excluded
    # parent is impossible. Probe the directory itself (trailing /), so a file-only rule such as
    # `*.py` does not count; the path need not exist.
    # 0 = ignored, 1 = not ignored, 128 = not a git repo (then only our own line can say so).
    gi_rc=0
    git -C "$TARGET_DIR" check-ignore -q -- .codex/.agent-harness/ 2>/dev/null || gi_rc=$?
    if [ "$gi_rc" -eq 0 ] || { [ "$gi_rc" -ne 1 ] && [ -f "$GI" ] \
         && grep -qxE '[[:space:]]*/?\.codex/\.agent-harness/?[[:space:]]*' "$GI" 2>/dev/null; }; then
      gi_skip="ignored"
    fi
  fi
  if [ -z "$gi_skip" ] && [ -f "$GI" ] && grep -qE '^!/?\.codex/\.agent-harness/?[[:space:]]*$' "$GI" 2>/dev/null; then
    gi_skip="negated"
  fi
  if [ "$gi_skip" = "tracked" ]; then
    printf 'codex-install: warning: .codex/.agent-harness/ is tracked in this repo — leaving .gitignore alone.\n' >&2
  elif [ "$gi_skip" = "ignored" ]; then
    printf 'codex-install: git already ignores .codex/.agent-harness/ — .gitignore left as is.\n'
  elif [ "$gi_skip" = "negated" ]; then
    printf 'codex-install: .gitignore explicitly keeps .codex/.agent-harness/ (a ! rule) — left as is.\n'
  elif ! {
        { [ ! -s "$GI" ] || [ -z "$(tail -c 1 "$GI" 2>/dev/null)" ] || printf '\n' >> "$GI"; } &&
        printf '# Harness: .codex/.agent-harness/ is derived — rebuilt by install-codex-harness.sh\n.codex/.agent-harness/\n' >> "$GI"
      } 2>/dev/null; then
    printf 'codex-install: warning: could not update .gitignore — add .codex/.agent-harness/ to it manually.\n' >&2
  else
    printf 'codex-install: .gitignore now lists .codex/.agent-harness/\n'
  fi
fi

# ---------- workflow structure, doctor mode, and the hook-trust next step ----------
# Same condition as the .gitignore step: only after a successful deploy, never under --dry-run
# or --remove. Every call is guarded so nothing here can end the install non-zero. The doctor
# runs with --no-persist (no runtime-mode record before the user has reviewed trust) and is
# read-only toward Codex: it never edits trust configuration.
if [ "$GI_RUN" -eq 1 ]; then
  if [ -f "$SOURCE_DIR/scripts/init-structure.sh" ]; then
    bash "$SOURCE_DIR/scripts/init-structure.sh" --root "$TARGET_DIR" || true
  else
    printf 'codex-install: init-structure.sh not in this source checkout; skipping the workflow structure.\n'
  fi
  # Codex agent profiles read agents/PROJECT.md at the target root; never overwrite an existing
  # entry (a dangling symlink counts as existing). Seed from .claude/agents/PROJECT.md only when the
  # project customized it: an untouched copy is the harness's own PROJECT.md, whose commands are
  # wrong for this project. Copy through a temporary file so a failed copy leaves nothing behind.
  PROJECT_FILE="$TARGET_DIR/agents/PROJECT.md"
  CLAUDE_PROJECT="$TARGET_DIR/.claude/agents/PROJECT.md"
  PROJECT_SRC=""
  if [ -e "$PROJECT_FILE" ] || [ -L "$PROJECT_FILE" ]; then
    printf 'codex-install: agents/PROJECT.md exists; left as is.\n'
  elif [ -f "$CLAUDE_PROJECT" ] && ! cmp -s "$CLAUDE_PROJECT" "$SOURCE_DIR/agents/PROJECT.md"; then
    PROJECT_SRC="$CLAUDE_PROJECT"
    PROJECT_MSG='created agents/PROJECT.md from .claude/agents/PROJECT.md; Codex agents read the root copy, so keep the two in step.'
  elif [ -f "$SOURCE_DIR/agents/PROJECT.template.md" ]; then
    PROJECT_SRC="$SOURCE_DIR/agents/PROJECT.template.md"
    PROJECT_MSG='created agents/PROJECT.md from the template; fill in its Test execution section.'
  else
    printf 'codex-install: agents/PROJECT.template.md not in this source checkout; skipping agents/PROJECT.md.\n'
  fi
  if [ -n "$PROJECT_SRC" ]; then
    PROJECT_TMP="$PROJECT_FILE.tmp.$$"
    if mkdir -p "$TARGET_DIR/agents" && cp "$PROJECT_SRC" "$PROJECT_TMP" && mv "$PROJECT_TMP" "$PROJECT_FILE"; then
      printf 'codex-install: %s\n' "$PROJECT_MSG"
    else
      rm -f "$PROJECT_TMP" 2>/dev/null || true
      printf 'codex-install: could not create agents/PROJECT.md (see the error above); create it from agents/PROJECT.template.md yourself.\n'
    fi
  fi
  DOCTOR_ARGS=(--root "$TARGET_DIR" --repo-root "$SOURCE_DIR" --no-persist)
  # The doctor runs Codex with cwd=<target>, so make relative paths absolute first.
  case "$CODEX_BIN_ARG" in */*) case "$CODEX_BIN_ARG" in /*) ;; *) CODEX_BIN_ARG="$PWD/$CODEX_BIN_ARG" ;; esac ;; esac
  case "$CODEX_HOME_ARG" in ''|/*) ;; *) CODEX_HOME_ARG="$PWD/$CODEX_HOME_ARG" ;; esac
  CODEX_FLAGS=()
  [ -z "$CODEX_BIN_ARG" ] || CODEX_FLAGS+=(--codex-bin "$CODEX_BIN_ARG")
  [ -z "$CODEX_HOME_ARG" ] || CODEX_FLAGS+=(--codex-home "$CODEX_HOME_ARG")
  DOCTOR_ARGS+=(${CODEX_FLAGS[@]+"${CODEX_FLAGS[@]}"})
  doctor_rc=0
  doctor_out=$(python3 "$SOURCE_DIR/scripts/codex_harness_doctor.py" "${DOCTOR_ARGS[@]}" 2>/dev/null) || doctor_rc=$?
  [ "$doctor_rc" -eq 0 ] || doctor_out=""
  doctor_line=$(printf '%s' "$doctor_out" | python3 -c '
import json, sys
try:
    record = json.load(sys.stdin)
    mode = record["mode"]
    reasons = record.get("reason_codes") or []
except Exception:
    sys.exit(1)
if not isinstance(mode, str) or not mode:
    sys.exit(1)
print("%s (%s)" % (mode, ", ".join(str(r) for r in reasons) or "none"))
' 2>/dev/null) || doctor_line=""
  if [ -n "$doctor_line" ]; then
    printf 'codex-install: doctor mode: %s\n' "$doctor_line"
  elif [ "$doctor_rc" -ne 0 ]; then
    printf 'codex-install: doctor could not run (exit %s); run it yourself (below)\n' "$doctor_rc"
  else
    printf 'codex-install: doctor output was not a mode record; run it yourself (below)\n'
  fi
  # Shell-quoted, so the printed command survives a paste even when a path has spaces.
  q_flags=""
  for flag in ${CODEX_FLAGS[@]+"${CODEX_FLAGS[@]}"}; do q_flags="$q_flags $(printf '%q' "$flag")"; done
  q_target=$(printf '%q' "$TARGET_DIR")
  printf 'codex-install: next: start Codex in %s, choose "Review hooks" (or run /hooks and press t on each Agent Harness hook); hooks do not run until trusted.\n' "$TARGET_DIR"
  if [ -n "$WORK" ]; then
    printf 'codex-install: then run: git clone --depth 1 --branch %s %s agent-harness && python3 agent-harness/scripts/codex_harness_doctor.py --root %s%s\n' "$(printf '%q' "$BRANCH")" "$(printf '%q' "$REPO_URL")" "$q_target" "$q_flags"
  else
    printf 'codex-install: then run: python3 %s --root %s%s\n' "$(printf '%q' "$SOURCE_DIR/scripts/codex_harness_doctor.py")" "$q_target" "$q_flags"
  fi
fi
