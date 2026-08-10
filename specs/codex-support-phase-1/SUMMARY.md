# codex-support-phase-1 — Summary

Lane: high-risk
Confidence: high
Reason: Establishes the evidence contract every later Codex phase stands on, and adds scripts the
CI-equivalent suite runs. `workflow-engine` + `external-provider` fire; the matrix is a registered
manifest contract.
Flags: workflow-engine, external-provider
Affects: codex-capability-evidence (new contract)
Input-type: plan execution (Phase 1 of `specs/codex-support/ROADMAP.md`)

### Intent

> make the deep research and deep review current codebase in current repo (on simplify branch)
> now i want to support for the user with codex. Let thinking and make the overral design + high
> level spec for it.

Phase 1 of the approved roadmap: a versioned capability baseline, before any adapter exists.

## What changed

Added a version-pinned Codex capability matrix with a stdlib validator, a bounded capture command,
sanitized Codex 0.147.0 evidence, and a fake-CLI contract suite.

Nothing here is registered in `settings.json` or runs in a session. The new scripts are invoked by
hand and by `scripts/run-tests.sh`. No adapter, no `.codex/` tree, no installer surface.

### Rationale

The stale premise this replaces was "Codex hook support for `apply_patch` is experimental/missing".
On CLI 0.147.0 that is false, but proving it needs more than a session observation: the claim has to
survive a CLI upgrade, a platform change, and a config change. Hence a matrix keyed by runtime, CLI
version and platform, where every row carries its own freshness window and an unknown is a
first-class state with an owner and a closure condition — not an absence.

The review of the first implementation pass found the inverse failure: fixtures that *looked*
captured but were hand-authored. Provenance that cannot be distinguished from assertion is
assertion, so the `capture` vocabulary is now closed and validated.

### Alternatives considered

- **Assert capabilities in prose in `design.md`** — rejected; prose cannot be re-checked after a CLI
  upgrade, and a stale claim is indistinguishable from a fresh one.
- **Require live probes for every row** — rejected; several rows (Linux, WSL, effective project
  trust) have no deterministic local probe. Owned unknowns keep them visible instead of absent.
- **Let the checker infer support from fixture content** — rejected as over-engineering for a
  single-consumer schema; the negative scope is recorded instead.

### Deviations

- Rule 1 — Re-derived `doctor.json`, `platform.json`, `trust-config.json`, and
  `session-end-timing.json` from the installed Codex CLI 0.147.0. The versions committed in
  `872dc32` carried the capture tool's own deterministic-path labels but could not be produced by
  it (`doctor.json` held a `sanitized_fields` key the script never writes and lacked the `checks`
  key it always writes; `trust-config.json` held a `hooks_feature` value the script could not
  emit). They claimed provenance and delivered traceability.
- Rule 2 — Closed the `capture` vocabulary in `check_codex_capabilities.py`. It was previously
  required to exist but unconstrained, so a hand-authored fixture and a captured one were
  indistinguishable to every gate.
- Rule 2 — `capture_codex_capabilities.sh` now treats a disabled hooks feature as grounds to keep
  hook evidence `unknown`, and records `hooks_feature` as `<maturity>-<enabled|disabled>`. This is
  the "untrusted/disabled hooks" case Task 1.2 named but the suite did not cover.
- Rule 1 — Re-pointed `tools.shell` at `hooks-shell.json`. It claimed `observed` against
  `doctor.json`, which records no shell-tool observation at all.
- Rule 1 — An absent `hooks/state-breadcrumb.sh` now publishes an explicit-unknown SessionEnd row
  instead of aborting the whole capture with exit 2.
- Rule 3 — Removed an `if False else` dead branch in the benchmark hook-path resolution.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Capability matrix schema | `python3 scripts/check_codex_capabilities.py specs/codex-support/capability-matrix.json` | 0 | 21 rows; rejects stale sources, unowned unknowns, mismatched fixture identity, unknown capture labels | SC-1 |
| Capture contract suite | `bash tests/scripts/codex-capability-probe.test.sh` | 0 | 30 cases against a fake CLI; no network, no real Codex config touched | SC-2 |
| Load-bearing evidence | `python3 scripts/check_codex_capabilities.py specs/codex-support/capability-matrix.json --require-evidence` | 0 | every load-bearing row resolves to a version-pinned fixture or an owned unknown | SC-3 |
| Manifest contract drift | `python3 scripts/check_manifest.py` | 0 | `codex-capability-evidence` registered with its surface and consumers | SC-4 |

`scripts/test_check_codex_capabilities.py` (26 tests, including both capture-vocabulary cases) is
registered in `scripts/run-tests.sh` and runs there. It is deliberately **not** a Verify row: the row
would read `python3 -m pytest …`, and the default interpreter on a developer machine need not have
pytest installed — `run-tests.sh` resolves the shared venv first and skips cleanly when it cannot. A
row that only passes under one interpreter is not re-runnable evidence.

The CI-equivalent `bash scripts/run-tests.sh` completed `ALL GREEN` with 480 Python tests.
Full-suite evidence is intentionally prose rather than a Verify row, because Verify commands carry a
60-second strict-gate budget.

### Not auto-verified

- **Row coverage is unchecked (traceability).** `check_codex_capabilities.py` validates every row
  that is present; it holds no required-id list, so deleting a capability row leaves SC-1 and SC-3
  green. Nothing today proves the matrix still covers every claim in `design.md` §112–117.
- **The matrix cannot check that a fixture substantiates its row (traceability).** It verifies
  fixture identity — runtime, CLI version, platform, config hash, `result.status`, and the closed
  `capture` vocabulary — never that the fixture's *content* demonstrates the capability. The
  `tools.shell` mislink was caught by reading, not by a gate.
- **`tools.unified_exec` is observed only at feature-availability tier (provenance, partial).**
  `doctor.json` proves the feature is stable and enabled; the unified-exec *payload envelope* is not
  captured anywhere. Phase 4 Task 4.1 must capture it before Task 4.4 parses it.
- **`hooks.user_prompt_submit` rests on documentation (traceability).** It is marked
  `load_bearing: false`, which is what exempts it from `--require-evidence`. Phase 4 makes
  `scope-gate.sh` consume that payload, so its golden fixture must be an observed capture, not a
  transcription of the docs.
- **The four live-probe fixtures are transcriptions (provenance, second-hand).**
  `hooks-shell.json`, `hooks-apply-patch.json`, `agents-fresh-bounded.json`, and
  `agents-full-history-rejection.json` are labelled `transcribed-isolated-live-probe`: they record
  an earlier observed run and were not re-derived by the capture tool in this branch. Re-deriving
  them needs `--allow-live-model-probe` against a disposable account.
- **Effective project trust is an owned unknown.** `config.project_trust` carries an exit condition
  requiring a disposable-account probe in Phase 2; the hook-config hash is observed separately.
- **Linux, WSL, and native Windows are owned unknowns.** No Phase-1 runner capture exists for any of
  them. The evidence directory is macOS/arm64 only.
- **Codex CLI 0.148.0+ behaviour is unverified.** Every row expires 2026-11-08; the checker rejects
  a fixture whose `cli_version` disagrees with the matrix, so an upgrade forces a re-capture rather
  than silently inheriting these claims.

### Rollback

- `git revert 872dc32` — removes the Phase-1 scripts, matrix, evidence, and manifest entry.
- `git checkout 872dc32~1 -- scripts/run-tests.sh harness-manifest.json` if the revert conflicts.
- Nothing is registered in `settings.json`, so no session behaviour changes on rollback.

### Harness-Delta

- backlog — a plan whose Success Criteria span several independently-shippable phases cannot keep an
  honest mid-flight record: `commit-quality-gate.sh` Check 1.6 blocks every `specs/<slug>/` commit
  until the SUMMARY covers all SC ids. This plan was split into per-phase slugs to resolve it. The
  reusable lesson is that phase count should drive slug count at planning time; `writing-plans`
  could say so.
- backlog — the stale SUMMARY that this review found had survived because the earlier commits used a
  chained `git add && git commit`, which makes the PreToolUse gate read an empty index and fail
  open. That fail-open is a known hole (`docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md`
  documents the deny direction, not this one).
