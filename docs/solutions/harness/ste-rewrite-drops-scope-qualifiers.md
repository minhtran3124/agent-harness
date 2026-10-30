---
problem_type: failure
module: skills/*/SKILL.md, rules/*.md, agents/*.md (agent-executed prose under an STE rewrite)
tags: [ste100, prose-rewrite, scope-qualifier, sentence-split, word-ceiling, meaning-equivalence, green-is-not-correct, review-oracle]
severity: critical
applicable_when: You rewrite agent-executed prose (a skill, rule, agent or dispatch prompt) for style, for example with the asd-ste100 skill, and the rewrite splits long sentences or cuts words to fit the 600-word skill ceiling.
affects:
  - skills/feature-intake/SKILL.md
  - skills/subagent-driven-development/SKILL.md
  - rules/orchestration.md
supersedes: null
confidence: high
confirmed_at: 2026-10-15
---
## Applicable When

You rewrite agent-executed prose for style, for example with `skills/asd-ste100/SKILL.md`. The
rewrite splits long sentences into short ones, or it cuts words to fit the 600-word ceiling that
`scripts/audit_skill_prompts.py` sets for each `SKILL.md`.

## Symptom

The rewrite reads well and every test passes. The agent that reads the new text will do a
different thing. In the ste100-harness-prose pilot this happened twice in one task (Task 2.2):

- `skills/feature-intake/SKILL.md` Step 1. The original was one sentence: "Read intent.md if
  present: stop unless …; pin with … (empty: stop); if `git diff …` is non-zero, stop; ask the user
  to commit it." The rewrite split it into short sentences. Only the first sentence kept "if
  present". "Pin with … (empty: stop)" became unconditional, so intake would stop on every legacy
  slug that has no intent.md. "Ask the user to commit it" also moved out of the non-zero branch.
- `skills/feature-intake/SKILL.md` Step 6. The file was at 599 of 600 words. A fix round cut
  "For a new SUMMARY, write it from" to "Write a new SUMMARY from". The condition went away, so on a
  legacy slug the step reads as an order to overwrite the existing SUMMARY.

## Wrong Approach

The rewrite treated a colon, a semicolon or a leading phrase as style. It split or cut them to
lower the STE lint count. The proof of "no behavior change" was the test suite plus the lint count.

## Why It Failed

- In instruction prose, a colon or a semicolon often carries scope. "X if present: A; B; C" means
  that A, B and C all depend on the condition. Split the sentence, and only A keeps the condition.
- A leading phrase such as "For a new SUMMARY" is a condition, not filler. A word cut to meet a
  ceiling removes the cheapest words, and condition words are cheap.
- Tests match literal strings and file shape. They do not check which steps are conditional. All
  the SDD, run-state and propagation tests passed on both broken versions.
- The STE lint count went down on both broken versions. A lower count does not mean the meaning
  stayed the same.

## Correct Approach

- Give every rewritten file an independent meaning-equivalence review that compares each removed
  line with its replacement. Ask for dropped conditions, exceptions, hedges and scope qualifiers.
  The task reviewer caught both drops, but only because the Task 2.2 brief asked for this review
  (`specs/ste100-harness-prose/PLAN.md` Task 2.2). The task-reviewer prompt does not run it on its
  own, so every rewrite plan must ask for it again.
- When you split "X if present: A; B; C", repeat the scope on each part, or keep one lead sentence
  that names the scope for all parts. For example: "If intent.md exists, run these checks. Stop
  unless … Pin with … If `git diff …` is non-zero, stop and ask the user to commit it."
- Do not cut a condition word to meet the word ceiling. If the file is at the ceiling, keep the
  hardest sentences in their original form and list them as "kept long on purpose". A skill at the
  ceiling leaves an STE rewrite no room for scope words.
- Measure comprehension after the rewrite, as the pilot did with probes and real classification
  runs (`specs/ste100-harness-prose/DECISION.md`). The pilot found no measured loss only after the
  two drops were fixed.

## Guardrail

proposed: `scripts/check_scope_qualifiers.py` reads a BASE..HEAD diff of prose files and lists each
condition word (if, unless, only, when, never, except, for a new, without) that a removed line had
and that no added line in the same hunk has. Add its output to the review package as an advisory
section beside `## STE lint`, so the task reviewer sees each candidate drop.

proposed: add a meaning-equivalence instruction for changed prose files to `skills/subagent-driven-development/task-reviewer-prompt.md` (spec verdict), so the review runs on every prose task without a plan having to ask for it. Today it runs only when the task brief requests it.

## Related

- docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md
- docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md
- docs/research/ste-terminology-evidence/DECISION.md
- specs/ste100-harness-prose/DECISION.md
