# install-uv-autoinstall — Design

## Goal

When `scripts/install-harness.sh` runs on a machine without `uvx`, it installs `uv` itself, after
printing one warning line, so the `code-review-graph` MCP server it wires into `.mcp.json` can
actually launch. The user can opt out.

## Current state

- `scripts/install-harness.sh:126-131` sets `UVX_MISSING=1` and only prints a warning plus the
  manual install command when `uvx` is absent; `:328-330` repeats the warning after install.
- `scripts/install-harness.sh:188` wires `.mcp.json` to `uvx code-review-graph serve`, so without
  `uv` the wired server fails to launch every session (observed in this repo: ENOENT on `uvx`).
- Existing env overrides use the `CS_` prefix (`CS_REPO_URL`, `CS_BRANCH`, `:18-19`).
- Four test files run the installer for real (not `--dry-run`):
  `tests/scripts/install-harness.test.sh`, `deploy-profile.test.sh`, `install-tty-gate.test.sh`,
  `install-gitignore.test.sh`. CI (`harness-ci.yml`, ubuntu + macos) does not install `uv`.

## Approaches considered

1. **Default-on install, `--no-uv` opt-out** — chosen. Matches the request ("cài luôn") and the
   primary entry `curl … | bash -s -- --yes`.
2. Opt-in `--install-uv` — rejected: the user asked for install as part of harness install.
3. Interactive y/N prompt — rejected: the primary entry has no tty.

## Architecture

One new preflight function `ensure_uv` in `install-harness.sh`, replacing the block at `:126-131`:

```
uvx on PATH?  ── yes ──────────────────────────────────────────────► UVX_MISSING=0
   │ no
   ├─ --dry-run            → warn (as today) + "would install uv"     UVX_MISSING=1
   ├─ --no-uv / CS_NO_UV=1 → warn (as today, manual command)          UVX_MISSING=1
   ├─ no curl on PATH      → warn "curl not found — install uv manually: <cmd>"   UVX_MISSING=1
   └─ otherwise → ONE warning line, exactly:
        warn "uvx not found — installing uv from astral.sh for the code-review-graph MCP server (skip with --no-uv)"
        then
        if curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1   (both streams quieted)
        prepend each SET candidate dir, in installer order, to PATH (set -u safe):
          UV_INSTALL_DIR, CARGO_DIST_FORCE_INSTALL_DIR, UV_UNMANAGED_INSTALL,
          XDG_BIN_HOME, XDG_DATA_HOME/../bin, HOME/.local/bin   (research-brief A1)
        installer runs with UV_PRINT_QUIET=1 as well as the redirect
        uvx on PATH now? ── yes → ok "Installed uv" + hint "open a new shell before restarting Claude Code"   UVX_MISSING=0
                          └ no  → warn "uv install failed — install manually: <cmd>"   UVX_MISSING=1
```

Branches are checked top to bottom and the first match wins, so `--dry-run --no-uv` prints the
`--dry-run` output. The polling budget in the tests is one variable so it can be raised if CI flakes.

Pre-fetch (the "install code-review-graph" half of the request): when `UVX_MISSING=0`, not
`--dry-run`, and not opted out (`--no-uv`/`CS_NO_UV=1` skip it too, even when `uvx` was already
present), start a short `uvx code-review-graph <cheap subcommand>` **detached in the background**
(`… </dev/null >/dev/null 2>&1 &`), print `info "Pre-fetching code-review-graph in the background"`, and
never wait on it. Detaching bounds the installer's own runtime without `timeout` (absent on
macOS); a failed or slow pre-fetch costs nothing — the first MCP launch downloads instead. The
exact subcommand is A2; if xia2 finds none, the pre-fetch task is dropped (A2 fallback). All three
redirects are load-bearing: the stdout/stderr redirect keeps a caller's `$(…)` command
substitution from blocking until the pre-fetch exits, and `</dev/null` keeps the pre-fetch off
the script pipe on the `curl … | bash` path.

Interfaces:
- New flag `--no-uv` (documented in `usage()`, `install-harness.sh:55-89`), and env `CS_NO_UV=1`
  (same effect, follows the `CS_` convention). Opt-out skips both the uv install and the
  pre-fetch. `tests/lib.sh` exports `CS_NO_UV=1` so no test touches the network (astral.sh or
  PyPI) by default.
- The post-install warning at `:328-330` is unchanged; it now fires only when uv is still missing.

## Error behavior

- Every uv failure (no `curl`, network error, installer non-zero, `uvx` still not on PATH) is
  non-fatal: one warning naming the manual command, and the harness install continues with exit 0.
- `set -euo pipefail` is active; the install pipeline runs inside an `if` so a failure is handled,
  not fatal.
- The installer's own output is suppressed on success; on failure the warning tells the user to run
  the manual command to see why.

## Tests

In `tests/scripts/install-harness.test.sh` (truth tier — behavior re-run, no network).

PATH contract for every row below: `env -u CS_NO_UV -u XDG_BIN_HOME -u UV_INSTALL_DIR
HOME=$tmphome PATH=$fakebin:/usr/bin:/bin bash "$INSTALL" …`. `$fakebin` holds the fake `curl`
(shadowing `/usr/bin/curl`), which appends a line to `$tmphome/curl.log` on each call. `jq`, `git`,
`python3`, `sh` come from `/usr/bin:/bin`. Each row first checks `env PATH=/usr/bin:/bin sh -c
'command -v uvx'` — the *restricted* PATH, not the outer one — and skips if a system `uvx` is
reachable there.

Every `uvx` stub is a no-op that appends one line to a log inside `$tmphome` and exits 0, so a
detached call cannot write outside the temp dir. Assertions about the detached pre-fetch poll the
stub log for up to 2 s (budget; 20 × `sleep 0.1`, no `timeout`) before deciding.

- auto-install success (no `--dry-run`): fake curl prints a script that creates the `uvx` stub at
  `$HOME/.local/bin/uvx`; assert exit 0, exactly one `uvx not found` line, `Installed uv`,
  `curl.log` non-empty, and no post-install `Install uv before that restart` warning.
- pre-fetch runs by default (no `--dry-run`, `CS_NO_UV` unset): `uvx` stub already in `$fakebin`;
  poll until the stub log has an entry; assert it does, and `curl.log` stays absent.
- auto-install failure: fake curl exits 22; assert exit 0, `curl.log` non-empty, the
  `uv install failed` warning, and the post-install warning.
- no curl: same env as the contract above, with PATH replaced by `$nocurlbin` only, where `$nocurlbin` holds a symlink to every entry of
  `/usr/bin` and `/bin` except `curl` and `uvx`, created with `ln -sf` (on usrmerge Linux `/bin` is
  a symlink to `usr/bin`, so names repeat); assert exit 0 and the `curl not found` warning.
- `--no-uv`: assert `curl.log` absent, today's warning.
- `CS_NO_UV=1` (set explicitly): assert `curl.log` absent.
- `--dry-run`: assert `curl.log` absent.
- pre-fetch opt-out (no `--dry-run`, so it cannot pass for the dry-run reason): same setup as
  "pre-fetch runs by default" plus `CS_NO_UV=1`; poll the full 2 s window, then assert the stub
  log is still empty. The positive row above proves the same polling detects a real call.
- the existing "missing uvx warns" test keeps passing.

## Success criteria

- SC-1: missing `uvx` + default flags → exactly one warning line precedes the install, then uv is
  installed and the run exits 0 — test above.
- SC-2: install failure never fails the harness install — failure test.
- SC-3: `--no-uv`, `CS_NO_UV=1`, and `--dry-run` never invoke the uv installer or the pre-fetch —
  fake-curl and stub-uvx call logs.
- SC-4: the full suite (`bash scripts/run-tests.sh`) passes and, with `CS_NO_UV=1` exported by
  `tests/lib.sh`, makes no network call to astral.sh or PyPI from the installer.
- SC-5: README (`:89`, `:110-115`) and `usage()` (`install-harness.sh:55-89`) describe the new
  default and the opt-out.
- SC-6: no curl on PATH → install still exits 0 with the manual-command warning.
- SC-7: with `uvx` available and no opt-out, the installer launches the code-review-graph
  pre-fetch — "pre-fetch runs by default" row. Dropped together with the pre-fetch if A2 fails.

## Non-goals

- Installing `uv` through package managers (brew, apt) or on Windows.
- Pinning or verifying a checksum of the astral.sh installer.
- Building the code-review-graph graph data, or changing `.mcp.json` wiring.
- Changing `deploy-harness.sh` (it only warns when `.mcp.json` is missing).

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | The official installer puts `uv`/`uvx` in the first set of `UV_INSTALL_DIR`, `CARGO_DIST_FORCE_INSTALL_DIR`, `UV_UNMANAGED_INSTALL`, `XDG_BIN_HOME`, `XDG_DATA_HOME/../bin`, else `$HOME/.local/bin` | provenance: Upstream, 2026-10-09, uv-installer.sh v0.12.24 (research-brief Evidence Ledger) | SC-1 | PATH prepend misses the binary → treated as failure (warn), not broken |
| A2 | `uvx code-review-graph --version` exits 0 without serving and downloads the package | truth: Docs, 2026-10-09, isolated probe on this host (research-brief) | SC-7 | drop the pre-fetch step; first MCP launch downloads instead |
| A3 | No other test or CI job runs the installer without inheriting `tests/lib.sh` | provenance: Local, 2026-10-09, grep of `tests/` and `.github/workflows` | SC-4 | a job hits the network → add `CS_NO_UV=1` there |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| The downloaded installer is authentic/integrity-checked | We run the vendor's official `curl \| sh` as documented; no checksum pinning (Non-goal) |
| `uvx` is on PATH in the user's *next* shell / Claude Code session | We only fix PATH for this process; the success message tells the user to open a new shell before restarting Claude Code |
| The harness install leaves the user's shell profile files untouched | D5 keeps the official uv installer's default, which adds its bin dir to shell profiles |
| The code-review-graph package is cached when the installer exits | The pre-fetch is detached and unawaited by design; it may still be running or may have failed |
| Works on Windows | The installer script is POSIX `sh` only |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Install uv by default when `uvx` is missing, after one warning line | Consumers get a working MCP server with no extra step; installer downloads and runs a remote script | settled |
| D2 | Opt out with `--no-uv` or `CS_NO_UV=1` | Air-gapped/CI users and the test suite can skip the network | settled |
| D3 | Every uv failure is non-fatal | Harness install never regresses because of uv | settled |
| D4 | `tests/lib.sh` exports `CS_NO_UV=1`; auto-install tests unset it explicitly | Suite never downloads uv or the package; auto-install path is tested with a fake `curl` under a restricted PATH | settled |
| D5 | Let the uv installer edit shell profiles (its default) | `uvx` is on PATH in new shells, so Claude Code can launch the MCP server after restart | settled |
| D6 | Pre-fetch runs detached in the background and is skipped by the opt-out | Installer never hangs on a slow PyPI download; tests never reach PyPI | settled |
