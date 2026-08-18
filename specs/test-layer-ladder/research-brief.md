# Research Brief — test-layer-ladder

Depth: **Deep** (intake lane high-risk → Deep per `rules/research-depth.md`; no waiver). No
evidence-driven upgrade possible (already at Deep). External surface: **none** — prose-only edits
to three tracked markdown files; no dependency, external system, or version-specific API.

---

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Reuse existing structures — insert three prose blocks into existing sections (approach A of `design.md`) |
| **Why this is the lightest credible path** | The harness already encodes both ladder endpoints; only the ordering prose and a stack-strategy checklist line are missing, and each has one existing home |
| **Confidence** | 90% |
| **Next step** | `writing-plans` — one-wave plan with three single-file tasks and grep-level SC rows |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Meta/harness repo — skills, rules, hooks (no application stack; `techstacks/` is a README-only placeholder) |
| Primary language + runtime | Markdown prose + Bash hooks + Python 3 scripts |
| Frameworks / platforms | Claude Code skill framework (own product) |
| Relevant packages | none (no manifest governs the three target files) |
| Detectable versions | n/a for this change |
| Important constraints | `rules/behavior.md` §2–3 (simplicity, surgical); terminology profile (`git show 8428bae:rules/terminology.md` — not yet on `simplify`); `rules/plan-format.md` is the `artifact-schema-plan` contract surface |

---

## Feature Understanding and Assumptions

- **Requested feature:** Distill two missing pieces of a user-supplied testing philosophy into the
  harness: (1) an explicit verification layer ladder in the plan-format Verify guardrails and the
  implementer prompt; (2) a stack-specific testing-strategy hint in `techstacks/README.md`.
  Wording must follow the previously implemented terminology (STE) profile.
- **What success appears to mean:** The three inserted blocks exist verbatim per `design.md`;
  `bash scripts/run-tests.sh` exits 0; no schema or hook behavior changes.
- **Assumptions from the request:** The user's "có"/"duyệt" approved approach A with the exact
  wording in `design.md` (revised post-review); the ~70% of the prompt already mechanized needs no
  restatement.
- **Assumptions still needing confirmation:** none material — scope was confirmed twice in
  conversation.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `rules/plan-format.md:114-117` Guardrails holds exactly items 1–3; SC "Check" definition at :82-85 already says "never a whole-suite row" |
| `Local` | `skills/subagent-driven-development/implementer-prompt.md:38` — `3. Verify implementation works` occurs exactly once across `skills/`, `scripts/`, `agents/` (spec-reviewer verified); the current wording uses §3-banned `works` |
| `Local` | `techstacks/README.md:33` — `**Testing** — runner, structure, coverage target.` single checklist line, extendable in place |
| `Local` | `scripts/render_skill_prompt.py` CONTEXT_MATRIX requires only the `rules/auto-correct-scope.md` reference inside implementer-prompt.md — the step-3 edit does not touch it |
| `Local` | `evals/skills/prompt-refactor/results/baseline.json` records line/char counts for implementer-prompt.md but is a historical snapshot, already stale (139 recorded vs 141 on disk) — not a live assertion |
| `Local` | `docs/solutions/critical-patterns.md` (verify-row pipe-free/<60s entry) — full suite "cited in prose, never a Verify row": the new guardrail 4 sentence agrees with the KB |
| `Local` | `skills/finishing-a-development-branch/SKILL.md:20` — finish runs "the repository's targeted suite, or the full suite if no safe subset is known"; guardrail wording says "the suite" (not "the full suite") to match |
| `Upstream` | The user-supplied external prompt itself is the upstream pattern being adapted (quoted verbatim in `SUMMARY.md ### Intent`); no repository search beyond it |
| `Docs` | none (local-only; no external surface) |
| `Inference` | Consumers of `artifact-schema-plan` (`render_plan.py`, `check_plan_contract.py`) parse task/SC grammar, not Guardrails prose — grep found no Guardrails parsing; adding item 4 cannot break them |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** the three targets; `scripts/run-tests.sh`
  (doc-truth lint + contract suites); `scripts/ci-strict-gate.sh` (block tier: `hooks/`,
  `settings.json`, `templates/`, `render_plan.py` — none touched; `rules/` + `skills/` covered by
  the warn-mode `workflow-engine` signal instead).
- **Existing abstractions or extension points:** Guardrails is a numbered list (extend to 4); the
  implementer "Your Job" step list; the techstacks starter checklist.
- **Conventions worth preserving:** terse imperative guardrail style; terminology profile §3
  (no vague acceptance terms) and §1 (`verify` = re-runnable proof, `check` = read state);
  4-space indentation inside the implementer prompt block.
- **What can likely be reused:** everything — no new file, no new section heading.
- **What appears missing locally:** only the ladder ordering prose and the stack-strategy line
  (the gap this spec fills).

---

## Upstream Findings

- **Repositories inspected:** none beyond the user-supplied prompt (the direct source being
  adapted). The skills' ancestor repo (obra/superpowers) was not consulted: the change distills
  user-approved wording into local guardrails rather than importing an upstream mechanism.
- **Pattern or capability already present upstream:** the ten-line testing philosophy; the
  gap analysis in `SUMMARY.md ### Intent` maps each line to its harness analog.
- **How closely the upstream pattern matches this repo:** ~70% already mechanized locally
  (Verify <60s, full-suite-at-finish, weakening-validation gate, repeated-failure escalation);
  the two adapted pieces are the remainder.
- **Any upstream gaps or uncertainties:** none load-bearing.

---

## Docs Findings

No external surface — no dependency, integration, or version-specific API. Official-docs search
not applicable.

---

## Recommendation

- **Primary recommendation:** Reuse existing structures (approach A) — three in-place prose
  insertions, wording pinned in `design.md`.
- **Why this is the lightest credible path:** zero new surfaces; every consumer of the touched
  files parses grammar the change does not alter.
- **Why the next-best alternative lost:** a new `rules/test-strategy.md` adds an auto-load/deploy
  surface for ~10 lines; mechanizing the ladder in `verify_summary.py` would gate on a property
  (a command's test layer) that is not machine-decidable from a SUMMARY row.
- **What would change this recommendation:** a decision to make the ladder enforceable — that
  would reopen approach C with a real classifier, out of scope here.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** (1) `rules/plan-format.md` drifts from the deployed `.claude/rules/` copy
  until the user deploys (currently identical; deploy is user-run — never run by the agent).
  (2) Deduplication temptation: guardrail 4's last sentence deliberately repeats the SC "Check"
  definition; `design.md` instructs the implementer not to remove the existing line.
  (3) `workflow-engine` warn-mode gate will print a note at commit — expected, not a block.
- **Evidence gaps:** obra/superpowers not consulted (low impact — source content is user-supplied
  and approved verbatim).
- **Version uncertainties:** none.
- **Follow-up questions for the user:** none.

---

## Source Pack

- **Local files read:** `rules/plan-format.md`, `skills/subagent-driven-development/implementer-prompt.md`,
  `techstacks/README.md`, `skills/finishing-a-development-branch/SKILL.md`,
  `rules/orchestration.md`, `rules/auto-correct-scope.md`, `harness-manifest.json`,
  `scripts/render_skill_prompt.py` (grep), `scripts/check_plan_contract.py` (grep),
  `skills/visual-planner/render_plan.py` (grep), `evals/skills/prompt-refactor/results/baseline.json`,
  `docs/solutions/critical-patterns.md`, `docs/solutions/INDEX.md` (session-loaded),
  `git show 8428bae:rules/terminology.md`, `specs/ste-terminology-evidence/design.md`,
  `specs/intake-lane-check-timing/SUMMARY.md`
- **Upstream repositories or pages checked:** the user-supplied prompt text only (quoted in
  `SUMMARY.md ### Intent`); no external repositories searched
- **Official docs domains or pages checked:** none (local-only; no external surface)

---

## Evidence Boundary

> Confirmed from artifacts: Guardrails list content and position; uniqueness of the step-3
> phrase; CONTEXT_MATRIX requirement for implementer-prompt.md; techstacks Testing line; finish
> skill's targeted-or-full suite wording; terminology profile content (from git history);
> baseline.json staleness.
> Inferred from patterns: no consumer parses Guardrails prose (grep over the named consumers
> returned no such parsing — `not_observed != absent`, but the consumer set is enumerated by
> `harness-manifest.json` `contracts.artifact-schema-plan`, which bounds the search).
> Not checked: obra/superpowers upstream wording; behavior of unreleased branch
> `plan/terminology-artifact-authoring` beyond `rules/terminology.md` content.
