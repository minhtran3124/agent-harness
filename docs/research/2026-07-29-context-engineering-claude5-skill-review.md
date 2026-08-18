# Research — Context Engineering for Claude 5 & review of the skills/rules in harness-skills

> Date: 2026-07-29 · Source: [The New Rules of Context Engineering for Claude 5-Generation Models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)
> (Anthropic blog) · Question: what should the `harness-skills` repo (skills + rules + CLAUDE.md) adopt from
> this new context-engineering philosophy, and where does it currently diverge from / align with it?
>
> Method: fetch + extract the full text of the article → survey the actual repo with 1 Explore subagent
> (line count, density of rigid MUST/NEVER/ALWAYS language, repetition check, progressive
> disclosure, prose vs. schema) → cross-reference the 2 sources to produce recommendations. This is a **research /
> proposal** document, not yet implemented — the items in section 4 are candidates for a separate lane if approved.

---

## 1. Summary of the article

**Core finding:** Anthropic stripped away more than 80% of Claude Code's system prompt for the new-generation
models (Opus 5, Fable 5) with no measurable performance degradation on coding evals. The new models
have enough judgment that the heavy "rule-scaffolding" becomes a net harmful factor —
creating excess deliberation cost and paralysis from contradictory instructions (old example: "leave documentation
where appropriate" conflicting with "do NOT add comments").

**5 changes, old → new:**

| Old | New |
|---|---|
| Explicit rules ("never write multi-paragraph docstrings, one line maximum") | Judgment-based guidance ("match comment density to the surrounding code") |
| Examples illustrating correct tool usage | Clear tool design (clear parameters/enums) implies correct usage on its own |
| Cramming all information into the system prompt up front | Progressive disclosure — split into Skills loaded on demand, deferred tool schemas |
| Repeating the same instruction in both the system prompt and the tool description | A single authoritative place for each instruction |
| Manually saving memory via the `#` shortcut | Automatic memory capture |
| Specs in plain markdown | Rich references — HTML mockups, real test suites, rubrics, real code |

**The article's practical guidance:**
- CLAUDE.md should be lightweight, containing only what is "non-obvious" (omitting whatever Claude can discover
  on its own from the filesystem).
- Use `/doctor` to periodically recalibrate context.
- Eliminate contradictions between the system prompt / Skills / the user's request turns.
- Prefer code-form specs (HTML mockups, test suites, rubrics) over prose descriptions/screenshots —
  because code is a language the model understands with high fidelity.

## 2. Distilled ideas

The theme running through it all: **don't decide for the model what the model can decide for itself, and don't say
the same thing twice.** Impose absolute constraints only where a wrong judgment is genuinely expensive (irreversible,
wide blast radius, security/data-loss related); otherwise state the *why* clearly and let the
model decide the *how*. Structurally: fewer absolute rules, more single-source reference points,
content loaded only when the task actually needs it.

## 3. Comparison against the current repo

The survey was carried out with 1 Explore subagent, reading `rules/behavior.md`,
`rules/orchestration.md`, `CLAUDE.md` in full; sample-reading the largest SKILL.md files.

### 3.1 What the repo already does right

- **No SKILL.md exceeds 76 lines** (`feature-intake` is the largest of the 12 skills) — still far from the
  threshold that would require more progressive disclosure. `rules/*.md` range from 9–180 lines (`plan-format.md`
  largest), `CLAUDE.md` is 92 lines — all below the ~300-line threshold.
- **7/12 skills already externalize details** into `references/`, `templates/`, `tests/`, or separate
  prompt files instead of merging them into one monolithic SKILL.md: `brainstorming`, `compound`,
  `finishing-a-development-branch`, `subagent-driven-development`, `visual-planner`,
  `writing-plans`, `xia2`.
- **`rules/behavior.md` — the document that shapes general judgment — has 0 occurrences of
  MUST/NEVER/ALWAYS/hard-gate.** It uses soft language ("bias toward caution", "use judgment"), matching
  the article's "trust the model" spirit.
- **Rigid language is concentrated in the right places**: MUST/NEVER/hard-gate appear mainly in
  `rules/auto-correct-scope.md` (5 occurrences) and `rules/orchestration.md` (3 occurrences) — both govern
  autonomy boundaries and irreversible actions. This matches the "only constrain where a wrong judgment
  is genuinely expensive" principle — no fix needed.
- **4 core skills were checked** (feature-intake, correctness-review,
  subagent-driven-development, writing-plans) and all **reference** (`Read rules/...` at the top) instead of
  copy-pasting shared rules — the single-source principle is fairly well respected at this layer.
- **`rules/plan-format.md` already uses a real inline schema/examples** (task block ~lines 1-164) instead of a
  prose description — matching the article's "code over description" principle.

### 3.2 Points that diverge from the article's philosophy

> The numbering continues the original 4-item list from the discussion that preceded this doc — item **1**
> (rigid language placed in the right spot) moved to §3.1 because it is not a divergence, so this section
> starts at **2**.

**(2) The Lane/Confidence taxonomy is repeated in 4 places, with no single point of origin definition.**
`tiny | normal | high-risk` and `high | medium | low` appear in:
- `rules/orchestration.md` (the "Intake fields" section)
- `rules/auto-correct-scope.md` (lane-aware autonomy table, lines ~19-26)
- `skills/feature-intake/SKILL.md` (classify/assign step, lines ~23-32; Routes table line ~48)
- `CLAUDE.md` (workflow chain, lines ~21-34)

Each place has a different angle (autonomy scope vs. evidence requirements vs. classification procedure vs.
workflow chain), so it is not pure copy-paste, but there is no anchor point saying "the definition lives here,
everywhere else just links to it". This is exactly the kind of repetition the article warns about: if one copy is
fixed and another is forgotten, they silently drift apart — violating the "single authoritative place" principle.

> **Discussion 2026-07-29 (review before implementing item 2 in §4).** Re-reading all 4 places shows the
> original proposal wrongly lumped 4 different things into one. Only 1 of the 4 places actually contains a
> *definition* — the classification algorithm (`feature-intake/SKILL.md` Step 3, lines 23-25: hard gate →
> `high-risk`; 0-1 flags + 1 file → `tiny`; 2-3 flags → `normal`; 4+ → `high-risk`). The other three places
> contain information that **cannot be replaced by a link without losing content**: `orchestration.md`
> §Intake fields declares the field + consumers (`risk-corroboration.sh`, trust ledger), not how it is computed;
> the `auto-correct-scope.md` lane-aware table is the **autonomy consequence** of each lane
> (autonomy/plan/human-confirm) — an entirely different information axis, not duplication; `CLAUDE.md`
> (lines 21-36) already pointed at the source beforehand ("See
> `rules/orchestration.md`, `skills/feature-intake/SKILL.md`... for the full inventory") and does not
> list the full enum — no fix needed. What is genuinely repeated is only the **enum value string** appearing in
> 3 of the 4 places, like a shared type used across several modules — a far narrower risk than the original
> description: drift on rename, not contradictory instructions.
>
> Two remediation directions were considered: (1) just add a "source of origin" label pointing back to
> `feature-intake/SKILL.md` Step 3 in the 2 remaining places — cheap, no behavior change, but does not
> automatically prevent drift; (2) mechanize it with a script that checks enum values across files (like the
> `scripts/verify_summary.py --lane` + `check_manifest.py` pattern already used for evidence mapping) —
> actually prevents drift but is far more work (modifying `scripts/`, needing separate tests) to solve a risk
> that has **never occurred** in the repo's history — against CLAUDE.md's own "don't design for hypothetical
> requirements" principle.
>
> **Decision:** direction (1) — narrow it down. Add 1 line in `rules/orchestration.md` §Intake fields and
> the `rules/auto-correct-scope.md` lane-aware table, pointing back to `feature-intake/SKILL.md` Step 3 as where
> the classification algorithm lives. Do not delete/replace any table or algorithm in the other 3 places.
> Not yet implemented — left for a separate turn.

**(3) `correctness-scorer-prompt.md` embeds a prose anecdote instead of a structured case.**
Lines ~93-98 tell a prose story ("Worked example, 2026-07-13, PR #51") instead of a table/rubric
the way `skills/feature-intake/tests/*.md` does for canary cases. The "higher-fidelity references over
prose examples" principle suggests turning this into a structured test case — a pattern the repo already uses
elsewhere (`skills/xia2/tests/`, `skills/feature-intake/tests/`), just not applied here yet.

> **Discussion 2026-07-29 (review before implementing item 3 in §4).** An important point missed
> in the first survey: this anecdote is **not side documentation** — it sits inside the
> ` ``` ` block (lines 31-138) that is exactly the `prompt: |` content sent straight to the scorer subagent at runtime.
> Conversely, `feature-intake/tests/lane-classification-cases.md` — the pattern taken as the model —
> is a canary/eval file sitting **outside** the runtime context, used only for regression-checking `SKILL.md`, never
> loaded into the prompt at run time. The two are different in nature: one is few-shot calibration living in
> the real prompt, the other is an external verification fixture. Therefore "lift the anecdote verbatim into
> `skills/correctness-review/tests/` and delete it from the prompt" — as the original proposal described — is a
> **runtime behavior change**, not the "pure documentation fix" the risk table in §4 once recorded.
>
> **Decision:** keep the anecdote **in-prompt** (do not move it to `tests/`), only **compress it to 1-2
> structured lines** (case + verdict) to cut the excess prose without losing the calibration signal for
> the scoring model. Not yet implemented — the `correctness-scorer-prompt.md` lines 93-98 edit is left for a
> separate turn.

**(4) `context-propagation-audit` is the only skill without a supporting `references/` file.**
At 38 lines it doesn't need splitting yet — recorded only as a point to watch if this skill grows.

## 4. Proposals (candidates for a separate lane, not yet implemented)

| # | Proposal | Value | Risk/effort |
|---|---|---|---|
| 2 | ~~Designate orchestration.md as the official source, with the other 3 places linking to it~~ → **Add a "source of origin" label pointing back to `feature-intake/SKILL.md` Step 3 (where the classification algorithm actually lives) in `rules/orchestration.md` §Intake fields and the `rules/auto-correct-scope.md` lane-aware table; delete/replace no content in these 2 places or in `CLAUDE.md`** (decision after the discussion in §3.2 item 2 — see the discussion box) | Closes the "no idea where the taxonomy definition lives" gap without losing the existing autonomy table or classification algorithm | Low — 2 added lines in 2 doc files, no change to `scripts/`/`hooks/`; does not automatically prevent drift when a lane is renamed (the mechanized option was considered and rejected as too much work for a risk that has never occurred) |
| 3 | ~~Move the anecdote out to `tests/`~~ → **Compress the "Worked example PR #51" anecdote in `correctness-scorer-prompt.md` (lines 93-98) into 1-2 structured lines, keeping it in-prompt** (decision after the discussion in §3.2 item 3 — see the discussion box) | Cuts the excess prose without losing the calibration signal for the scorer model at runtime | Low-medium — edits content sitting inside a real runtime prompt (not pure docs); 1-2 scorer runs should be cross-checked after the edit to be sure the score-0 behavior on `unmodified-line` is unchanged |
| 4 (not doing) | Split `context-propagation-audit` out into `references/` | Not needed yet — 38 lines, below the threshold | — |
| 1 (not doing) | Reduce MUST/NEVER density in `auto-correct-scope.md`/`orchestration.md` | Wrong direction — by the article's own reasoning this is exactly where hard language belongs (autonomy boundaries, hard-to-reverse actions) | — |

**Recommendation:** items 2 and 3 remain the two with real implementation value, but they are no longer uniform
in risk profile after the discussion. Item 2, after establishing that only 1 of the 4 places
(`feature-intake/SKILL.md` Step 3) holds the real definition and that the other 3 cannot be replaced by a link
without losing content, has narrowed down to 2 purely anchor lines — a documentation edit, no change to
`scripts/`/`hooks/`, no loss of any existing autonomy table or classification algorithm. Item 3, after
establishing that the anecdote sits inside a runtime prompt (not side documentation), is an edit affecting the
scoring model's behavior — still small (1 file, compressing 5 lines to 1-2) but the scorer's behavior should be
cross-checked before/after; it can no longer be treated as "no logic change". Both can still be done directly
(tiny lane) if approved — no separate plan/design needed, just an added cross-check step for item 3.

## 5. Status

Items 2 and 3 are **implemented** (2026-07-29, branch `chore/context-eng-lane-anchors` off
`simplify`), following exactly the direction settled after the discussion:

- `rules/orchestration.md` §Intake fields — added 1 sentence pointing to `skills/feature-intake/SKILL.md`
  Steps 3–4 as the source of the taxonomy definition.
- `rules/auto-correct-scope.md` §Lane-aware autonomy — added a similar sentence, keeping the autonomy
  table unchanged.
- `skills/correctness-review/correctness-scorer-prompt.md` lines 93-95 — compressed the PR #51 anecdote from
  6 prose lines to 3 structured lines (Case/Verdict), still in-prompt.

The full test suite (`bash scripts/run-tests.sh`) run after the edits: `ALL GREEN` (278 unit tests +
all shell test files pass). Not yet committed — awaiting user confirmation. Items 1 and 4 keep their
"not doing" conclusion.
