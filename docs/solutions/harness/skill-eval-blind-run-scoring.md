---
problem_type: knowledge
module: evals / scripts/score_intake_eval.py
tags: skill-eval, workflow-eval, blind-run, deterministic-scorer, claim-discipline, non-determinism, hard-gate-respect, answer-key, llm-as-judge
severity: critical
applicable_when: Building or extending a behavioral eval for a prompt-driven skill or workflow stage (feature-intake, correctness-review, …) — anything where "prove it works" means measuring LLM judgment, not a green unit-test.
affects:
  - evals/
  - scripts/score_intake_eval.py
supersedes: null
confidence: high
confirmed_at: 2026-07-17
---
## Applicable When

You want to *prove a prompt-driven skill classifies/judges correctly*. Unit tests can't — the
output is non-deterministic LLM judgment. Use this playbook (it built `evals/workflow/intake-classifier`).

## Pattern

**Auto-score / manual-run**, mirroring `evals/skills/review-chain`:

1. **Labeled fixtures** — `fixtures/<name>/{request.md, truth.md}`. `truth.md` = a parseable
   `key: value` header the scorer reads + prose. Support an `any` value for dimensions a fixture
   does not assert (e.g. lane on an ambiguity fixture — score only confidence/escalate there).
2. **Blind runs** — dispatch one subagent per fixture given ONLY `request.md` + the skill,
   **never `truth.md`**. The orchestrator authored the answer key, so a non-blind run makes the
   number meaningless. This is the single most important integrity rule.
3. **Deterministic scorer** (`scripts/score_intake_eval.py`, unit-tested) — pure Python, no LLM,
   no key. Parses the emitted header, compares to `truth.md`, prints a scorecard. Runs free/local;
   only the run step costs tokens.
4. **Separate the safety-critical dimension from judgment dimensions.** Report a headline per
   dimension, and make the non-negotiable one a hard fail: here `--strict` exits non-zero if any
   hard-gate fixture is classified below `high-risk`. Lane/confidence accuracy can wobble; gate
   respect must be 100%.
5. **Multi-run.** One run hides borderline non-determinism. Four blind runs showed hard-gate
   respect 3/3 every time (stable) while one lane-boundary fixture flipped tiny↔normal (3/4 tiny)
   — a real skill finding only a multi-run reveals.

## How to Use

Score command: `python3 scripts/score_intake_eval.py --run <run_dir> [--strict]`. In Claude Code,
"run the eval" = the orchestrator dispatches the blind subagents (uses the session's quota, no API
key); a standalone/CI runner would need `ANTHROPIC_API_KEY` and is deliberately not built (LLM in
CI = token cost + flaky). Record each run under `results/<date>-<label>/`; the first scored run is
the record (honesty rule — don't re-run a fixture until it passes).

## Gotchas

- **Scorer must normalize LLM free-text.** The skill emits its *own* canonical spelling (the flag
  table's `Data model`, with a space) while your key may use `data-model` (hyphen). Compare on
  alphanumerics only (`re.sub(r"[^a-z0-9]", "", s.lower())`) or a correct classification scores as
  a false miss. This shipped as a real false-INCORRECT before the fix.
- **When N blind runs consistently disagree with a fixture, suspect the answer key, not the skill.**
  Three independent runs all called `multi-domain` normal; the key's "4+ flags → high-risk" was too
  aggressive. Revise `truth.md`, note the revision, mark prior runs non-comparable — do not tune the
  skill to a wrong key. (Contrast: a fixture that *leans* one way but the literal rule supports the
  key is a genuine skill finding, e.g. intake under-counting an added test file toward the `≤1 file`
  tiny bar — keep the key, record the finding.)
- **Claim discipline:** a number is a claim about *these fixtures and this skill only* — not the
  full chain, not real-world rate (`not_observed != absent`). State it wherever the number appears.

## Related
- evals/README.md
- docs/solutions/harness/automation-readiness.md
- docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md
