#!/bin/bash
# Contract for /harness:tickets. Each case pins a rule that an earlier word-ceiling trim or a
# review of the skill showed to be easy to lose or to get wrong.
source "$(dirname "$0")/../lib.sh"
DIR="$ROOT/plugins/harness/skills/tickets"
SKILL="$DIR/SKILL.md"
PROCESS="$DIR/references/process.md"

t "references holds the three templates and the required process file"
got="$(ls "$DIR/references" | sort | tr '\n' ' ')"
[ "$got" = "bug.md docs.md feature.md process.md " ] && pass || fail "got: $got"

t "SKILL.md makes the process file a required Read"
grep -q 'Required: Read `references/process.md`' "$SKILL" && pass || fail "required Read missing"

t "the goal line names intake READY and autopilot"
grep -q 'Goal: every ticket you create passes `harness:intake` as READY' "$SKILL" && grep -q 'no new question' "$SKILL" \
  && pass || fail "goal line missing"

t "the skill has a NEVER list"
grep -q '^## NEVER' "$SKILL" && pass || fail "NEVER list missing"

t "owner decisions end at step 2, so no Decide ticket can be written"
grep -q 'Never write a `Decide:` ticket' "$SKILL" && ! grep -q 'its own ticket, `Decide' "$SKILL" "$PROCESS" \
  && pass || fail "a Decide ticket is still possible"

t "dedup reads issue bodies and compares the source line exactly"
grep -qF 'gh issue list --state all --limit 1000 --json number,title,body,state' "$PROCESS" \
  && grep -q 'exact match' "$PROCESS" && ! grep -q 'gh issue list --state all --search' "$SKILL" "$PROCESS" \
  && pass || fail "dedup is still fuzzy"

t "the source key is unique per ticket"
grep -qF 'source: <brief path>#<section>/<slug>' "$SKILL" && pass || fail "source key has no slug"

t "the epic has its own source key and stays out of the milestone"
grep -qF 'source: <brief path>#epic' "$PROCESS" && grep -q 'Never put the epic in the milestone' "$SKILL" \
  && pass || fail "epic rule missing"

t "a label reuses a name only when it matches ignoring case"
grep -q 'only when the name matches ignoring case' "$PROCESS" && ! grep -q 'differs by 1 or 2 characters, use' "$SKILL" "$PROCESS" \
  && pass || fail "fuzzy label rule still present"

t "deps cover the batch, closed issues and skipped tickets"
grep -q 'in this batch or closed issues' "$PROCESS" && grep -q 'skipped ticket' "$SKILL" \
  && pass || fail "deps rule missing"

t "a changed section is listed for the owner, not edited"
grep -q 'list them for the owner' "$PROCESS" && pass || fail "changed-section rule missing"

t "approval keeps one go question and puts overlaps in one multi-select"
grep -q 'multi-select' "$PROCESS" && grep -q 'in the question text' "$SKILL" && pass || fail "approval rule missing"

t "the kept conditions from the ticket are back"
grep -q 'merge the tickets' "$PROCESS" && grep -q 'not by layer' "$PROCESS" && grep -q 'Ask the owner only for decisions' "$SKILL" \
  && pass || fail "a trimmed condition is still lost"

t "repo reads have no default page cap"
grep -qF 'gh label list --limit 1000' "$SKILL" && grep -qF 'state=all --paginate' "$SKILL" && pass || fail "a read can miss rows"

t "the dedup read prints source lines only, because full bodies can be cut off"
grep -qF -- '--jq' "$PROCESS" && grep -qF 'startswith("source:")' "$PROCESS" && pass || fail "full bodies are still printed"

t "issues are read in step 1, before any slug is written"
grep -q '^## 1. Read' "$SKILL" && sed -n '/^## 1. Read/,/^## 2/p' "$SKILL" | grep -q 'Required: Read `references/process.md`' \
  && sed -n '/^## 1. Read/,/^## 2/p' "$SKILL" | grep -q 'Duplicates' && pass || fail "the read is out of order"

t "a dep on an open issue outside the milestone, and on a wait ticket, is held"
grep -q 'A ticket that depends on a `wait` ticket is also `wait`' "$PROCESS" && grep -q 'open and outside this milestone' "$PROCESS" \
  && pass || fail "deps rules conflict"

t "the overlap question says what a selection means"
grep -q 'Which overlaps should I create anyway' "$PROCESS" && grep -q 'each selected overlap adds one' "$PROCESS" \
  && pass || fail "overlap answer is ambiguous"

t "the brief path in source: is relative to the repo root"
grep -q 'relative to the repo root' "$PROCESS" && pass || fail "path is not normalized"

t "a closed milestone with the same name stops at approval"
grep -q 'closed milestone' "$PROCESS" && pass || fail "closed milestone has no rule"

t "the self-check requires Verify to fail before the change"
grep -q 'fails on the base commit' "$PROCESS" && pass || fail "a weak Verify row can pass"

t "an issue body goes on stdin, because a multi-line --body is denied and the skill has no Write"
grep -qF -- "--body-file - <<'EOF'" "$SKILL" && pass || fail "body form missing"

t "every milestones call stays inside the allowed-tools pattern"
# A quote before repos/ misses Bash(gh api repos/*/milestones*), and "?" fails as a glob in zsh.
! grep -E "api ['\"]repos" "$SKILL" "$PROCESS" && ! grep -F 'milestones?' "$SKILL" "$PROCESS" \
  && grep -qF 'repos/{owner}/{repo}/milestones -X GET -f state=all' "$SKILL" \
  && pass || fail "a milestones call would be denied at runtime"

finish
