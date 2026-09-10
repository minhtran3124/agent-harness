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
| 1 | `risk-corroboration.sh` will not block at `Lane: normal` | see commit result below |
| 2 | The conformance gate stays green on itself | **Correct** — 25 commands, 0 findings |
| 3 | The `authorization` lexical trap fires if a line containing "permission" is added | see commit result below |

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
