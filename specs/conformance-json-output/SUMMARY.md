# conformance-json-output — Summary

Lane: normal
Confidence: high
Reason: 1 flag (existing-behavior) but 2 files and a new CLI contract on a shipped checker, so not `tiny` per feature-intake Step 3 (`tiny` requires one file and no new public callable). No manifest hard gate: the staged set is `scripts/*.py` only — no `skills/*/SKILL.md`, `hooks/`, or `settings.json`, so neither `workflow-engine` (risk-corroboration.sh:170) nor `high-blast` (:167) fires.
Flags: existing-behavior
Affects: scripts/check_skill_tool_conformance.py output contract (consumed by run-tests.sh and, after this change, by CI/agents)
Input-type: harness improvement
Route: normal — using-git-worktrees → subagent-driven-development. Already branch-isolated on `feat/cheap-adoptions-spotify-report`; no new worktree cut for this simulation run.
Escalate: no — single clear interpretation, no hard gate, reversible

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- verbatim -->

> Thêm cờ --json cho scripts/check_skill_tool_conformance.py để CI và agent parse được kết quả thay vì phải đọc dòng ✓/✗

Context: this closes the agent-native review finding on PR #229 — the new gates emit only
human-formatted `✓`/`✗` lines, so a caller cannot tell a pass from a skip or enumerate
findings without string-matching prose.

## What changed

`scripts/check_skill_tool_conformance.py` gained `--json`. Findings are now collected as
structured records alongside the human strings — built in parallel rather than parsed back out
of the formatted output, since re-parsing your own output is how the two drift apart. Default
stdout is unchanged, and exit codes are identical in both modes: the flag changes the *format*,
never the *verdict*.

| # | Delivered |
|---|---|
| 1.1 | `--json` emits `{ok, checked_skills, checked_commands, findings[]}` on stdout in BOTH outcomes, so a caller reads one stream instead of merging stdout and stderr. Findings carry `file`, `line`, `kind` (`ungranted-command` / `ungranted-dispatch`), `skill`, `command`. |
| 1.2 | Six cases pin the contract, including the load-bearing guard that default output is untouched. |

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| JSON contract | `python3 scripts/check_skill_tool_conformance.py --json` | 0 | `ok: true`, 25 commands across 12 skills, empty findings | SC-1 |
| Contract tests | `python3 -m pytest scripts/test_check_skill_tool_conformance.py -q` | 0 | 23 passed (17 pre-existing + 6 new) | SC-2 |
| Default output unchanged | `diff /tmp/ce-human-before.txt /tmp/ce-human-after.txt` | 0 | Captured before the edit, re-captured after: byte-identical | SC-3 |

Full suite, cited not tabled: `bash scripts/run-tests.sh` -> `ALL GREEN`, 619 tests (613 before
this task). At ~3.5 minutes it exceeds the strict gate's 60s per-command cap.

### Correctness review

Four independent FIND angles ran over `3d72f12..HEAD`. Every angle reproduced its findings by
execution rather than inspection, and three of four converged on the same top defect — in code
written earlier in this same session.

| # | Finding | Angles | Fixed |
|---|---|---|---|
| 1 | `--json` emitted NOTHING on stdout on all four fail-closed paths, contradicting its own "one object in BOTH outcomes" comment. A wrapper treating unparseable stdout as "no findings" turns fail-closed into fail-open — the `green can mean skipped` shape | enclosing-function, guard-completeness, call-site-impact, stack-defects | Single exit point via `emit()`; payload written on every path |
| 2 | `records` was never deduped while `problems` is `sorted(set(...))`, so the same run reported two different finding counts | enclosing-function, guard-completeness, call-site-impact | `dedupe()` mirrors the human collapse |
| 3 | `json.loads` on the manifest was unguarded — a malformed or non-object manifest raised a traceback and blocked only incidentally | guard-completeness, enclosing-function | Caught, with a named `kind` per failure |
| 4 | The docstring claimed `*prompt*.md` was out of scope; the `references/` glob did not implement it. Charging a parent skill for a subagent's command forces OVER-granting — an under-grant checker causing over-grants | guard-completeness | Glob filters `prompt` |
| 5 | No `schema_version`, against 13 other payload producers in this repo; `audit_skill_prompts.py` even validates its own | stack-defects (prior-art) | Added, `SCHEMA_VERSION = 1` |
| 6 | Exit 1 conflated "found gaps" with "could not run", while `check_skill_eval_readiness.py` and `codex_harness_doctor.py` reserve exit 2 for the latter | stack-defects (prior-art) | Setup failures now exit 2 |

All six are Rule 1 (localized auto-fix) under `rules/auto-correct-scope.md` — own new code, no design
fork. Each is pinned by a regression test; the suite went 619 -> 627.

**What the review says about the run itself:** the gate I built to catch under-grants was itself
shipped with a fail-open hole, and no gate in the repo would have caught it. Four reviewers reading
the same 168-line diff found it independently. That is the argument for the review step, not for
the gate.

### Not auto-verified

- **No caller consumes the JSON yet.** `run-tests.sh` still reads the human lines, so the new
  contract is exercised only by its own tests. Reached **truth** for the format, **not observed**
  in a real consumer.
- **`--json` covers one gate of three.** `check_frontmatter_contract.py` and
  `check-allowed-tools.sh` still emit text only, so an agent auditing the suite must still mix
  two styles. Deliberate — one output contract at a time.
- **The `kind` vocabulary is unversioned.** Adding a finding class later changes the payload
  with nothing to detect it. No schema, no version field; the tests pin today's shape only.

### Rollback

- `git revert <sha>` — one file plus its tests, no state, no migration. Default behaviour is
  unchanged, so a revert is invisible to every current caller.

### Prediction outcomes

Scored against the predictions recorded at intake, before implementation:

| # | Predicted | Actual |
|---|---|---|
| 1 | `risk-corroboration.sh` will not block at `Lane: normal` | **Correct** — commit 3ec8244 passed the gate; staged set was `scripts/*.py` + `specs/`, no block-mode category |
| 2 | The conformance gate stays green on itself | **Correct** — 25 commands, 0 findings |
| 3 | The `authorization` lexical trap fires if a line containing "permission" is added | **Correct, vacuously** — the diff added 0 lines matching `permission\|authorize\|role\|...`, so it did not fire. The trap is real (it fired on commit 3d72f12 over one docstring word) but this diff did not trigger it |

### Prediction (recorded BEFORE implementation, to be checked after)

Recorded so the run can be scored rather than narrated:

1. `risk-corroboration.sh` will NOT block this commit at `Lane: normal` — the staged set is
   `scripts/*.py` only, so no block-mode category fires.
2. `check_skill_tool_conformance.py` will stay green on itself: adding argparse/JSON code
   introduces no new instructed shell command in any SKILL.md.
3. The `authorization` lexical trap (`risk-corroboration.sh:174` grepping added lines for
   `permission|authorize`) WILL fire again if the diff adds a line containing "permission" —
   including a docstring. This is the failure mode recorded in
   `docs/solutions/harness/ratchet-matches-spelling-not-property.md`.
