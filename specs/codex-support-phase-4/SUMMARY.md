# codex-support-phase-4 — Summary

Lane: high-risk
Confidence: high
Reason: Rewrites the input parsing of every registered hook, including the branch-isolation hard
gate and the git-command dispatcher. `workflow-engine` + `high-blast` fire; all six hooks run in
every session.
Flags: workflow-engine, high-blast
Affects: hook-input-normalization (new contract), hook-registration (consumers repointed; the
registration itself is unchanged)
Input-type: plan execution (Phase 4 of `specs/codex-support/ROADMAP.md`)

### Intent

Close the empty-fallback fail-open the design names (§3.1): every hook parsed the raw Claude payload
directly and fell back to an empty string on a missing field, so an unparsed Codex payload exited 0
past the gates. One tested normaliser now owns payload truth, with per-gate unknown policy —
hard gates fail closed, advisory hooks fail visible.

## What changed

- **Task 4.1** — `hooks/lib/normalize-tool-input.py`: one stdlib executable emitting runtime/event
  identity, tool class, a deduplicated repo-relative path set, command/prompt/outcome, and
  `known|partial|unknown` with named diagnostics. Rejects traversal, NUL, and outside-root paths
  without collapsing valid siblings. Registered as the `hook-input-normalization` manifest contract.
- **Task 4.2** — `branch-isolation-guard.sh` consumes the normalised path set: bookkeeping-exempt
  only when **every** known path is under `specs/` (the old hook exempted on a single leading
  `file_path`); partial/unknown/misclassified payloads are denied on shared branches with an
  actionable reason; break-glass and detached/non-repo behaviour preserved.
- **Task 4.3** — `ruff-on-edit`, `blast-radius-check`, and `render-plan-on-write` iterate every
  applicable path once, and stay non-blocking on partial/unknown input (probed: twelve bad-input
  combinations, all exit 0). Cross-hook Codex suite added.
- **Task 4.4** — `pre-bash-dispatch.sh` fails closed (exit 2) on an unclassifiable shell payload,
  matching its existing missing-lib precedent; `scope-gate.sh` stays advisory and emits one bounded
  additionalContext line on unclassifiable input. Git sub-hooks still receive the raw payload relay
  unchanged. `settings.json` untouched.

### Rationale

The alternative — teaching each hook the Codex patch envelope separately — reproduces the original
defect five times: five parsers drift independently and each grows its own empty fallback. One seam
means one place where "I could not parse this" is a first-class result instead of an accidental
success. Per-gate unknown policy lives in the consumer, not the normaliser, because blocking is a
property of what the gate protects, not of the payload.

### Alternatives considered

- **Parse in each hook with a shared jq library** — rejected; jq cannot express the patch-envelope
  parsing safely (path extraction from patch bodies with spaces/newlines), and five call sites would
  still each own their fallback behaviour.
- **Fail open on unknown dispatch payloads (warn only)** — rejected; the dispatcher guards the four
  git gates, and design §3.1 names the silent pass-through as the defect this phase closes. The
  fail-closed cost is bounded by golden fixtures per supported shape.
- **Normalise inside `settings.json` matchers** — rejected; matchers select hooks, they cannot
  rewrite payloads, and `settings.json` is out of scope for this plan.

### Deviations

- Rule 1 — Review found a reachable fail-open in the hard gate: an edit payload with no `tool_name`
  whose command did not start at offset 0 with `*** Begin Patch` (one leading newline sufficed) was
  classified `shell`/`known` with an empty path set, which the guard's empty-paths allow let through
  on a shared branch. Fixed in both layers: the normaliser recognises a patch program by a
  `*** Begin Patch` line anywhere (a tool_name-less patch now classifies as `edit`), and the guard
  denies any payload whose `tool_class` is not `edit` — a shell-classified payload on the
  `Write|Edit` matcher is a contradiction and contradictions at a hard gate fail closed.
  Mutation-verified: reintroducing the normaliser bug fails the normaliser suite while the guard
  still denies (defence in depth); removing the guard's `tool_class` check fails the guard suite.
- Rule 2 — Added the missing test cases: tool_name-less patch → `edit` (normaliser), tool_name-less
  plain command → `shell` (normaliser), and two guard cases proving a shell-classified or empty
  payload cannot pass the edit matcher on a shared branch.
- Rule 1 — Review measured a 5× latency regression on `pre-bash-dispatch.sh`, which runs on every
  Bash call (~9ms → ~47ms: a python3 spawn plus three jq calls before deciding the command was not
  git). Restored a fast path — `tool_name == "Bash"` with a non-empty string command is resolved by
  one jq, no Python, byte-equivalent to what the normaliser would return — and collapsed the slow
  path to two jq calls (command read separately because it may be multi-line, which a line-oriented
  read would truncate — and the truncated command is what the git matcher tokenizes). Re-measured at
  ~12ms/call; multi-line commands still reach the matcher (probed: a two-line command whose second
  line is `git commit` triggers the untracked-py deny; the no-git control is silent).
- Rule 1 — Reverted the capability-matrix edit that closed Phase 1's unified-exec evidence gap by
  rewording: the row's `reference` had been changed to cite the official hook schema while `kind`,
  `evidence_level`, and `evidence_path` continued to assert an observed fixture, and `checked_at`
  was bumped on two documentation rows whose sources have no recorded re-fetch. The reference now
  states the negative scope explicitly and the freshness dates match the evidence. See
  `### Not auto-verified`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Normaliser contract | `bash tests/hooks/normalize-tool-input.test.sh` | 0 | 16 cases: both runtimes, patch forms, traversal/NUL/Windows paths, misclassification regression | SC-1 |
| Branch isolation fail-closed | `bash tests/hooks/branch-isolation-guard.test.sh` | 0 | multi-path, mixed-specs-first, partial/malformed/misclassified deny, break-glass audit | SC-2 |
| Advisory hooks non-blocking | `bash tests/hooks/codex-edit-hooks.test.sh` | 0 | cross-hook multi-file/move-delete/malformed/no-path cases | SC-3 |
| Blast radius path set | `bash tests/hooks/blast-radius-check.test.sh` | 0 | every out-of-plan path reported once | SC-3 |
| Ruff path set | `bash tests/hooks/ruff-on-edit.test.sh` | 0 | each existing `.py` processed; partial warns | SC-3 |
| Plan render path set | `bash tests/hooks/render-plan-on-write.test.sh` | 0 | each touched PLAN rendered once | SC-3 |
| Dispatch fail-closed | `bash tests/hooks/pre-bash-dispatch.test.sh` | 0 | known routes as before; partial/unknown exit 2 | SC-4 |
| Prompt gate advisory | `bash tests/hooks/scope-gate.test.sh` | 0 | both runtimes' prompts; malformed visible, exit 0 | SC-5 |
| Manifest contract drift | `python3 scripts/check_manifest.py` | 0 | `hook-input-normalization` registered with six hook consumers | SC-6 |

The CI-equivalent `bash scripts/run-tests.sh` completed `ALL GREEN` with 514 Python tests plus all
hook suites.

### Not auto-verified

- **The Codex unified-exec envelope is not captured (traceability).** Task 4.1's Action required
  capturing it and promoting `tools.unified_exec`; that was not done — the row keeps its Phase-1
  feature-availability evidence (`doctor.json`) with an honest reference naming the gap. The
  fixtures `codex-unified-exec.json` and `codex-user-prompt.json` are hand-written from the official
  hook schema, and the normaliser's `exec_command` alias has no cited source. Because
  `pre-bash-dispatch.sh` now fails closed, a runtime whose real envelope differs would block every
  Codex shell command — the plan's own named risk, whose mitigation (an observed fixture) is still
  owed. Owner: codex-support-phase-5; exit condition: capture the envelope in a disposable live
  probe before the alpha adapter ships.
- **`hooks.user_prompt_submit` remains `documented` and `load_bearing: false`** — the promotion Task
  4.1 asked for did not happen. `scope-gate.sh` is advisory, so the consequence of a wrong shape is
  a lost nudge, not a lost gate; the capture obligation transfers to Phase 5 with the row above.
- **`python3` is now a hard dependency of every Bash call (truth-tier for the failure mode, by
  design).** No `python3` on PATH → `normalizer-unavailable` → exit 2 → all Bash blocked, and the
  recovery command is itself Bash. This matches the existing missing-`git-command.sh` fail-closed
  precedent and is deliberate, but it is a second single point of failure on the hottest path.
- **The fast-path/normaliser equivalence is asserted by construction, not by differential test.**
  The dispatch fast path claims `tool_name=="Bash"` + non-empty string command is the one shape the
  normaliser can only classify shell/known. True by reading both today; no test cross-checks them
  against each other on generated payloads.
- **Dispatcher latency is a point measurement** (20 runs, one machine), not a tracked benchmark.
- Linux/WSL hook behaviour remains unobserved, per the Phase-1 owned unknowns.

### Rollback

- `git revert <sha>` — restores direct per-hook parsing; `hooks/lib/normalize-tool-input.py` and the
  new test suites are removed with it.
- `settings.json` was never touched, so hook registration needs no change on rollback.
- Consumers that re-synced meanwhile: re-run `bash scripts/deploy-harness.sh <target>` to restore
  the pre-seam hook bodies.

### Harness-Delta

- backlog — `hooks/blast-radius-check.sh` still resolves one active plan; with several per-phase
  plans `active` it warned against Phase-1's file set on every legitimate Phase-4 edit (same delta
  recorded by Phase 3; it will keep recurring until fixed).
- backlog — an evidence gap was closed by rewording instead of capturing for the second time in this
  initiative (Phase-1 fixtures, then the unified-exec reference). The capability checker validates
  fixture *identity*, not whether the fixture's content substantiates the row; a `Verifies:/Does not
  verify:` pair on the matrix contract should make that boundary explicit at the gate.
