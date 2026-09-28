---
status: active
---

# PLAN — machine-readable output for the skill-tool conformance gate

Lane: normal. Source: agent-native review finding on PR #229 — the new gates emit only
human-formatted `✓`/`✗` lines, so a caller cannot distinguish pass from skip, nor enumerate
findings, without string-matching prose.

## 1. Approach

Add `--json` to `scripts/check_skill_tool_conformance.py`. Human output stays byte-identical by
default so `run-tests.sh` and every existing reader are unaffected; `--json` swaps stdout for one
JSON object. Exit codes are unchanged in both modes — the flag changes the *format*, never the
*verdict*, so a caller can adopt it without re-learning the contract.

## Global Constraints

- Default (no flag) stdout must not change by a single byte — `run-tests.sh` greps it.
- Exit code semantics unchanged: 0 = conformant, 1 = findings or a fail-closed condition.
- Stdlib only (no new dependency); CI has no pyyaml and must not need one.
- JSON goes to stdout even on failure, so a caller reads one stream rather than two.

## 2. Tasks

### Task 1.1 — Emit a JSON report under `--json` (wave 1)

- **Files:** scripts/check_skill_tool_conformance.py
- **Action:** Add an argparse `--json` flag. Collect findings as structured records
  (`file`, `line`, `kind`, `skill`, `command`) instead of pre-formatted strings, then render
  either the existing human lines or one JSON object. Keep the human renderer as the default
  branch so its output is untouched.
- **Criteria:** SC-1
- **Interfaces:** Consumes: `harness-manifest.json` registers and each registered skill's Markdown. Produces: `scripts/check_skill_tool_conformance.py` with a `--json` stdout contract of ok, checked_skills, checked_commands and a findings array of file/line/kind/skill/command.
- **Verify:** `python3 scripts/check_skill_tool_conformance.py --json`
- **Done:** Valid JSON on stdout with `ok: true` on a conformant tree; exit 0.

### Task 1.2 — Pin the contract with tests (wave 1)

- **Files:** scripts/test_check_skill_tool_conformance.py
- **Action:** Add cases for valid JSON in both the clean and the finding case, `ok` tracking the
  exit code, each finding carrying file/line/kind, and — the load-bearing one — default stdout
  staying byte-identical to the pre-change output.
- **Criteria:** SC-2, SC-3
- **Interfaces:** Consumes: `scripts/check_skill_tool_conformance.py` and its JSON contract. Produces: `scripts/test_check_skill_tool_conformance.py` cases pinning the JSON shape and the unchanged default output.
- **Verify:** `python3 -m pytest scripts/test_check_skill_tool_conformance.py -q`
- **Done:** All cases pass, including the byte-identical default-output guard.

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
| --- | --- | --- | --- |
| SC-1 | `--json` emits parseable JSON | `python3 scripts/check_skill_tool_conformance.py --json` | exit 0 |
| SC-2 | The contract is pinned by tests | `python3 -m pytest scripts/test_check_skill_tool_conformance.py -q` | exit 0 |
| SC-3 | Default output is unchanged, so no existing caller regresses | `diff /tmp/ce-human-before.txt /tmp/ce-human-after.txt` | exit 0 |

All three are truth tier — behavior is re-run and exit codes compared. The whole suite
(`bash scripts/run-tests.sh`) is cited in prose at ship, never tabled: at ~3.5 minutes it
exceeds the 60s per-command cap
(`docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`).

## 4. Out of scope

- `--json` for `check_frontmatter_contract.py` and `check-allowed-tools.sh` — same argument
  applies, but one gate at a time keeps the output-contract change reviewable.
- Changing `run-tests.sh` to consume JSON — that is a separate decision about suite reporting.
