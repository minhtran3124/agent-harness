# Phase 2 review — packaging decision

**Reviewed:** the uncommitted Phase-2 working tree against `specs/codex-support-phase-2/PLAN.md`
**Base:** `be9bc21` (Phase-1 review/fix)
**Date:** 2026-08-10
**Reviewer:** Claude Code (read + re-run; no changes applied)
**Vietnamese translation:** `REVIEW.vi.md`

## Verdict

Scope and conformance are good: every file in the Task 2.1/2.2 `Files:` lists is present, nothing
outside them was touched, and all in-scope checks pass. The defects are in **what the evidence
proves**, not in what was built.

| Check | Result |
| --- | --- |
| `bash tests/scripts/codex-packaging-probe.test.sh` (SC-1) | exit 0 — 12 passed |
| `python3 scripts/check_codex_packaging.py specs/codex-support/packaging-decision.md` (SC-2) | exit 0 |
| `python3 scripts/check_codex_capabilities.py … --require-evidence` | exit 0 |
| `python3 scripts/check_plan_contract.py specs/codex-support-phase-2/PLAN.md` | exit 0 |
| `python3 scripts/verify_summary.py --lane codex-support-phase-2` | exit 0 |
| `python3 scripts/verify_summary.py --check codex-support-phase-2` | **exit 1** — see F5 |
| `bash scripts/run-tests.sh` | `ALL GREEN`, 489 Python tests |

The 489 count matches the SUMMARY's claim exactly (480 + 9 new checker tests).

## What is genuinely well done

Recording this because the findings below are narrow, and the rest of the phase is not.

- The deterministic suite asserts the **exact** 14-call CLI protocol, in order, by regex
  (`tests/scripts/codex-packaging-probe.test.sh:114-116`). That is a real contract, not a smoke test.
- Every CLI call is asserted to have run under an isolated `HOME` **and** `CODEX_HOME`, with a
  caller-state sentinel proving the real config was untouched.
- A failing lifecycle publishes **no** partial evidence — tested by fault injection
  (`FAKE_MARKETPLACE_FAIL=1`).
- Version-tolerant cache discovery: the builder docs say the local cache segment is `local`, CLI
  0.147.0 actually uses the manifest version `0.0.1`. The probe discovers whichever single directory
  exists rather than hard-coding either. This is a real upstream finding, correctly handled.
- The runtime-execution boundary is enforced in three independent places — the fixture field
  `runtime_execution_observed`, the checker (`check_codex_packaging.py:131-132`), and the decision's
  `## Unresolved gaps`. CLI lifecycle is never allowed to masquerade as execution proof.

## Findings

### F1 — The `direct` candidate observes nothing (high)

The direct-candidate block (`scripts/probe_codex_packaging.sh:274-334`) **never invokes Codex**.

Proof: the probe's own call log under the fake CLI records 14 invocations — `--version`,
`--strict-config --help`, and 12 `plugin …` commands. All 12 belong to the hybrid candidate. Zero
mention the direct project.

Its six checks are computed over files the probe itself created ~140 lines earlier (`:135-141`):

| Check | What it actually tests |
| --- | --- |
| `skill_discovery_surface` | the variable `installed` (`:285`) — "the files I copied exist" |
| `hook_registration_visible` | the **same** variable `installed` |
| `agent_discovery_surface` | the **same** variable `installed` |
| `conflict_preserves_local_and_writes_incoming` | two inline `write_text` calls (`:287-291`) |
| `source_update_staged` | `incoming.name.endswith(".harness-incoming")` on a name built one line above |
| `cleanup` | it unlinks the files, then asserts they are gone |

Every check is true by construction, so `packaging-direct.json` can only ever emit
`passed: true, status: observed`. There is no input under which it reports failure.

Two consequences:

- `conflict_preserves_local_and_writes_incoming` re-implements the `.harness-incoming` behaviour
  inline instead of invoking `scripts/deploy-harness.sh`. It therefore proves nothing about the real
  conflict guard.
- Task 2.1 requires both candidates through "discovery, install, upgrade, conflict, and removal".
  The decision doc tells a reader: *"The direct candidate also passed representative project-file
  install, update/conflict, incoming-sidecar, removal, and cleanup checks."* A reader takes that as
  a comparison; it is not one.

**Suggested fix.** Stop presenting the direct block as a probe. Emit it as `status: unknown` with an
owner and an exit condition (Phase 5 proves project-level discovery), exactly as Phase 1 handles
Linux/WSL. If a real direct-candidate probe is wanted instead, it must ask Codex to enumerate the
project's skills/agents and must call `deploy-harness.sh` for the conflict case.

### F2 — The fallback branch has no executable path (high)

Task 2.2: *"Select hybrid only if every required discovery/lifecycle case passes; otherwise select
direct sync."* That "otherwise" cannot be recorded:

- `run_cli` (`probe_codex_packaging.sh:181-196`) calls `die` on any CLI failure, so a failing hybrid
  produces **no fixture at all**.
- `check_codex_packaging.py:127-130` rejects any evidence containing a false check or a
  non-`observed` status — and it validates `hybrid_evidence` and `direct_evidence` identically,
  regardless of which candidate is selected.

So a decision of the form "hybrid failed, therefore direct" is unrepresentable: it would need a
hybrid fixture recording failure, which the checker refuses, and which the probe never writes. The
fallback exists as prose and as a `fallback_trigger` string; it has never been exercised.

This matters beyond tidiness — the fallback is the plan's stated protection against committing
Phase 5 to an unsuitable package boundary.

**Suggested fix.** Let the probe publish a non-passing hybrid fixture (`status: unknown` plus the
failing check) instead of dying, and teach the checker that the **unselected** candidate may carry a
failing result — that is precisely the evidence that justifies selecting the other one.

### F3 — `strict_config: true` is a literal (medium)

`probe_codex_packaging.sh:364` hardcodes `True` into the hybrid checks map. The actual strict-config
probe is ~185 lines earlier (`:177-179`) and dies on failure, so the recorded value happens to be
correct today — but delete that probe and the fixture still reports the check green. This is the
"green can mean skipped" shape: a constant that is indistinguishable from a measurement.

It is also weak on its own terms: `codex --strict-config --help` proves the flag is accepted at top
level, not that a configuration was strictly parsed. The Status Log records that this check was
*deliberately separated* (because `codex --strict-config plugin …` is rejected by 0.147.0), which
makes hardcoding its outcome more surprising, not less.

### F4 — `no_op_reinstall` does not check the reinstall was a no-op (medium)

`probe_codex_packaging.sh:359` is `(raw / "plugin-reinstall.stdout").is_file()` — true because
`run_cli` created the file by redirection and would have died on a non-zero exit. That proves a
second `add` succeeded, which is worth something, but not that it was idempotent.

Nothing after the reinstall re-checks that the cache still holds exactly one version directory with
unchanged content: the uniqueness check runs *before* it (`:205-216`), and the next assertion
(`:238`) is post-removal.

### F5 — The pytest Verify row fails on re-run (medium)

```
$ python3 scripts/verify_summary.py --check codex-support-phase-2
PASS     [Packaging lifecycle contract]  exit=0
SC-FAIL  [Packaging decision unit contract]  criterion=SC-2  sc_expected=0  actual=1
         command: python3 -m pytest scripts/test_check_codex_packaging.py -q
PASS     [Packaging decision evidence]  exit=0
```

The default interpreter on this machine has no pytest; `run-tests.sh` resolves a separate venv first.
This is the **identical** defect fixed in Phase 1 and written into
`specs/codex-support-phase-1/SUMMARY.md` as an explicit stated reason — it recurred here.

SC-2 keeps a covering row via the decision checker, so the SC-coverage gate still passes. But
`scripts/ci-strict-gate.sh` re-runs Verify rows, and a row that only passes under one interpreter is
not re-runnable evidence.

**Suggested fix.** Drop the row and cite the unit suite in prose, as Phase 1 does.

### F6 — `packaging.plugins` promoted to `status: supported` (low)

The row carries `support_target: advisory` and `load_bearing: false`, and its own evidence carries
`runtime_execution_observed: false`. Its Phase-1 value was `advisory`, which matched the observation
better.

The promotion is not optional: `check_codex_packaging.py:190-196` **requires**
`status == "supported"`. A gate that forces a claim broader than its evidence is worth flagging on
its own — it is the same failure class the phase otherwise defends against well.

### F7 — The probe's sanitizer is weaker than Phase 1's (low)

`probe_codex_packaging.sh:396` matches only `/Users/|/home/|/root/`. Phase 1's `_private_strings`
flags **any** string starting with `/`. A `/var/folders/…` temp path would clear the probe's own
sanitizer and only be caught later by `check_codex_packaging.py:86-90`, which does use the stricter
rule. Two different contracts for the same job, in the same phase.

No leak occurs today — the fixtures embed only booleans and a version string.

### F8 — The HOME-aliasing guard cannot fire (low)

`probe_codex_packaging.sh:146-151` compares `$WORK/home` — freshly created by `mktemp -d` — against
`$HOME`. They can never be equal, so the guard is unfalsifiable. It reads as the isolation safety
check, but the actual guarantee comes from `mktemp` itself, which nothing asserts.

## Recommendation

F1 and F2 are the ones to close before this lands. Together they mean the packaging decision rests
on one real candidate and one self-fulfilling one, and the escape hatch it names cannot be
exercised. F3–F5 are cheap and mechanical. F6–F8 can be recorded as negative scope in the SUMMARY's
`### Not auto-verified` if they are not fixed.

Whatever is not fixed should be stated in `### Not auto-verified` with its evidence tier, per
`CLAUDE.md` → Gate verifiability. In particular, the current SUMMARY's line

> The committed evidence contains no user paths, auth, transcripts, model calls, or unrelated
> configuration.

is accurate, but the SUMMARY does not say that the direct-candidate evidence contains no *Codex
observation* either. That belongs in the record.

## Resolution (2026-08-10)

All findings were addressed before further phase work:

- **F1:** direct is now an owned `unknown`; representative files are not presented as Codex
  observation, and Phase 5 owns the explicit discovery/conflict exit condition.
- **F2:** hybrid lifecycle failures publish non-passing evidence; the checker requires only the
  selected candidate to pass, and a unit test proves selection of a separately proven fallback.
- **F3:** strict parsing is measured: an unknown key must produce the strict-config diagnostic,
  while an empty valid config must parse through to the non-terminal boundary without a model call.
- **F4:** reinstall compares the unique cache version and deterministic tree fingerprint before and
  after; fault injection proves changed content fails the check.
- **F5:** the standalone pytest Verify row was removed. The 11-case unit suite remains registered in
  `scripts/run-tests.sh`; the originally reported failure was not reproducible on the final run.
- **F6:** `packaging.plugins` is advisory with observed lifecycle evidence, not supported runtime
  evidence.
- **F7:** probe sanitization now recursively rejects every absolute Unix/Windows or `file://` path,
  matching the checker boundary.
- **F8:** the redundant caller-alias comparison was replaced with a falsifiable assertion that both
  state roots are empty, distinct, resolved direct children of the fresh probe directory.
