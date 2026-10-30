#!/bin/bash
# ground-check.sh: check the factual claims of a research brief, a design or a plan against the code on a git ref.
#
# Usage: ground-check.sh --repo <dir> --ref <ref> --mode full|paths-only <file>...
#
# It reads code only from the ref (the ls-tree listing, git show, git grep), never from the working tree of
# the checkout. Claims it checks:
#   path:line citations     the path is on the ref, the line is within the file; in full mode a backtick quote
#                           after the citation on the same line must occur in lines N-2..M+2
#   backtick paths          `src/a.js`, `docs/`, a bare file name (a unique base name on the ref)
#   Files: lines            each comma-separated entry of a plan "Files:" line is a path claim
#   backtick symbols        (full mode) code-like names: they contain _ or . or (), or are camelCase
#   Done-when commands      the path words of the backtick command on a Done-when / done_when line
#   Pins: <sha>             (full mode) the sha resolves and is an ancestor of the ref
#   (new) marker            a path or symbol followed by (new) is exempt everywhere in the input set
# paths-only mode checks paths, citation paths and line numbers, and command paths: no symbols, quotes or Pins.
#
# Output (stdout): one "FILE <name> <line-count> <byte-count>" line per input, then one
#   "FAIL <kind>: <claim> (<reason>)" line per failed claim; kind is path, line, quote, symbol, command or pins.
# Exit: 0 every claim holds, 1 at least one claim failed, 2 usage error, missing input file or unresolved ref.
#
# Portable to bash 3.2 and BSD tools: no associative arrays, mapfile, case-changing expansions, grep -P or gawk.

# shellcheck disable=SC2016  # the backticks in the single-quoted patterns are literal markdown backticks
REPO=""; REF=""; MODE=""

die() { printf 'ground-check: %s\n' "$1" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) [ $# -ge 2 ] || die "--repo needs a value"; REPO=$2; shift 2 ;;
    --ref)  [ $# -ge 2 ] || die "--ref needs a value"; REF=$2; shift 2 ;;
    --mode) [ $# -ge 2 ] || die "--mode needs a value"; MODE=$2; shift 2 ;;
    --) shift; break ;;
    -*) die "unknown option: $1" ;;
    *) break ;;
  esac
done
[ -n "$REPO" ] || die "usage: ground-check.sh --repo <dir> --ref <ref> --mode full|paths-only <file>..."
[ -n "$REF" ] || die "--ref is required"
case "$MODE" in full|paths-only) ;; *) die "--mode must be full or paths-only" ;; esac
[ $# -gt 0 ] || die "no input file"
for f in "$@"; do [ -f "$f" ] || die "input file not found: $f"; done

g() { git -C "$REPO" "$@" </dev/null; }
g rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository: $REPO"
g rev-parse --verify --quiet "$REF^{commit}" >/dev/null 2>&1 || die "ref does not resolve: $REF"

TMP=$(mktemp -d) || die "mktemp failed"
trap 'rm -rf "$TMP"' EXIT
mkdir "$TMP/c"
: > "$TMP/out"; : > "$TMP/new"; : > "$TMP/tokens"; : > "$TMP/cites"; : > "$TMP/cmds"
: > "$TMP/newraw"; : > "$TMP/fileents"

# The tree of the ref, read once: every file path and every directory.
g ls-tree -r --name-only "$REF" > "$TMP/tree" 2>/dev/null
awk '{ n = split($0, a, "/"); p = ""; for (i = 1; i < n; i++) { p = p (i > 1 ? "/" : "") a[i]; print p } }' "$TMP/tree" | sort -u > "$TMP/dirs"

KNOWN_EXT=" js mjs cjs ts tsx jsx json md mdx sh bash py yml yaml toml txt html css scss sql lock cfg ini conf go rs rb java kt swift c h cpp hpp php xml csv tf vue svelte ps1 bats "

fail() { # fail <kind> <claim> <reason>
  local line="FAIL $1: $2 ($3)"
  grep -qxF -- "$line" "$TMP/out" || printf '%s\n' "$line" >> "$TMP/out"
}

is_new() { grep -qxF -- "$1" "$TMP/new"; }

# norm <token>: strip a trailing (), :N or :N-M and trailing slashes.
norm() {
  local t=$1
  t=${t%\(\)}
  if [[ $t =~ ^(.*):[0-9]+(-[0-9]+)?$ ]]; then t=${BASH_REMATCH[1]}; fi
  while [ -n "$t" ] && [ "${t%/}" != "$t" ]; do t=${t%/}; done
  printf '%s' "$t"
}

has_known_ext() { # the text after the last dot is a known file extension
  case "$1" in *.*) ;; *) return 1 ;; esac
  case "$KNOWN_EXT" in *" ${1##*.} "*) return 0 ;; esac
  return 1
}

# pathlike <token> <strict>: does the token read as a repo path? A slash alone is enough only when strict;
# otherwise it needs a known extension or an existing first directory, so prose such as read/write is no claim.
pathlike() {
  local t=$1 strict=$2
  case "$t" in
    */*)
      [ "$strict" = 1 ] && return 0
      has_known_ext "$t" && return 0
      grep -qxF -- "${t%%/*}" "$TMP/dirs" && return 0
      return 1 ;;
    *) has_known_ext "$t" ;;
  esac
}

# resolve_path <path> <allow-dir>: 0 found (RP set), 1 missing, 2 not a claim (new, ignored, ambiguous bare name).
resolve_path() {
  local p=${1#./} c
  RP=""
  is_new "$p" && return 2
  case "$p" in specs|specs/*) return 2 ;; esac
  if grep -qxF -- "$p" "$TMP/tree"; then RP=$p; return 0; fi
  if [ "$2" = 1 ] && grep -qxF -- "$p" "$TMP/dirs"; then RP=$p; return 0; fi
  case "$p" in */*) return 1 ;; esac
  c=$(awk -F/ -v n="$p" '$NF == n' "$TMP/tree" | wc -l | tr -d ' ')
  if [ "$c" = 0 ]; then
    if [ "$2" = 1 ] && awk -F/ -v n="$p" '$NF == n { f = 1 } END { exit !f }' "$TMP/dirs"; then return 0; fi
    return 1
  fi
  if [ "$c" = 1 ]; then RP=$(awk -F/ -v n="$p" '$NF == n' "$TMP/tree"); return 0; fi
  return 2
}

check_path() { # check_path <path> <kind>
  resolve_path "$1" 1
  [ $? = 1 ] && fail "$2" "${1#./}" "not on $REF"
  return 0
}

# classify <raw backtick token> <strict>: sets KIND (path, sym or skip) and TOK (the normalised token).
classify() {
  local t=$1 strict=${2:-0} paren=0
  KIND=skip; TOK=""
  case "$t" in ''|*[[:space:]]*|-*|/*|'~'*|*://*|../*) return ;; esac
  case "$t" in *'()') paren=1 ;; esac
  t=$(norm "$t")
  [ -n "$t" ] || return
  [[ $t =~ ^[A-Za-z0-9_.@+/-]+$ ]] || return
  case "$t" in
    */*) if pathlike "$t" "$strict"; then KIND=path; TOK=$t; fi; return ;;
  esac
  if has_known_ext "$t"; then KIND=path; TOK=$t; return; fi
  [[ $t =~ ^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$ ]] || return
  if [ "$paren" = 1 ] || [[ $t == *_* ]] || [[ $t == *.* ]] || [[ $t =~ [a-z][A-Z] ]]; then KIND=sym; TOK=$t; fi
}

check_symbol() { # check_symbol <symbol>
  local s=$1 last
  is_new "$s" && return 0
  g grep -q -F -w -e "$s" "$REF" -- >/dev/null 2>&1 && return 0
  last=${s##*.}
  if [ "$last" != "$s" ] && g grep -q -F -w -e "$last" "$REF" -- >/dev/null 2>&1; then return 0; fi
  fail symbol "$s" "not found on $REF"
}

# cache_file <path>: CFILE holds the content of the path on the ref, CCOUNT its line count.
cache_file() {
  local key
  key=$(printf '%s' "$1" | cksum | awk '{ print $1 "_" $2 }')
  CFILE="$TMP/c/$key"
  [ -f "$CFILE" ] || g show "$REF:$1" > "$CFILE" 2>/dev/null
  CCOUNT=$(awk 'END { print NR }' "$CFILE")
}

squash() { printf '%s' "$1" | tr -s '[:space:]' ' ' | sed -E 's/^ //; s/ $//'; }

check_cite() { # check_cite <path> <n> <m> <quote>
  local p=${1#./} n=$2 m=$3 q=$4 rp a b win key
  case "$p" in */*) ;; *) has_known_ext "$p" || return 0 ;; esac
  resolve_path "$p" 0; key=$?
  if [ "$key" = 1 ]; then fail path "$p" "not on $REF"; return 0; fi
  [ "$key" = 0 ] || return 0
  rp=$RP
  cache_file "$rp"
  if [ "$n" -gt "$CCOUNT" ]; then fail line "$p:$n" "$rp has $CCOUNT lines on $REF"; return 0; fi
  if [ -n "$m" ] && [ "$m" -gt "$CCOUNT" ]; then fail line "$p:$n-$m" "$rp has $CCOUNT lines on $REF"; return 0; fi
  [ "$MODE" = full ] || return 0
  [ -n "$q" ] || return 0
  q=$(squash "$q"); q=${q%%...*}; q=${q%%…*}; q=$(squash "$q")
  [ -n "$q" ] || return 0
  a=$((n - 2)); [ "$a" -ge 1 ] || a=1
  b=$(( ${m:-$n} + 2 ))
  win=$(sed -n "${a},${b}p" "$CFILE" | tr -s '[:space:]' ' ')
  win=" $win"
  case "$win" in *"$q"*) ;; *) fail quote "$p:$n${m:+-$m} \`$q\`" "not in lines $a-$b of $rp on $REF" ;; esac
}

cmd_path() { # cmd_path <word> <command>
  local w=${1#./} key
  resolve_path "$w" 1; key=$?
  [ "$key" = 1 ] && fail command "$w" "not on $REF; in: $2"
  return 0
}

check_command() { # check_command <command text>
  local cmd=$1 w expect=0
  set -f
  for w in $cmd; do
    w=${w//\"/}; w=${w//\'/}
    case "$w" in '&&'|'||'|';'|'|') expect=0; continue ;; esac
    case "$w" in -c|-e|-p) break ;; esac
    if [ "$expect" = 1 ]; then
      expect=0
      case "$w" in -*) continue ;; esac
      case "$w" in /*|'~'*|*://*|*'*'*|*'?'*|*'<'*|*'>'*|*'{'*|*'$'*|*'='*|*'|'*|*';'*|*'&'*|*'('*|*'`'*) continue ;; esac
      cmd_path "$w" "$cmd"
      continue
    fi
    case "$w" in bash|sh|node|python3|python) expect=1; continue ;; esac
    case "$w" in -*|/*|'~'*|*://*|*'*'*|*'?'*|*'<'*|*'>'*|*'{'*|*'$'*|*'='*|*'|'*|*';'*|*'&'*|*'('*|*'`'*) continue ;; esac
    case "$w" in */*) if pathlike "${w%/}" 0; then cmd_path "${w%/}" "$cmd"; fi ;; esac
  done
  set +f
}

check_pins() { # check_pins <line>
  local sha
  for sha in $(printf '%s\n' "$1" | tr -c '0-9a-f' '\n' | grep -E '^[0-9a-f]{7,40}$' | grep '[0-9]'); do
    if ! g rev-parse --verify --quiet "$sha^{commit}" >/dev/null 2>&1; then
      fail pins "$sha" "does not resolve to a commit"
    elif ! g merge-base --is-ancestor "$sha" "$REF" >/dev/null 2>&1; then
      fail pins "$sha" "is not an ancestor of $REF"
    fi
  done
}

# Inputs with fenced code blocks removed. Collect the (new) marker over the whole set first.
FILES_RE='^[[:space:]]*([-*][[:space:]]+)?\**Files?\**:'
i=0
for f in "$@"; do
  i=$((i + 1))
  printf 'FILE %s %s %s\n' "$f" "$(awk 'END { print NR }' "$f")" "$(wc -c < "$f" | tr -d '[:space:]')"
  awk '/^[[:space:]]*```/ { skip = !skip; next } !skip' "$f" > "$TMP/in$i"
  grep -oE '`[^`]+`[[:space:]]*\(new[ ,)]' "$TMP/in$i" | sed -E 's/`[[:space:]]*\(new[ ,)]$//; s/^`//' >> "$TMP/newraw"
  grep -E "$FILES_RE" "$TMP/in$i" | sed -E 's/^[^:]*://' | tr ',' '\n' | grep -E '\(new[ ,)]' \
    | sed -E 's/\(new.*$//; s/^[[:space:]`]+//; s/[[:space:]`]+$//' >> "$TMP/newraw"
done
while IFS= read -r raw; do
  norm "$raw" >> "$TMP/new"; printf '\n' >> "$TMP/new"
done < "$TMP/newraw"
NFILES=$i

CITE_RE='([A-Za-z0-9_./@+-]+\.[A-Za-z][A-Za-z0-9]*):([0-9]+)(-([0-9]+))?'
QUOTE_RE='^[[:space:]]*[-—–:,;(=]*[[:space:]]*`([^`]+)`'
# The quote must follow the citation directly (only space and punctuation between); a later unrelated span is not its quote.
j=0
while [ "$j" -lt "$NFILES" ]; do
  j=$((j + 1))
  IN="$TMP/in$j"
  grep -oE '`[^`]+`' "$IN" | sed -E 's/^`//; s/`$//' >> "$TMP/tokens"
  # Files: entries are path claims even without backticks.
  grep -E "$FILES_RE" "$IN" | sed -E 's/^[^:]*://' | tr ',' '\n' | sed -E 's/\(.*$//; s/^[[:space:]`]+//; s/[[:space:]`]+$//' >> "$TMP/fileents"
  # Done-when commands: every backtick span on a Done-when / done_when line.
  grep -iE 'done[-_ ]when' "$IN" | grep -oE '`[^`]+`' | sed -E 's/^`//; s/`$//' >> "$TMP/cmds"
  # Pins lines.
  if [ "$MODE" = full ]; then
    while IFS= read -r pl; do check_pins "$pl"; done < <(grep -E '(^|[^A-Za-z])Pins?:' "$IN")
  fi
  # path:line citations, with the backtick quote that follows on the same line.
  while IFS= read -r line; do
    rest=$line
    while [[ $rest =~ $CITE_RE ]]; do
      whole=${BASH_REMATCH[0]}; cp=${BASH_REMATCH[1]}; cn=${BASH_REMATCH[2]}; cm=${BASH_REMATCH[4]}
      before=${rest%%"$whole"*}
      after=${rest#*"$whole"}
      inside=0; [ "${before: -1}" = '`' ] && inside=1
      seg=$after
      if [ "$inside" = 1 ]; then
        case "$seg" in *'`'*) seg=${seg#*'`'} ;; *) seg="" ;; esac
      fi
      if [[ $seg =~ $CITE_RE ]]; then seg=${seg%%"${BASH_REMATCH[0]}"*}; fi
      quote=""
      if [[ $seg =~ $QUOTE_RE ]]; then quote=${BASH_REMATCH[1]}; fi
      printf '%s\001%s\001%s\001%s\n' "$cp" "$cn" "$cm" "$quote" >> "$TMP/cites"
      rest=$after
    done
  done < "$IN"
done

# Citations.
TAB=$(printf '\001')
while IFS="$TAB" read -r cp cn cm quote; do
  [ -n "$cp" ] && check_cite "$cp" "$cn" "$cm" "$quote"
done < "$TMP/cites"

# Backtick paths and symbols.
sort -u "$TMP/tokens" > "$TMP/tokens.u"
while IFS= read -r raw; do
  classify "$raw" 0
  case "$KIND" in
    path) check_path "$TOK" path ;;
    sym) [ "$MODE" = full ] && check_symbol "$TOK" ;;
  esac
done < "$TMP/tokens.u"

# Files: entries.
sort -u "$TMP/fileents" > "$TMP/fileents.u"
while IFS= read -r raw; do
  classify "$raw" 1
  [ "$KIND" = path ] && check_path "$TOK" path
done < "$TMP/fileents.u"

# Done-when commands.
sort -u "$TMP/cmds" > "$TMP/cmds.u"
while IFS= read -r cmd; do
  [ -n "$cmd" ] && check_command "$cmd"
done < "$TMP/cmds.u"

if [ -s "$TMP/out" ]; then
  cat "$TMP/out"
  exit 1
fi
exit 0
