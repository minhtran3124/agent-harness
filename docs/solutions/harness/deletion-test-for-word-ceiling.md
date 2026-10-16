---
problem_type: knowledge
module: skills/*/SKILL.md (600-word progressive-disclosure ceiling, scripts/audit_skill_prompts.py)
tags: [word-ceiling, deletion-test, progressive-disclosure, scope-qualifier, skill-trim, ste100]
severity: high
applicable_when: A SKILL.md is at or over the 600-word ceiling that scripts/audit_skill_prompts.py enforces, or you must free room in a skill before you add sentences to it.
affects:
  - scripts/audit_skill_prompts.py
  - skills/*/SKILL.md
  - skills/*/references/
supersedes: null
confidence: high
confirmed_at: 2026-10-16
---
## Applicable When

`scripts/audit_skill_prompts.py` reports `skill exceeds 600-word progressive-disclosure ceiling`
for a `skills/<name>/SKILL.md`, or a skill is near the ceiling and a planned change must add
sentences to it. A vendored skill (one with an `UPSTREAM.md`) is exempt from the ceiling and is out
of scope here.

## Pattern

Trim by whole sentences and whole blocks, never by cutting words inside a sentence. Word-level
cuts are how a trim drops a condition with all tests green: see
`docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md` (feature-intake Step 1 and Step 6).

The procedure:

1. List each sentence of the skill.
2. **Deletion test.** Delete a whole sentence when the model already does it by default, or when
   it restates a file the skill already points to.
3. **Disclosure.** Move a whole block that only some branches reach into the skill's
   `references/` folder, and leave a one-line pointer in the skill. Inline what every branch
   needs; put behind a pointer what only some branches reach.
4. **Never shorten a sentence that holds a condition word.** Keep it whole or move it whole. The
   condition words are the same list as `WORDS` in `scripts/check_scope_qualifiers.py`:
   `if`, `unless`, `only`, `when`, `never`, `except`, `for a new`, `without`.
5. **Stop when nothing safe is left.** If the skill is still over budget, stop, keep the remaining
   sentences, and list them as "kept long on purpose" in the spec's `SUMMARY.md`.

**Split-scope warning.** When a moved or deleted sentence sits under a leading condition ("If X,
run these checks."), keep that condition in scope for every sentence that still depends on it:
the condition moves with the block, or it is repeated beside the sentences that stay.
`scripts/check_scope_qualifiers.py` does not list a split that keeps the condition word but moves
later sentences out of its scope (its documented known limit,
`test_pilot_step1_split_is_not_listed_known_limit`). Only the task reviewer's meaning check covers
that case, so apply this warning yourself.

**"Kept long on purpose" applies to the word budget only.** It records a shortfall against the
word count. It never closes a lost condition: a condition word that the qualifier check lists and
the reviewer resolves as a finding is fixed by restoring the condition in scope.

Upstream source: Matt Pocock, `skills/productivity/writing-for-agents/SKILL.md` @ `49dd158`
(no-op hunt sentence by sentence, delete the whole sentence rather than trim words; branching as
the disclosure test). The condition-word rule is the local addition; upstream has none.

## How to Use

- Run `python3 scripts/audit_skill_prompts.py` to see each skill's word count. The over-ceiling
  message points to this entry.
- Before you delete a sentence, grep it against `tests/` and `hooks/`; a shell test may pin it.
- Name new `references/` files without `prompt`: the audit counts `skills/**/*prompt*.md` as
  companion prompts.
- Review the trim diff with `scripts/check_scope_qualifiers.py --base <base> --head <head>` (also
  emitted as `## Scope qualifiers` in the SDD review package). Resolve each listed word as "kept",
  with a cited HEAD line, or restore it.
- Record any "kept long on purpose" sentences in the spec's `SUMMARY.md`.
