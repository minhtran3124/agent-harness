---
problem_type: failure
module: hooks/repo-root-resolution
tags: ratchet-blind-spot, spelling-vs-property, variable-name-enumeration, shared-blind-spot, text-anchored-guards, code-review-catch
severity: critical
applicable_when: Watch for this when the same change that fixes a defect also writes the ratchet meant to prevent it, and the ratchet matches an identifier by name — a checker sourced from the same enumeration as the fix inherits that enumeration's blind spot and reports clean over the instances both missed.
affects:
  - scripts/check-hook-root-source.sh
  - hooks/session-knowledge.sh
  - tests/hooks/repo-root-resolution.test.sh
supersedes: null
confidence: high
confirmed_at: 2026-09-09
---
## Applicable When

Watch for this when the same change that fixes a defect also writes the ratchet meant to prevent it,
and the ratchet matches an identifier by name (a variable, function, flag, or path fragment) rather
than by the property that makes the code wrong. Especially when the fix list was produced by a
manual `grep` pass — the checker will be written from that same list.

## Symptom

A ratchet shipped alongside a fix reported **clean**, `run-tests.sh` printed `ALL GREEN`, CI passed
on both platforms, and the defect the ratchet existed to prevent was still present one file away.

Nothing in the run said otherwise. There was no failing test, no warning, no skipped-check notice —
the guard genuinely ran and genuinely found nothing, because it was looking for the wrong thing.

## Wrong Approach

Fixing the repo-root defect (see `hook-root-must-not-come-from-install-location.md`) began with a
manual enumeration:

```bash
grep -rn 'git -C "$SCRIPT_DIR" rev-parse --show-toplevel' hooks/
```

That returned seven hooks. Seven were fixed. Then a ratchet was written to stop the pattern coming
back — and it was written from the same mental model, matching the same literal string:

```bash
# scripts/check-hook-root-source.sh, first version
HITS=$(grep -rnE 'rev-parse --show-toplevel' hooks/ \
  | grep -vE ':[0-9]+:[[:space:]]*#' \
  | grep -E 'git -C "\$(SCRIPT_DIR|\{SCRIPT_DIR\})"|git -C "\$\(dirname "\$0"\)"')
```

But `hooks/session-knowledge.sh:22` carried the identical defect under a different variable name:

```bash
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$HOOK_DIR" rev-parse --show-toplevel 2>/dev/null)"
```

Eight hooks were affected. Seven were fixed, one was invisible to both the enumeration and the
guard, and the guard's green result was read as confirmation that the work was complete.

## Why It Failed

**The checker and the fix were derived from the same enumeration pass, so they shared one blind
spot and neither could catch the other.** This is the whole lesson. A ratchet is supposed to be an
independent oracle — the thing that catches what you missed. One generated from the same list as the
change it guards is not independent; it is the same judgement written twice, and it converts a gap
in that judgement into *evidence of correctness*. It added confidence without adding coverage.

The mechanism underneath: `SCRIPT_DIR` is a *spelling*. The defect is a *property* — "this hook
derives the root it audits from its own install location". Grepping for the name enforces the
spelling, and any instance of the property spelled differently passes. The name was never the bug.

It was caught only by an independent code review of a *sibling* PR — the reviewers re-derived the
hook list from source rather than from the document that named it. That is the shape of oracle that
works here: one that goes back to the ground truth instead of inheriting the list.

## Correct Approach

Widen the match to the defect's **shape**, not one observed name, and then prove the widened guard
bites:

```bash
# any *_DIR-suffixed variable used as a `git -C` root source, plus the dirname $0 spellings
grep -rnE 'rev-parse --show-toplevel' hooks/ \
  | grep -vE ':[0-9]+:[[:space:]]*#' \
  | grep -E 'git -C "\$\{?[A-Za-z_][A-Za-z0-9_]*_DIR\}?"|git -C "\$\(dirname "\$0"\)"|git -C "\$\(cd "\$\(dirname'
```

Then run the new ratchet against the **previous** commit and require it to fail. It exits 1 and
names `hooks/session-knowledge.sh:22`. A ratchet that has never been observed failing is not known
to be a ratchet — the same argument as
`mutation-testing-proves-a-suite-is-load-bearing.md`, applied to a lint instead of a test suite.

Two regression cases were added (`tests/hooks/repo-root-resolution.test.sh`, 11 → 13). Only one
discriminates: hosting `session-knowledge` inside a foreign repo carrying its own
`docs/solutions/` and asserting the session does **not** receive that repo's knowledge base. The
other ("no resolvable root → silent exit 0") passes before and after; it is a posture guard, and the
spec's SUMMARY labels it as such rather than counting it as proof.

**The residual is stated, not hidden:** the widened regex is still an enumeration of spellings. A
hook deriving its root a third way — `realpath "$0"`, a `$BASH_SOURCE` chain, a hard-coded relative
path — would still pass. This guard reached traceability tier and no further.

- **Always:** derive a ratchet's match from the defect's shape, and demonstrate it failing on the
  pre-fix tree before trusting its green — ✅ `git show <pre-fix>:… > tmp/ && bash <ratchet>` exits 1
- **Never:** write a ratchet whose match list was produced by the same enumeration pass as the fix
  it guards, without a second pass from a different angle — ❌ grepping only `SCRIPT_DIR` because
  that was the name the first seven hooks happened to use

## Guardrail

`existing:` `scripts/check-hook-root-source.sh` (wired into `run-tests.sh` L1) now matches any
`*_DIR` variable rather than the literal name, and its Verifies/Does-not-verify header states that
it is traceability-tier only.

`proposed:` a check that does not depend on spelling at all. Two viable shapes, in preference order:

1. **Taint-track the path's provenance.** Flag any `git -C <expr>` feeding `rev-parse
   --show-toplevel` whose `<expr>` traces back to `$0`, `${BASH_SOURCE[0]}`, `dirname`, or
   `realpath "$0"` — regardless of what the intermediate variable is called. A second pass over
   `shellcheck -f json`, or a small AWK/python taint walk, is enough; full parsing is not needed.
   Target path `scripts/check-hook-root-source.sh` (replacing the regex body).
2. **Retire the static check and rely on the behavioural test instead.**
   `tests/hooks/repo-root-resolution.test.sh` already hosts each hook inside a foreign git repo and
   observes which repo it acts on — that technique is spelling-independent *by construction* and
   sits at truth tier rather than traceability. The cost is that it only covers hooks someone
   remembered to add a case for, which is the same enumeration problem one layer up; the lint's
   value is that it scans all of `hooks/` unprompted. Keeping both, with the lint understood as the
   weaker of the two, is why option 1 is preferred over this one.

Until either exists, read this guard's green as "no known spelling present", **not** "the property
holds".

## Related

- docs/solutions/harness/hook-root-must-not-come-from-install-location.md — the defect this ratchet
  was built to prevent, and the one instance it let through
- docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md — same principle for
  test suites: a green assertion proves nothing until you have seen it fail
- docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md — the same shared-
  blind-spot shape at the review layer: a check fitted to the assumptions of the thing it checks
- docs/solutions/harness/test-and-doc-lint-gate-scope.md — a lint reporting clean over cases outside
  the scope it was written against
