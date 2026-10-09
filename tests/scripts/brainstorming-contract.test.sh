#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="skills/brainstorming/SKILL.md"
REF="skills/brainstorming/references/spec-review-loop.md"
t "brainstorming keeps the approval hard gate"
grep -q '<HARD-GATE>' "$ROOT/$SKILL" && grep -q 'Do not write code' "$ROOT/$SKILL" && pass || fail "approval gate missing"
t "brainstorming preserves xia2 then writing-plans handoff"
grep -q 'Invoke only `xia2`' "$ROOT/$SKILL" && grep -q '`writing-plans`' "$ROOT/$SKILL" && pass || fail "handoff missing"
t "review loop is conditionally referenced and exists"
grep -q 'references/spec-review-loop.md' "$ROOT/$SKILL" && [ -f "$ROOT/$REF" ] && pass || fail "review reference missing"
TPL="skills/brainstorming/references/design-template.md"
REVIEWER="skills/brainstorming/spec-document-reviewer-prompt.md"
BRIEF="skills/xia2/references/research-brief-template.md"
has_all() { local f="$1"; shift; for a in "$@"; do grep -qF -- "$a" "$ROOT/$f" || return 1; done; }
t "design template exists and brainstorming reads it"
[ -f "$ROOT/$TPL" ] && grep -qF 'references/design-template.md' "$ROOT/$SKILL" && pass || fail "design template or its Read missing"
t "design template carries its sections, reopen pointer and number labels"
has_all "$TPL" 'To reopen a settled decision after approval' '## What must be true' \
  '## What we do not claim' '## Decisions' '## Decision changes' \
  '`prediction`' '`budget`' '`measured <YYYY-MM-DD> <source>`' && pass || fail "design template anchor missing"
t "design reviewer gets the template and its checks"
has_all "$REVIEWER" 'What must be true' 'Proven by' 'load-bearing' 'superseded by' \
  'Decision changes' 'To reopen a settled decision' '[TEMPLATE_FILE_PATH]' \
  && grep -qF 'design-template.md' "$ROOT/$REF" && pass || fail "reviewer template checks or loop path missing"
t "research-brief template carries the number-label rule"
# The brief template carries an inline copy of the design template's label rule; anchor the whole
# label set and the load-bearing definition so the copy cannot drift to a subset unnoticed.
has_all "$BRIEF" '`measured <YYYY-MM-DD> <source>`' '`prediction`' '`budget`' 'load-bearing' \
  && pass || fail "research-brief number-label rule incomplete"
QTPL="templates/QUESTIONS.template.md"
t "brainstorming points multi-phase specs at the open-questions register"
has_all "$SKILL" 'In a multi-phase spec, record non-blocking unknowns in specs/<slug>/QUESTIONS.md from templates/QUESTIONS.template.md.' \
  && pass || fail "brainstorming QUESTIONS.md sentence missing"
t "questions template carries the blocking-question sentence and its six field keys"
[ -f "$ROOT/$QTPL" ] && has_all "$QTPL" 'A question that blocks work does not belong here: write it in ESCALATIONS.md.' \
  '## OQ-1' 'raised-by:' 'closes-at:' 'decided-by:' 'default-until-closed:' 'status:' 'closed-by:' \
  && pass || fail "questions template anchor missing"
t "specs README lists QUESTIONS.md"
has_all "templates/structure/specs-README.md" '| `QUESTIONS.md` |' && pass || fail "specs README QUESTIONS.md row missing"
finish
