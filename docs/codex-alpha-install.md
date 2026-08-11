# Codex alpha installation

The Codex adapter is an advisory alpha pinned to the evidence boundary in
`specs/codex-support/packaging-decision.md`: Codex CLI 0.147.0 on the observed macOS platform.
Installation does not imply that hooks are trusted or that enforcement mode is active. Task 5.4's
outside-hook doctor is the authority for that claim.

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
- the generated `.codex/agents/*.toml` files named by the manifest;
- `.codex/harness-instructions.md`; and
- one bounded section in the repository-root `AGENTS.md`.

Codex reads project instructions from the repository hierarchy, from the project root toward the
working directory. The adapter therefore adds a sentinel-delimited pointer to the existing root
file; it does not create `.codex/AGENTS.md` or replace project prose. See the official
[AGENTS.md instruction hierarchy](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

The installer does not directly edit `.codex/config.toml`, project trust, project hooks, unrelated
marketplaces/plugins, custom agents, or content outside its `AGENTS.md` markers. Marketplace and
plugin registration go through the Codex CLI so Codex can merge its own state.

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
generated state. User-owned configuration and custom agents remain untouched.

The deployer stages a complete render before changing target state. If marketplace or plugin
registration fails, it removes the partial registration and restores the previous persistent
marketplace before returning an error. Re-run the install after correcting the Codex CLI or source
problem; do not delete `.codex/config.toml` or trust entries as a recovery step.
