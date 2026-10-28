#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="skills/brainstorming/SKILL.md"
REF="skills/brainstorming/references/spec-review-loop.md"
t "brainstorming agrees the design before any code and hands off to xia2 then writing-plans"
grep -q 'No code until the design is agreed' "$ROOT/$SKILL" && grep -q '`xia2`' "$ROOT/$SKILL" && grep -q '`writing-plans`' "$ROOT/$SKILL" && pass || fail "design gate or handoff missing"
t "brainstorming drops the mandatory spec-review loop"
! grep -q 'spec-review-loop\|spec-document-reviewer' "$ROOT/$SKILL" && [ ! -e "$ROOT/skills/brainstorming/spec-document-reviewer-prompt.md" ] && [ ! -e "$ROOT/skills/brainstorming/references/spec-review-loop.md" ] && pass || fail "review loop still present"
t "brainstorming has an Auto mode section and writes design.md for depth L"
grep -q '^## Auto mode' "$ROOT/$SKILL" && grep -q 'specs/<slug>/design.md' "$ROOT/$SKILL" && pass || fail "Auto mode or design.md output missing"
TPL="skills/brainstorming/references/design-template.md"
BRIEF="skills/xia2/references/research-brief-template.md"
has_all() { local f="$1"; shift; for a in "$@"; do grep -qF -- "$a" "$ROOT/$f" || return 1; done; }
t "design template exists and brainstorming reads it"
[ -f "$ROOT/$TPL" ] && grep -qF 'references/design-template.md' "$ROOT/$SKILL" && pass || fail "design template or its Read missing"
t "design and research-brief templates carry the provenance header"
has_all "$TPL" '# <slug> — Design' 'Written <YYYY-MM-DD>. Pins:' && has_all "$BRIEF" '# <slug> — Research Brief' 'Written <YYYY-MM-DD>. Pins:' && pass || fail "provenance header missing"
QTPL="templates/QUESTIONS.template.md"
t "questions template carries the blocking-question sentence and its six field keys"
[ -f "$ROOT/$QTPL" ] && has_all "$QTPL" 'A question that blocks work does not belong here: write it in ESCALATIONS.md.' \
  '## OQ-1' 'raised-by:' 'closes-at:' 'decided-by:' 'default-until-closed:' 'status:' 'closed-by:' \
  && pass || fail "questions template anchor missing"
t "specs README lists QUESTIONS.md"
has_all "templates/structure/specs-README.md" '| `QUESTIONS.md` |' && pass || fail "specs README QUESTIONS.md row missing"
finish
