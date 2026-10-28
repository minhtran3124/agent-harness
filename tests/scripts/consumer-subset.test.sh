#!/bin/bash
# Integration tests for the three DERIVE-TIME transforms in scripts/deploy-harness.sh:
#   copy_consumer_subset   — ship the allow-listed helpers + data a consumer's skills actually run
#   rewrite_derived_paths  — repoint `scripts/X` -> `.claude/scripts/X` in derived Markdown
#   strip_skill_tests      — drop harness CI fixtures/unit tests from the derived tree
#   strip_maintenance_docs — drop HARNESS_ONLY_DOCS + <!-- harness-only --> regions
#
# WHY THIS FILE EXISTS: before these transforms, every consuming repo silently fail-opened on the
# gates its own skills/rules described — the helper they name (scripts/write_adrs.py etc.) never
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
for f in rebuild_solution_index.py render_skill_prompt.py \
         run_at_commit.py write_adrs.py; do
  [ -f "$C/scripts/$f" ] || missing="$missing $f"
done
if [ "$RC" -eq 0 ] && [ -z "$missing" ] && python3 -m py_compile "$C"/scripts/*.py 2>/dev/null; then pass
else fail "rc=$RC missing:$missing (or a deployed helper does not compile)"; fi

t "the removed run-state and receipt helpers are not shipped"
leaked=""
for f in verify_summary.py check_plan_contract.py check_review_receipt.py resolve_finish_context.py; do
  [ -e "$C/scripts/$f" ] && leaked="$leaked $f"
done
[ -e "$C/runtime" ] && leaked="$leaked runtime/"
if [ -z "$leaked" ]; then pass; else fail "removed machinery deployed:$leaked"; fi

t "harness-manifest.json is not shipped (the manifest and hook profiles were removed)"
if [ ! -e "$C/harness-manifest.json" ]; then pass
else fail "manifest deployed at .claude/harness-manifest.json"; fi

t "harness-development scripts are NOT shipped (the subset is an allow-list, not a copy of scripts/)"
leaked=""
for f in deploy-harness.sh init-structure.sh harness-audit.sh run-tests.sh; do
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
# skills/decision-record/SKILL.md names write_adrs.py.
if grep -q '\.claude/scripts/write_adrs\.py' "$C/skills/decision-record/SKILL.md" \
   && ! grep -qE '(^|[^.])(^|[^/])\bscripts/write_adrs\.py' "$C/skills/decision-record/SKILL.md"; then pass
else fail "derived skill still points at the undeployed scripts/write_adrs.py"; fi

t "every .claude/scripts/ path named in derived Markdown actually resolves"
unresolved=$(grep -rhoE '\.claude/scripts/[A-Za-z0-9_.-]+' "$C" --include='*.md' 2>/dev/null | sort -u \
  | while read -r p; do [ -e "$T/$p" ] || echo "$p"; done)
if [ -z "$unresolved" ]; then pass; else fail "named but not shipped: $(echo "$unresolved" | tr '\n' ' ')"; fi

t "derived docs invoke render_plan.py at the deployed path, and it resolves"
# the wave-boundary rule and the visual-planner skill run render_plan.py; in a consumer it lives under .claude/skills/, one level in.
rp_bad=""
for f in rules/wave-parallelism.md; do
  grep -q '\.claude/skills/visual-planner/render_plan\.py' "$C/$f" || rp_bad="$rp_bad $f(missing)"
  grep -qE '(^|[^./])skills/visual-planner/render_plan\.py' "$C/$f" && rp_bad="$rp_bad $f(unrewritten)"
done
[ -e "$T/.claude/skills/visual-planner/render_plan.py" ] || rp_bad="$rp_bad render_plan.py(not-shipped)"
if [ -z "$rp_bad" ]; then pass; else fail "$rp_bad"; fi

t "vendored asd-ste100 skill ships with its linter and without the unvendored upstream files"
# The consumer gets SKILL.md and ste-lint.py. Upstream README.md and the linter edge-case
# examples are not vendored, so they must not appear in the consumer.
ste_bad=""
for f in SKILL.md scripts/ste-lint.py; do
  [ -f "$C/skills/asd-ste100/$f" ] || ste_bad="$ste_bad $f(missing)"
done
for f in README.md examples/linter-edge-cases.md; do
  [ -e "$C/skills/asd-ste100/$f" ] && ste_bad="$ste_bad $f(present)"
done
if [ -z "$ste_bad" ]; then pass; else fail "$ste_bad"; fi

t "derived asd-ste100 SKILL.md names ste-lint.py at the deployed path, and it resolves"
# In a consumer the linter lives under .claude/skills/. A bare skills/... path does not resolve
# from the consumer root. This check uses the same idea as the render_plan.py check above.
ste_bad=""
grep -qE '(^|[^./])skills/asd-ste100/scripts/ste-lint\.py' "$C/skills/asd-ste100/SKILL.md" \
  && ste_bad="$ste_bad SKILL.md(unrewritten)"
grep -q '\.claude/skills/asd-ste100/scripts/ste-lint\.py' "$C/skills/asd-ste100/SKILL.md" \
  || ste_bad="$ste_bad SKILL.md(missing)"
[ -e "$T/.claude/skills/asd-ste100/scripts/ste-lint.py" ] || ste_bad="$ste_bad ste-lint.py(not-shipped)"
if [ -z "$ste_bad" ]; then pass; else fail "$ste_bad"; fi

t "derived feature-intake SKILL.md names diagnosing-bugs SKILL.md at the deployed path, and it resolves"
# feature-intake routes a bug to the diagnosing-bugs skill by path. In a consumer that file
# lives under .claude/skills/. This check uses the same idea as the ste-lint.py check above.
db_bad=""
grep -qE '(^|[^./])skills/diagnosing-bugs/SKILL\.md' "$C/skills/feature-intake/SKILL.md" \
  && db_bad="$db_bad SKILL.md(unrewritten)"
grep -q '\.claude/skills/diagnosing-bugs/SKILL\.md' "$C/skills/feature-intake/SKILL.md" \
  || db_bad="$db_bad SKILL.md(missing)"
[ -e "$T/.claude/skills/diagnosing-bugs/SKILL.md" ] || db_bad="$db_bad diagnosing-bugs(not-shipped)"
if [ -z "$db_bad" ]; then pass; else fail "$db_bad"; fi

t "derived diagnosing-bugs SKILL.md names hitl-loop.template.sh at the deployed path, and it resolves"
# Phase 1 tells the agent to copy the loop template by path. The whole skills/diagnosing-bugs/
# prefix is rewritten, so the template path must resolve from the consumer root too.
db_bad=""
grep -qE '(^|[^./])skills/diagnosing-bugs/scripts/hitl-loop\.template\.sh' "$C/skills/diagnosing-bugs/SKILL.md" \
  && db_bad="$db_bad SKILL.md(unrewritten)"
grep -q '\.claude/skills/diagnosing-bugs/scripts/hitl-loop\.template\.sh' "$C/skills/diagnosing-bugs/SKILL.md" \
  || db_bad="$db_bad SKILL.md(missing)"
[ -e "$T/.claude/skills/diagnosing-bugs/scripts/hitl-loop.template.sh" ] || db_bad="$db_bad hitl-loop.template.sh(not-shipped)"
if [ -z "$db_bad" ]; then pass; else fail "$db_bad"; fi

t "rewrite is idempotent — a second deploy never produces .claude/.claude/"
run_deploy "$T"
dbl=$(grep -rl '\.claude/\.claude/' "$C" --include='*.md' 2>/dev/null)
if [ "$RC" -eq 0 ] && [ -z "$dbl" ]; then pass; else fail "rc=$RC double-prefixed: $dbl"; fi

t "hooks are NOT rewritten - a derived hook is byte-identical to its source"
# rewrite_derived_paths is Markdown-only; assert that literally, so a future widening to *.sh trips here.
if cmp -s "$C/hooks/secrets-scan.sh" "$ROOT/hooks/secrets-scan.sh" \
   && cmp -s "$C/hooks/clean-worktrees.sh" "$ROOT/hooks/clean-worktrees.sh"; then pass
else fail "a derived hook diverged from source - path rewriting must stay Markdown-only"; fi

# ---------------------------------------------------------------------------
# strip_skill_tests
# ---------------------------------------------------------------------------
t "harness CI fixtures and unit tests are stripped from the derived tree"
left=$(find "$C/skills" \( -path '*/tests/*' -o -name 'test_*.py' \) 2>/dev/null)
if [ -z "$left" ]; then pass; else fail "test material shipped: $(echo "$left" | tr '\n' ' ')"; fi

t "stripping is derive-only — the harness sources still hold their tests"
if [ -f "$ROOT/skills/xia2/tests/behavioural/pressure-scenarios.md" ] \
   && [ -f "$ROOT/skills/visual-planner/test_render_plan.py" ]; then pass
else fail "sources lost their tests — strip_skill_tests must never touch \$ROOT"; fi

# ---------------------------------------------------------------------------
# strip_maintenance_docs
# ---------------------------------------------------------------------------
t "HARNESS_ONLY_DOCS are absent from the consumer and intact at the source"
bad=""
for f in skills/compound/README.md agents/README.md; do
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
t "deployed rebuild_solution_index.py resolves the REPO root, not .claude/"
# Path(__file__).parents[1] is .claude/ once deployed; docs/ lives one level further out.
mkdir -p "$T/docs/solutions"
out=$(cd "$T" && python3 .claude/scripts/rebuild_solution_index.py 2>&1)
if printf '%s' "$out" | grep -qF "$T/docs/solutions/INDEX.md" \
   && ! printf '%s' "$out" | grep -qF '.claude/docs'; then pass
else fail "resolved the wrong root: $(printf '%s' "$out" | head -1)"; fi

finish
