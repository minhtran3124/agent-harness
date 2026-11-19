#!/usr/bin/env bash
# End-state evidence check for one ticket that free agent sessions worked on. It checks results,
# never the order of work. Fixed checks only: receipt, report, acceptance, security, repro, suite.
#
# Threat model: the worker controls its checkout (--repo): refs, tags, refs/replace, .git/config,
# hooks, attributes, the shallow file and every commit. The evidence dir and the CLI arguments come
# from the trusted orchestrator, but JSON values inside the evidence files are untrusted text: they
# are compared and counted, never executed, and every untrusted string that is printed or written
# is stripped to printable ASCII and cut to 200 characters.
#
# The --repo is never written. The script fetches --base and --head by full object name into a
# private bare mirror inside its temp dir and runs every git command and worktree against that mirror
# (own config, no templates, no hooks, no attributes file, replace objects off, no global or system
# config, a cleared environment). The mirror is deleted with the temp dir.
#
# Warning: --repro-cmd and --suite-cmd run the worker's own code (the repo's tests). They run in a
# reduced environment (env -i with PATH, HOME, TMPDIR, LANG and TERM only) in throwaway worktrees,
# but they are NOT sandboxed: they can still read the disk and use the network. Run this script where
# that is acceptable.
#
# Usage:
#   fleet-check.sh --repo <checkout> --base <40|64 hex> --head <40|64 hex> --kind bug|feature|docs
#                  --evidence <dir> [--repro-cmd '<cmd>' --repro-files 'path path']
#                  [--suite-cmd '<cmd>' | --no-suite] [--qa-dir <path> --qa-commit <sha> ...]
#                  [--ticket-id <id>] [--risky] [--mode warn|block]
# Output: one line per check (`ok|MISMATCH|skip <name>: <detail>`), <evidence>/fleet-check.json, and
# the last line `fleet-check: <n> mismatch(es), mode <mode>`.
# Exit: 2 on a usage error; 0 in warn mode; in block mode 1 when there is a mismatch.
# Needs git and jq; without jq the JSON-reading checks report a MISMATCH.
set -u

usage() { echo "fleet-check: $*" >&2; echo "usage: fleet-check.sh --repo <dir> --base <sha> --head <sha> --kind bug|feature|docs --evidence <dir> [--repro-cmd C --repro-files 'p ...'] [--suite-cmd C | --no-suite] [--qa-dir P --qa-commit SHA ...] [--ticket-id ID] [--risky] [--mode warn|block]" >&2; exit 2; }

lower() { printf '%s' "$1" | LC_ALL=C tr '[:upper:]' '[:lower:]'; }
is_full_hex() { # 40 or 64 hex characters
  case "$1" in ''|*[!0-9a-fA-F]*) return 1 ;; esac
  [ "${#1}" -eq 40 ] || [ "${#1}" -eq 64 ]
}
# san <text>: printable ASCII only (no control characters, CR, ESC or bytes >= 0x80), at most 200 chars.
san() { printf '%s' "$1" | LC_ALL=C tr -cd '\040-\176' | cut -c1-200; }

repo=""; base=""; head=""; kind=""; evid=""; repro_cmd=""; repro_files=""
suite_cmd="bash scripts/run-tests.sh"; no_suite=0; suite_set=0; qa_dir=""; ticket_id=""; mode="warn"
risky_flag=0; qa_n=0; QA_COMMITS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --no-suite) no_suite=1; shift; continue ;;
    --risky) risky_flag=1; shift; continue ;;
    --repo|--base|--head|--kind|--evidence|--repro-cmd|--repro-files|--suite-cmd|--qa-dir|--qa-commit|--ticket-id|--mode)
      [ $# -ge 2 ] || usage "$1 needs a value" ;;
    *) usage "unknown argument: $1" ;;
  esac
  case "$1" in
    --repo) repo=$2 ;;
    --base) base=$2 ;;
    --head) head=$2 ;;
    --kind) kind=$2 ;;
    --evidence) evid=$2 ;;
    --repro-cmd) repro_cmd=$2 ;;
    --repro-files) repro_files=$2 ;;
    --suite-cmd) suite_cmd=$2; suite_set=1 ;;
    --qa-dir) qa_dir=$2 ;;
    --qa-commit)
      is_full_hex "$2" || usage "--qa-commit must be a full 40 or 64 hex object name"
      QA_COMMITS[qa_n]=$(lower "$2"); qa_n=$((qa_n + 1)) ;;
    --ticket-id) ticket_id=$2 ;;
    --mode) mode=$2 ;;
  esac
  shift 2
done

[ -n "$repo" ] || usage "--repo is required"
[ -n "$base" ] || usage "--base is required"
[ -n "$head" ] || usage "--head is required"
[ -n "$kind" ] || usage "--kind is required"
[ -n "$evid" ] || usage "--evidence is required"
is_full_hex "$base" || usage "--base must be a full 40 or 64 hex object name"
is_full_hex "$head" || usage "--head must be a full 40 or 64 hex object name"
base=$(lower "$base"); head=$(lower "$head")
case "$kind" in bug|feature|docs) ;; *) usage "--kind must be bug, feature or docs" ;; esac
case "$mode" in warn|block) ;; *) usage "--mode must be warn or block" ;; esac
if [ "$no_suite" = 1 ] && [ "$suite_set" = 1 ]; then usage "--suite-cmd and --no-suite exclude each other"; fi
if [ "$kind" = bug ] && [ -n "$repro_cmd" ] && [ -z "$repro_files" ]; then usage "--repro-files is required with --repro-cmd for kind bug"; fi
if [ -n "$qa_dir" ]; then
  while [ "${qa_dir#./}" != "$qa_dir" ]; do qa_dir=${qa_dir#./}; done
  while [ "${qa_dir%/}" != "$qa_dir" ]; do qa_dir=${qa_dir%/}; done
  case "$qa_dir" in ''|.|..|/*|../*|*/../*|*/..|*/./*|*/.) usage "--qa-dir is empty, absolute or not a clean relative path" ;; esac
  [ "$qa_n" -ge 1 ] || usage "--qa-dir needs at least one --qa-commit"
elif [ "$qa_n" -gt 0 ]; then
  usage "--qa-commit needs --qa-dir"
fi

resolve_dir() { # resolve_dir <path>: absolute physical path
  local d=$1
  case "$d" in /*) ;; *) d="./$d" ;; esac
  CDPATH='' cd -P -- "$d" 2>/dev/null && pwd -P
}
repo=$(resolve_dir "$repo") || usage "--repo is not a directory"
evid=$(resolve_dir "$evid") || usage "--evidence is not a directory"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/fleet-check.XXXXXX" 2>/dev/null) || { echo "fleet-check: cannot create a temp dir" >&2; exit 2; }
tmpout=""
# shellcheck disable=SC2317,SC2329  # called by the traps (SC2329 is the name newer shellcheck uses)
cleanup() {
  [ -n "$tmpout" ] && rm -f -- "$tmpout"
  [ -n "$tmp" ] && rm -rf -- "$tmp"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

# --- result bookkeeping -------------------------------------------------------------------------
mismatches=0
checks_json=""

json_str() { # json_str <printable ASCII text>: a JSON string literal
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  printf '"%s"' "$s"
}

record() { # record <name> <ok|mismatch|skip> <detail>
  local name=$1 res=$2 detail label
  detail=$(printf '%s' "$3" | LC_ALL=C tr -cd '\040-\176')
  case "$res" in ok) label=ok ;; mismatch) label=MISMATCH; mismatches=$((mismatches + 1)) ;; *) label=skip ;; esac
  printf '%s %s: %s\n' "$label" "$name" "$detail"
  [ -n "$checks_json" ] && checks_json="$checks_json,"
  checks_json="$checks_json{\"name\":$(json_str "$name"),\"result\":\"$res\",\"detail\":$(json_str "$detail")}"
}

# --- private git mirror -------------------------------------------------------------------------
mirror="$tmp/mirror.git"
mkdir -p "$tmp/home" "$tmp/ev"
GENV=(env -i "PATH=$PATH" "HOME=$tmp/home" GIT_NO_REPLACE_OBJECTS=1 GIT_CONFIG_NOSYSTEM=1
  GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 GIT_LITERAL_PATHSPECS=1 LC_ALL=C
  GIT_NO_LAZY_FETCH=1 GIT_ALLOW_PROTOCOL=file) # no lazy fetch from a worker's promisor remote, file transport only
gm() { "${GENV[@]}" git --git-dir="$mirror" -c core.hooksPath=/dev/null "$@"; }
gmw() { local w=$1; shift; "${GENV[@]}" git -C "$w" -c core.hooksPath=/dev/null "$@"; }

git_err=""
setup_mirror() {
  local out fmt=sha1
  [ "${#head}" -eq 64 ] && fmt=sha256   # the mirror must use the object format of --repo
  if [ "${#head}" -ne "${#base}" ]; then git_err="--base and --head use different object formats"; return; fi
  if ! out=$("${GENV[@]}" git init --bare -q --template= --object-format="$fmt" "$mirror" 2>&1); then git_err="cannot create the mirror: $(san "$out")"; return; fi
  if ! out=$(gm -c uploadpack.allowAnySHA1InWant=true fetch -q --no-tags -- "$repo" "$head:refs/fleet/head" "$base:refs/fleet/base" 2>&1); then
    # A by-SHA fetch is not possible: fetch every head and tag into a private namespace instead.
    if ! out=$(gm fetch -q --no-tags -- "$repo" '+refs/heads/*:refs/fleet/h/*' '+refs/tags/*:refs/fleet/t/*' 2>&1); then
      git_err="cannot fetch from --repo: $(san "$out")"; return
    fi
  fi
  if ! gm cat-file -e "$head^{commit}" 2>/dev/null; then git_err="head commit is not in --repo"; return; fi
  if ! gm cat-file -e "$base^{commit}" 2>/dev/null; then git_err="base commit is not in --repo"; return; fi
  if [ -e "$mirror/shallow" ] || [ "$(gm rev-parse --is-shallow-repository 2>/dev/null)" = true ]; then
    git_err="--repo is shallow: history is incomplete"; return
  fi
  if ! gm merge-base --is-ancestor "$base" "$head" 2>/dev/null; then git_err="head does not descend from base"; return; fi
}
need_git() { [ -z "$git_err" ]; }

WT_DIR=""; WT_ERR=""
mk_wt() { # mk_wt <name> <sha>: sets WT_DIR or WT_ERR
  local out dir="$tmp/wt-$1"
  WT_DIR=""; WT_ERR=""
  if out=$(gm worktree add -q --detach "$dir" "$2" 2>&1); then WT_DIR=$dir; return 0; fi
  WT_ERR=$(san "$out"); return 1
}

# --- evidence snapshot: the checks read only these copies ---------------------------------------
for n in receipt.json report.json security-receipt.json; do
  s="$evid/$n"
  if [ -L "$s" ]; then st=symlink
  elif [ -f "$s" ]; then
    if cat -- "$s" > "$tmp/ev/$n" 2>/dev/null; then st=ok; else st=unreadable; fi
  else st=missing; fi
  printf '%s' "$st" > "$tmp/ev/$n.state"
done
ev_state() { cat "$tmp/ev/$1.state"; }

have_jq=1; command -v jq >/dev/null 2>&1 || have_jq=0

JV=""
# jqs <file> <filter>: sets JV to the exact output (one trailing newline removed, so a value that ends
# in a newline or a file with two JSON documents does not compare equal); returns jq's status.
jqs() {
  local rc
  JV=$(jq -r "$2" "$1" 2>/dev/null; rc=$?; printf x; exit "$rc"); rc=$?
  JV=${JV%x}; JV=${JV%$'\n'}
  return "$rc"
}

head_ok() { # head_ok <value from JSON>: full-length hex, equal to --head as lowercase strings
  local v
  is_full_hex "$1" || return 1
  v=$(lower "$1")
  [ "$v" = "$head" ]
}

FC_PROB=""; FC_N1=0; FC_N2=0; FC_N3=0; FC_N4=0; FC_N5=0
# shellcheck disable=SC2016  # $f, $s and the like are jq variables
JQ_FINDINGS='
def norm: if type == "string" then (gsub("^\\s+|\\s+$"; "") | ascii_downcase) else null end;
(.findings) as $f
| if ($f | type) != "array" then "notarray"
  elif ([$f[] | select(type != "object")] | length) > 0 then "nonobject"
  else
    ([$f[] | select(((.status | norm) as $s | ($s == "open" or $s == "fixed" or $s == "accepted")) | not)] | length) as $bs
    | ([$f[] | select(((.severity | norm) as $s | ($s == "critical" or $s == "high" or $s == "medium" or $s == "low")) | not)] | length) as $bv
    | ([$f[] | select((.status | norm) == "open")] | length) as $op
    | ([$f[] | select((.status | norm) == "accepted") | select(((.accepted_by | norm) as $a | ($a == "advisor" or $a == "owner")) | not)] | length) as $ba
    | ([$f[] | select((.status | norm) == "open" and ((.severity | norm) == "critical" or (.severity | norm) == "high"))] | length) as $oh
    | "\($bs) \($bv) \($op) \($ba) \($oh)"
  end'
eval_findings() { # eval_findings <file>: sets FC_PROB (empty when the findings are valid) and FC_N1..5
  local out
  FC_PROB=""
  out=$(jq -r "$JQ_FINDINGS" "$1" 2>/dev/null) || { FC_PROB="findings could not be read"; return; }
  case "$out" in
    notarray) FC_PROB="findings is not an array"; return ;;
    nonobject) FC_PROB="findings holds a non-object entry"; return ;;
    ''|*[!0-9\ ]*) FC_PROB="findings result is not numeric"; return ;;
  esac
  # shellcheck disable=SC2086  # five space-separated integers
  set -- $out
  [ $# -eq 5 ] || { FC_PROB="findings result is malformed"; return; }
  FC_N1=$1; FC_N2=$2; FC_N3=$3; FC_N4=$4; FC_N5=$5
}

# --- 1. receipt ---------------------------------------------------------------------------------
check_receipt() {
  local f="$tmp/ev/receipt.json" st probs=""
  st=$(ev_state receipt.json)
  if [ "$st" != ok ]; then record receipt mismatch "receipt.json is $st"; return; fi
  if [ "$have_jq" = 0 ]; then record receipt mismatch "jq is not installed, cannot read receipt.json"; return; fi
  if ! jq -e -s 'length == 1 and (.[0] | type) == "object"' "$f" >/dev/null 2>&1; then record receipt mismatch "receipt.json does not parse as a JSON object"; return; fi
  jqs "$f" '.head | strings' || probs="$probs head could not be read;"
  head_ok "$JV" || probs="$probs head '$(san "$JV")' is not the full --head;"
  jqs "$f" '.verdict | strings' || probs="$probs verdict could not be read;"
  [ "$JV" = pass ] || probs="$probs verdict is '$(san "$JV")', not pass;"
  if [ -n "$ticket_id" ]; then
    jqs "$f" '.ticket | if (type == "string" or type == "number") then tostring else empty end' || probs="$probs ticket could not be read;"
    [ "$JV" = "$ticket_id" ] || probs="$probs ticket '$(san "$JV")' is not $(san "$ticket_id");"
  fi
  eval_findings "$f"
  if [ -n "$FC_PROB" ]; then probs="$probs $FC_PROB;"
  else
    [ "$FC_N1" = 0 ] || probs="$probs $FC_N1 finding(s) with a status other than open, fixed or accepted;"
    [ "$FC_N2" = 0 ] || probs="$probs $FC_N2 finding(s) with an unknown severity;"
    [ "$FC_N3" = 0 ] || probs="$probs $FC_N3 open finding(s);"
    [ "$FC_N4" = 0 ] || probs="$probs $FC_N4 accepted finding(s) without accepted_by advisor or owner;"
  fi
  if [ -n "$probs" ]; then record receipt mismatch "${probs# }"; else record receipt ok "head matches, verdict pass, no open finding"; fi
}

# --- 2. report ----------------------------------------------------------------------------------
check_report() {
  local f="$tmp/ev/report.json" st probs=""
  st=$(ev_state report.json)
  if [ "$st" != ok ]; then record report mismatch "report.json is $st"; return; fi
  if [ "$have_jq" = 0 ]; then record report mismatch "jq is not installed, cannot read report.json"; return; fi
  if ! jq -e -s 'length == 1 and (.[0] | type) == "object"' "$f" >/dev/null 2>&1; then record report mismatch "report.json does not parse as a JSON object"; return; fi
  jqs "$f" '.v | numbers' || probs="$probs v could not be read;"
  [ "$JV" = 2 ] || probs="$probs v is '$(san "$JV")', not 2;"
  jqs "$f" '.head | strings' || probs="$probs head could not be read;"
  head_ok "$JV" || probs="$probs head '$(san "$JV")' is not the full --head;"
  jqs "$f" '.status | strings' || probs="$probs status could not be read;"
  [ "$JV" = "done" ] || probs="$probs status is '$(san "$JV")', not done;"
  if [ -n "$ticket_id" ]; then
    jqs "$f" '.ticket | if (type == "string" or type == "number") then tostring else empty end' || probs="$probs ticket could not be read;"
    [ "$JV" = "$ticket_id" ] || probs="$probs ticket '$(san "$JV")' is not $(san "$ticket_id");"
  fi
  if [ -n "$probs" ]; then record report mismatch "${probs# }"; else record report ok "v 2, head matches, status done"; fi
}

# --- 3. acceptance ------------------------------------------------------------------------------
qal=""; CL_IN=0; CL_OUT=0
classify() { # classify <commit>: sets CL_IN / CL_OUT (1 when a path is inside / outside the qa dir)
  local p
  CL_IN=0; CL_OUT=0
  gm diff-tree --no-commit-id --name-only -r -z --root --no-renames "$1" > "$tmp/paths" 2>/dev/null || return 1
  while IFS= read -r -d '' p; do
    p=$(lower "$p")
    case "$p" in "$qal"|"$qal"/*) CL_IN=1 ;; *) CL_OUT=1 ;; esac
  done < "$tmp/paths"
  return 0
}

check_acceptance() {
  local c q probs="" listed first_qa
  if [ -z "$qa_dir" ]; then record acceptance skip "no --qa-dir"; return; fi
  if ! need_git; then record acceptance mismatch "git mirror not usable: $git_err"; return; fi
  qal=$(lower "$qa_dir")
  if ! gm rev-list --topo-order --reverse "$base..$head" > "$tmp/range" 2>/dev/null; then record acceptance mismatch "cannot list $base..$head"; return; fi
  if [ -n "$(gm rev-list --merges "$base..$head" 2>/dev/null)" ]; then record acceptance mismatch "a merge commit is in the range"; return; fi
  first_qa=${QA_COMMITS[0]}
  for q in "${QA_COMMITS[@]}"; do
    if ! grep -qFx -- "$q" "$tmp/range"; then probs="$probs qa commit ${q:0:12} is not in $base..$head;"; continue; fi
    if ! classify "$q"; then probs="$probs cannot read the paths of ${q:0:12};"; continue; fi
    [ "$CL_OUT" = 0 ] || probs="$probs qa commit ${q:0:12} touches paths outside $qa_dir;"
    [ "$CL_IN" = 1 ] || probs="$probs qa commit ${q:0:12} touches nothing in $qa_dir;"
  done
  while IFS= read -r c; do
    [ -n "$c" ] || continue
    listed=0
    for q in "${QA_COMMITS[@]}"; do [ "$q" = "$c" ] && listed=1; done
    [ "$listed" = 1 ] && continue
    if ! classify "$c"; then probs="$probs cannot read the paths of ${c:0:12};"; continue; fi
    if [ "$CL_IN" = 1 ]; then probs="$probs commit ${c:0:12} touches $qa_dir but is not a --qa-commit;"; fi
    if [ "$CL_OUT" = 1 ] && ! gm merge-base --is-ancestor "$first_qa" "$c" 2>/dev/null; then
      probs="$probs code commit ${c:0:12} does not come after the first qa commit ${first_qa:0:12};"
    fi
  done < "$tmp/range"
  if [ -n "$probs" ]; then record acceptance mismatch "${probs# }"
  else record acceptance ok "$qa_n qa commit(s) touch only $qa_dir, no other commit does, and all code follows the first one"; fi
}

# --- 4. security --------------------------------------------------------------------------------
risky_re='(^|/)(hooks|migrations?|auth|security|secrets?)(/|$)|(^|/)(scripts|\.github)(/|$)|settings\.json$|settings\.local\.json$|\.sql$|\.env|(^|/)REVIEW\.md$'
check_security() {
  local f="$tmp/ev/security-receipt.json" st mb p nrisky=0 risky="" where probs=""
  if ! need_git; then record security mismatch "git mirror not usable: $git_err"; return; fi
  if ! mb=$(gm merge-base "$base" "$head" 2>/dev/null) || [ -z "$mb" ]; then record security mismatch "cannot find the merge base"; return; fi
  if ! gm diff --no-renames --name-only -z "$mb" "$head" -- > "$tmp/sp" 2>/dev/null; then record security mismatch "git diff failed"; return; fi
  while IFS= read -r -d '' p; do
    if printf '%s\n' "$p" | LC_ALL=C grep -Eiq -- "$risky_re"; then
      nrisky=$((nrisky + 1))
      [ "$nrisky" -le 3 ] && risky="$risky $(san "$p")"
    fi
  done < "$tmp/sp"
  if [ "$nrisky" -gt 0 ]; then where="risky path (${risky# })"; else where="no risky path"; fi
  st=$(ev_state security-receipt.json)
  if [ "$st" = missing ]; then
    if [ "$nrisky" -gt 0 ]; then record security mismatch "$where but security-receipt.json is missing"
    elif [ "$risky_flag" = 1 ]; then record security mismatch "--risky: security-receipt.json is required and is missing"
    else record security ok "no risky path"; fi
    return
  fi
  if [ "$st" != ok ]; then record security mismatch "$where: security-receipt.json is $st"; return; fi
  if [ "$have_jq" = 0 ]; then record security mismatch "$where: jq is not installed, cannot read security-receipt.json"; return; fi
  if ! jq -e -s 'length == 1 and (.[0] | type) == "object"' "$f" >/dev/null 2>&1; then record security mismatch "$where: security-receipt.json does not parse as a JSON object"; return; fi
  jqs "$f" '.head | strings' || probs="$probs head could not be read;"
  head_ok "$JV" || probs="$probs head '$(san "$JV")' is not the full --head;"
  eval_findings "$f"
  if [ -n "$FC_PROB" ]; then probs="$probs $FC_PROB;"
  else
    [ "$FC_N1" = 0 ] || probs="$probs $FC_N1 finding(s) with a status other than open, fixed or accepted;"
    [ "$FC_N2" = 0 ] || probs="$probs $FC_N2 finding(s) with an unknown severity;"
    [ "$FC_N4" = 0 ] || probs="$probs $FC_N4 accepted finding(s) without accepted_by advisor or owner;"
    [ "$FC_N5" = 0 ] || probs="$probs $FC_N5 open critical or high finding(s);"
  fi
  if [ -n "$probs" ]; then record security mismatch "$where:$probs"
  else record security ok "$where, receipt head matches, no open critical or high finding"; fi
}

# --- commands (worker code) ---------------------------------------------------------------------
RENV=(env -i "PATH=$PATH")
[ -n "${HOME:-}" ] && RENV+=("HOME=$HOME")
[ -n "${TMPDIR:-}" ] && RENV+=("TMPDIR=$TMPDIR")
[ -n "${LANG:-}" ] && RENV+=("LANG=$LANG")
[ -n "${TERM:-}" ] && RENV+=("TERM=$TERM")
run_in() { # run_in <dir> <cmd>: the command text comes from the CLI only
  ( cd -P -- "$1" && "${RENV[@]}" bash -c "$2" </dev/null >/dev/null 2>&1 )
}

# --- 5. repro -----------------------------------------------------------------------------------
check_repro() {
  local rc_base rc_head p why="" wt_base wt_head
  if [ -z "$repro_cmd" ]; then
    if [ "$kind" = bug ]; then record repro mismatch "kind bug needs --repro-cmd and none was given"
    else record repro skip "no --repro-cmd"; fi
    return
  fi
  if ! need_git; then record repro mismatch "git mirror not usable: $git_err"; return; fi
  if ! mk_wt repro-base "$base"; then record repro mismatch "cannot create the base worktree: $WT_ERR"; return; fi
  wt_base=$WT_DIR
  if ! mk_wt repro-head "$head"; then record repro mismatch "cannot create the head worktree: $WT_ERR"; return; fi
  wt_head=$WT_DIR
  set -f
  for p in $repro_files; do
    if ! gmw "$wt_base" checkout "$head" -- "$p" >/dev/null 2>&1; then
      set +f
      record repro mismatch "cannot overlay '$(san "$p")' from head onto base"
      return
    fi
  done
  set +f
  run_in "$wt_base" "$repro_cmd"; rc_base=$?
  run_in "$wt_head" "$repro_cmd"; rc_head=$?
  if [ "$rc_base" -eq 126 ] || [ "$rc_base" -eq 127 ]; then
    record repro mismatch "test did not run on base (exit $rc_base), head exit $rc_head"
  elif [ "$rc_base" -ne 0 ] && [ "$rc_head" -eq 0 ]; then
    record repro ok "red on base (exit $rc_base), green on head (exit $rc_head)"
  else
    [ "$rc_base" -eq 0 ] && why="not red on base"
    [ "$rc_head" -ne 0 ] && why="${why:+$why, }not green on head"
    record repro mismatch "$why: base exit $rc_base, head exit $rc_head"
  fi
}

# --- 6. suite -----------------------------------------------------------------------------------
check_suite() {
  local rc
  if [ "$no_suite" = 1 ]; then record suite skip "--no-suite"; return; fi
  if ! need_git; then record suite mismatch "git mirror not usable: $git_err"; return; fi
  if ! mk_wt suite-head "$head"; then record suite mismatch "cannot create the head worktree: $WT_ERR"; return; fi
  run_in "$WT_DIR" "$suite_cmd"; rc=$?
  if [ "$rc" -eq 0 ]; then record suite ok "exit 0"; else record suite mismatch "suite command exited $rc"; fi
}

setup_mirror
# Read-only checks first, then the commands.
check_receipt
check_report
check_acceptance
check_security
check_repro
check_suite

# --- result file --------------------------------------------------------------------------------
write_failed=0
target="$evid/fleet-check.json"
if [ -L "$target" ] || [ -d "$target" ]; then
  echo "fleet-check: refusing to write $target (it is a symlink or a directory)" >&2
  write_failed=1
elif tmpout=$(mktemp "$evid/.fleet-check.XXXXXX" 2>/dev/null) \
  && printf '{"v":1,"head":%s,"mode":"%s","checks":[%s],"mismatches":%d}\n' \
    "$(json_str "$head")" "$mode" "$checks_json" "$mismatches" > "$tmpout" \
  && chmod 644 "$tmpout" && mv -f -- "$tmpout" "$target"; then
  tmpout=""
else
  echo "fleet-check: cannot write $target" >&2
  write_failed=1
fi

echo "fleet-check: $mismatches mismatch(es), mode $mode"
if [ "$mode" = block ] && { [ "$mismatches" -gt 0 ] || [ "$write_failed" = 1 ]; }; then exit 1; fi
exit 0
