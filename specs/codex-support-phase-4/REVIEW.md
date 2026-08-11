# Phase 4 review — runtime-neutral hook input seam

**Reviewed:** the uncommitted Phase-4 working tree against `specs/codex-support-phase-4/PLAN.md`
**Base:** `73671c6` (Phase 3)
**Date:** 2026-08-11
**Reviewer:** Claude Code (read + re-run + adversarial probing; no changes applied)
**Vietnamese translation:** `REVIEW.vi.md`

## Verdict

The migration itself is well executed — every intended behaviour I probed works, including the ones
that are genuinely hard (traversal rejection without collapsing valid siblings, mixed
bookkeeping/code denial, dedup, advisory hooks staying non-blocking). Three things need attention:
a reachable **fail-open in the hard gate**, an evidence claim that was closed by editing a string
rather than by capturing, and a 5× latency regression on the hook that fires for every Bash call.

| Check | Result |
| --- | --- |
| `bash tests/hooks/normalize-tool-input.test.sh` (SC-1) | exit 0 |
| `bash tests/hooks/branch-isolation-guard.test.sh` (SC-2) | exit 0 |
| `bash tests/hooks/codex-edit-hooks.test.sh` (SC-3) | exit 0 |
| `bash tests/hooks/pre-bash-dispatch.test.sh` (SC-4) | exit 0 |
| `bash tests/hooks/scope-gate.test.sh` (SC-5) | exit 0 |
| `python3 scripts/check_manifest.py` (SC-6) | exit 0 |
| `blast-radius-check` / `ruff-on-edit` / `render-plan-on-write` suites | exit 0 |
| `python3 scripts/verify_summary.py --lane codex-support-phase-4` | **fails — SUMMARY.md is not a file** |

`settings.json` is unchanged, as the plan requires.

## What is genuinely well done

Verified by direct probing, not by reading the tests:

- **Traversal rejection preserves valid siblings.** A patch touching `src/good.py` and
  `../../etc/passwd` yields `paths: ["src/good.py"]`, `status: partial`,
  `diagnostics: ["unsafe-path:outside-root"]` — and the guard then denies on a shared branch. This
  is the exact behaviour the Global Constraints demand and the easy thing to get wrong.
- **Mixed bookkeeping/code is denied even when the specs path comes first.** The old hook exempted
  on a single `file_path` beginning with `specs/`; the new one requires *every* known path to be
  under `specs/`. That is a real tightening of the hard gate, and it has a test.
- **Path dedup works** — the same file twice in one patch yields one path.
- **All four advisory hooks stay non-blocking** under malformed JSON, an unparseable patch, and `{}`.
  I probed all twelve combinations; every one exits 0.
- **`scope-gate.sh` behaviour is unchanged** for a normal Claude prompt — byte-identical outcome
  against the pre-migration version.
- **The normaliser test suite is honest in its naming**: the unified-exec case is called
  *"documented unified exec hook shape normalizes as Bash"* — it does not claim observation.
- **`tests/lib.sh`** correctly excludes copied `hooks/` fixtures from fixture repos so
  `check-untracked-py` does not fire on test infrastructure.

## Findings

### F1 — Reachable fail-open in the hard gate (high)

An edit payload that arrives on the `Write|Edit` matcher **without** `tool_name` and whose command
does not begin exactly with `*** Begin Patch` is classified as a *shell* command, not an edit — and
the guard allows it on a shared branch.

Reproduction, against `hooks/branch-isolation-guard.sh` on a repo checked out at `main`:

```
payload: {"hook_event_name":"PreToolUse","turn_id":"t",
          "tool_input":{"command":"\n*** Begin Patch\n*** Update File: src/app.py\n*** End Patch"}}

normaliser →  {"tool_class":"shell","status":"known","paths":[],"diagnostics":[]}
guard      →  exit 0, no deny JSON   ← the edit is ALLOWED on main
```

The mechanism is `hooks/lib/normalize-tool-input.py:142-146`: the shell branch claims any payload
with no `tool_name` whose command does not literally start with the patch marker. A single leading
newline is enough. `status` is then `known` with an empty `paths`, and
`hooks/branch-isolation-guard.sh` allows via `[ -z "$PATHS" ] && exit 0` — it inspects `status` and
`paths` but **never `tool_class`**.

This defeats Task 4.2's stated acceptance: *"the hard gate cannot silently allow a supported Codex
edit because a path is missing, reordered, or accompanied by a bookkeeping path."* It is also
self-inconsistent: `_patch_paths` already emits a `patch-missing-begin` diagnostic for exactly this
malformed shape, so the author anticipated it — but only on the branch that requires
`tool_name == "apply_patch"`.

Neither runtime emits a `tool_name`-less edit today, so this is latent rather than active. But the
normaliser has code paths that exist *only* to serve the missing-`tool_name` case, and a hard gate
whose guarantee depends on a field being present should not fail open when it is absent.

**Suggested fix.** In `branch-isolation-guard.sh`, deny unless `tool_class == "edit"`. A hook
registered on `Write|Edit` receiving a shell-classified payload is a contradiction, and a
contradiction at a hard gate must fail closed. Add the missing-`tool_name` case to both the
normaliser and branch-isolation suites.

### F2 — The unified-exec evidence gap was closed by editing a reference string (high)

Phase 1 recorded this as explicit negative scope:

> **`tools.unified_exec` is observed only at feature-availability tier (provenance, partial).**
> `doctor.json` proves the feature is stable and enabled; the unified-exec *payload envelope* is not
> captured anywhere. Phase 4 Task 4.1 must capture it before Task 4.4 parses it.

Task 4.1's Action says, in the plan: *"**Capture — do not transcribe from documentation** — the
Codex unified-exec shell envelope and the Claude/Codex `UserPromptSubmit` prompt payloads, and
promote the corresponding capability-matrix rows … from feature-availability/documented to
observed."*

What actually changed in `capability-matrix.json`:

- `tools.unified_exec` — `evidence_path` still points at `doctor.json`; `evidence_level` still
  `observed`; `source.kind` still `captured-fixture`. Only the human-readable `reference` changed,
  from *"feature availability only, not the payload envelope shape (Task 4.1 captures that)"* to
  *"official hook schema separately establishes that unified exec matches Bash and uses
  `tool_input.command`"*. That is a **documentation** claim (traceability tier) inserted into a row
  whose kind and level assert **observation**.
- `hooks.user_prompt_submit` — unchanged: still `documented`, still `load_bearing: false`. Not
  promoted.
- No new evidence fixture was captured; `specs/codex-support/evidence/codex-0.147.0/` is untouched.

The fixtures `codex-unified-exec.json` and `codex-user-prompt.json` are therefore assumptions written
by hand. The normaliser's `exec_command` alias has no cited source at all.

This is load-bearing, not cosmetic. `pre-bash-dispatch.sh` now **fails closed** on an unclassifiable
shell payload, so if the real unified-exec envelope uses a different `tool_name`, every Codex shell
command is blocked — the precise risk the plan names: *"Fail-closed dispatch on unknown payloads
could block legitimate Bash calls if a runtime changes its payload shape. Mitigation: version-pinned
capability-matrix rows for shell payloads, golden fixtures per supported shape."* The mitigation is
the observed row that was not produced.

**Suggested fix.** Either capture the envelope (a Codex session with the recorder hook from Phase 1's
capture script), or restore the honest reference and record the row as `documented` with an owner and
exit condition. The row must not read `observed` on a documentation source.

Related: `checked_at` was bumped from `2026-08-10` to `2026-08-11` on three rows whose evidence did
not change, which extends their freshness window. For the two `official-documentation` rows that
asserts the docs were re-fetched today; nothing records that they were.

### F3 — Phase 4 has no `SUMMARY.md` (high)

`specs/codex-support-phase-4/` contains only `PLAN.md`. `verify_summary.py --lane` reports
*"not a file"*. The plan marks 4/4 done across the hard gate, the git dispatcher, and all four
advisory hooks — no Verify rows, no Rollback, no `### Not auto-verified`.

Fourth consecutive phase. The per-phase slug split exists so this record can land with its phase.

### F4 — 5× latency regression on the every-Bash-call path (medium)

`pre-bash-dispatch.sh` fires on **every** Bash tool call. Measured over 20 runs of a trivial
non-git command:

| Version | 20 runs | per call |
| --- | --- | --- |
| Pre-Phase-4 (`73671c6`) | 0.185s | ~9ms |
| Phase 4 | 0.933s | ~47ms |

The common case now spawns `python3` plus three separate `jq` invocations before it can decide the
command is not `git commit`. The hook's own header previously described this path as *"one jq, no
child processes"*; that sentence was deleted in this change rather than preserved as a constraint.

It also adds `python3` as a hard runtime dependency of every Bash call: no `python3` on `PATH` →
`normalizer-unavailable` → `exit 2` → every Bash command blocked. That matches the existing
fail-closed precedent for a missing `git-command.sh`, so it is not a new *class* of risk, but it is a
second single point of failure on the hottest path, and the recovery action (`git pull`, redeploy) is
itself a Bash command.

**Suggested fix.** Have the normaliser emit one shell-evaluable line and parse it with a single read
instead of three `jq` calls, and consider short-circuiting on the unambiguous Claude
`tool_name == "Bash"` shape before spawning Python.

### F5 — No test covers the missing-`tool_name` edit payload (medium)

The normaliser suite has 14 well-chosen cases, including NUL paths, Windows absolute paths, unsafe
siblings, and unparsed control lines. None constructs an edit payload without `tool_name`, which is
why F1 survives a green suite. The branch-isolation suite gained seven good cases — partial,
malformed, move/delete, mixed-specs-first, break-glass over unknown — but likewise never exercises a
misclassified payload.

### F6 — `CLAUDE.md`'s hook table states the intended contract, not the actual one (low)

The updated row reads: *"An edit is bookkeeping-exempt only when all known paths are under `specs/*`;
partial/unknown input fails closed on shared branches."* Both clauses are true. What it does not say
is that an edit payload classified as *shell* is exempt from both clauses — the F1 hole. Once F1 is
fixed the sentence becomes accurate; until then the documentation is ahead of the code.

## Resolution (2026-08-11)

F1–F5 fixed in the working tree; F6 resolved as a consequence of F1.

| Finding | Outcome |
| --- | --- |
| F1 | Fixed in both layers. The normaliser recognises a patch program by a `*** Begin Patch` line anywhere (tool_name-less patch → `edit`, a plain command stays `shell`), and the guard denies any payload whose `tool_class` is not `edit` on a shared branch. Mutation-verified both ways: reintroducing the normaliser bug fails the normaliser suite while the guard *still denies* (defence in depth); removing the guard's `tool_class` check fails the guard suite. |
| F2 | The matrix reference no longer claims the envelope: it states the negative scope (feature availability observed; envelope shape traceability-only, hand-written fixtures, `exec_command` uncited) with a Phase-5 capture obligation. The two unearned `checked_at` bumps on documentation rows were reverted. `--require-evidence` still passes. The envelope itself remains uncaptured — deliberately recorded as owed, not silently re-claimed. |
| F3 | `SUMMARY.md` written: nine Verify rows, all re-run clean under `verify_summary.py --check`; the Task-4.1 capture/promotion shortfall is recorded in `### Not auto-verified` with an owner rather than papered over. |
| F4 | Fast path restored: `tool_name == "Bash"` with a non-empty string command resolves in one jq with no Python (the one shape the normaliser can only classify shell/known). Slow path collapsed to two jq calls, with the command extracted separately because it may be multi-line and a line-oriented read would truncate exactly what the git matcher tokenizes. Re-measured: ~0.24s/20 runs vs 0.19 pre-Phase-4 and 0.93 before the fix. Probed: a two-line command whose second line is `git commit` triggers the untracked-py deny; the no-git control is silent. |
| F5 | Four regression cases added: two normaliser (tool_name-less patch → edit; tool_name-less plain command → shell) and two guard (misclassified and shell-classified payloads denied on the edit matcher). |
| F6 | The `CLAUDE.md` row is now accurate — the code caught up with the documentation. |

Shellcheck clean on both edited hooks and both edited suites; all 8 hook suites and
`check_manifest.py` pass.

## Recommendation

F1 first — it is a reachable fail-open in the one gate the phase exists to harden, and the fix is a
single condition. F2 next: it is the second time an evidence gap has been closed by rewording rather
than by capturing (Phase 1's fixtures were the first), and this one is what the fail-closed dispatch
rests on. F3 is the standing record gap. F4 and F5 are cheap. F6 resolves itself with F1.
