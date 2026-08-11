# codex-support-phase-3 — Summary

Lane: high-risk
Confidence: high
Reason: Rewrites the shared instruction corpus and moves Claude model/tool policy out of agent role
documents into generated bindings — the workflow engine itself (skills, rules, agents, templates)
plus the deploy path. `workflow-engine` + `high-blast` fire.
Flags: workflow-engine, high-blast
Affects: agent-bindings (new contract), codex-neutral-sources (new contract), hook-registration
Input-type: plan execution (Phase 3 of `specs/codex-support/ROADMAP.md`)

### Intent

Make the shared corpus consumable by a second runtime without a deploy-time prose rewrite, so
workflow policy cannot drift per runtime. Rule addresses become repository-rooted, skill invocation
becomes runtime-neutral, and vendor model/tool policy moves into explicit per-runtime bindings.

## What changed

- **Task 3.1** — a frozen neutralisation inventory plus a count-exact lint
  (`scripts/check_runtime_neutral_sources.py`). 13 remaining findings, each an owned Phase-5
  exception with an exit condition.
- **Task 3.2** — `.claude/rules/…` addresses became repository-rooted `rules/…`, and
  `scripts/render_skill_prompt.py` grew a ten-context delivery matrix so every isolated consumer
  declares which contextual rules it needs (or a rationale for needing none).
- **Task 3.3** — invocation-neutral skill names across skills, rules, agents, and `templates/`.
- **Task 3.4** — `agents/agent-contracts.json` + `agents/runtime-bindings.json`; `deploy-harness.sh`
  now *renders* Claude agent definitions instead of copying vendor frontmatter, and the source-time
  binding JSON is never deployed.

Nothing Codex-specific is emitted: `--runtime codex` is validated but refuses to render, and
`settings.json` and root `AGENTS.md` are byte-identical.

### Rationale

The shared corpus addressed rules by their *deployed* path (`.claude/rules/…`), which only exists
after a Claude deploy, and invoked skills with Claude slash syntax. Both are runtime facts embedded
in runtime-agnostic policy, so a second runtime could only consume them by rewriting prose at deploy
time — and prose rewritten per runtime is prose that drifts.

Agent role documents had the same problem one level deeper: `model:` and `tools:` are security
policy, not role semantics. Separating them means the *role* is shared and reviewable while each
runtime's policy is explicit and total.

The lint is count-exact rather than an allowlist because an allowlist can be widened silently; a
count cannot. Adding a violation trips a mismatch and prints the offending line.

### Alternatives considered

- **Keep `.claude/rules/…` and rewrite at deploy time** — rejected; the rewrite is per-runtime prose
  transformation, exactly the drift this phase exists to prevent.
- **Rely on Claude's `paths:` frontmatter auto-loading alone** — rejected; it is a Claude
  accelerator, not a guarantee, and it never fires for plan-blind reviewers. Kept as an accelerator
  on top of the explicit reads.
- **Emit Codex TOML now** — rejected; deferred to Phase 5 per the roadmap's phase boundary.
- **Hash the whole role body as the render golden** — rejected; any wording change would fail with an
  unusable diff. Substance tokens fail only on deletion.

### Deviations

- Rule 1 — Restored two load-bearing statements to `agents/reviewer.md` that the first pass dropped:
  the description's "structurally read-only … enforced by the harness, not by instruction" plus the
  ensemble-diversity model rationale, and the body's **Acknowledged limitation** sentence stating
  that the inspection shell is *not* covered by the structural guarantee. Both are restated in
  runtime-neutral wording. Losing the second one silently upgraded a contract-tier promise to a
  structural one — the failure `CLAUDE.md` → Gate verifiability names directly.
- Rule 2 — Added `test_rendered_roles_retain_load_bearing_substance`. The existing
  `test_claude_render_preserves_legacy_model_tools_and_role_body` compares the rendered body against
  the *current* source, so deleting a sentence from both keeps it green; that is why the loss above
  was invisible. Mutation-checked: removing the acknowledged-limitation sentence fails the suite.
- Rule 1 — `render_agent_definitions.py` now inserts `tools`/`model` directly after `description`,
  where they were authored, instead of appending them. `coding.md` previously rendered with reordered
  keys, so every consumer's deployed copy would have been rewritten by a re-sync. Three of four roles
  now render **byte-identical** to their pre-Phase-3 versions; `reviewer.md` differs only by the
  approved vendor-name neutralisation.
- Rule 3 — SC-3's check was `python3 -m pytest …`, which exits 1 under an interpreter without pytest.
  Replaced with `python3 scripts/render_agent_definitions.py --check` (already implemented, exits
  0/1). The unit suite runs via `scripts/run-tests.sh`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Runtime-neutral sources | `python3 scripts/check_runtime_neutral_sources.py --root .` | 0 | count-exact against 13 owned exceptions; `templates/` scanned, zero findings | SC-1 |
| Contextual-rule delivery | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | 6 cases incl. the ten-context matrix and both historical mutation guards | SC-2 |
| Agent contract totality | `python3 scripts/render_agent_definitions.py --check` | 0 | every role×runtime×capability mapped or an owned unsupported exception | SC-3 |
| Manifest contract drift | `python3 scripts/check_manifest.py` | 0 | `agent_bindings` registered; semantic sources carry no runtime policy field | SC-4 |
| Deployed-agent boundary | `bash tests/scripts/deploy-prune.test.sh` | 0 | rendered agents carry model/tools; binding JSON not deployed; consumer custom agent survives | SC-3 |
| Reviewer read-only contract | `bash tests/scripts/task-reviewer-readonly.test.sh` | 0 | semantic source has no runtime policy; rendered artifact keeps the structural whitelist | SC-3 |

`scripts/test_check_runtime_neutral_sources.py` (10 tests) and
`scripts/test_render_agent_definitions.py` (9 tests) are registered in `scripts/run-tests.sh` and run
there. They are deliberately not Verify rows: the row would read `python3 -m pytest …`, and the
default interpreter on a developer machine need not have pytest — a row that passes under only one
interpreter is not re-runnable evidence.

The CI-equivalent `bash scripts/run-tests.sh` completed `ALL GREEN` with 514 Python tests.

### Not auto-verified

- **The context matrix is presence-checked, not delivery-checked (traceability).** `check_all` tests
  that a rule path appears in a consumer's text. All ten declared edges are, today, a real Read
  instruction placed before the point of use — verified by reading each. But an edit that demotes a
  Read to a passing mention (a "Related:" footer) keeps the check green. Only the two historical
  anchors (implementer prompt, correctness shared fragment) carry positional assertions.
- **Two consumers declare no required rules by rationale, not by check (traceability).**
  `correctness-scorer` ("scores evidence only") is sound. `task-reviewer` ("does not parse plan
  syntax or route fixes") is debatable — it issues a *spec* verdict, and judging whether a deviation
  was a legitimate Rule 1–3 auto-fix plausibly needs `rules/auto-correct-scope.md`. The checker
  enforces that an empty delivery *has* a rationale; it cannot judge whether the rationale is right.
- **Prose neutralisation preserved meaning by review, not by gate (traceability).** A normalised diff
  over all 37 changed markdown files isolates the semantic changes to `agents/reviewer.md`,
  `agents/README.md`, `skills/visual-planner/SKILL.md`, and `skills/xia2/README.md`; the rest is pure
  invocation/path substitution. Nothing re-checks that automatically.
- **`skills/visual-planner/SKILL.md` and `skills/xia2/README.md` replaced literal repository paths
  with a `<visual-planner-dir>` placeholder and a runtime-relative install instruction.** Task 3.3's
  Action says to neutralise invocation prose "while preserving literal repository paths", so this
  exceeds the task text. It is kept because a Codex skill directory is not `skills/visual-planner/`,
  but nothing tests that an agent resolves the placeholder correctly.
- **`agents/README.md` no longer names concrete model IDs (traceability).** They live in
  `agents/runtime-bindings.json`; the inventory table now names model *classes*. This partially
  reverses commit `670ccbc` at the documentation level.
- **Codex bindings are shape-validated only (traceability).** No Codex profile has been emitted or
  loaded by a Codex runtime. `--runtime codex` deliberately refuses to render.
- **Render fidelity is asserted against a hand-maintained golden, not the git history.**
  `LEGACY_CLAUDE` and `LOAD_BEARING_SUBSTANCE` are literals in the test file; nothing compares the
  rendered output to the pre-refactor blobs in git.

### Rollback

- `git revert <sha>` — restores the Claude-pathed prose, the vendor frontmatter in `agents/*.md`, and
  the copy-based deploy path.
- Re-run `bash scripts/deploy-harness.sh <target>` afterwards: the deployed `.claude/agents/*.md` are
  generated, so a revert without a re-sync leaves rendered copies in place.
- `settings.json` is untouched, so no hook registration changes on rollback.

### Harness-Delta

- backlog — `hooks/blast-radius-check.sh` resolves *one* active plan. With `codex-support-phase-1`
  and `codex-support-phase-3` both `status: active`, editing a legitimate Phase-3 file warns against
  Phase-1's file set. Per-phase slugs make concurrent active plans normal, so the hook should resolve
  the plan whose file set contains the edited path, or check all active plans.
- backlog — a Verify row reading `python3 -m pytest …` fails `verify_summary.py --check` on a machine
  whose default interpreter lacks pytest, while `run-tests.sh` resolves its own venv. This has now
  recurred in three consecutive phases. `writing-plans` should say that SC checks must be
  interpreter-independent.
