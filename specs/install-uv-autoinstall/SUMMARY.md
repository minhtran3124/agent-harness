# install-uv-autoinstall — Summary

Lane: high-risk
Confidence: high
Reason: public-contract hard gate (new installer flag + changed consumer-visible install behavior) plus external download-and-execute of the astral.sh uv installer
Flags: public-contract, external-systems, audit/security, cross-platform, existing-behavior
Affects: scripts/install-harness.sh (consumer installer entry point)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> có cách nào khi install harness script chúng ta cài luôn uv và code-review-graph ko?
> trước khi cài chúng ta sẽ wwarning trước cho user 1 dòng

Approved design (assistant proposal, user replied "dong y"): install by default when `uvx` is
missing, one-line warning before installing, opt-out `--no-uv`, no install under `--dry-run`,
install failure is non-fatal (warn and continue), pre-fetch code-review-graph through `uvx`.

## What changed

`scripts/install-harness.sh` now installs uv when `uvx` is missing: one warning line
(`uvx not found — installing uv from astral.sh for the code-review-graph MCP server (skip with --no-uv)`),
then the official astral.sh installer, quieted, inside an `if` so every failure is non-fatal. It
then announces and starts a detached `uvx code-review-graph --version` pre-fetch. Both steps run
only after every abort gate (source checks, the re-sync consent prompt, and deploy-harness.sh's
conflict prompt), are skipped under `--dry-run`, and are skipped by the new `--no-uv` flag or
`CS_NO_UV=1`. `tests/lib.sh` exports `CS_NO_UV=1` so no test touches the network; 10 new rows in
`tests/scripts/install-harness.test.sh` drive the new paths with a fake `curl` and stub `uvx`.
README documents the default and the opt-out.

### Rationale

The installer already wires `.mcp.json` to `uvx code-review-graph serve`, so without uv the server
fails every session. Calling the vendor's documented installer is the lightest credible path; a
background pre-fetch makes "install code-review-graph" real for a uvx-launched server without
risking a hung install. Default-on with an opt-out matches the request ("cài luôn") and the no-tty
`curl … | bash` entry point.

### Alternatives considered

- Opt-in `--install-uv` flag instead of default-on — rejected: the user asked to install as part of the harness install ("cài luôn").
- Interactive y/N prompt — rejected: the primary entry is `curl … | bash -s -- --yes`, which has no tty.

### Deviations

- Rule 1 — the no-curl test bin dir uses `ln -sfn`, not the plan's `ln -sf`: `/usr/bin/X11` is a directory symlink on usrmerge Linux and `-sf` followed it. `tests/scripts/install-harness.test.sh`, `b9db48d`; plan text corrected in `9118704`.
- Rule 1 — the "--help documents --no-uv" row greps inline with `grep -qF --` because `tests/lib.sh` `assert_rc_contains` lacks `--`. `b9db48d`.
- Rule 1 — restored `usage()`/`case` column alignment the feature commit disturbed. `9118704`.
- Review fix (user-approved) — the uv install moved after the re-sync consent gate (`3b9621e`), then after deploy-harness.sh's conflict prompt (`3b99e4d`), so an aborted run installs nothing; new row "declined re-sync installs nothing".
- Review fix (user-approved) — the pre-fetch line now prints before the background job starts. `3b9621e`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| auto-install success row | `bash tests/scripts/install-harness.test.sh` | 0 | 20 passed; fake curl, no network | SC-1 |
| auto-install failure row | `bash tests/scripts/install-harness.test.sh` | 0 | same run | SC-2 |
| opt-out and dry-run rows | `bash tests/scripts/install-harness.test.sh` | 0 | --no-uv, CS_NO_UV=1, --dry-run, pre-fetch opt-out | SC-3 |
| test lib network opt-out | `grep -qx "export CS_NO_UV=1" tests/lib.sh` | 0 | | SC-4 |
| README documents --no-uv | `grep -q -e "--no-uv" README.md` | 0 | | SC-5 |
| no-curl row | `bash tests/scripts/install-harness.test.sh` | 0 | | SC-6 |
| pre-fetch default row | `bash tests/scripts/install-harness.test.sh` | 0 | | SC-7 |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | | SC-8 |
| README documents CS_NO_UV | `grep -q "CS_NO_UV" README.md` | 0 | | SC-9 |
| help and dry-run text rows | `bash tests/scripts/install-harness.test.sh` | 0 | --help documents --no-uv; --dry-run prints would install uv | SC-10 |
| installer syntax | `bash -n scripts/install-harness.sh` | 0 | | |
| plan contract | `python3 scripts/check_plan_contract.py specs/install-uv-autoinstall/PLAN.md` | 0 | | |
| tty-gate suite around moved call | `bash tests/scripts/install-tty-gate.test.sh` | 0 | 7 passed | |
| gitignore suite | `bash tests/scripts/install-gitignore.test.sh` | 0 | 15 passed | |
| profile suite | `bash tests/scripts/deploy-profile.test.sh` | 0 | 23 passed | |
| review receipt | `python3 scripts/check_review_receipt.py specs/install-uv-autoinstall --require correctness,intent --require-audit-if 2eb0bd1` | 0 | reviewed head 3b99e4d | |

Full suite (`bash scripts/run-tests.sh`) — ALL GREEN at baseline (2eb0bd1, before any edit) and
after the last code commit (3b99e4d); 802 pytest + all shell suites.

### Not auto-verified

- "No test reaches the network" (design SC-4) — reached traceability: `tests/lib.sh` exports `CS_NO_UV=1` and every installer test sources it (grep); no network monitor observed a suite run.
- The real astral.sh installer path (default dir, profile edits) — reached provenance only: installer script read 2026-10-09 (v0.12.24) plus one isolated `UV_UNMANAGED_INSTALL` probe; tests use a fake `curl`.
- `uvx code-review-graph --version` downloads the package — reached truth once (isolated probe, 2026-10-09), not re-run by any gate.
- Deploy `[a]` conflict-prompt abort installs nothing — reached traceability (code order + re-review); no test, it needs a real tty.
- macOS Bash 3.2 behavior — not run locally; CI macOS runs the network-free suite.

### Rollback

- Code: `git revert 3b99e4d 3b9621e 9118704 b9db48d 42cbfd5` (or revert the PR merge commit).
- A consumer machine where the installer already installed uv: `rm ~/.local/bin/uv ~/.local/bin/uvx` (or the dir in `UV_INSTALL_DIR`/`XDG_BIN_HOME`) and remove the `. "$HOME/.local/bin/env"` line uv added to `.profile`/`.bashrc`/`.zshrc`; `uv cache clean` drops the pre-fetched package.

### Advisory Findings

Correctness-review, all below the 75 threshold (independent scorer score in brackets):

- [50→fixed] uv installed before abort gates — fixed in 3b9621e/3b99e4d at the user's request.
- [50] `curl` uv install has no `--connect-timeout`/`--max-time`; a black-holed network can stall the install silently (`scripts/install-harness.sh` ensure_uv).
- [25] `CS_NO_UV` opts out only for exactly `1`; `true`/`yes` are ignored (docs promise only `=1`).
- [50] The post-install PATH prepend is script-global and never restored, so later `git`/`jq`/`python3` may resolve from `~/.local/bin` etc.
- [50] Success is judged on the patched PATH: with `UV_NO_MODIFY_PATH`/`UV_UNMANAGED_INSTALL` set, the closing "Install uv before that restart" warning is suppressed though a new shell lacks uvx.
- [50] `--dry-run --no-uv` prints "would install uv" (design-mandated order: dry-run wins).
- [25] A forced install dir equal to `CARGO_HOME` makes uv install into `<dir>/bin`, misreported as "uv install failed".
- [unmodified-line, 0] After the move, a source lacking `scripts/init-structure.sh` (old `-b` branch) fails after uv was installed; add it to the source checks.

### Intent Findings

- drift (equivalent, advisory) — "cài luôn … code-review-graph" is met as a uvx cache pre-fetch, not a persistent install; matches the approved design since the MCP server runs via `uvx`.
- excess (report-only) — `CS_NO_UV=1` env opt-out beyond the approved `--no-uv`; it is what keeps the test suite off the network.
- excess (report-only, first pass) — `curl not found` branch, 6-dir PATH candidates, the "open a new shell" hint, and `--no-uv` also skipping the pre-fetch when uvx exists.
- drift (secondary, first pass) — design SC-4 names the full suite; repo rule forbids whole-suite Verify rows, so it is recorded in prose above and the network claim is listed under Not auto-verified.

### Harness-Delta

- backlog — `tests/lib.sh` `assert_rc_contains`/`assert_rc_not_contains` run `grep -qF "$2"` without `--`, so any substring starting with `-` breaks them.
- backlog — `scripts/check_plan_contract.py` reads only the first line of a multi-line `**Interfaces:**` bullet (`FIELD` regex `(.+)$`), so a backticked artifact on a continuation line is reported missing.
- backlog — `review_package.py` includes `specs/**` diffs (PLAN.md, research-brief.md) in the branch package handed to the plan-blind intent reviewer, so the blind rule is not structurally enforced; the reviewer disclosed seeing them.
