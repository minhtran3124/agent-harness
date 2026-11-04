# recall eval

Prompts and assertions: `plugins/harness/skills/recall/evals/evals.json`. Raw outputs: `runs/<date>/<id>-with-skill.md` and `<id>-baseline.md`.

Command, with the skill (the baseline arm uses the same flags and the bare prompt):

    claude -p --plugin-dir plugins/harness --max-budget-usd 1 --allowedTools=Read,Grep,Glob -- '/harness:recall <prompt>'

Scoring (phrase match, same rule for both arms):

- path: the record path appears anywhere in the output.
- action: at least one `any_of` phrase appears in the output, case-insensitive.
- stale_premise: the record path is under Possibly stale and not under Do first, Avoid or Check before done. With-skill arm only; the baseline has no such sections.

Limits: the prompts and phrases are written by the skill's author, so rates can be biased upward. A phrase match can miss a correct rewrite.
