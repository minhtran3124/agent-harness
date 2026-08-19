#!/bin/bash
# Integration tests for the three DERIVE-TIME transforms in scripts/deploy-harness.sh:
#   copy_consumer_subset   — ship the allow-listed helpers + data a consumer's skills actually run
#   rewrite_derived_paths  — repoint `scripts/X` -> `.claude/scripts/X` in derived Markdown
#   strip_skill_tests      — drop harness CI fixtures/unit tests from the derived tree
#   strip_maintenance_docs — drop HARNESS_ONLY_DOCS + <!-- harness-only --> regions
#
# WHY THIS FILE EXISTS: before these transforms, every consuming repo silently fail-opened on the
# gates its own skills/rules described — the helper they name (scripts/verify_summary.py etc.) never
# deployed. The failure was invisible to CI because scripts/lint-doc-truth.sh validates paths in the
# HARNESS repo, where scripts/ is present. These assertions pin the consumer-side contract instead.
#
# SAFETY: mirrors tests/scripts/resync-conflict.test.sh — every deploy takes --target and reads
# stdin from /dev/null, so a stray prompt fails loudly instead of hanging CI, and this repo's own
# .claude/ is never rewritten.
source "$(dirname "$0")/../lib.sh"

DEPLOY="$ROOT/scripts/deploy-harness.sh"

new_target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }
run_deploy() { local tgt="$1"; shift; OUT_TXT=$(bash "$DEPLOY" --target "$tgt" "$@" </dev/null 2>&1); RC=$?; }

T=$(new_target)
run_deploy "$T"
C="$T/.claude"

# ---------------------------------------------------------------------------
# copy_consumer_subset
# ---------------------------------------------------------------------------
t "allow-listed helpers land in .claude/scripts/ and are importable Python"
missing=""
for f in verify_summary.py check_plan_contract.py check_review_receipt.py \
         resolve_finish_context.py rebuild_solution_index.py render_skill_prompt.py; do
  [ -f "$C/scripts/$f" ] || missing="$missing $f"
done
if [ "$RC" -eq 0 ] && [ -z "$missing" ] && python3 -m py_compile "$C"/scripts/*.py 2>/dev/null; then pass
else fail "rc=$RC missing:$missing (or a deployed helper does not compile)"; fi

t "harness-manifest.json ships so a consumer can read the hard-gate vocabulary"
if [ -f "$C/harness-manifest.json" ] && python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$C/harness-manifest.json"; then pass
else fail "manifest missing or not valid JSON at .claude/harness-manifest.json"; fi

t "harness-development scripts are NOT shipped (the subset is an allow-list, not a copy of scripts/)"
leaked=""
for f in check_manifest.py deploy-harness.sh init-structure.sh harness-audit.sh run-tests.sh; do
  [ -e "$C/scripts/$f" ] && leaked="$leaked $f"
done
# its own unit tests must not travel either
[ -n "$(find "$C/scripts" -name 'test_*.py' 2>/dev/null)" ] && leaked="$leaked test_*.py"
if [ -z "$leaked" ]; then pass; else fail "leaked into the consumer:$leaked"; fi

t "source-time adapter inputs stay undeployed (pinned by deploy-prune/install-harness too)"
leaked=""
[ -e "$C/agents/runtime-bindings.json" ] && leaked="$leaked agents/runtime-bindings.json"
[ -e "$C/adapters" ] && leaked="$leaked adapters/"
if [ -z "$leaked" ]; then pass; else fail "source-time input deployed:$leaked"; fi

# ---------------------------------------------------------------------------
# rewrite_derived_paths
# ---------------------------------------------------------------------------
t "derived Markdown repoints an allow-listed helper at the copy that exists"
# rules/auto-correct-scope.md names verify_summary.py as the lane -> evidence authority.
if grep -q '\.claude/scripts/verify_summary\.py' "$C/rules/auto-correct-scope.md" \
   && ! grep -qE '(^|[^.])(^|[^/])\bscripts/verify_summary\.py' "$C/rules/auto-correct-scope.md"; then pass
else fail "derived rule still points at the undeployed scripts/verify_summary.py"; fi

t "every .claude/scripts/ path named in derived Markdown actually resolves"
unresolved=$(grep -rhoE '\.claude/scripts/[A-Za-z0-9_.-]+' "$C" --include='*.md' 2>/dev/null | sort -u \
  | while read -r p; do [ -e "$T/$p" ] || echo "$p"; done)
if [ -z "$unresolved" ]; then pass; else fail "named but not shipped: $(echo "$unresolved" | tr '\n' ' ')"; fi

t "rewrite is idempotent — a second deploy never produces .claude/.claude/"
run_deploy "$T"
dbl=$(grep -rl '\.claude/\.claude/' "$C" --include='*.md' 2>/dev/null)
if [ "$RC" -eq 0 ] && [ -z "$dbl" ]; then pass; else fail "rc=$RC double-prefixed: $dbl"; fi

t "hooks are NOT rewritten — risk-corroboration must keep reading the manifest from the git index"
# Invariant #2 in hooks/risk-corroboration.sh: modes come from `git show :harness-manifest.json`
# (the index) or the embedded defaults — never a worktree or derived .claude/ policy file, which an
# unstaged edit could loosen. rewrite_derived_paths is Markdown-only; assert that literally, so a
# future widening to *.sh trips here. (Byte-identity, not a grep: the hook's own prose contains the
# forbidden path inside the comment that forbids it.)
if cmp -s "$C/hooks/risk-corroboration.sh" "$ROOT/hooks/risk-corroboration.sh" \
   && cmp -s "$C/hooks/commit-quality-gate.sh" "$ROOT/hooks/commit-quality-gate.sh" \
   && grep -q 'git show :harness-manifest.json' "$C/hooks/risk-corroboration.sh"; then pass
else fail "a derived hook diverged from source — path rewriting must stay Markdown-only"; fi

# ---------------------------------------------------------------------------
# strip_skill_tests
# ---------------------------------------------------------------------------
t "harness CI fixtures and unit tests are stripped from the derived tree"
left=$(find "$C/skills" \( -path '*/tests/*' -o -name 'test_*.py' \) 2>/dev/null)
if [ -z "$left" ]; then pass; else fail "test material shipped: $(echo "$left" | tr '\n' ' ')"; fi

t "stripping is derive-only — the harness sources still hold their tests"
if [ -f "$ROOT/skills/xia2/tests/structural/depth-modes-test-cases.md" ] \
   && [ -f "$ROOT/skills/visual-planner/test_render_plan.py" ]; then pass
else fail "sources lost their tests — strip_skill_tests must never touch \$ROOT"; fi

# ---------------------------------------------------------------------------
# strip_maintenance_docs
# ---------------------------------------------------------------------------
t "HARNESS_ONLY_DOCS are absent from the consumer and intact at the source"
bad=""
for f in skills/xia2/README.md skills/compound/README.md agents/README.md; do
  [ -e "$C/$f" ] && bad="$bad deployed:$f"
  [ -f "$ROOT/$f" ] || bad="$bad lost-at-source:$f"
done
if [ -z "$bad" ]; then pass; else fail "$bad"; fi

t "a <!-- harness-only --> region is removed and its markers never leak"
if ! grep -rq 'harness-only:' "$C" --include='*.md' \
   && ! grep -q 'Per-skill Design Rationales' "$C/skills/README.md"; then pass
else fail "sentinel markers or fenced content survived into the derived tree"; fi

t "content OUTSIDE the fence survives — the strip is scoped, not a truncation"
if grep -q 'Development Workflows' "$C/skills/README.md" \
   && grep -q 'Skill Handoff Map' "$C/skills/README.md"; then pass
else fail "strip_maintenance_docs removed runtime sections of skills/README.md"; fi

t "no derived doc points at a stripped maintenance doc"
dangling=$(grep -rhoE '(skills/(xia2|compound)|agents)/README\.md' "$C" --include='*.md' 2>/dev/null | sort -u)
if [ -z "$dangling" ]; then pass; else fail "still referenced: $(echo "$dangling" | tr '\n' ' ')"; fi

# ---------------------------------------------------------------------------
# the reason the subset exists at all: the helper must work from where it lands
# ---------------------------------------------------------------------------
t "deployed verify_summary.py resolves the REPO root, not .claude/"
# Path(__file__).parents[1] is .claude/ once deployed; specs/ lives one level further out.
mkdir -p "$T/specs/probe-slug"
printf 'Lane: tiny\nConfidence: high\nReason: probe\n' > "$T/specs/probe-slug/SUMMARY.md"
out=$(cd "$T" && python3 .claude/scripts/verify_summary.py --lane probe-slug 2>&1)
if printf '%s' "$out" | grep -qF "$T/specs/probe-slug/SUMMARY.md" \
   && ! printf '%s' "$out" | grep -qF '.claude/specs'; then pass
else fail "resolved the wrong root: $(printf '%s' "$out" | head -1)"; fi

finish
