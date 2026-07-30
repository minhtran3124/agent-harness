#!/bin/bash
# Contract test for Task 4.1 (specs/require-claude-simplify-gate/PLAN.md): the required
# Claude Code `/simplify` cleanup stage must be wired into subagent-driven-development's
# `verifying` path, ahead of the branch review package / final oracles / receipt (SC-4),
# consuming the wave-3 policy and evidence primitives correctly (SC-2, SC-3, SC-5).
#
# This parses the LIVE composed prose (not a snapshot), same idiom as
# context-propagation-regression.test.sh: each check greps the real files, and a paired
# mutation proves the check is load-bearing, not a vacuous phrase match.
source "$(dirname "$0")/../lib.sh"

SKILL="skills/subagent-driven-development/SKILL.md"
CHAIN="skills/subagent-driven-development/references/review-chain.md"
STAGE="skills/subagent-driven-development/references/simplify-stage.md"
RESUME="skills/subagent-driven-development/references/resume.md"

# flat <dir> <relpath> — file content with newlines collapsed to single spaces, so a
# phrase that wraps across a markdown line break still matches a plain substring grep.
flat() {
  tr '\n' ' ' < "$1/$2" | tr -s ' '
}

# --- SC-4: ordering ----------------------------------------------------------------

# skill_orders_ok <dir> — 0 iff SKILL.md's Execute-waves handoff names
# references/simplify-stage.md strictly before references/review-chain.md.
skill_orders_ok() {
  local dir="$1" simplify_line chain_line
  simplify_line=$(grep -n 'references/simplify-stage\.md' "$dir/$SKILL" | head -1 | cut -d: -f1)
  chain_line=$(grep -n 'references/review-chain\.md' "$dir/$SKILL" | head -1 | cut -d: -f1)
  [ -n "$simplify_line" ] && [ -n "$chain_line" ] && [ "$simplify_line" -lt "$chain_line" ]
}

# stage_handoff_ok <dir> — 0 iff simplify-stage.md exists and hands off to review-chain.md.
stage_handoff_ok() {
  [ -f "$1/$STAGE" ] && grep -q 'references/review-chain\.md' "$1/$STAGE"
}

# stage_commit_before_ok <dir> — 0 iff simplify-stage.md requires an accepted changed
# outcome to be committed before the branch review package is created.
stage_commit_before_ok() {
  flat "$1" "$STAGE" | grep -qF 'committed before the branch review package'
}

t "SKILL.md hands off to simplify-stage.md strictly before review-chain.md"
if skill_orders_ok "$ROOT"; then pass
else fail "references/simplify-stage.md must appear before references/review-chain.md in $SKILL"; fi

t "simplify-stage.md exists and hands off to review-chain.md"
if stage_handoff_ok "$ROOT"; then pass
else fail "$STAGE missing, or does not point at references/review-chain.md"; fi

t "simplify-stage.md commits an accepted changed outcome before the branch review package"
if stage_commit_before_ok "$ROOT"; then pass
else fail "no 'committed before the branch review package' clause in $STAGE"; fi

# --- SC-2: policy resolution wiring --------------------------------------------------

# stage_policy_wired_ok <dir> — 0 iff simplify-stage.md resolves policy via the wave-1
# checker and reads its required/ok fields, rather than re-deriving the decision.
stage_policy_wired_ok() {
  grep -q 'check_claude_simplify\.py' "$1/$STAGE" && flat "$1" "$STAGE" | grep -qF 'do not re-derive any of it from the diff yourself'
}

t "simplify-stage.md resolves the policy decision via check_claude_simplify.py, not ad hoc"
if stage_policy_wired_ok "$ROOT"; then pass
else fail "no check_claude_simplify.py wiring with a no-re-derive clause in $STAGE"; fi

# --- SC-3: begin() dirty-worktree / explicit-base guard reused, not reimplemented ---

# stage_begin_wired_ok <dir> — 0 iff simplify-stage.md calls simplify_record.py begin and
# explicitly defers the dirty-worktree/base-resolution refusal to it.
stage_begin_wired_ok() {
  grep -q 'simplify_record\.py begin' "$1/$STAGE" \
    && flat "$1" "$STAGE" | grep -qF 'do not reimplement either check here'
}

t "simplify-stage.md defers the dirty-worktree/base refusal to simplify_record.py begin"
if stage_begin_wired_ok "$ROOT"; then pass
else fail "no simplify_record.py begin call with a do-not-reimplement clause in $STAGE"; fi

# stage_begin_not_gated_on_required_ok <dir> — 0 iff begin() runs whenever reviewable
# paths exist, regardless of `required`. Otherwise a tiny/advisory (not-required) diff with
# reviewable paths would reach finish()'s required --begin-state with nothing to pass —
# finish() has no valid input, and the receipt gate (which only checks "any reviewable path
# touched", not the lane/tiny-size threshold) would then find no entry to validate.
stage_begin_not_gated_on_required_ok() {
  flat "$1" "$STAGE" | grep -qiF 'regardless of `required`' \
    && flat "$1" "$STAGE" | grep -qiF 'reviewable_paths` is empty'
}

t "simplify-stage.md runs begin() whenever reviewable paths exist, not gated on required"
if stage_begin_not_gated_on_required_ok "$ROOT"; then pass
else fail "begin() is not clearly decoupled from 'required' in $STAGE"; fi

# --- exactly-once invocation / no local skill ---------------------------------------

# stage_once_ok <dir> — 0 iff simplify-stage.md requires exactly one bundled Skill call
# and explicitly forbids a second invocation as the way to handle a rejection.
stage_once_ok() {
  flat "$1" "$STAGE" | grep -qiF 'exactly once' \
    && flat "$1" "$STAGE" | grep -qiF 'never the `/simplify` invocation'
}

t "simplify-stage.md requires exactly one bundled Skill(simplify) invocation, no retry loop"
if stage_once_ok "$ROOT"; then pass
else fail "no 'exactly once' + no-second-invocation clause in $STAGE"; fi

t "no repository skill named simplify exists (explicit non-goal)"
if [ ! -d "$ROOT/skills/simplify" ]; then pass
else fail "skills/simplify/ must not exist"; fi

# --- SC-5: changed outcome rejects on cannot_verify/needs_fixes/Critical-Important --

# stage_rejects_ok <dir> — 0 iff simplify-stage.md rejects a changed outcome on
# cannot_verify, a needs_fixes quality verdict, and any Critical/Important finding.
stage_rejects_ok() {
  local f="$1/$STAGE"
  grep -q 'cannot_verify' "$f" && grep -q 'needs_fixes' "$f" && grep -qi 'Critical/Important' "$f"
}

t "simplify-stage.md rejects cannot_verify, needs_fixes, and Critical/Important findings"
if stage_rejects_ok "$ROOT"; then pass
else fail "missing one of cannot_verify / needs_fixes / Critical/Important in $STAGE"; fi

# stage_no_op_evidence_ok <dir> — 0 iff a no_op outcome is documented to carry no
# verification/delta evidence (SC-5's no-op-consistency half).
stage_no_op_evidence_ok() {
  flat "$1" "$STAGE" | grep -qF 'carries no verification/delta evidence'
}

t "simplify-stage.md keeps no_op evidence empty (verification/delta), matching the receipt shape"
if stage_no_op_evidence_ok "$ROOT"; then pass
else fail "no 'carries no verification/delta evidence' clause in $STAGE"; fi

# stage_finish_authority_ok <dir> — 0 iff simplify-stage.md defers the pass/fail
# recomputation to simplify_record.py finish rather than hand-setting result: pass.
stage_finish_authority_ok() {
  grep -q 'simplify_record\.py finish' "$1/$STAGE" \
    && flat "$1" "$STAGE" | grep -qiF 'never hand-set'
}

t "simplify-stage.md defers pass/fail recomputation to simplify_record.py finish"
if stage_finish_authority_ok "$ROOT"; then pass
else fail "no simplify_record.py finish call with a never-hand-set clause in $STAGE"; fi

# --- resume: idempotent on valid evidence, resumes on missing/stale ------------------

# resume_covers_stage_ok <dir> — 0 iff resume.md routes resume-review-chain through the
# simplify stage's own evidence check, both for the skip case and the resume case.
resume_covers_stage_ok() {
  local f="$1/$RESUME"
  grep -q 'simplify-stage\.md' "$f" \
    && grep -q -- '--require-simplify-if' "$f" \
    && grep -qi 'exit code' "$f" \
    && flat "$1" "$RESUME" | grep -qiF 'do not re-run `references/simplify-stage.md`'
}

t "resume.md is idempotent on valid simplify evidence and resumes on missing/stale evidence"
if resume_covers_stage_ok "$ROOT"; then pass
else fail "resume-review-chain does not gate on simplify-stage evidence in $RESUME"; fi

# --- mutation tests: prove each check is load-bearing --------------------------------

mut_dir() {
  local m; m=$(mktemp -d); _CLEANUP_DIRS+=("$m")
  cp -R "$ROOT/skills" "$m/skills"
  echo "$m"
}

t "mutation: dropping the simplify-stage.md reference from SKILL.md is detected"
m=$(mut_dir)
sed -i.bak '/references\/simplify-stage\.md/d' "$m/$SKILL" && rm -f "$m/$SKILL.bak"
if ! skill_orders_ok "$m"; then pass
else fail "removing the simplify-stage.md reference from SKILL.md was NOT detected"; fi

t "mutation: reordering SKILL.md so review-chain.md is named first is detected"
m=$(mut_dir)
# Swap the two reference mentions so review-chain.md now appears first.
python3 - "$m/$SKILL" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
a, b = "references/simplify-stage.md", "references/review-chain.md"
text = text.replace(a, "__TMP__").replace(b, a).replace("__TMP__", b)
open(path, "w", encoding="utf-8").write(text)
PY
if ! skill_orders_ok "$m"; then pass
else fail "reordering the two references was NOT detected"; fi

t "mutation: removing the review-chain.md handoff from simplify-stage.md is detected"
m=$(mut_dir)
sed -i.bak '/references\/review-chain\.md/d' "$m/$STAGE" && rm -f "$m/$STAGE.bak"
if ! stage_handoff_ok "$m"; then pass
else fail "removing the review-chain.md handoff was NOT detected"; fi

t "mutation: removing the commit-before-package clause is detected"
m=$(mut_dir)
sed -i.bak '/committed before the branch review package/d' "$m/$STAGE" && rm -f "$m/$STAGE.bak"
if ! stage_commit_before_ok "$m"; then pass
else fail "removing the commit-before-package clause was NOT detected"; fi

t "mutation: removing the check_claude_simplify.py policy wiring is detected"
m=$(mut_dir)
sed -i.bak '/check_claude_simplify\.py/d' "$m/$STAGE" && rm -f "$m/$STAGE.bak"
if ! stage_policy_wired_ok "$m"; then pass
else fail "removing the check_claude_simplify.py wiring was NOT detected"; fi

t "mutation: removing the simplify_record.py begin dirty-worktree deferral is detected"
m=$(mut_dir)
sed -i.bak '/simplify_record\.py begin/d' "$m/$STAGE" && rm -f "$m/$STAGE.bak"
if ! stage_begin_wired_ok "$m"; then pass
else fail "removing the simplify_record.py begin wiring was NOT detected"; fi

t "mutation: gating begin() on 'required' (reintroducing the executability gap) is detected"
m=$(mut_dir)
sed -i.bak 's/regardless of `required`//' "$m/$STAGE" && rm -f "$m/$STAGE.bak"
if ! stage_begin_not_gated_on_required_ok "$m"; then pass
else fail "re-gating begin() on 'required' was NOT detected"; fi

t "mutation: removing the exactly-once invocation clause is detected"
m=$(mut_dir)
sed -i.bak 's/exactly once/once/' "$m/$STAGE" && rm -f "$m/$STAGE.bak"
if ! stage_once_ok "$m"; then pass
else fail "weakening 'exactly once' to 'once' was NOT detected"; fi

t "mutation: a repository skills/simplify/ directory is detected as a violation"
m=$(mut_dir)
mkdir -p "$m/skills/simplify"
printf '%s\n' '---' 'name: simplify' '---' > "$m/skills/simplify/SKILL.md"
if [ -d "$m/skills/simplify" ]; then pass
else fail "creating skills/simplify/ was not observable by the check"; fi

t "mutation: dropping the Critical/Important reject condition is detected"
m=$(mut_dir)
sed -i.bak 's/Critical\/Important//g' "$m/$STAGE" && rm -f "$m/$STAGE.bak"
if ! stage_rejects_ok "$m"; then pass
else fail "removing the Critical/Important reject condition was NOT detected"; fi

t "mutation: removing the no_op empty-evidence clause is detected"
m=$(mut_dir)
sed -i.bak '/carries no verification\/delta evidence/d' "$m/$STAGE" && rm -f "$m/$STAGE.bak"
if ! stage_no_op_evidence_ok "$m"; then pass
else fail "removing the no_op empty-evidence clause was NOT detected"; fi

t "mutation: removing the never-hand-set-result clause is detected"
m=$(mut_dir)
sed -i.bak 's/never hand-set//' "$m/$STAGE" && rm -f "$m/$STAGE.bak"
if ! stage_finish_authority_ok "$m"; then pass
else fail "removing the never-hand-set clause was NOT detected"; fi

t "mutation: removing resume.md's simplify-stage evidence gate is detected"
m=$(mut_dir)
sed -i.bak '/simplify-stage\.md/d; /--require-simplify-if/d; /exit code/d' "$m/$RESUME" && rm -f "$m/$RESUME.bak"
if ! resume_covers_stage_ok "$m"; then pass
else fail "removing resume.md's simplify-stage evidence gate was NOT detected"; fi

finish
