# Design — deliver the terminology profile before research and summary authoring

Approved by the user on 2026-08-13 after choosing the narrow delivery option: load the existing
terminology rule for `research-brief.md` and `SUMMARY.md` authoring without applying §3 to research
prose or rewriting `SUMMARY.md ### Intent`.

## Problem

`rules/terminology.md` is path-scoped. Its `paths:` entries load the rule when an existing
artifact is read, but they do not put the rule into an agent's context before that agent creates a
new artifact. The plan flow closes this gap with an explicit Read in `writing-plans`; the research
and summary authoring flows do not.

This leaves two declared scopes dependent on incidental context:

- `xia2` can write `research-brief.md` without receiving the advisory terminology profile.
- `feature-intake` can write `SUMMARY.md` without receiving §3 before it authors `### Verify`.

## Decision

Add an explicit Read of `rules/terminology.md` to the two source authoring skills and register both
delivery edges in the existing context matrix.

Apply the existing profile exactly as written:

| Artifact section | Applied profile |
| --- | --- |
| `research-brief.md` | §1 terminology consistency is advisory; §3 remains excluded so uncertainty and hedging remain valid |
| `SUMMARY.md ### Verify` | §3 is required: checks state a command-observable result |
| `SUMMARY.md` rationale and alternatives | §1 is advisory; §3 is not required |
| `SUMMARY.md ### Intent` | all terminology rules remain excluded; preserve the user's words verbatim |

The context matrix remains the deterministic authority for delivery. Its existing mutation test
must fail when either new explicit Read disappears.

## Non-goals

- Claiming full ASD-STE100 compliance.
- Applying §3 to research findings, design prose, or `SUMMARY.md ### Intent`.
- Adding a linter, hook, model review, or always-on rule.
- Rewriting existing artifacts retroactively.
- Changing the `PLAN.md` delivery path, which is already covered.

## Risks and controls

- **The explicit Read exists but its applicable subset is unclear.** State the subset beside the
  Read in each authoring skill and keep the canonical definitions in `terminology.md`.
- **A future edit silently removes one delivery edge.** Add both consumers to
  `render_skill_prompt.py`'s context matrix; retain its generic mutation test.
- **Research prose becomes falsely certain.** Keep §3's research exclusion unchanged and mention
  it in the `xia2` instruction.
- **User intent is normalized.** Keep the hard exclusion for `### Intent` unchanged and mention it
  in the `feature-intake` instruction.

