# In-depth synthesis: how should the `brainstorming` skill be improved — and the evidence

> Date: 2026-06-15
> Inputs: `docs/research/harness-review-improvements/2026-06-15-ce-brainstorm-comparison.md` + `docs/research/harness-review-improvements/2026-06-15-superpowers-comparison.md`
> Goal: Filter out the changes that deliver **real effectiveness**, with external evidence (academic + industry) to justify WHETHER we should update and HOW to update.
> Evidence method: 4 purposeful web queries for the 4 most load-bearing claims (anchoring, LLM self-correction, product discovery, cost-of-change). Sources listed at the end. Every structural claim about the 2 skills was checked directly against the text in context.

---

## 0. Evaluation framework

Each proposal is scored on 3 axes: **real value** × **strength of evidence** × **implementation cost/risk**. Only items that win on all three go into Tier 1. Note in particular: the evidence below **reverses an earlier recommendation** (see section 5).

Two foundational facts (established in the 2 prior docs):
- Our `brainstorming` skill is a **fork of superpowers**, already upgraded (subagent review instead of self-review, +xia2, +lane, +docs/solutions). → We are a **superset** of superpowers but **less sophisticated than ce-brainstorm**.
- Our `rules/orchestration.md` says `design.md` scales with signal and the `tiny` lane goes straight to direct edits — **contradicting** the sentence "every project, no exceptions" in the current SKILL.md.

---

## TIER 1 — Strong evidence, high value, SHOULD DO

### 1.1 Bring in the Product Pressure Test (4 gap lenses) — *most novel + strongest evidence*

**Current state:** our skill only says "ask clarifying questions" in a generic way. There is no mechanism for detecting gaps in the product argument.

**Proposal:** add an **internal analysis step (agent self-scan)** before proposing approaches, following ce-brainstorm's 4 lenses: evidence / specificity / counterfactual / attachment. Raise only **real** gaps as open questions, woven into the conversational flow — don't fire them off as a checklist.

**External evidence (strong):** this is not ce-brainstorm's invention — it is **The Mom Test** (Rob Fitzpatrick) automated. The core principles of The Mom Test map almost 1:1 onto the gap lenses:
- *"Ask about past behavior, not hypotheticals"* → **evidence gap** ("the most concrete thing someone has done — paid money, built a workaround?").
- *"How do they currently address the problem? What alternatives have they investigated?"* → **counterfactual gap** ("what do they do today when they hit the problem?").
- *"Past behavior is real; hypothetical answers are mostly unreliable."* → exactly why the probes must ask about what has already happened, not about future opinions.

→ This is a product practice **proven in industry for >10 years**, not a fad. Adoption risk is low (it is just discipline in asking), value is high (it prevents building the wrong thing — the most expensive error). **Verdict: DO IT.**

**How to update (concretely):** add a sub-section under "Ask clarifying questions" in `SKILL.md`:
- Before moving to "Propose approaches", scan the user's opening through the 4 lenses (with 1 sample question per lens).
- Probe only the lenses that are genuinely missing. Probe open-ended (no menu) — because a menu tells the user "which kind of evidence counts".
- Note the source: "based on The Mom Test — ask about past behavior, not hypotheticals."

### 1.2 Make brainstorming lane-aware — *consistency fix + proportionality evidence*

**Current state:** the sentence "Every project goes through this process... regardless of perceived simplicity" directly contradicts `orchestration.md` (tiny lane → direct edit) and the artifact policy (design.md by signal).

**Resolving the contradiction (important — this is not just loosening):** the HARD-GATE ("present the design + get approval before implementing") is a rule **inside** the brainstorming skill. It is `feature-intake` that decides **whether we enter** brainstorming at all. For the `tiny` lane we **do not call brainstorming** → there is no conflict. The problem is the wording "every project regardless of simplicity" — it should become **"every project *worth* brainstorming"**, letting artifact depth + review scale with the lane.

**External evidence:** the effort-risk proportionality principle is backed by **Boehm's cost-of-change** data — requirements defects found late cost 50–200× more than fixing them early. Two-way consequence:
- For **substantial** work: investing in early brainstorm + review is cheap relative to the consequences → keep full ceremony.
- For **tiny** work: consequence cost is low, so heavy ceremony is pure waste → cut it.

*Honest note on the evidence:* Boehm's "100×/200×" figures come from 1970s TRW/IBM waterfall projects and are **disputed** for modern agile (see the Slashdot debate). The **direction** (earlier = cheaper) holds; the **magnitude** should not be quoted as absolute. Use it to justify *proportionality*, not to scare people with a number.

**Verdict: DO IT** (this is both an improvement and a correctness fix to internal consistency).

**How to update (concretely):**
- Top of `SKILL.md`: read `specs/<slug>/SUMMARY.md` → `Lane:` if feature-intake has run.
- Fix the "This Is Too Simple" anti-pattern: the HARD-GATE still applies **once we are inside brainstorming**; but brainstorming should not be invoked for the tiny lane.
- Scaling table: `tiny` → don't enter this skill / short alignment, `design.md` may be dropped; `normal` → current flow + 1 round of subagent review; `high-risk` → full chain + subagent loop up to 5 rounds.

---

## TIER 2 — Strong evidence, moderate effort

### 2.1 Reverse the order: present all approaches FIRST, then recommend (anti-anchoring)

**Current state:** our SKILL.md says *"Lead with your recommended option and explain why"* (inherited from superpowers). ce-brainstorm does the opposite: present-all-then-recommend.

**External evidence (strong, and especially fitting for the AI context):** **anchoring bias** is one of the most firmly established cognitive biases — the first piece of information becomes an "anchor" that distorts subsequent judgment. More importantly: a 2025 study on *AI-assisted decision making* (ScienceDirect) shows that **an AI's recommendation directly anchors human judgment** — exactly our scenario (an agent giving a recommendation to a user). Leading with the recommendation = setting the anchor before the user has had a chance to weigh the options.

**Verdict: DO IT** — the cheapest change (a wording fix), strong evidence, matching the AI-gives-recommendation context. This is one of the rare points where ce-brainstorm beats both us and the original superpowers.

**How to update:** change 2 places in `SKILL.md`:
- "Exploring approaches": *"Present all approaches and their trade-offs first; give your recommendation only after the user has seen the full set."*
- Key Principles: drop "Lead with your recommended option", add "Present-then-recommend (avoid anchoring)".

### 2.2 A scope-synthesis checkpoint before writing `design.md`

**Current state:** we approve the design **section by section** (step 5) and then write the doc. There is no "zoom out — confirm the whole picture" step.

**ce-brainstorm's insight:** *approving each piece ≠ approving the whole*. After a one-question-at-a-time dialogue, the user has agreed to many disconnected things but has never seen the assembled picture — where the **non-obvious consequences** of combining the answers surface.

**External evidence:** Boehm cost-of-change again — this checkpoint catches *scope/requirements* errors **before** the doc drops into `writing-plans`/implementation, i.e. at the cheapest point on the cost curve.

**Realistic assessment:** since we **already have** section-by-section approval, the incremental value concentrates in the 2 parts ce-brainstorm has and we lack: (a) **integration check** — actively combining the answers to expose consequences; (b) **call-outs** — naming the "scope bets" for the user to confirm or redirect. The "restate everything" part partially overlaps with section approval.

**Verdict: DO A TRIMMED VERSION** — add a short whole-picture confirmation step (not lifting ce-brainstorm's entire 2-stage/Path A/B/soft-cut machinery — too heavy for us). Focus: integration check + 1–3 call-outs before writing the doc.

**How to update:** add a step 5.5 between "Present design" and "Write design doc": *"Before writing, assemble the decisions and state (1) the overall shape in 1–3 sentences, (2) 0–3 call-outs that are non-obvious consequences/scope bets. Wait for confirmation, then write."*

---

## TIER 3 — Evidence that REVERSES an earlier recommendation

### 3.1 ⚠️ Do NOT use superpowers' self-review for the lightweight tier — counter-evidence

**OLD recommendation (in the superpowers doc):** "use superpowers' lightweight self-review for tiny/Lightweight, keep the subagent loop for normal/high-risk."

**Evidence that makes me PARTIALLY RETRACT this recommendation:** Huang et al., *"Large Language Models Cannot Self-Correct Reasoning Yet"* (ICLR 2024) — an LLM **correcting itself without external feedback** usually does not improve, and **sometimes gets worse** after self-correction. Self-review (an agent re-reading the spec it just wrote) is precisely the intrinsic self-correction scenario this paper warns about.

→ Consequence: **our independent subagent review is the CORRECT, evidence-backed choice** (subagent = "external feedback"). We should not downgrade to self-review just to save cost, even for small work — because self-review is exactly the weakest setting.

**Balanced nuance (don't absolutize):**
- A more recent paper (*Self-Correct with Key Condition Verification*, EMNLP 2024) shows self-correction **CAN** work with the right prompting method. So this is not "self-review is always useless".
- Importantly: self-review in a **verification-checklist style** (scanning for TBD/placeholders, contradictions, correct scope) is closer to *verification* than to *reasoning self-correction* — far lower risk. Scanning for placeholders is not "self-correcting reasoning".

**Verdict (recalibrated):** For light lanes, do **not** drop independent review in favor of an agent self-critiquing its own reasoning. If a cheap tier is needed, either (a) use a **mechanical self-verification checklist** (TBD/placeholder/contradiction — safe) OR (b) use an **independent subagent for 1 round** (cheaper than the full loop but still external feedback). Keep the full subagent loop for high-risk. → This is an example of external evidence directly correcting the design.

---

## NOT prioritized (low value for our context)

- **HTML output / non-software routing / CONCEPTS.md vocab capture** (from ce-brainstorm): we are an internal FastAPI repo; these features cost maintenance effort and deliver little value.
- **Resume detection for brainstorm** (Phase 0.1): useful but marginal; defer.
- **ce-brainstorm's full section-catalog prose economy:** worth referencing for `spec-document-reviewer-prompt.md`, no need to lift it wholesale.

---

## Proposed roadmap (ordered by ROI)

| # | Change | Evidence | Cost | Risk |
|---|---|---|---|---|
| 1 | Anti-anchoring: present-then-recommend | Anchoring bias + AI-anchoring study (strong) | Very low (wording fix) | Very low |
| 2 | Lane-aware + fix the "every project" contradiction | Boehm proportionality + internal consistency | Low | Low |
| 3 | Product Pressure Test (4 gap lenses) | The Mom Test (industry-proven) | Medium | Low |
| 4 | Trimmed synthesis checkpoint (integration check + call-outs) | Boehm cost-of-change | Medium | Low |
| 5 | Keep independent review; do NOT downgrade to self-review | LLM-cannot-self-correct (ICLR'24) | 0 (already correct) | — |

**Overall recommendation:** do #1 and #2 first (cheap, partly a correctness fix), then #3 (highest value), then #4. #5 is a confirmation to keep the current design as-is (don't "optimize" in the wrong direction).

Any change touching `skills/brainstorming/SKILL.md` (core skill, high risk per the rules) → must go through feature-intake + a plan before editing.

---

## Sources

- Anchoring bias (overview + AI context): [The Decision Lab](https://thedecisionlab.com/biases/anchoring-bias), [EBSCO Research Starters](https://www.ebsco.com/research-starters/social-sciences-and-humanities/anchoring-cognitive-bias), [ScienceDirect — anchoring in AI-assisted decision making (2025)](https://www.sciencedirect.com/science/article/pii/S0268401225000076)
- LLM self-correction: [Huang et al., "LLMs Cannot Self-Correct Reasoning Yet", ICLR 2024 (arXiv:2310.01798)](https://arxiv.org/abs/2310.01798); conditional counterpoint: [Self-Correct with Key Condition Verification, EMNLP 2024 (arXiv:2405.14092)](https://arxiv.org/pdf/2405.14092)
- Product discovery / asking about past behavior: [The Mom Test — mtlynch.io review](https://mtlynch.io/book-reports/the-mom-test/), [UXtweak — What Is the Mom Test](https://blog.uxtweak.com/the-mom-test/), [3 Rules to Customer Interviews](https://www.atlantaventures.com/blog/the-3-rules-to-customer-interviews-from-the-mom-test)
- Cost-of-change (Boehm) + the debate over magnitude: [Steve McConnell — An Ounce of Prevention](https://stevemcconnell.com/articles/an-ounce-of-prevention/), [DZone — Real Cost of Change](https://dzone.com/articles/real-cost-change-software), [Slashdot — Do Late Bugs Really Cost More?](https://developers.slashdot.org/story/03/10/21/0141215/software-defects---do-late-bugs-really-cost-more)
