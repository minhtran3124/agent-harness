# install-uv-autoinstall — Research Brief

Depth: **Deep** (intake lane `high-risk`; no upgrade needed — already the maximum). External
surface: yes (downloads and runs the astral.sh uv installer; fetches the `code-review-graph`
package from PyPI through `uvx`).

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | build (small extension of the existing preflight in `scripts/install-harness.sh`), using the official uv installer as a built-in |
| **Why this is the lightest credible path** | The installer already detects missing `uvx` (`:126-131`); the official one-line installer covers download, checksum, and placement, so only orchestration is new |
| **Confidence** | 85% |
| **Next step** | `writing-plans` with the A1 refinement below (search a candidate list for `uvx`, not one dir) and A2 resolved to `uvx code-review-graph --version` |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Meta-repo: Claude Code harness (skills, rules, hooks, Bash/Python scripts) |
| Primary language + runtime | Bash (`set -euo pipefail` scripts), Python 3 helpers |
| Frameworks / platforms | Claude Code; CI on ubuntu + macos (`.github/workflows/harness-ci.yml`) |
| Relevant packages | uv / uvx (external, installer 0.12.24 at read time); `code-review-graph` 2.3.9 (PyPI) |
| Detectable versions | No manifest pins either; `.mcp.json` runs `uvx code-review-graph serve` unpinned |
| Important constraints | `rules/behavior.md` §3: no `timeout` on macOS; CLAUDE.md: run `bash scripts/run-tests.sh` before changing `scripts/`; `ci-strict-gate.sh` warn tier for `scripts/` |

## Feature Understanding and Assumptions

- **Requested feature:** install harness also installs uv and code-review-graph, with a one-line warning first.
- **What success appears to mean:** after `install-harness.sh`, the wired `code-review-graph` MCP server can launch in the next Claude Code session.
- **Assumptions from the request:** approved design D1–D6 (`design.md`).
- **Assumptions still needing confirmation:** none that change the recommendation.

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/install-harness.sh:126-131` preflight sets `UVX_MISSING`; `:188` wires `uvx code-review-graph serve`; `:328-330` post-install warning; `:18-19` `CS_` env convention |
| `Local` | Four test files run the installer for real and all source `tests/lib.sh` (grep, 2026-10-09); `.github/` and `run-tests.sh` never call it directly |
| `Docs` | uv installer reference: override with `UV_INSTALL_DIR`; disable profile edits with `UV_NO_MODIFY_PATH`; `UV_UNMANAGED_INSTALL` for CI (docs.astral.sh/uv/reference/installer, 2026-10-09) |
| `Docs` | uv storage reference: executable dir precedence `$XDG_BIN_HOME` → `$XDG_DATA_HOME/../bin` → `$HOME/.local/bin` (docs.astral.sh/uv/reference/storage) |
| `Upstream` | Installer script (`astral.sh/uv/install.sh` **301 →** `releases.astral.sh/installers/uv/latest/uv-installer.sh`, v0.12.24): force-dir order `UV_INSTALL_DIR` → `CARGO_DIST_FORCE_INSTALL_DIR` → `UV_UNMANAGED_INSTALL`, then the XDG chain; quiet via `UV_PRINT_QUIET=1` or `-q`; needs `curl` or `wget` plus `uname mktemp chmod mkdir rm tar grep cat`; writes `<bindir>/env` and sources it from `.profile/.bashrc/.zshrc` when it modifies PATH; skips modifying PATH when the dir is already on PATH |
| `Upstream` | PyPI `code-review-graph` 2.3.9 (2026-09-18), Python ≥3.10; MCP entry is `uvx code-review-graph serve` |
| `Docs` | Truth-tier probe, 2026-10-09, this Linux host: `curl -LsSf …/install.sh \| env UV_UNMANAGED_INSTALL=<tmp> UV_PRINT_QUIET=1 sh` → exit 0, **0 bytes** of output, `uv`+`uvx` in `<tmp>`; `uvx code-review-graph --help` → exit 0, 5 s cold (downloads ~30 MB, 76 packages), 0 s warm; `uvx code-review-graph --version` → `code-review-graph 2.3.9` |
| `Inference` | Snap-packaged curl: the uv installer itself skips snap curl and falls back to wget; our `curl … \| sh` uses whichever `curl` is first on PATH to fetch the script only |

## Local Findings

- **Relevant files:** `scripts/install-harness.sh`, `tests/lib.sh`, `tests/scripts/install-harness.test.sh` (existing uvx test at `:119-124`), `README.md:89,110-115`.
- **Extension points:** the preflight block (`:126-131`) and the arg loop (`:92-107`) + `usage()` (`:55-89`).
- **Conventions worth preserving:** `warn`/`ok`/`info` helpers (`:43-47`); `CS_*` env overrides; `have_tty` rationale (`docs/solutions/scripts/test-r-dev-tty-does-not-detect-missing-controlling-terminal.md`) — not needed here since the design never prompts.
- **Reusable:** `UVX_MISSING` flag and its post-install warning stay as-is.
- **Missing locally:** any network-free test harness for installer side effects (fake-`curl` pattern is new).

## Upstream Findings

- **Repositories/pages inspected:** the uv installer script itself (official, read via WebFetch, not executed except in the isolated probe); uv docs mirrors from search.
- **Pattern present upstream:** documented CI form `curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh`; `command -v uv` guard is common practice but not documented officially (search found no authoritative example).
- **How closely it matches:** direct — we call the documented one-liner.
- **Gaps:** none blocking.

## Docs Findings

- **Official sources checked:** docs.astral.sh/uv/reference/installer, docs.astral.sh/uv/reference/storage, the installer script, pypi.org/project/code-review-graph.
- **Version-matched vs latest-stable:** the installer URL always serves latest (0.12.24 at read time); behavior can drift — mitigated because every failure path is non-fatal (D3).
- **Built-in capabilities:** `UV_PRINT_QUIET=1` (quiet), `UV_NO_MODIFY_PATH=1`, `UV_INSTALL_DIR`, `UV_UNMANAGED_INSTALL`.
- **Current recommended workflow:** `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- **Caveats:** `astral.sh/uv/install.sh` is a **301 redirect** — `-L` is mandatory. `--no-modify-path` is deprecated in favor of `UV_NO_MODIFY_PATH`.

## Recommendation

- **Primary:** build, calling the official installer.
- **A1 resolved, with a refinement:** the install dir is not always `${UV_INSTALL_DIR:-${XDG_BIN_HOME:-$HOME/.local/bin}}` — the real chain also has `CARGO_DIST_FORCE_INSTALL_DIR`, `UV_UNMANAGED_INSTALL`, and `$XDG_DATA_HOME/../bin`. Instead of computing one dir, after the install prepend each **set** candidate in installer order (`UV_INSTALL_DIR`, `CARGO_DIST_FORCE_INSTALL_DIR`, `UV_UNMANAGED_INSTALL`, `XDG_BIN_HOME`, `XDG_DATA_HOME/../bin`, `$HOME/.local/bin`) to PATH, all `set -u`-safe, then re-check `command -v uvx`. This keeps the design's interface and failure semantics (miss → warn) and only widens the search. Also pass `UV_PRINT_QUIET=1` to the installer in addition to the redirect.
- **A2 resolved:** use `uvx code-review-graph --version` (exit 0, prints one line, triggers the full package download). Pre-fetch and SC-7 stay.
- **Why the next-best alternative lost:** `uv tool install code-review-graph` would put a second, separately-updated copy on PATH that `.mcp.json` (which uses `uvx`) never runs.
- **What would change this:** astral changing the installer URL or dropping the redirect target — caught as a non-fatal warning.

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** remote script execution (accepted in D1/What we do not claim); cold pre-fetch downloads ~30 MB (measured 2026-10-09, this host) — detached, so it does not slow the installer.
- **Evidence gaps:** the default-dir branch (`$HOME/.local/bin` with profile edits) was not executed on this host to avoid touching the user's profile; covered by the docs, the script read, and the fake-curl tests. macOS not probed locally — CI macOS runs the network-free tests.
- **Version uncertainties:** installer version floats (latest).
- **Follow-up questions for the user:** none.

## Source Pack

- **Local files read:** `scripts/install-harness.sh`, `tests/lib.sh`, `tests/scripts/install-harness.test.sh`, `tests/scripts/{deploy-profile,install-tty-gate,install-gitignore}.test.sh` (grep), `.github/workflows/harness-ci.yml` (grep), `README.md:80-120`, `docs/solutions/INDEX.md`, `CLAUDE.md`
- **Upstream repositories or pages checked:** https://astral.sh/uv/install.sh → https://releases.astral.sh/installers/uv/latest/uv-installer.sh; https://pypi.org/project/code-review-graph/; search mirrors of the uv installer docs (git.joshthomas.dev)
- **Official docs domains or pages checked:** https://docs.astral.sh/uv/reference/installer/, https://docs.astral.sh/uv/reference/storage/

## Evidence Boundary

> Confirmed from artifacts: install-harness.sh line anchors; test files source `tests/lib.sh`; installer redirect; installer env vars and dir precedence (script read); quiet install produces no output; `uvx code-review-graph --version`/`--help` exit 0 and download the package (probe).
> Inferred from patterns: snap-curl behavior for the outer fetch; macOS behaves like Linux for these paths.
> Not checked: the default-dir install with profile edits on this host; macOS locally; Windows (non-goal).
