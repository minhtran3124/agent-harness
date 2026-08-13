# Decision — which ASD-STE100 rules earn enforcement in this harness

Status: decided on measurement, 2026-08-13. Supersedes the design sketched in the
shared conversation `claude.ai/share/367af290-6ee1-4a2a-b2db-4a6301ef1df4`.

## Question

That conversation proposed `rules/terminology.md` (a four-section controlled-language rule)
plus `scripts/lint_ste.py` wired into `PostToolUse`. Its central claim was that for prose an
**LLM executes** — unlike prose a human reads — one-concept-one-word is *load-bearing*,
"because the model infers obligation strength from word choice."

That claim was never measured. This repo's own standard (`CLAUDE.md`, "Gate verifiability")
forbids shipping a gate whose value proposition is unverified. So it was measured before
anything was mechanised.

## Method

76 subagent trials, two rounds, ground truth read from the filesystem rather than from any
agent's self-report. Each trial ran in its own sandbox with identical fixtures; **only the
wording of the instruction differed between arms**.

| Hypothesis | Arm A | Arm B | Outcome measured |
| --- | --- | --- | --- |
| H1 §2 modality | `you should <step>` | `you must <step>` | did the file change on disk? |
| H2 §3 acceptance | "verify it is correct" | the observable stated | verdict vs known defect |
| H3 §1 one word | `check`/`verify`/`confirm`/`validate` | `verify` ×4 | accuracy of 4 assertions |

Round 1 fixtures were easy and **every arm scored 100%** — a ceiling, not a result. Round 2
rebuilt each fixture so the naive answer is wrong: the defect is debatable rather than
obvious (H2), the required step conflicts with a stated constraint (H1), and reading the file
cannot answer the question — only running a command can (H3). Round 2 is the result of
record; round 1 is reported because a ceiling is itself evidence about when wording matters.

Primary model Sonnet; H2 re-run on Opus as a generality check. Two-sided Fisher exact.
Reproduce: `specs/ste-terminology-evidence/experiment/` (`setup.sh`, `setup2.sh`, `final.py`).

## Results

```
H1 §2 modality      round 1  should  5/5    must  5/5    p=1.0000   (ceiling)
                    round 2  should 0/10    must 4/10    p=0.0867
H2 §3 acceptance    round 1  vague   5/5    stated 5/5   p=1.0000   (ceiling)
                    round 2  vague   1/8    stated 8/8   p=0.0014   (Sonnet+Opus pooled)
H3 §1 one word      round 1  mixed 20/20    one-verb 16/16          no difference
                    round 2  mixed 20/20    one-verb 20/20          no difference
```

## Decisions

### 1. §3 (machine-decidable acceptance criteria) — ADOPT and enforce

The only rule with a measured effect, and the effect is large and holds on both models.
Under "verify it is correct" reviewers accepted a defective artifact in 7 of 8 runs. Two of
them went further and asserted a property that is **false in the file** — one wrote "unique
sequential ids 1-4" when the column reads 1,3,2,4; an Opus run noticed the disorder and
rationalised it as intentional score-ordering. A vague criterion does not merely fail to
catch the defect, it manufactures a confident false claim about the artifact.

This is the rule the original conversation ranked most valuable on intuition. The intuition
was right; the mechanism it was attributed to was not.

### 2. §1 (one concept, one word) — KEEP AS ADVISORY, DO NOT MECHANISE

Zero measurable effect across 40 assertions per arm at two difficulty levels. The proposal's
central premise does not survive measurement. Keeping §1 as a readability convention is
cheap; building `lint_ste.py`, a `<!-- lint:terms -->` parser, and a `PostToolUse` hook on
top of it would buy a maintenance burden and a gate that proves nothing about behaviour.

The word-frequency table that motivated it (`check` 88 / `verify` 61 / `confirm` 13 /
`validate` 3, `must` 72 / `should` 20, `subagent` 65 / `sub-agent` 3) is real and reproducible
— but variety in that table is not evidence of a behavioural problem.

### 3. §2 (must/should) — DEFINE ONCE, DO NOT TREAT AS A COMPLIANCE LEVER

`must` beat `should` 4/10 vs 0/10 (`p = 0.087`, directional, underpowered). Note what the
other 6 did: they stopped and escalated, citing the conflict. That is the behaviour
`rules/orchestration.md` asks for, so the low compliance rate is not a defect to fix by
strengthening wording. The operational conclusion: **a genuinely mandatory step belongs in a
gate, not in a modal verb.**

Consequently the original proposal's plan to redefine `should` as "skipping requires a
recorded reason" is dropped from this change. It is a policy decision about the harness, not
a vocabulary decision, and it would ride in unexamined under a terminology file.

### 4. `run` vs `session` — TWO CONCEPTS, resolved from the repo

The blocking question from the shared conversation. They are distinct: a *run* is one
workflow pass intake→merge; a *session* is one Claude Code process (`SessionStart` /
`SessionEnd` hooks, `session-knowledge.sh`, `state-breadcrumb.sh`). One run spans several
sessions — which is precisely why `subagent-driven-development resume <slug>` exists.
Collapsing them, as the draft table did, would have made a linter warn on every correct use
of `session`.

### 5. Delivery cannot be `paths:` alone — architectural correction

`paths:` frontmatter injects on **read**, and write-flows do not trigger it (recorded in
`CHANGELOG.md` for v2.1.216, "verified empirically"). Every `paths:` glob in this repo targets
`specs/**`. So the proposed design — a rule path-scoped to `skills/`, `agents/`, `rules/` that
loads "when writing instruction prose" — could not have fired at all in the case it was built
for. §3 reaches a write-flow only through an **explicit Read step** in the consuming skill.

This also reorders the leverage. The highest-value target both analyses agree on is the
`Action:` / `Verify:` fields an LLM writes fresh each run — and a `PostToolUse` linter is the
weakest tool for it, firing after the text exists and only warning. The same rule placed in
`templates/PLAN.template.md` and `skills/writing-plans/SKILL.md` acts at generation time.

### 6. `rules/research-depth.md` — the reported "bug" was a misdiagnosis

The shared conversation flagged this file as falling outside both loading tiers and suggested
adding `paths:` frontmatter. Direct evidence from this session's startup context: it **is**
loaded, with no `paths:` frontmatter and no Read. The mechanism is `paths:` present →
contextual, absent → always-on; `CLAUDE.md`'s hand-maintained list of four had simply drifted
and omitted it. Adding `paths:` would have **removed** a canonical policy file from the
always-on set — a silent behaviour regression with no test to catch it. Fixed as one prose
line in `CLAUDE.md`, which now states the mechanism instead of an enumeration.

## What was deliberately not done

- `scripts/lint_ste.py` — not written. §1 and §2, the sections a term-linter would enforce,
  showed no effect and an unreliable effect respectively. §3 is enforceable but is better
  placed at generation time; a lint for it can follow if §3 adoption shows drift in practice.
- No `PostToolUse` hook wired. Touching `hooks/` is a block-tier `ci-strict-gate.sh` change
  requiring a high-risk SUMMARY with re-running Verify rows; nothing here justifies that yet.
- `specs/**` history untouched. §3 governs prose being written, not closed specs.

## Threats to validity

- n is small (10/arm for H1, 8/arm pooled for H2, 5/arm for H3). H2 is significant; H1 is
  directional only; H3's null is a null at this power, not proof of no effect anywhere.
- Fixtures are synthetic sandbox tasks, not real `PLAN.md` execution. They isolate wording
  cleanly at the cost of realism.
- H3 tested verb choice on *assertions*. It did not test terminology drift across a long
  document, where a reader must resolve whether two words mean the same thing. A null here
  does not license inconsistent vocabulary in a 2,000-word skill.
- Round 1's ceiling means these effects appear only under difficulty or conflict. On easy,
  unambiguous instructions no wording rule tested here changes anything.
