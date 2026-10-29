#!/bin/bash
# Provision one isolated sandbox (a git worktree plus the untracked environment) for one ticket.
# A plain `git worktree add` checks out committed files only, so .env, CLAUDE.local.md, caches and
# installed dependencies are missing. This script adds them from a manifest, gives the sandbox its
# own port block, runs the project's setup commands, and checks the result before it says "ready".
#
# Usage: provision-sandbox.sh <repoDir> <runId> <n> <slug> [--branch B] [--from REF] [--remote R] [--port-base N] [--max-kb N] [--mode worktree|clone]
#   Sandbox dir:  <parent of repoDir>/.ship-<repo name>/<runId>-t<n>-<slug>
#   Manifest:     <repoDir>/.harness-sandbox   (one directive per line, # starts a comment)
#       copy <path>      copy a file or directory from repoDir if it exists (.env, CLAUDE.local.md)
#       link <path>      symlink it from repoDir if it exists (node_modules, .venv)
#       require <path>   fail if the sandbox lacks this path after copy, link and setup
#       setup <command>  run in the sandbox; it sees SANDBOX_PORT, SANDBOX_PORT_RANGE, SANDBOX_DB_NAME
#       require-env <VAR>  fail if the shell variable is unset or empty. Checked first, before the
#                        worktree, copy, link or setup run; the error names the variable
#       check <command>  run in the sandbox after setup and require, with the .sandbox.env variables
#                        (for example start the app and call its health endpoint). The sandbox is
#                        "ready" only when every check exits 0. Each check has 60 s (override with
#                        HARNESS_CHECK_TIMEOUT, in seconds); its process group is killed when it
#                        ends, so a background server does not outlive the check.
#   A project with a web and an API process uses two ports: web on $SANDBOX_PORT and API on
#   $((SANDBOX_PORT+1)) (the block holds ten, SANDBOX_PORT_RANGE).
#       teardown <command>  not run at provision time. `clean --yes` runs every teardown line in reverse
#                        order, in the sandbox with the .sandbox.env variables, before it removes the
#                        sandbox (for example drop the database a setup line made). The first failure
#                        stops the removal, keeps the sandbox and says which command failed.
#   Paths are relative to the repo root. Absolute paths and `..` are rejected.
#       skip <path>      state that the sandbox deliberately does not carry (the audit stops asking)
#   Without a manifest line, provisioning classifies every ignored path the way --audit does:
#       small local-only files (CLAUDE.local.md, *.local ...) are copied on its own;
#       credential or state files (.env, .env.*, *.db, *.sqlite, .auth) are never copied on their own:
#       they stop the run until a manifest `copy` line says so (an unattended agent must not get secrets);
#       regenerable paths (node_modules, caches, build output) are left out;
#       any unknown path (a prod-named file, a config file over --max-kb, no rule) stops the run
#       BEFORE the worktree is created and before anything is copied, and prints one manifest
#       line to add for each such path. A manifest copy line wins over the prod rule; a prod-named
#       file is never copied by default; a manifest skip line settles a path. --max-kb N is the size
#       limit for config or state files in KB (default 5120). The main checkout is only read.
# Audit: provision-sandbox.sh --audit <repoDir> [--max-kb N] [--all]
#   Lists every ignored file or directory in repoDir and says what a sandbox would do with it:
#   covered (the manifest handles it), copy (small local-only file), skip (regenerable or skipped),
#   unknown (needs a manifest line). Skip lines are hidden unless --all. Exits 1 when any path is
#   unknown. Read-only. Provisioning runs the same classification.
# Mode:  --mode worktree (default) makes a git worktree that shares repoDir's .git.
#        --mode clone makes a standalone `git clone --local` with its own .git, so nothing in it can touch
#        repoDir's refs. It carries committed content only (--from must be committed in repoDir, else exit 1),
#        gets repoDir's remote URL as origin (--remote names the remote whose URL is copied; clone mode does
#        not fetch, and its origin/* refs mirror repoDir's refs/remotes/<remote>/*; no such remote: warning, no set-url), and repoDir's local user.name and user.email.
#        A clone is marked by .git/harness-sandbox-source holding repoDir's path; re-runs reuse only such a clone.
#        Manifest, port, setup, require and the JSON line are the same in both modes.
# Registry: every sandbox gets <sandbox>/.sandbox.json with runId, ticket {n, slug}, branch
#   ("detached" when HEAD is detached; a re-run on a detached HEAD keeps the recorded branch), created_at (UTC ISO 8601) and pr (null). A re-run keeps
#   created_at. The file and .sandbox.pid are excluded from git status.
# List: provision-sandbox.sh list <repoDir>
#   Prints SANDBOX BRANCH STATE SIZE AGE for each sandbox in <parent>/.ship-<repo name>/.
#   STATE is running, PR open, merged, abandoned, in progress or unknown. Prints nothing when
#   there are no sandboxes.
#   running: <sandbox>/.sandbox.pid holds a live pid. A caller that runs work in the sandbox
#   writes its pid there. A dead or invalid pid is not running.
#   PR state comes from `gh pr view <branch>`. If gh fails or is missing, the state is unknown.
#   abandoned: no PR, not running, older than 7 days.
# Clean: provision-sandbox.sh clean <repoDir> (--run ID | --branch B | --merged | --older Nd) [--yes]
#   Without --yes it prints "would remove" lines and changes nothing. With --yes it runs
#   `git worktree remove` with no force flag, after the manifest teardown lines (see above). A dirty
#   sandbox is refused first, before any teardown runs, and left in place, and the exit code is 1. A
#   failing teardown refuses the sandbox the same way. There is no flag that skips a failing teardown. Running and unknown sandboxes are always skipped. --older also skips
#   sandboxes with an open PR. Branches are kept. A directory that is not a registered
#   sandbox worktree is reported and kept. Bad usage exits 2.
# Prints one JSON line on stdout when ready (it carries "mode"). Exit 0 ready, 1 failed, 2 bad usage.
# Running it again for the same sandbox re-syncs the manifest and reuses the worktree or clone.
set -u

die() { printf 'provision-sandbox: %s\n' "$1" >&2; exit "${2:-1}"; }

# ---- classification (shared by --audit and provisioning) ---------------------------------------
under() { # under <path> <list item>: the path is the item, inside it, or holds it
  case "$1" in "$2"|"$2"/*) return 0 ;; esac
  case "$2" in "$1"/*) return 0 ;; esac
  return 1
}
has_part() { # has_part <path> <glob>...: any path component matches a glob
  local path=$1 g c; shift
  local -a parts; IFS=/ read -ra parts <<< "$path"
  for c in "${parts[@]}"; do
    for g in "$@"; do
      # shellcheck disable=SC2254
      case "$c" in $g) return 0 ;; esac
    done
  done
  return 1
}

# classify_repo <repo> <max_kb> fills ROWS (tab-separated: decision, size, path, why), COPY_PATHS
# (paths to copy without a manifest line) and UNKNOWN_PATHS / UNKNOWN_WHY (parallel arrays).
classify_repo() {
  local repo=$1 max_kb=$2 line verb arg entry code path nested c kb size why decision
  local -a covered=() skipped=() untracked_dirs=()
  ROWS=(); COPY_PATHS=(); UNKNOWN_PATHS=(); UNKNOWN_WHY=()
  if [ -f "$repo/.harness-sandbox" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      line=${line%%#*}; verb=${line%%[[:space:]]*}
      arg=${line#"$verb"}; arg=${arg#"${arg%%[![:space:]]*}"}; arg=${arg%"${arg##*[![:space:]]}"}; arg=${arg%/}
      case "$verb" in copy|link) covered+=("$arg") ;; skip) skipped+=("$arg") ;; esac
    done < "$repo/.harness-sandbox"
  fi
  while IFS= read -r entry; do
    code=${entry:0:2}; path=${entry:3}; path=${path%/}
    case "$code" in '!!'|'??') ;; *) continue ;; esac
    # git descends into an untracked directory to list its ignored files; the directory already says it all.
    nested=0
    for c in ${untracked_dirs[@]+"${untracked_dirs[@]}"}; do case "$path/" in "$c"/*) nested=1; break ;; esac; done
    [ "$nested" -eq 0 ] || continue
    [ "$code" != '??' ] || untracked_dirs+=("$path")
    kb=$(du -sk "$repo/$path" 2>/dev/null | cut -f1); kb=${kb:-0}
    size="${kb}K"; [ "$kb" -ge 1024 ] && size="$((kb / 1024))M"
    why=''; decision=''
    for c in ${covered[@]+"${covered[@]}"}; do under "$path" "$c" && { decision=covered; why='manifest copy/link'; break; }; done
    if [ -z "$decision" ]; then
      for c in ${skipped[@]+"${skipped[@]}"}; do under "$path" "$c" && { decision=skip; why='manifest skip'; break; }; done
    fi
    if [ -z "$decision" ] && [ "$code" = '??' ]; then
      decision=skip; why='untracked, not ignored: a worktree never carries it'
    fi
    if [ -z "$decision" ] && has_part "$path" node_modules .venv venv __pycache__ .next .turbo dist build target \
        .pytest_cache .ruff_cache .mypy_cache .cache .parcel-cache coverage .gradle '*.egg-info' '*.pyc' \
        '*.tsbuildinfo' .DS_Store .idea .vscode next-env.d.ts test-results playwright-report .playwright-mcp worktrees; then
      decision=skip; why='regenerable or per-checkout'
    fi
    if [ -z "$decision" ] && has_part "$path" '*prod*'; then
      decision=unknown; why='production-looking name: decide by hand'
    fi
    if [ -z "$decision" ] && has_part "$path" '.env' '.env.*' '*.db' '*.sqlite' '*.sqlite3' .auth; then
      if [ "$kb" -le "$max_kb" ]; then decision=unknown; why='credential or state file: copy only with a manifest line'
      else decision=unknown; why="config or state over ${max_kb}K"; fi
    fi
    if [ -z "$decision" ] && has_part "$path" '*.local' '*.local.*'; then
      if [ "$kb" -le "$max_kb" ]; then decision=copy; why='small local-only file'
      else decision=unknown; why="config or state over ${max_kb}K"; fi
    fi
    [ -n "$decision" ] || { decision=unknown; why='no rule matches'; }
    ROWS+=("$decision"$'\t'"$size"$'\t'"$path"$'\t'"$why")
    case "$decision" in
      copy) COPY_PATHS+=("$path") ;;
      unknown) UNKNOWN_PATHS+=("$path"); UNKNOWN_WHY+=("$why") ;;
    esac
  done < <(git -C "$repo" status --porcelain --ignored=traditional -unormal)
}

# ---- audit mode -------------------------------------------------------------------------------
if [ "${1:-}" = --audit ]; then
  [ "$#" -ge 2 ] || die 'usage: provision-sandbox.sh --audit <repoDir> [--max-kb N] [--all]' 2
  a_repo=$2; max_kb=5120; show_all=0; shift 2
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --max-kb) [ "$#" -ge 2 ] || die '--max-kb needs a value' 2; max_kb=$2; shift 2 ;;
      --all) show_all=1; shift ;;
      *) die "unknown option: $1" 2 ;;
    esac
  done
  case "$max_kb" in ''|*[!0-9]*) die '--max-kb must be a number' 2 ;; esac
  a_repo=$(cd "$a_repo" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null) || die 'repoDir is not a git checkout' 2

  classify_repo "$a_repo" "$max_kb"
  counts_copy=0; counts_skip=0; counts_cov=0
  printf '%-9s %9s  %s\n' DECISION SIZE PATH
  for row in ${ROWS[@]+"${ROWS[@]}"}; do
    IFS=$'\t' read -r decision size path why <<< "$row"
    case "$decision" in
      copy) counts_copy=$((counts_copy + 1)) ;; skip) counts_skip=$((counts_skip + 1)) ;;
      covered) counts_cov=$((counts_cov + 1)) ;;
    esac
    if [ "$decision" != skip ] || [ "$show_all" -eq 1 ]; then
      printf '%-9s %9s  %s   (%s)\n' "$decision" "$size" "$path" "$why"
    fi
  done
  unknown=${#UNKNOWN_PATHS[@]}
  printf '\ncovered %s, copy %s, skip %s, unknown %s\n' "$counts_cov" "$counts_copy" "$counts_skip" "$unknown"
  [ "$unknown" -eq 0 ] || { printf 'audit: %s path(s) unknown; add copy, link or skip lines to %s/.harness-sandbox\n' "$unknown" "$a_repo" >&2; exit 1; }
  exit 0
fi

# ---- list and clean modes ---------------------------------------------------------------------
sb_json() { sed -n 's/.*"'"$2"'":"\([^"]*\)".*/\1/p' "$1" 2>/dev/null | head -1; } # sb_json <file> <key>

sb_running() { # the pid in <sandbox>/.sandbox.pid is alive
  local pid; pid=$(head -1 "$1/.sandbox.pid" 2>/dev/null)
  case "$pid" in ''|*[!0-9]*) return 1 ;; esac
  [ "$pid" -gt 0 ] && kill -0 "$pid" 2>/dev/null
}

sb_pr_state() { # sb_pr_state <repo> <branch>: PR open, merged, none or unknown
  local out err_file rc
  [ -n "$2" ] && [ "$2" != detached ] || { printf none; return; }
  command -v gh >/dev/null 2>&1 || { printf unknown; return; }
  err_file=$(mktemp)
  out=$(cd "$1" && gh pr view "$2" --json state -q .state 2>"$err_file"); rc=$?
  if [ "$rc" -eq 0 ]; then
    case "$out" in OPEN) printf 'PR open' ;; MERGED) printf merged ;; CLOSED) printf none ;; *) printf unknown ;; esac
  elif grep -qi 'no pull requests found' "$err_file"; then printf none
  else printf unknown
  fi
  rm -f "$err_file"
}

sb_age_days() { # sb_age_days <created_at>: whole days, or -1 when the time cannot be read
  local ts=$1 t0 now
  t0=$(date -u -d "$ts" +%s 2>/dev/null) || t0=$(date -j -u -f '%Y-%m-%dT%H:%M:%SZ' "$ts" +%s 2>/dev/null) || t0=''
  case "$t0" in ''|*[!0-9]*) printf -- -1; return ;; esac
  now=$(date +%s)
  [ "$now" -ge "$t0" ] || { printf 0; return; }
  printf '%s' $(((now - t0) / 86400))
}

sb_scan_init() { # sb_scan_init <repoDir>: sets sb_repo, sb_root
  sb_repo=$(cd "$1" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null) || die 'repoDir is not a git checkout' 2
  sb_root="$(dirname "$sb_repo")/.ship-$(basename "$sb_repo")"
}

sb_classify() { # sb_classify <sandbox dir>: sets sb_branch sb_age sb_kb sb_state
  local pr
  sb_branch=$(sb_json "$1/.sandbox.json" branch)
  sb_age=$(sb_age_days "$(sb_json "$1/.sandbox.json" created_at)")
  sb_kb=$(du -sk "$1" 2>/dev/null | cut -f1); sb_kb=${sb_kb:-0}
  if sb_running "$1"; then sb_state=running; return; fi
  pr=$(sb_pr_state "$sb_repo" "$sb_branch")
  case "$pr" in
    'PR open'|merged|unknown) sb_state=$pr ;;
    *) if [ "$sb_age" -lt 0 ]; then sb_state=unknown
       elif [ "$sb_age" -gt 7 ]; then sb_state=abandoned
       else sb_state='in progress'; fi ;;
  esac
}

if [ "${1:-}" = list ]; then
  [ "$#" -eq 2 ] || die 'usage: provision-sandbox.sh list <repoDir>' 2
  sb_scan_init "$2"
  rows=''
  for sb in "$sb_root"/*/; do
    sb=${sb%/}; [ -f "$sb/.sandbox.json" ] || continue
    sb_classify "$sb"
    size="${sb_kb}K"; [ "$sb_kb" -ge 1024 ] && size="$((sb_kb / 1024))M"
    age='?'; [ "$sb_age" -lt 0 ] || age="${sb_age}d"
    rows="$rows$(printf '%-40s %-28s %-12s %7s %5s' "$(basename "$sb")" "${sb_branch:-?}" "$sb_state" "$size" "$age")"$'\n'
  done
  [ -n "$rows" ] || exit 0
  printf '%-40s %-28s %-12s %7s %5s\n' SANDBOX BRANCH STATE SIZE AGE
  printf '%s' "$rows"
  exit 0
fi

if [ "${1:-}" = clean ]; then
  cusage='usage: provision-sandbox.sh clean <repoDir> (--run ID | --branch B | --merged | --older Nd) [--yes]'
  [ "$#" -ge 3 ] || die "$cusage" 2
  c_repo=$2; shift 2
  sel=''; sel_val=''; yes=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --run) [ "$#" -ge 2 ] || die '--run needs a value' 2; [ -z "$sel" ] || die "$cusage" 2; sel=run; sel_val=$2; shift 2 ;;
      --older) [ "$#" -ge 2 ] || die '--older needs a value' 2; [ -z "$sel" ] || die "$cusage" 2; sel=older; sel_val=$2; shift 2 ;;
      --branch) [ "$#" -ge 2 ] || die '--branch needs a value' 2; [ -z "$sel" ] || die "$cusage" 2; sel=branch; sel_val=$2; shift 2 ;;
      --merged) [ -z "$sel" ] || die "$cusage" 2; sel=merged; shift ;;
      --yes) yes=1; shift ;;
      *) die "unknown option: $1" 2 ;;
    esac
  done
  [ -n "$sel" ] || die "$cusage" 2
  if [ "$sel" = older ]; then
    case "$sel_val" in *d) sel_val=${sel_val%d} ;; *) die '--older needs a value like 7d' 2 ;; esac
    case "$sel_val" in ''|*[!0-9]*) die '--older needs a value like 7d' 2 ;; esac
  fi
  [ "$sel" != run ] || sel_val=$(printf '%s' "$sel_val" | tr -c 'A-Za-z0-9\n' '-' | sed 's/^-*//; s/-*$//')
  sb_scan_init "$c_repo"
  registered=$(git -C "$sb_repo" worktree list --porcelain | sed -n 's/^worktree //p')
  rc=0
  teardowns=()
  if [ -f "$sb_repo/.harness-sandbox" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      line=${line%%#*}; verb=${line%%[[:space:]]*}
      [ "$verb" = teardown ] || continue
      arg=${line#"$verb"}; arg=${arg#"${arg%%[![:space:]]*}"}; arg=${arg%"${arg##*[![:space:]]}"}
      [ -n "$arg" ] || die 'manifest: empty teardown command'
      teardowns+=("$arg")
    done < "$sb_repo/.harness-sandbox"
  fi
  for sb in "$sb_root"/*/; do
    sb=${sb%/}; [ -d "$sb" ] || continue
    name=$(basename "$sb")
    # --run and --branch read only .sandbox.json: filter before any gh call or skip line.
    case "$sel" in
      run) [ "$(sb_json "$sb/.sandbox.json" runId)" = "$sel_val" ] || continue ;;
      branch) [ "$(sb_json "$sb/.sandbox.json" branch)" = "$sel_val" ] || continue ;;
    esac
    real=$(cd "$sb" && pwd -P)
    is_clone=0
    if [ -f "$sb/.sandbox.json" ] && [ -d "$sb/.git" ] && [ -f "$sb/.git/harness-sandbox-source" ] \
      && [ "$(cat "$sb/.git/harness-sandbox-source")" = "$(cd "$sb_repo" && pwd -P)" ]; then
      is_clone=1
    elif ! printf '%s\n' "$registered" | grep -qxF "$real" || [ ! -f "$sb/.sandbox.json" ]; then
      printf 'skip %s (not a registered sandbox worktree or clone)\n' "$name"; continue
    fi
    sb_classify "$sb"
    case "$sel" in
      merged) [ "$sb_state" = merged ] || continue ;;
      older) { [ "$sb_age" -ge "$sel_val" ] && [ "$sb_state" != 'PR open' ]; } || continue ;;
    esac
    case "$sb_state" in
      running|unknown) printf 'skip %s (%s)\n' "$name" "$sb_state"; continue ;;
    esac
    if [ "$yes" -eq 0 ]; then printf 'would remove %s (%s)\n' "$name" "$sb_state"; continue; fi
    if [ -n "$(git -C "$sb" status --porcelain 2>/dev/null)" ]; then
      printf 'refused %s (%s): sandbox has uncommitted changes\n' "$name" "$sb_state"; rc=1; continue
    fi
    if [ "$is_clone" -eq 1 ]; then
      # A clone's own commits live only in its .git: refuse when a branch or HEAD holds one that no remote
      # ref and not the source repo has.
      unpushed=0
      while IFS= read -r c; do
        [ -n "$c" ] || continue
        git -C "$sb_repo" cat-file -e "$c^{commit}" 2>/dev/null || { unpushed=1; break; }
      done < <(git -C "$sb" rev-list --branches HEAD --not --remotes 2>/dev/null)
      if [ "$unpushed" -eq 1 ]; then
        printf 'refused %s (%s): clone has unpushed commits\n' "$name" "$sb_state"; rc=1; continue
      fi
    fi
    if [ "${#teardowns[@]}" -gt 0 ] && [ ! -f "$sb/.sandbox.env" ]; then
      printf 'refused %s (%s): .sandbox.env is missing, teardown needs its variables\n' "$name" "$sb_state"; rc=1; continue
    fi
    failed=''
    i=${#teardowns[@]}
    while [ "$i" -gt 0 ]; do
      i=$((i - 1))
      if ! (cd "$sb" && set -a && { [ ! -f ./.sandbox.env ] || . ./.sandbox.env; } && set +a && bash -c "${teardowns[$i]}") >&2; then
        failed=${teardowns[$i]}; break
      fi
    done
    if [ -n "$failed" ]; then
      printf 'refused %s (%s): teardown failed: %s\n' "$name" "$sb_state" "$failed"; rc=1; continue
    fi
    if [ "$is_clone" -eq 1 ]; then
      if rm -rf "$sb"; then printf 'removed %s (%s)\n' "$name" "$sb_state"
      else printf 'refused %s (%s): cannot remove the clone\n' "$name" "$sb_state"; rc=1; fi
    elif err=$(git -C "$sb_repo" worktree remove "$sb" 2>&1); then
      printf 'removed %s (%s)\n' "$name" "$sb_state"
    else
      printf 'refused %s (%s): %s\n' "$name" "$sb_state" "$(printf '%s' "$err" | head -1)"; rc=1
    fi
  done
  exit "$rc"
fi

[ "$#" -ge 4 ] || die 'usage: provision-sandbox.sh <repoDir> <runId> <n> <slug> [--branch B] [--from REF] [--remote R] [--port-base N] [--max-kb N] [--mode worktree|clone]' 2
repo=$1; run=$2; n=$3; slug=$4; shift 4
branch=''; from=HEAD; remote=''; port_base=4000; max_kb=5120; mode=worktree
while [ "$#" -gt 0 ]; do
  case "$1" in
    --branch) [ "$#" -ge 2 ] || die '--branch needs a value' 2; branch=$2; shift 2 ;;
    --from) [ "$#" -ge 2 ] || die '--from needs a value' 2; from=$2; shift 2 ;;
    --remote) [ "$#" -ge 2 ] || die '--remote needs a value' 2; remote=$2; shift 2 ;;
    --mode) [ "$#" -ge 2 ] || die '--mode needs a value' 2; mode=$2; shift 2 ;;
    --port-base) [ "$#" -ge 2 ] || die '--port-base needs a value' 2; port_base=$2; shift 2 ;;
    --max-kb) [ "$#" -ge 2 ] || die '--max-kb needs a value' 2; max_kb=$2; shift 2 ;;
    *) die "unknown option: $1" 2 ;;
  esac
done
case "$mode" in worktree|clone) ;; *) die "--mode must be worktree or clone, got '$mode'" 2 ;; esac
case "$n" in ''|*[!0-9]*) die "n must be a number, got '$n'" 2 ;; esac
case "$port_base" in ''|*[!0-9]*) die "--port-base must be a number" 2 ;; esac
case "$max_kb" in ''|*[!0-9]*) die '--max-kb must be a number' 2 ;; esac
slug=$(printf '%s' "$slug" | tr -c 'A-Za-z0-9\n' '-' | sed 's/^-*//; s/-*$//')
run=$(printf '%s' "$run" | tr -c 'A-Za-z0-9\n' '-' | sed 's/^-*//; s/-*$//')
[ -n "$slug" ] && [ -n "$run" ] || die 'runId and slug need at least one letter or digit' 2

repo=$(cd "$repo" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null) || die 'repoDir is not a git checkout' 2
parent=$(dirname "$repo")
dir="$parent/.ship-$(basename "$repo")/$run-t$n-$slug"

# require-env first: a missing variable must fail before any worktree, copy, link or setup exists.
if [ -f "$repo/.harness-sandbox" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    line=${line%%#*}; verb=${line%%[[:space:]]*}
    [ "$verb" = require-env ] || continue
    arg=${line#"$verb"}; arg=${arg#"${arg%%[![:space:]]*}"}; arg=${arg%"${arg##*[![:space:]]}"}
    case "$arg" in ''|[0-9]*|*[!A-Za-z0-9_]*) die "manifest: bad variable name for 'require-env': '$arg'" ;; esac
    [ -n "${!arg:-}" ] || die "required environment variable is not set: $arg"
  done < "$repo/.harness-sandbox"
fi

safe_path() { # reject absolute paths and `..` segments
  case "$1" in /*|..|../*|*/..|*/../*|'') return 1 ;; esac
}

# Preflight: classify every ignored path the way --audit does. Any unknown path stops the run here,
# before the worktree exists and before anything is copied. The main checkout is only read.
classify_repo "$repo" "$max_kb"
if [ "${#UNKNOWN_PATHS[@]}" -gt 0 ]; then
  {
    printf 'provision-sandbox: %s path(s) unknown; add one line per path to %s/.harness-sandbox:\n' "${#UNKNOWN_PATHS[@]}" "$repo"
    i=0
    while [ "$i" -lt "${#UNKNOWN_PATHS[@]}" ]; do
      printf '  copy %s   (or: skip %s)   # %s\n' "${UNKNOWN_PATHS[$i]}" "${UNKNOWN_PATHS[$i]}" "${UNKNOWN_WHY[$i]}"
      i=$((i + 1))
    done
  } >&2
  exit 1
fi

cleanup_dir=''
trap '[ -z "$cleanup_dir" ] || rm -rf "$cleanup_dir"' EXIT
sandbox_parent="$parent/.ship-$(basename "$repo")"

if [ "$mode" = clone ]; then
  repo_real=$(cd "$repo" && pwd -P)
  if [ -d "$dir/.git" ] && [ -f "$dir/.git/harness-sandbox-source" ]; then
    [ "$(cat "$dir/.git/harness-sandbox-source")" = "$repo_real" ] || die "$dir exists and is not a clone of $repo"
  elif [ -e "$dir" ] || [ -L "$dir" ]; then
    die "$dir exists and is not a clone of $repo"
  else
    sha=$(git -C "$repo" rev-parse --verify -q "$from^{commit}") || die "ref not committed in $repo: $from"
    mkdir -p "$sandbox_parent" || die 'cannot create the sandbox parent'
    cleanup_dir=$dir
    git clone -q --local --no-checkout "$repo" "$dir" || die 'git clone failed'
    git -C "$dir" cat-file -e "$sha^{commit}" 2>/dev/null || git -C "$dir" fetch -q "$repo" "$sha" || die "cannot get $from into the clone"
    if [ -n "$branch" ]; then
      git -C "$dir" checkout -q -b "$branch" "$sha" || die 'git checkout failed'
    else
      git -C "$dir" checkout -q --detach "$sha" || die 'git checkout failed'
    fi
    printf '%s\n' "$repo_real" > "$dir/.git/harness-sandbox-source"
    url=$(git -C "$repo" remote get-url "${remote:-origin}" 2>/dev/null) || url=''
    if [ -n "$url" ]; then
      git -C "$dir" remote set-url origin "$url" || die 'git remote set-url failed'
      # The clone's origin/* refs are copies of repoDir's local branches, not of the remote. Rebuild them
      # from repoDir's own remote-tracking refs for that remote (local data, no fetch).
      git -C "$dir" for-each-ref --format='%(refname)' refs/remotes/origin | while read -r r; do
        git -C "$dir" update-ref -d "$r"
      done
      git -C "$repo" for-each-ref --format='%(objectname) %(refname)' "refs/remotes/${remote:-origin}" | while read -r oid r; do
        n=${r#"refs/remotes/${remote:-origin}/"}
        [ "$n" = HEAD ] && continue
        git -C "$dir" cat-file -e "$oid^{commit}" 2>/dev/null || git -C "$dir" fetch -q "$repo" "$oid" 2>/dev/null || continue
        git -C "$dir" update-ref "refs/remotes/origin/$n" "$oid"
      done
    else
      printf 'provision-sandbox: warning: %s has no remote %s; clone origin left as the local path\n' "$repo" "${remote:-origin}" >&2
    fi
    for key in user.name user.email; do
      val=$(git -C "$repo" config --local --get "$key" 2>/dev/null) || val=''
      [ -z "$val" ] || git -C "$dir" config "$key" "$val"
    done
  fi
elif [ -e "$dir/.git" ]; then
  [ -f "$dir/.git" ] || die "$dir exists but is not a worktree of $repo"
  common=$(git -C "$dir" rev-parse --git-common-dir 2>/dev/null) && common=$(cd "$dir" && cd "$common" && pwd -P)
  [ "$common" = "$(cd "$repo" && cd "$(git rev-parse --git-common-dir)" && pwd -P)" ] \
    || die "$dir exists but is not a worktree of $repo"
elif [ -e "$dir" ]; then
  die "$dir exists and is not a worktree"
else
  [ -z "$remote" ] || git -C "$repo" fetch -q "$remote" || die "git fetch $remote failed"
  mkdir -p "$sandbox_parent" || die 'cannot create the sandbox parent'
  if [ -n "$branch" ]; then
    git -C "$repo" worktree add -q -b "$branch" "$dir" "$from" || die 'git worktree add failed'
  else
    git -C "$repo" worktree add -q --detach "$dir" "$from" || die 'git worktree add failed'
  fi
fi

# Keep sandbox-only files out of git status. info/exclude lives in the common dir, shared by all worktrees.
excl=$(git -C "$dir" rev-parse --path-format=absolute --git-path info/exclude)
for ex in /.sandbox.env /.sandbox.json /.sandbox.pid; do
  grep -qxF "$ex" "$excl" 2>/dev/null || printf '%s\n' "$ex" >> "$excl"
done

port=$((port_base + n * 10))
db="sandbox_$(printf '%s' "$run-t$n" | tr '-' '_')"
{
  printf 'SANDBOX_PORT=%s\n' "$port"
  printf 'SANDBOX_PORT_RANGE=%s-%s\n' "$port" "$((port + 9))"
  printf 'SANDBOX_DB_NAME=%s\n' "$db"
} > "$dir/.sandbox.env"

# Small config or state the classifier found: copy it with no manifest line (no clobber).
for p in ${COPY_PATHS[@]+"${COPY_PATHS[@]}"}; do
  safe_path "$p" || die "unsafe path from the repo scan: '$p'"
  if [ -e "$repo/$p" ] && [ ! -e "$dir/$p" ]; then
    mkdir -p "$dir/$(dirname "$p")"
    cp -R "$repo/$p" "$dir/$p" || die "copy failed: $p"
  fi
done

# Registry record. A re-run keeps the first created_at.
head_branch=$(git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null || printf detached)
# A re-run on a detached HEAD (UAT detaches it) keeps the branch the registry already records.
prev_branch=$(sed -n 's/.*"branch":"\([^"]*\)".*/\1/p' "$dir/.sandbox.json" 2>/dev/null | head -1)
if [ "$head_branch" = detached ] && [ -n "$prev_branch" ] && [ "$prev_branch" != detached ]; then
  head_branch=$prev_branch
fi
created_at=$(sed -n 's/.*"created_at":"\([^"]*\)".*/\1/p' "$dir/.sandbox.json" 2>/dev/null | head -1)
[ -n "$created_at" ] || created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
json_branch=$(printf '%s' "$head_branch" | sed 's/\\/\\\\/g; s/"/\\"/g')
printf '{"runId":"%s","ticket":{"n":%s,"slug":"%s"},"branch":"%s","created_at":"%s","pr":null}\n' \
  "$run" "$n" "$slug" "$json_branch" "$created_at" > "$dir/.sandbox.json"

manifest="$repo/.harness-sandbox"
requires=(); setups=(); checks=()
if [ -f "$manifest" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    line=${line%%#*}
    verb=${line%%[[:space:]]*}
    arg=${line#"$verb"}; arg=${arg#"${arg%%[![:space:]]*}"}; arg=${arg%"${arg##*[![:space:]]}"}
    [ -n "$verb" ] || continue
    case "$verb" in
      copy|link|require)
        safe_path "$arg" || die "manifest: unsafe or empty path for '$verb': '$arg'" ;;
    esac
    case "$verb" in
      copy)
        if [ -e "$repo/$arg" ] && [ ! -e "$dir/$arg" ]; then
          mkdir -p "$dir/$(dirname "$arg")"
          cp -R "$repo/$arg" "$dir/$arg" || die "copy failed: $arg"
        fi ;;
      link)
        if [ -e "$repo/$arg" ] && [ ! -e "$dir/$arg" ] && [ ! -L "$dir/$arg" ]; then
          mkdir -p "$dir/$(dirname "$arg")"
          ln -s "$repo/$arg" "$dir/$arg" || die "link failed: $arg"
          # A `node_modules/` ignore pattern matches a directory, not a symlink to one.
          grep -qxF "/$arg" "$excl" || printf '/%s\n' "$arg" >> "$excl"
        fi ;;
      skip) ;;
      require) requires+=("$arg") ;;
      require-env) ;; # checked before the worktree exists
      check) [ -n "$arg" ] || die 'manifest: empty check command'; checks+=("$arg") ;;
      teardown) [ -n "$arg" ] || die 'manifest: empty teardown command' ;;
      setup) [ -n "$arg" ] || die 'manifest: empty setup command'; setups+=("$arg") ;;
      *) die "manifest: unknown directive '$verb'" ;;
    esac
  done < "$manifest"
fi

for cmd in "${setups[@]+"${setups[@]}"}"; do
  (cd "$dir" && set -a && . ./.sandbox.env && set +a && bash -c "$cmd") >&2 || die "setup failed: $cmd"
done

for p in "${requires[@]+"${requires[@]}"}"; do
  [ -e "$dir/$p" ] || die "required path missing in sandbox: $p (not in $repo and not made by setup)"
done

cleanup_dir=''
# run_check <command>: run in the sandbox in its own process group, kill the group when it ends.
run_check() {
  local cmd=$1 limit=${HARNESS_CHECK_TIMEOUT:-60} ticks=0 pid rc
  case "$limit" in ''|*[!0-9]*) limit=60 ;; esac
  set -m
  (cd "$dir" && set -a && . ./.sandbox.env && set +a && exec bash -c "$cmd") >&2 &
  pid=$!
  set +m
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$ticks" -ge $((limit * 5)) ]; then
      kill -TERM -- "-$pid" 2>/dev/null; sleep 0.2; kill -KILL -- "-$pid" 2>/dev/null
      wait "$pid" 2>/dev/null
      die "check timed out after ${limit}s: $cmd"
    fi
    sleep 0.2; ticks=$((ticks + 1))
  done
  wait "$pid"; rc=$?
  kill -TERM -- "-$pid" 2>/dev/null; kill -KILL -- "-$pid" 2>/dev/null
  [ "$rc" -eq 0 ] || die "check failed: $cmd"
}
for cmd in "${checks[@]+"${checks[@]}"}"; do run_check "$cmd"; done

printf '{"status":"ready","mode":"%s","dir":"%s","branch":"%s","port":%s,"db":"%s"}\n' "$mode" "$dir" "$head_branch" "$port" "$db"
