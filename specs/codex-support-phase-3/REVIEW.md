# Phase 3 review — semantic source neutralisation

**Reviewed:** the uncommitted Phase-3 working tree against `specs/codex-support-phase-3/PLAN.md`
**Base:** `4a5a721` (Phase 2)
**Date:** 2026-08-10
**Reviewer:** Claude Code (read + re-run; no changes applied)
**Vietnamese translation:** `REVIEW.vi.md`

## Verdict

This is the strongest phase so far. The lint is count-exact rather than allowlist-shaped, the
context matrix genuinely enumerates all ten isolated consumers, and the deploy/install tests assert
real behaviour. Two things need attention before it lands: one agent role document lost load-bearing
text that no test can see, and the phase has no `SUMMARY.md` at all.

| Check | Result |
| --- | --- |
| `python3 scripts/check_runtime_neutral_sources.py --root .` (SC-1) | exit 0 |
| `bash tests/scripts/context-propagation-regression.test.sh` (SC-2) | exit 0 — 6 passed |
| `python3 -m pytest scripts/test_render_agent_definitions.py -q` (SC-3) | 8 passed under the harness venv; **exit 1** under the default interpreter — see F3 |
| `python3 scripts/check_manifest.py` (SC-4) | exit 0 |
| `python3 scripts/check_plan_contract.py …` | exit 0 |
| `python3 scripts/verify_summary.py --lane codex-support-phase-3` | **fails — SUMMARY.md is not a file** |
| `bash scripts/run-tests.sh` | `ALL GREEN`, 513 Python tests |

`settings.json` and root `AGENTS.md` are untouched, as the plan requires.

## What is genuinely well done

- **The lint cannot be silently loosened.** `check_runtime_neutral_sources.py` compares an *exact
  count* per (path, category) against what it observes. A new violation trips a mismatch and prints
  the offending line; a removed one trips a stale-count error. This is materially stronger than an
  allowlist.
- **`templates/` is in `scan_roots` and has zero findings.** Task 3.3's template neutralisation is
  complete and machine-checked, not asserted.
- **All 13 remaining findings are owned exceptions** with a Phase-5 owner and an exit condition —
  hook/script message prose and test fixtures. None is a shared-source violation in disguise.
- **The lint's 10 unit tests are non-vacuous**: unowned-finding detection with line/category
  reporting, stale-path rejection, escaped-invocation and repository-path false-positive guards,
  vendor-policy-only-in-frontmatter, duplicate-entry rejection.
- **`test_each_policy_delivery_edge_is_load_bearing`** mutates *every* declared matrix edge and
  asserts the checker reports it. The checker itself is proven load-bearing, not just exercised.
- **The deploy/install tests assert behaviour**: rendered `reviewer.md` must carry `model:` and
  `tools:`, the source-time binding JSON must **not** be deployed, and a consumer's custom agent must
  survive a re-sync.
- **`task-reviewer-readonly.test.sh` was re-pointed correctly** — it now asserts the semantic source
  has *no* runtime policy while the *rendered* artifact carries the structural whitelist. That is the
  right shape for a render-based pipeline, and it kept its negative assertion.
- **Render fidelity is mostly exact**: `task-reviewer.md` and `test-runner.md` render **byte-identical**
  to their pre-Phase-3 committed versions.

## Findings

### F1 — `agents/reviewer.md` lost two load-bearing statements, and no test can see it (high)

Rendering the Claude agents and diffing against the pre-Phase-3 originals: `task-reviewer` and
`test-runner` are byte-identical, `coding` differs only in frontmatter key order (F4), and `reviewer`
differs **semantically** in two places.

**Description.** The original stated the structural guarantee and the model rationale:

> It is structurally read-only: the tools whitelist excludes Write, Edit, and Agent, so review
> independence is enforced by the harness, not by instruction. The frontmatter pins the default
> (claude-opus-5) so a forgotten dispatch never inherits the implementer's model; the correctness
> scorer overrides it to claude-opus-4-8 (a distinct model from the finders) per the
> ensemble-diversity rule in the reviewer prompts.

The replacement drops both the "enforced by the harness, not by instruction" claim and the entire
ensemble-diversity pointer:

> It is read-only, cannot delegate, and returns findings rather than fixes. Runtime bindings enforce
> the available tools and model-class isolation.

**Body.** This sentence was deleted outright:

> **Acknowledged limitation:** Bash can technically mutate state; the "never fix" rule below is the
> only guard on that channel. The structural guarantee covers Write/Edit/Agent.

and replaced with "A read-only inspection shell may be available … never use it to mutate state."

That inverts an explicit negative-scope statement into an implied guarantee. The binding itself is
honest — `runtime-bindings.json` says `"shell": "Bash limited by role contract to read-only
inspection"`, i.e. by *contract*, not structurally — but the role body no longer tells the agent
that. This is the failure `CLAUDE.md` → Gate verifiability names directly: a claim must not assert a
higher tier than it enforces.

It also breaks the plan's own Global Constraint: derived Claude definitions "must retain the intended
model, tools, descriptions, and role bodies **except for approved invocation/path neutralisation**".
A description rewrite and a body deletion are neither.

**Why nothing caught it.** `test_claude_render_preserves_legacy_model_tools_and_role_body` asserts
`rendered_body == source_body` — both sides move together, so body drift is invisible by
construction. Only model and tools have a real golden (`LEGACY_CLAUDE`); the test name overclaims the
rest. Task 3.4's Action asked to "compare generated Claude semantics against the pre-refactor roles";
that comparison exists for model/tools only.

**Suggested fix.** Restore the description and the acknowledged-limitation sentence (neutralising only
the vendor tool names if needed), and extend `LEGACY_CLAUDE` with a body/description hash or golden
so a future rewrite fails the suite.

### F2 — Phase 3 has no `SUMMARY.md` (high)

`specs/codex-support-phase-3/` contains only `PLAN.md` (and its rendered HTML).
`verify_summary.py --lane codex-support-phase-3` reports *"not a file"*.

The plan marks 4/4 tasks done across 66 files touching the workflow engine itself — skills, rules,
agents, templates, and `deploy-harness.sh` — with no Verify rows, no Rollback, and no
`### Not auto-verified`. This is the third consecutive phase where the record lagged the code; the
per-phase slug split done in `be9bc21` existed precisely so this record *could* land incrementally.

### F3 — SC-3's check cannot pass under the default interpreter (medium)

`python3 -m pytest scripts/test_render_agent_definitions.py -q` exits 1 here — the active
interpreter has no pytest; `run-tests.sh` resolves a separate venv first (the suite passes there:
8 tests).

This is the fourth recurrence of the same defect, and this time it is in the **plan's SC table**,
written during the phase split — so any honest Phase-3 SUMMARY cannot cover SC-3 with that command.

**Suggested fix.** Replace SC-3's check with an interpreter-independent command —
`python3 scripts/render_agent_definitions.py --check` is already implemented and exits 0/1 — and cite
the pytest suite in prose.

### F4 — `coding.md` renders with reordered frontmatter keys (medium)

The renderer appends `model:` last, so `color:` now precedes it where the original had `model:` first.
Semantically identical to Claude, but the rendered file is no longer byte-stable against the previous
deployment: every consumer's `.claude/agents/coding.md` changes content on the next re-sync, and the
copy deployed in this repo already differs from what `render_agent_definitions.py` now produces.

A renderer whose selling point is determinism should preserve the source key order and insert
`model`/`tools` in place.

### F5 — The context matrix is presence-checked, not delivery-checked (medium)

`check_all` tests `token not in text`. I verified all ten declared edges by hand, and **every one is
currently a genuine Read instruction placed before the point of use** — e.g.
`skills/intent-review/SKILL.md:38` "Before any fix routing, **read `rules/auto-correct-scope.md`**".
So the content is right today.

The gap is what the check can defend: a future edit that demotes a Read step to a passing mention (a
"Related:" footer, a prose aside) keeps the check green. SC-2's wording — "reaches … through an
explicit read or a checked equivalent" — and the test name "complete contextual-rule consumer matrix
is checked" both read stronger than substring presence. The two historical anchors (implementer,
correctness shared fragment) do have positional assertions and mutation tests; the eight new edges
have presence only.

Traceability tier. Worth stating as negative scope rather than fixing, unless a positional assertion
is cheap.

### F6 — Two `required: []` entries decide policy by rationale rather than by check (medium)

`correctness-scorer` declares no required rules with the rationale *"Scores evidence only; Rule
classification and fix routing occur after scoring in the controller."* That is sound.

`task-reviewer` declares none with *"Consumes a normalized task brief and review package; it does not
parse plan syntax or route fixes."* This is more debatable: the task reviewer issues a **spec**
verdict, and judging whether an implementer's deviation was a legitimate Rule 1–3 auto-fix plausibly
needs `rules/auto-correct-scope.md`. Recording the decision with a rationale is the right process —
the checker even enforces that an empty delivery *has* one — but this specific call deserves a second
look before it hardens into the contract.

### F7 — Literal repository paths were replaced with a placeholder (low)

`skills/visual-planner/SKILL.md` now says `python3 <visual-planner-dir>/render_plan.py …` in three
commands, where it previously named `skills/visual-planner/render_plan.py`. `skills/xia2/README.md`
gets the same treatment for its install instructions.

Task 3.3's Action says to replace invocation prose "while **preserving literal repository paths**" —
this does the opposite. The motive is sound (a Codex skill directory is not `skills/visual-planner/`),
but it is a deviation from the task text, and nothing tests that an agent resolves the placeholder
correctly. Either widen the task's stated scope or record it as a deviation.

### F8 — `agents/README.md` replaced concrete model IDs with model classes (low)

The inventory table now reads "review high-capability, distinct from implementer" where it read
`claude-opus-5`. The IDs still exist in `agents/runtime-bindings.json`, so nothing is lost — but this
partially reverses commit `670ccbc` ("pin explicit model IDs for each review sub-agent") at the
documentation level, and a reader of the agents inventory can no longer see which model runs. A
pointer line to the bindings file would close it.

## Resolution (2026-08-11)

F1–F4 fixed in the working tree; F5–F8 recorded as negative scope in
`specs/codex-support-phase-3/SUMMARY.md` → `### Not auto-verified`.

| Finding | Outcome |
| --- | --- |
| F1 | Description and the **Acknowledged limitation** sentence restored to `agents/reviewer.md` in runtime-neutral wording. New `test_rendered_roles_retain_load_bearing_substance` pins the substance against the *rendered* artifact; mutation-checked (deleting the sentence fails the suite, restoring it passes). |
| F2 | `SUMMARY.md` written. Six Verify rows, all re-run clean under `verify_summary.py --check`; Rollback names the required re-sync; `### Not auto-verified` carries seven tiered entries. |
| F3 | SC-3's check is now `python3 scripts/render_agent_definitions.py --check` (exits 0 here, 1 on a bad root). The two task-level `Verify` rows still name pytest and were left alone — they record what the implementer ran, and rewriting a completed task's check would be revising history. |
| F4 | `render_agent_definitions.py` inserts `tools`/`model` after `description`, where they were authored. `coding.md`, `task-reviewer.md`, and `test-runner.md` now render **byte-identical** to their pre-Phase-3 versions; `reviewer.md` differs only by the approved vendor-name neutralisation. |
| F5, F6, F8 | Recorded as negative scope with evidence tiers. |
| F7 | Recorded as a scope deviation with its rationale (a Codex skill directory is not `skills/visual-planner/`) and its untested surface. |

One finding surfaced during the fix and is filed as a Harness-Delta rather than fixed here:
`hooks/blast-radius-check.sh` resolves a single active plan, so with `codex-support-phase-1` and
`-phase-3` both `active`, editing a legitimate Phase-3 file warns against Phase-1's file set.
Per-phase slugs make concurrent active plans normal.

## Recommendation

F1 and F2 before this lands. F1 is a real weakening of a reviewer-isolation statement in the one file
whose whole purpose is to state it precisely, and the test that should have caught it is vacuous for
bodies. F2 is the record gap for the third phase running.

F3 and F4 are cheap. F5, F6 and F8 are legitimate as recorded negative scope in the SUMMARY's
`### Not auto-verified`, with tiers stated per `CLAUDE.md` → Gate verifiability. F7 needs either a
scope note or a task-text correction.
