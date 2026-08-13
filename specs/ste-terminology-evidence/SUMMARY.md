# ste-terminology-evidence — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine signal — edits two skill prompts, a rule that enters agent context, and the `CONTEXT_MATRIX` delivery path; `skills/context-propagation-audit/SKILL.md` states workflow-engine changes are high-risk at intake and must not be lowered to bypass the delivery proof. No hooks, settings, or templates touched.
Flags: workflow-engine
Affects: rules/ (agent-loaded prose), skills/xia2 + skills/feature-intake prompts, prompt-compose delivery matrix
Input-type: change request

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

Prior record: this slug's previous SUMMARY documented the terminology-rule adoption and
measurement shipped in PR #204; it remains at
`git show 4e4a171:specs/ste-terminology-evidence/SUMMARY.md`.

### Intent

Apply the repository's measured terminology profile when agents author research-brief.md and SUMMARY.md.

(Derived from the approved `design.md` (2026-08-13) — the user's verbatim phrasing for this
follow-up phase was not preserved; treat as design-derived, not verbatim.)

## What changed

Two more write-flows now receive `rules/terminology.md` before authoring their artifact:
`skills/xia2/SKILL.md` (step 6, before `research-brief.md`) and `skills/feature-intake/SKILL.md`
(step 5, before `SUMMARY.md`), each with an explicit Read step mirroring the existing
`writing-plans` pattern. Both edges are registered in `scripts/render_skill_prompt.py`
`CONTEXT_MATRIX` as `main.research-author` and `main.summary-author` (with `required` +
`required_reads`), the generic mutation test now also weakens the `Read` verb while keeping the
rule path, and the terminology rule's Delivery paragraph names all three covered writers.

### Context-Propagation Audit

**Verdict: PASS** (diff 4e4a171..69e0fed; one deferred-delivery row recorded, no repair needed).

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `terminology.md` profile (§1 advisory / §3 excluded for research) | `skills/xia2/SKILL.md` step 6 (research-brief author) | main | explicit Read — **added by this change** | `main.research-author` `required_reads` edge; `--check-all` + extended mutation test (Read-verb weakening detected); hand-proven: weakening to "See" → exit 1 |
| `terminology.md` profile (§3 for `### Verify`, Intent verbatim) | `skills/feature-intake/SKILL.md` step 5 (summary author) | main | explicit Read — **added by this change** | `main.summary-author` `required_reads` edge; same checker + mutation test |
| authorship locality (no child context writes either artifact) | xia2 / feature-intake dispatch surfaces | implementer / subagents | not needed | inspected: neither skill dispatches a child to author; grep shows no other skill writes `research-brief.md` (writing-plans and intent-review only read it) |
| Delivery paragraph's three-writer claim | any reader of `rules/terminology.md` | all readers | in-file prose | corroborated: exactly the three named skills carry the Read line (grep count 1 each); paths lint green. Caveat: the oracle is line-local traceability (see Not auto-verified) |
| new `CONTEXT_MATRIX` entries | `check_all` + `test_render_skill_prompt.py` | CI / any session | source of truth itself | exact-inventory test updated; 7 passed |
| updated source skills/rule | live sessions of THIS repo | deployed `.claude/` runtime | **deferred** — stale until user-confirmed rebuild | recorded in Not auto-verified; controller surfaces the deploy ask at ship |

`paths:` fires on read, never on write (v2.1.216), so write-flows receive the rule only via these
explicit Reads. No `paths:` frontmatter was added or removed in any rule
(`tests/scripts/rule-loading-tiers.test.sh` inventory unchanged: 5 always-on, 4 contextual). The
documented exclusions hold in the added skill text: research-brief keeps §3 excluded;
`### Intent` stays verbatim and excluded from every rule.

### Rationale

Reused the one existing delivery mechanism (explicit Read + `CONTEXT_MATRIX` edge) rather than
introducing a second one, because the checker, its mutation test, and the regression suite
already enforce that shape and the plan review required the Read verb itself to be load-bearing.

### Alternatives considered

- Adding `paths:` write-side triggers or a new hook/linter/template rule — rejected: `paths:`
  fires on read only (verified empirically, v2.1.216), and the task forbids a second mechanism.
- Bespoke per-context tests for the two new writers — rejected: the generic
  `test_each_policy_delivery_edge_is_load_bearing` loop covers them without new test code.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Both authoring contexts require an explicit Read of `rules/terminology.md` | `python3 scripts/render_skill_prompt.py --check-all` | 0 | prompt-compose: all contracts present | SC-1 |
| Removing the rule-path token or the `Read` verb fails the mutation test | `python3 -m pytest scripts/test_render_skill_prompt.py -q` | 0 | 8 passed (incl. the registration-pin test added by review fix 9e04352); pytest was installed into the repo `.venv` at ship so this literal command re-runs locally as well as in CI | SC-2 |
| Existing context-propagation contracts stay green | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | 8 passed | SC-3 |
| Terminology delivery prose references only existing paths | `bash scripts/lint-doc-truth.sh` | 0 | all referenced paths exist; hook table matches settings.json | SC-4 |

Full-suite result (Global Constraint, cited in prose because it exceeds the 60s per-row
strict-gate cap): `bash scripts/run-tests.sh` exited 0 — ALL GREEN, 575 python tests plus every
shell suite, run after the five implementation files above were edited.

### Not auto-verified

- The two new Read steps cause an agent to actually load and apply the rule at authoring time — reached traceability (the instruction line exists and is checked); agent behavior is not re-run by any gate.
- The Delivery paragraph's claim that exactly three writers are covered — reached traceability (`lint-doc-truth` proves the paths exist; no gate counts covered writers).
- The deployed runtime copies under `.claude/` are stale until the user runs the rebuild — `.claude/skills/xia2/SKILL.md`, `.claude/skills/feature-intake/SKILL.md`, and `.claude/rules/terminology.md` do not yet carry the new delivery edges, so no live agent receives them until deploy (deliberate: `.claude/` deploys require explicit user confirmation; verify content, not the success line).
- `check_all`'s Read oracle is traceability-tier and line-local: it requires the word `Read` earlier on the same line as the backticked rule path, so it cannot distinguish an imperative Read step from a prose mention, and nothing checks the step precedes the authoring step (that ordering is human-inspected).

### Task review roll-up (per-task reviewer — 4 Minor, none blocking)

1. Deployed `.claude/` copies stale pending user-confirmed rebuild — recorded above; controller surfaces the ask at ship.
2. SC exit codes were implementer-asserted — closed: the controller independently re-ran all four SC commands post-change (exits 0, 0 [7 passed], 0, 0).
3. This SUMMARY replaces the shipped PR #204 record at tip — controller decision: the history pointer (`git show 4e4a171:…`) is sufficient; one canonical record per slug at tip.
4. The Delivery paragraph reads stronger than what `--check-all` actually proves — recorded in Not auto-verified above; forwarded to the final review chain.

### Rollback

- `git revert 159ed1e 9e04352 69e0fed`

### Advisory Findings

Correctness review (6 finder angles → dedup → independent scoring, threshold 75). One finding
scored 100 and was **fixed** (`9e04352`: the `required_reads` registration was itself unguarded —
deleting the key left the suite green — now pinned exactly, and the mutation loop asserts a
pre-mutation match; re-review verdict CLOSED). Two scored 50 and two re-review advisories were
**addressed opportunistically** in `9e04352`/`159ed1e` (Delivery paragraph now states creation-side
scope, traceability tier, the precise oracle shape, and the un-gated `paths:`-on-read update edge).
Below-threshold/unmodified-line findings, recorded per protocol (score 0 by the unmodified-line
rule — real but out of this diff's fix scope):

1. `scripts/render_skill_prompt.py:110` — the Read oracle passes when the word `Read` survives in
   an unrelated, negated, commented, or passive mention on the same line as the path
   (reproduced by three finders); it also fails closed on a pure re-wrap (Read and path split
   across lines). Tightening it is a candidate follow-up; the rule prose now states the tier
   honestly instead of overclaiming.
2. `skills/feature-intake/SKILL.md:48` (pre-existing) — step 6 tells intake to run
   `verify_summary.py --lane`, which deterministically fails for `normal`/`high-risk` at intake
   (Verify table is still the template placeholder; high-risk also lacks Rollback), and the
   skill's `allowed-tools` grants no `Bash(python *)`. Scope the step to tiny or move it to ship.
3. `tests/scripts/context-propagation-regression.test.sh:94-106` (pre-existing) — the two shell
   terminology mutation cases delete the path token together with the verb, so they pin the
   `required` edge, not the Read edge; the Python mutation loop is the non-vacuous form.
4. `rules/auto-correct-scope.md:38` (pre-existing) — stale pointer "(Step 7)"; feature-intake has
   six steps (the lane-check step is 6).
5. `scripts/render_skill_prompt.py:119` (pre-existing) — `check_all` raises an unhandled
   `AttributeError` when `review-config.json` is valid JSON but not an object; every other
   malformed-config path degrades to a clean error string.
6. Scope-table prose is now inlined in two skills (`feature-intake:30-32`, `xia2:37-38`) with no
   drift lint; the `<!-- lint:scope -->` markers in `terminology.md` have no consumer. A registry
   drift guard (the `inline-policy-drift.test.sh` shape) is a candidate follow-up.
7. The pinned registration test guards the four existing edges; nothing forces a *future* new
   covered-artifact writer to register (mitigated by the exact context-name inventory test and
   the rule prose's "today").
8. `skills/feature-intake/SKILL.md` is at 546/600 words under the progressive-disclosure ceiling
   (54 words of headroom before `audit_skill_prompts.py` trips).
9. Delivery-target question (scored 50, now documented in the rule): the §3-required
   `### Verify` rows are authored by the execution-phase context, whose delivery relies on
   un-gated `paths:`-on-read of the existing SUMMARY. Registering an execution-phase edge is a
   deliberate follow-up decision, out of this plan's scope.

### Intent Findings

Intent review (blind to plan, oracle = design-derived intent above) reported 3 findings, none
routed to the fix loop:

1. **gap (deferred — user decision):** the intent's "when agents author … SUMMARY.md" is
   gate-enforced only for the intake-time author (`feature-intake`); the execution-phase agent
   that appends the §3-**required** `### Verify` rows still receives the rule only incidentally
   (`paths:` on read of the existing SUMMARY). Same residual as Advisory Finding 9; the approved
   design explicitly scoped delivery to the two creating skills, and the rule prose now discloses
   the un-gated edge. Registering an execution-phase edge (SDD skill files) is a follow-up scope
   decision, not silently applied.
2. **drift (behaviorally near-null, design-corroborated):** for `research-brief.md` the delivered
   profile is §1-advisory/§3-excluded — the "measured" rule (§3) does not bind on that artifact by
   the rule's own scope table. Matches the approved design verbatim; recorded, no action.
3. **excess (low, accepted):** the reviewer-side sentence correction in `terminology.md` and the
   pinning of the two pre-existing registrations (`main.plan-author`, `plan-document-reviewer`)
   exceed the two named artifacts. Both are adjacent-necessary side effects of correcting a
   touched claim and of pinning the mapping exactly; report-only.

### Harness-Delta

- none
