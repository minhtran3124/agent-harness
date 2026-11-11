#!/bin/bash
# Acceptance tests for #460: the "Read by" bullet in docs/solutions/README.md and its scaffold
# copy must name the real v5 read paths, not the removed session-knowledge hook.
source "$(dirname "$0")/../lib.sh"

DOC=docs/solutions/README.md
TPL=plugins/harness/templates/structure/docs-solutions-README.md

# bullet <file-content-on-stdin>: the "Read by" bullet, up to the next blank line
bullet() { awk '/^- \*\*Read by:\*\*/{p=1} p&&/^[[:space:]]*$/{exit} p'; }

t "AC1: no session-knowledge mention in README or templates"
out=$(cd "$ROOT" && git grep -n session-knowledge -- "$DOC" plugins/harness/templates 2>&1)
[ -z "$out" ] && pass || fail "still mentioned: $out"

for f in "$DOC" "$TPL"; do
  b=$(bullet < "$ROOT/$f")
  t "AC2: $f Read by bullet lists xia2 (research, depth L)"
  echo "$b" | grep -q 'xia2' && echo "$b" | grep -qi 'research' && echo "$b" | grep -q 'depth L' && pass || fail "bullet: $b"
  t "AC2: $f Read by bullet lists brainstorming (design, depth L)"
  echo "$b" | grep -q 'brainstorming' && echo "$b" | grep -qi 'design' && pass || fail "bullet: $b"
  t "AC2: $f Read by bullet lists compound related-docs lookup"
  echo "$b" | grep -q 'compound' && echo "$b" | grep -qi 'related-docs' && pass || fail "bullet: $b"
  t "AC2: $f Read by bullet names CLAUDE.md and critical-patterns.md when planning"
  echo "$b" | grep -q 'CLAUDE.md' && echo "$b" | grep -q 'critical-patterns.md' && echo "$b" | grep -qi 'planning' && pass || fail "bullet: $b"
done

t "AC3: Read by bullet is byte-identical in README and template"
a=$(bullet < "$ROOT/$DOC"); b=$(bullet < "$ROOT/$TPL")
[ -n "$a" ] && [ "$a" = "$b" ] && pass || fail "README: [$a] template: [$b]"

# The owner chose (after the QA check of the pilot run found the two files differed) that the whole
# files are byte-equal, not only the Read by bullet.
t "AC3: docs/solutions/README.md and the scaffold copy are byte-identical"
cmp -s "$ROOT/$DOC" "$ROOT/$TPL" && pass || fail "the two files differ"

t "AC4: scripts/run-tests.sh ends with ALL GREEN"
if [ -n "${HARNESS_ACCEPTANCE_NESTED:-}" ]; then skip "nested run"; else
  out=$(cd "$ROOT" && HARNESS_ACCEPTANCE_NESTED=1 bash scripts/run-tests.sh 2>&1); rc=$?
  [ "$rc" -eq 0 ] && printf '%s\n' "$out" | tail -5 | grep -q 'ALL GREEN' && pass || fail "rc=$rc; tail: $(printf '%s\n' "$out" | tail -3)"
fi
finish
