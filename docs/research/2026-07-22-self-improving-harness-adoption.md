# Deep Research — Applying the "Self-Improving Harness" to harness-skills

> Date: 2026-07-22 · Question: how should a governance/harness repo (skills + hooks + rules + evals)
> apply "self-improving harness" techniques, and what does the strongest current evidence say
> about doing it **safely**?
>
> Method: deep-research workflow — 5 parallel search directions → fetch 22 sources → extract 110
> claims → adversarial verify (3 votes/claim, 2/3 refuting votes required to reject). Result: **19 claims
> confirmed (mostly 3-0), 0 refuted, 6 found but not yet verified** (the workflow was cut off at the
> synthesize step + 6 verifies due to session limit — 1:20pm Asia/Saigon). This synthesis was hand-written
> by the main thread from the 19 verified claims; the 6 unverified claims are **clearly labeled** and are not
> used as decision support.
>
> **Update (second harvest):** the workflow extracted **110 claims** but only verified the top 25; the ~85
> remaining claims sat in the journal, uncollected at first writing. **Section 6** gathers the high-value
> *central* claims that were missed — including *contrary* evidence that nuances the small-n story (section 3)
> and two claims that match the repo's internal learnings. All of section 6 is single-source extraction,
> **not put through 3-vote verification**.

---

## TL;DR

- **Self-Harness's 3-stage loop is real and matches** the repo's gap analysis: Weakness
  Mining → K minimal, diverse proposals → conservative acceptance gate. But one number in my initial
  grounding was **exaggerated**: the paper reports **+34% to +60% relative on
  held-out** (40.5→61.9, 23.8→38.1, 42.9→57.1%), **not "+16–138%"**.
- **Most important safety finding:** the paper's acceptance rule (`Δ_in ≥ 0 AND Δ_ho ≥ 0 AND
  max > 0` — *non-regression* only) is **insufficient when the fixture count is small**. Three independent sources
  (PAC-learnability, significance-gate, Anthropic error-bars) all say: at small n, a non-regression gate
  **cannot distinguish a real improvement from noise**. This is the heaviest correction for proposal #3.
- **Re-ranking the 8 proposals:** (2)+(1)+(5)+(6) are the cheap foundation and survive → do them first. (4) is a *precondition*
  of (3) and must come first. (3) survives **conditionally** (needs margin + power analysis, not
  non-regression). (7) survives but is costly — do it later. (8) is **not applicable (not yet a fit)** for the nature of this repo.

---

## 1. Re-reading the original paper (arXiv 2606.09498) — verified

| # | Claim (verified) | Vote | Source |
|---|---|---|---|
| 1 | 3-stage loop: Weakness Mining (mining per-model failure patterns from traces) → Harness Proposal (*diverse but minimal* modifications tied to the failure) → Proposal Validation (accept only after regression testing) | 3-0 | arxiv.org/abs/2606.09498 |
| 2 | **Held-out results**: MiniMax M2.5 40.5→61.9%, Qwen3.5-35B-A3B 23.8→38.1%, GLM-5 42.9→57.1% (≈ +34% to +60% relative). **Narrower than the "+16–138%"** in the grounding. | 3-0 | arxiv.org/abs/2606.09498 |
| 3 | The loop runs **with no human engineer and no stronger external model** — the same agent improves its own harness. | 3-0 | arxiv.org/abs/2606.09498 |
| 4 | **The failure signature is a deterministic 3-component tuple**: `φ(rᵢ)=(cᵢ, qᵢ, mᵢ)` = (cause at the verifier layer, causal state of the agent's behavior, abstract agent mechanism). Clustering is by **exact agreement**, not semantic similarity. | 3-0 | arxiv.org/html/2606.09498v1 |
| 5 | **The editable surface is declared in code** via config functions in **a single harness definition file** (`build_system_prompt()`, `build_bootstrap_instruction()`, `build_runtime_control_policy()`); the optimizer **may only edit that file**. | 3-0 | arxiv.org/html/2606.09498v1 |
| 6 | **Exact acceptance gate**: accept only when `Δ_in ≥ 0 AND Δ_ho ≥ 0 AND max(Δ_in, Δ_ho) > 0` (no split regresses, at least one strictly improves). | 3-0 | arxiv.org/html/2606.09498v1 |
| 7 | The proposer generates **K mutually diverse, minimal proposal bundles**, each targeting a specific failure mechanism, without rewriting the architecture. | 3-0 | huggingface.co/papers/2606.09498 |
| 8 | Weakness Mining clusters by **verifier-grounded signature**, *specifically to avoid conflating surface symptoms with reusable mechanisms*. | 3-0 | huggingface.co/papers/2606.09498 |
| 9 | **Limitations stated by the authors themselves**: this is only *bounded edits under fixed benchmarks*, not open-ended self-improvement; edits may be benchmark-specific; it depends on verifier/trace quality; **"higher-stakes harness changes would require stronger acceptance gates than pass-rate non-regression alone."** | 3-0 | arxiv.org/html/2606.09498v1 |

**Reading:** The paper's structure is solid. But the authors themselves (claim #9) warned that their gate is only
sufficient for low-risk changes — exactly the thing I need to be careful about, because in my repo I edit **rules/hooks/skills**
(higher risk than "rearranging the system prompt of a terminal agent").

---

## 2. Adjacent literature — corroboration & contradiction (verified)

**Supporting the reflect-propose-test loop:**

- **GEPA** (arxiv 2507.19457): reflecting in *natural language* over traces (reasoning, tool calls,
  outputs) is a *richer* learning signal than a sparse scalar reward. GEPA **beats the RL baseline GRPO by +6% on
  average (up to +20%) with up to 35× fewer rollouts** — highly relevant for a repo with few fixtures and a small
  eval budget. Key point: GEPA avoids premature convergence **not via a single accept/reject gate**, but
  by **keeping and combining a Pareto frontier of diverse candidates** → direct support for proposal #7
  (K-candidate) over a single accept. (3-0)
- **DGM / Darwin-Gödel Machine** (arxiv 2505.22954): the agent edits its own code, **gated by
  empirical benchmarks** (not formal proof), raising SWE-bench 20.0→50.0%, Polyglot
  14.2→30.7%. "Proving that a change is net-beneficial is practically infeasible" → the eval-gate is
  the pragmatic substitute. DGM also shows that an **archive/lineage tree of diverse agents** beats both
  no-self-improvement and greedy hill-climbing → supports #5 (lineage) and #7 (diversity). (3-0, except the
  claim "eval-gate substitutes for proof", which was 2-1)

**On deterministic vs semantic signatures (a CONTESTED point):**

- Supporting deterministic-by-mechanism: a practitioner source (latitude.so) describes "error signature
  clustering + behavioral pattern + quality score" — grouping by shared signature instead of triaging
  each case. Another source (2606.14589) argues that **classifying by *mechanism* (how the failure evades observation)
  matters more than by *location* (which job/file broke)**: location-based classes have "no predictive or
  defensive value", while a mechanism-layer defense "immunizes every location at once".
- Supporting semantic/bottom-up: **MAST** (arxiv 2503.13657) and langfuse use **Grounded-Theory open
  coding** — read traces, take free-form notes, let the failures define their own categories (MAST derived 14 failure modes
  from 150 traces, validated on 1600+). This is *qualitative* clustering, not deterministic
  signature matching.

  → **Pragmatic conclusion** (not "deterministic beats semantic"): what **both camps agree on** is *cluster
  by MECHANISM, not by surface symptom*. A deterministic tuple is the cheap, auditable way to *start*;
  semantic open-coding is the way to *discover* new signatures when the rigid tuple misses them. For my repo, the deterministic
  tuple fits better because I already have verifier-grounded signals on hand (hook fired, gate result, exit
  of a Verify row) — that is exactly the paper's `cᵢ`.

---

## 3. Adversarial on the load-bearing claim: does a non-regression gate resist overfitting at small n?

This is the make-or-break question for my repo (evals/ has only a handful of fixtures). The evidence:

- **VERIFIED (3-0):** PAC-learnability under self-modification (arxiv 2510.04399) — distribution-free
  guarantees are preserved **iff** the family of reachable models is uniformly capacity-bounded (VC dimension); if
  capacity inflates without bound, **self-changes that are "reasonable by utility" can turn a learnable task into
  an unlearnable one**. And: a **safe gate needs BOTH** — validation improvement *beyond a strictly positive margin
  τ* (not just Δ≥0) **AND** a capacity cap `K[m]`; under this Two-Gate rule each accepted edit
  *reduces true risk by at least τ*. → **Self-Harness's gate (only Δ≥0, no margin, no cap) is below
  the safety threshold the theory demands.**

- **FOUND BUT NOT YET VERIFIED** (session limit cut off the 3 votes — not refuted; re-read before
  relying on them):
  - `εV ≍ sqrt((K[m] + log(1/δV))/nᵥ)`: with a small held-out set (small nᵥ — few fixtures), **the detectable
    improvement threshold is large**; at small n a non-regression gate *cannot distinguish a real improvement from
    noise*; margin τ bounds the total number of accepted edits to ≤ `(R[h0]−R*)/τ`. (arxiv 2510.04399)
  - A conservative gate needs a **statistical significance criterion**, not just non-regression: one paper requires a **paired
    2σ test on a sealed test set**; at **n=26 (SWE-bench) a +5.1pp lift is NOT significant** → a direct
    implication: my small fixture count is **below the threshold for a meaningful gate**. (arxiv 2607.13683)
  - A held-out set is only reusable across multiple edits **if the reference family + every threshold (K, εV, τ)
    are fixed BEFORE looking at the validation data**; tuning anything on it → you need a new split or a
    reusable-holdout scheme. (arxiv 2510.04399)
  - "Untouchable kernel": the harness declares a mutable surface (prompt/knowledge/runtime/config) vs an
    **inviolable kernel (the measurement code, the evolution machinery)** — add a rule: **eval/scoring code must live
    OUTSIDE the editable surface**. (arxiv 2607.13683)
  - SkillOpt (arxiv 2605.23904): accept a skill-document edit only on a *strict improvement* on
    held-out — stricter than non-regression.

- **Additional corroboration** (Anthropic, "Adding Error Bars to Evals", arxiv 2411.00640, from search):
  treat an eval as an *experiment*, use **power analysis to compute the minimum number of questions** needed to detect a
  real difference, plus a paired-difference test. This is precisely the quantitative tool for "how many fixtures do I need".

**Section 3 conclusion:** The evidence converges strongly (one verified 3-0 claim + three independent sources not yet
verified but pointing the same way) that **non-regression at small n is a fake gate**. If I port Self-Harness's gate
over as-is with a handful of fixtures, I will *accept noise as if it were improvement*. This is not a reason
to drop proposal #3 — it is a reason to **fix it**: add a margin τ, run a power analysis to learn how many
fixtures are needed, fix thresholds before looking at the data, and until there are enough fixtures, **the eval is advisory, not
blocking**.

---

## 4. Re-scoring the 8 proposals — a grounded priority order

Notation: **Survives** / **Survives conditionally** / **Not applicable (not yet a fit)**. Effort = relative effort.

| # | Proposal | Verdict | Effort | Basis |
|---|---|---|---|---|
| 2 | Mechanical consumer for `Harness-Delta` | **Survives** | Low | Pure plumbing; it is the *sensor* that feeds everything downstream. A field with no consumer today will degrade to `none`. |
| 1 | Cross-session failure clustering by deterministic signature | **Survives** (cluster by *mechanism*) | Medium | Claims #4, #8 + latitude.so + 2606.14589. Uses the verifier-grounded signals I already have (hook/gate/exit). |
| 5 | Harness lineage record (surface changed + split results + rationale) | **Survives** | Low | The DGM archive beats greedy (3-0 claim). Cheap; makes every harness change recorded/reversible. |
| 6 | Manifest declaring the editable surface | **Survives** (add: eval/scoring = inviolable kernel) | Low | Claim #5 + "untouchable kernel" (2607.13683). In my repo this boundary is currently *implicit* via resync-protected-files. |
| 4 | Mine new eval fixtures from real failures, with held-in/held-out discipline | **Survives** — and is a **precondition of #3** | Medium | Without enough fixtures #3 is meaningless (section 3). Elevate it ahead of #3. |
| 3 | Eval-as-acceptance-gate with a conservative rule | **Survives CONDITIONALLY** | High | Non-regression Δ≥0 **is not enough at small n**. Requires: (a) a strictly positive margin τ, (b) power analysis for minimum n, (c) fixing thresholds before looking at the data, (d) advisory not blocking until n is sufficient. |
| 7 | A batch of K diverse proposals, letting the eval choose | **Survives** | High | GEPA (Pareto) + DGM (archive). But only worth doing *after* the #1→#3 loop exists. |
| 8 | Runtime-policy edits (loop-breaking, artifact-first) as a surface | **Not applicable (not yet a fit)** | High | The paper's runtime-policy wins are about a *terminal agent with a tool loop to police*. My repo is governance/skills, with no equivalent runtime loop. The analogy is thin; defer. The closest thing already exists: "in-flight escalation checks" in rules/orchestration.md. |

### Proposal rollout order

1. **Wave 1 — Sensors & bookkeeping (cheap, no risk):** #2 (consumer for Harness-Delta) + #5
   (lineage record) + #6 (editable-surface manifest, including the eval-code-is-inviolable rule). These three are
   purely additive and touch no decision path.
2. **Wave 2 — Mining:** #1 (cluster failures by mechanism from the ledger + SUMMARY) and #4 (turn every cluster
   above the threshold into a fixture candidate, keeping splits fixed). #4 runs in parallel because it *feeds* #3.
3. **Wave 3 — Gate (only once there are enough fixtures):** #3, but in its corrected form — advisory first, blocking only
   when the power analysis says n is enough for margin τ to be meaningful. Below that threshold, the gate only *reports* deltas.
4. **Wave 4 — Advanced:** #7 (K-candidate + Pareto) once the loop is stable. #8 goes to the backlog, not done yet.

---

## 5. Corrections to remember versus the preliminary gap analysis

1. **Fix the number:** use "+34–60% relative held-out" when citing Self-Harness, not "+16–138%".
2. **The paper's gate is a floor, not a standard:** the authors themselves (claim #9) + PAC (3-0 claim) say
   non-regression is not enough for high-risk changes. Editing my rules/hooks/skills *is* higher risk
   than the paper's example.
3. **New constraint for #6:** eval/scorer/hard-gate must be an *inviolable kernel*, separated from the surface that
   automated proposals are allowed to touch — otherwise self-modification can "fix" the measuring stick itself.
4. **#4 comes before #3:** without enough fixtures the gate is a safety illusion. This matches the existing learning
   `skill-eval-blind-run-scoring` and the warning `unverified-premise-propagates`.
5. **Deterministic vs semantic clustering is not a win-lose fight:** the common ground is *cluster by
   mechanism*. Start deterministic (cheap, auditable), and use semantic open-coding periodically to detect
   signatures the rigid tuple misses.

---

## 6. Addendum — second harvest: central claims extracted but NOT put through 3-vote verification

> Process transparency: the workflow extracted **110 claims** from 22 sources but only put the **top 25 into
> adversarial verify** (19 confirmed). The ~85 remaining claims sat unharvested in the journal. This section
> gathers the high-value *central* claims missed at first writing. **This entire section is single-source
> extraction, NOT put through 3-vote verification** — use it as direction, and read the original sources before relying on specific numbers.

### 6a. Small-n is NOT "always broken" — an important nuance missing from section 3

Section 3 leans toward "non-regression at small n is a fake gate". The second harvest provides **contrary evidence** that forces
a softening:

- **Held-out gates DO work against overfitting in practice** (arXiv 2607.13683): sealed-test retention of
  **86–147%** across 6 domains, with gains of +9 to +15.5pp *all exceeding the paired-2σ threshold* → real generalization, not
  overfitting. But in the same paper: the 7th domain (SWE-bench) had **+5.1pp at n=26, NOT significant**.
- **GEPA (gepa-ai FAQ): improvement is possible with as few as 3 examples** — "+9% on held-out with only 3 examples
  in a single iteration". And guidance on splitting by data size: **80/20 when >200 points, 50/50 when <200**
  (at small n the validation half must be *proportionally larger*).

→ **Corrected conclusion:** the problem is not "small n always fails", but **"small n + a bare non-regression
threshold (`Δ≥0`) = a decision dominated by noise"**. The fix is not to drop the gate but: (1) a stricter threshold
(one source measured a noise band of ±0.02–0.04 and suggests a threshold of ~+0.02), (2) a paired-difference test +
significance (Anthropic 2411.00640: paired diff is "free variance reduction"), (3) a proportionally larger validation split
at small n, (4) plateau-aware stopping. This is the concrete upgrade for proposal #3.

### 6b. Quantitative evidence on "how many fixtures are needed" (for #3/#4)

- **Anthropic (2411.00640):** "New evals should contain **at least 1,000 questions** in order to have
  good signaling ability" → a `Δ_in≥0 AND Δ_ho≥0` gate over a handful of fixtures is **underpowered**, with decisions
  dominated by noise. Comes with a concrete prescription: CLT standard errors, clustered SE, question-level paired
  diff, power analysis.
- **Empirical example (CONFIRM-gate source):** one run with in-sample +0.18 **collapsed to +0.04 on held-out**;
  a `confirm_delta ≥ 0.0` threshold is too loose at a high baseline → it keeps promoting within-noise changes (+0.01, +0.00),
  dragging the state from a peak of +0.09 back to +0.01. With 50 in-sample questions showing 6–21 failures → "genuine small-sample
  variance"; an n=100 held-out set had splits failing to reach p<0.05; **reusing the same held-out set across successive
  promotions inflates Type-I error**. → a *third fully-withheld split* is needed; do not reuse validation.
- **Reward-model overoptimization / Goodhart** (arXiv 2210.10760, Gao et al): optimizing against a proxy makes the
  proxy-score rise monotonically while the **gold-score rises then falls**; below ~2,000 comparisons the proxy is "nearly
  useless"; **a weak/small evaluator makes Goodhart worse** (β decreases as the RM gets larger). The antidote:
  **periodically retraining/refreshing the proxy** improves gold-score by ~`β·d·log(k)` over k rounds → supports #4 (periodically mining
  new fixtures) rather than gating forever on one fixed set.

### 6c. Two claims matching the repo's INTERNAL learnings (external validation)

- **"Ratchet discipline"** (addyosmani blog): *"every line in a good AGENTS.md should be traceable back
  to a specific thing that went wrong"* — an **exact match** for the repo's `improvement-backlog.md` ratchet
  mechanism. External confirmation that the direction is right.
- **A gate that fails silently must be sabotage-validated:** *"67 governance checks executed empty strings
  (vacuous passes) for months"* because the code read from a misnamed YAML field, only exposed when a sabotage-validation
  refused to fail. Plus: *"point fix → meta-rule → mechanized scanner; a lesson that stops at the point-fix recurs
  within days"*. → an **exact match** for the learning `mutation-testing-proves-a-suite-is-load-bearing` and the repo's
  `/compound` philosophy. A direct implication for #3: **the self-improving loop's acceptance gate must also be
  fault-injected to prove it knows how to reject** — otherwise we get a falsely-green gate like those 67 checks.
- **The eval suite does NOT discover new weaknesses** (same source): an audit of 15 incidents → declarative governance had
  **0% ex-ante prevention but 87% ex-post regression-blocking** — "audits are regression engines, not
  prediction engines". → reinforces #4: **mining must come from production traces, not from the eval suite**; the eval
  gate only *locks in* known lessons, it does not *discover* new weaknesses.

### 6d. Minimal-edit design (for #7)

- **"Textual learning rate" — a bounded edit budget** (SkillOpt/2605.23904 area source): limiting the number of edits
  per step *beats* free-form rewriting, because "unbounded rewrites erase useful rules... overfit to a local
  failure". → concrete grounding for #7's "K minimal edits" instead of free self-revision.
- **Cluster by minibatch, not by single trajectory:** "single trajectories produce anecdotal
  fixes; minibatches expose reusable procedural errors" → reinforces #1 (cluster cross-session, do not
  patch each incident individually).

---

## Sources (fetched; primary quality unless noted otherwise)

- arXiv 2606.09498 (abs + html) — Self-Harness (primary source)
- huggingface.co/papers/2606.09498 — mirror/metadata
- arXiv 2507.19457 — GEPA: Reflective Prompt Evolution
- arXiv 2505.22954 — Darwin-Gödel Machine (DGM)
- arXiv 2510.04399 — PAC-learnability under self-modification (Two-Gate)
- arXiv 2607.13683 — significance-gated harness evolution (**not yet verified**, needs re-reading)
- arXiv 2605.23904 — SkillOpt (**not yet verified**)
- arXiv 2503.13657 — MAST (failure taxonomy, open coding)
- arXiv 2509.25370 — AgentDebug (failure taxonomy by root cause)
- arXiv 2606.14589 — mechanism-vs-location failure classification
- arXiv 2411.00640 — Anthropic, "Adding Error Bars to Evals" (power analysis for minimum n)
- addyosmani.com/blog/agent-harness-engineering (blog), latitude.so, langfuse.com (blog)

> **Quality warning:** the 6 claims in section 3 (the ones labeled "not yet verified") were found in primary
> sources but the adversarial verify step was cut off by the session limit — they *point the same way* as the verified
> 3-0 PAC claim, but you should read 2510.04399 and 2607.13683 directly before relying on the specific numbers (n=26,
> the εV formula). To finish verification: re-run the workflow with `resumeFromRunId` once the session limit clears.
