# Codex alpha installation

The Codex adapter is an advisory alpha pinned to the evidence boundary in
`specs/codex-support/packaging-decision.md`: Codex CLI 0.147.0 on the observed macOS platform.
Installation does not imply that hooks are trusted or that enforcement mode is active. Task 5.4's
outside-hook doctor is the authority for that claim.

The alpha is not GA and does not establish peer enforcement with Claude Code. The complete observed
runtime baseline is macOS arm64. Linux and WSL are included in deterministic CI/contract coverage,
but their real Codex runtime behavior is not yet observed, so the doctor emits
`PLATFORM_UNVERIFIED` and cannot return `enforced` there.

Codex requires a `.codex-plugin/plugin.json` manifest and supports adding a local marketplace with
`codex plugin marketplace add`. The installer uses that supported lifecycle instead of editing
Codex configuration directly. See the official [plugin packaging and marketplace
documentation](https://developers.openai.com/plugins/build/plugins).

## Install or update

From a harness checkout:

```bash
bash scripts/install-codex-harness.sh --source . --directory /path/to/project --yes
```

Without `--source`, the installer clones the configured repository and branch into a temporary
directory. `CS_REPO_URL` and `CS_BRANCH` override the defaults. Re-run the same command to update.
Use `--dry-run` to validate and report the lifecycle without writing files or invoking Codex.

For isolated testing, `--codex-bin` selects the executable and `--codex-home` selects a disposable
state root. Normal installs omit both and use the current Codex installation.

The adapter owns only paths recorded in
`.codex/.agent-harness/deployment-manifest.json`:

- the persistent local marketplace/plugin source under `.codex/.agent-harness/marketplace/`;
- the harness payload under `.codex/.agent-harness/payload/`;
- the generated `.codex/agents/*.toml` files named by the manifest;
- `.codex/harness-instructions.md`; and
- one bounded section in the repository-root `AGENTS.md`.

The payload is a derived copy of `rules/`, non-test `runtime/`, `templates/`, the consumer helper
scripts, `harness-manifest.json`, and each shipped skill's helper files. Installed plugin skills
point their helper paths at it, and `commit-gate.sh` and `session-knowledge.sh` look there for
`verify_summary.py` and `runtime_mode.py`. Because the manifest lists it, a reinstall refreshes it
and it follows the same conflict, prune, and `--remove` rules as the other managed files. Do not
edit it in place.

The installer also appends `.codex/.agent-harness/` to the project's `.gitignore`, so the
payload's and plugin's untracked `.py` files do not trip the strict-profile commit gate. The step
only appends and never rewrites the file. It skips when a line already decides the directory
(`.codex`, `.codex/`, `/.codex/`, `.codex/*`, or a `.codex/.agent-harness` form, including a
negated `!` form, which is taken as a deliberate choice to keep it tracked), warns and skips when the
directory is already tracked, and does not run under `--dry-run`. This line is not recorded in the
deployment manifest.

Codex reads project instructions from the repository hierarchy, from the project root toward the
working directory. The adapter therefore adds a sentinel-delimited pointer to the existing root
file; it does not create `.codex/AGENTS.md` or replace project prose. See the official
[AGENTS.md instruction hierarchy](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

The installer does not directly edit `.codex/config.toml`, project trust, project hooks, unrelated
marketplaces/plugins, custom agents, or content outside its `AGENTS.md` markers. Marketplace and
plugin registration go through the Codex CLI so Codex can merge its own state.

## Review trust and runtime mode

Review the project and user trust configuration in Codex itself; do not copy or delete trust entries
to make the adapter pass. Then run the harness doctor outside any hook:

```bash
python3 scripts/codex_harness_doctor.py --root /path/to/project
```

The wrapper consumes the redacted machine-readable `codex doctor --json` report and persists only a
sanitized record under `.harness-state/codex-runtime.json`:

- `enforced` — every required feature, dependency, installed hash, matcher, discovery, trust, CLI,
  platform, and fresh evidence check passed for this local combination;
- `advisory` — the adapter may still be used, but one or more load-bearing claims are unknown,
  stale, untrusted, or mismatched; and
- `unsupported` — a required package, install, dependency, or supported platform precondition is
  missing.

Re-run the doctor after an install/update, Codex CLI change, config/trust change, or any managed-file
conflict. A cached record is invalidated when its install, config, CLI, or trust fingerprint changes.
The official [Codex CLI reference](https://developers.openai.com/codex/cli/reference) documents the
underlying diagnostic command; the harness mode is a repository-owned conservative overlay.

## Conflicts

On reinstall, an unchanged managed file is refreshed and an unchanged retired path is pruned. If a
managed file or the `AGENTS.md` section was edited locally, the default is:

1. preserve the local content;
2. write the new candidate beside it as `<path>.harness-incoming`; and
3. keep the conflict visible in the deployment manifest.

After review, resolve the file manually and reinstall, or explicitly choose:

```bash
bash scripts/install-codex-harness.sh --source . --directory /path/to/project \
  --overwrite-conflicts
```

This flag applies only to manifest-managed files and the bounded `AGENTS.md` section. It does not
authorize replacement of unrelated Codex or project configuration.

## Remove and recover

Remove the plugin registration, local marketplace, unchanged generated files, and unchanged
managed instruction section with:

```bash
bash scripts/install-codex-harness.sh --source . --directory /path/to/project --remove --yes
```

Edited managed files are preserved during removal because their current bytes are no longer purely
generated state. User-owned configuration and custom agents remain untouched. `--remove` leaves
the `.codex/.agent-harness/` line in `.gitignore` in place; the harness never deletes a
`.gitignore` line, so delete it by hand if you no longer want it.

The deployer stages a complete render before changing target state. If marketplace or plugin
registration fails, it removes the partial registration and restores the previous persistent
marketplace before returning an error. Re-run the install after correcting the Codex CLI or source
problem; do not delete `.codex/config.toml` or trust entries as a recovery step.
