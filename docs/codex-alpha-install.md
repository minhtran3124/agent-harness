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
- the generated `.codex/agents/*.toml` files named by the manifest; and
- one bounded section in the repository-root `AGENTS.md`, the managed block that carries the
  always-on rules (see "Always-on rules in `AGENTS.md`" below).

The payload is a derived copy of `rules/`, non-test `runtime/`, `templates/`, the consumer helper
scripts, `harness-manifest.json`, and each shipped skill's helper files. Installed plugin skills
point their helper paths at it, and `commit-gate.sh` and `session-knowledge.sh` look there for
`verify_summary.py` and `runtime_mode.py`. Because the manifest lists it, a reinstall refreshes it
and it follows the same conflict, prune, and `--remove` rules as the other managed files. Do not
edit it in place.

The installer also appends `.codex/.agent-harness/` to the project's `.gitignore`, so the
payload's and plugin's untracked `.py` files do not trip the strict-profile commit gate. The step
only appends and never rewrites the file. In a git repository it asks git (`git check-ignore`)
whether the directory is already ignored, so any existing rule such as `.codex/` or `.codex/*`
counts (including `.git/info/exclude` or a global excludes file), while a later `!.codex/` that
re-includes the parent, or a file-only rule such as `*.py`, does not. Outside a git repository,
only an existing `.codex/.agent-harness/` line counts. It also skips when an explicit
`!.codex/.agent-harness` line shows a deliberate choice to keep the directory tracked. It warns and skips when the
directory is already tracked, and does not run under `--dry-run`. This line is not recorded in the
deployment manifest.

Codex reads project instructions from the repository hierarchy, from the project root toward the
working directory. The adapter therefore writes its managed block, delimited by
`<!-- agent-harness:begin -->` and `<!-- agent-harness:end -->`, into the existing root `AGENTS.md`;
it does not create `.codex/AGENTS.md` or change project prose outside those markers. See the
official [AGENTS.md instruction hierarchy](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

The installer does not directly edit `.codex/config.toml`, project trust, project hooks, unrelated
marketplaces/plugins, custom agents, or content outside its `AGENTS.md` markers. Marketplace and
plugin registration go through the Codex CLI so Codex can merge its own state.

## Always-on rules in `AGENTS.md`

Claude Code loads the harness's five always-on rules (`architecture.md`, `behavior.md`,
`guidelines.md`, `orchestration.md`, and `research-depth.md`) from `.claude/rules/` in every
session. Codex has no equivalent, so the installer delivers them through the managed block in the
root `AGENTS.md`.

### What the block contains

The block is rendered from the harness rules on every install, so it is a derived copy and the
rule files stay the source of truth. Do not edit it by hand; a local edit is treated as a conflict
(see "Conflicts" below). In order, it contains:

1. a short preamble describing the harness and how to treat its generated files;
2. the full text of each always-on rule, sorted by file name, each introduced by a line of the form
   `Source: .codex/.agent-harness/payload/rules/<name>` and separated by a horizontal rule; and
3. an "On-demand rules" list naming each path-scoped rule (`auto-correct-scope.md`,
   `plan-format.md`, `terminology.md`, and `wave-parallelism.md`) by its payload path, together
   with its `paths:` globs, which say when to read it.

A rule is always-on when its file has no `paths:` frontmatter, the same test that decides which
rules Claude Code loads every session, so the block's rule set is derived from the files rather
than from a hand-maintained list.

The rules are inlined rather than referenced because Codex has no import or include mechanism for
`AGENTS.md`. A list of files to read would leave delivery to the model's choice to open them, and
the session-start hook cannot be relied on while Codex hook trust is unknown.

`.codex/harness-instructions.md` is no longer installed; its text became the block's preamble. On
reinstall an unchanged copy left by an older install is removed. If you edited that file, it is kept
and the installer prints `codex-deploy: preserved edited retired file
.codex/harness-instructions.md`; move anything you still need from it into your own `AGENTS.md`
prose, outside the markers, and delete the file.

### Size budget and truncation

Codex reads instruction files from the project root toward the working directory and stops at a
combined budget, `project_doc_max_bytes`, which defaults to 32 KiB. In the pinned Codex 0.147.0
source, the file that crosses the budget is truncated at the byte, with only a log-level warning.
The harness block is written at the end of the root `AGENTS.md`, so your own prose in that file
consumes the budget first and the rules at the end are what get cut. This was read in the Codex
source, not yet observed in a running 0.147.0 session.

Two limits guard against this:

- The rendered block is capped at 20 KiB. Rendering fails, and the install stops before writing
  anything, if the block would exceed it. The cap leaves at least 12 KiB of the 32 KiB default for
  your own `AGENTS.md` text and for `AGENTS.md` files in nested directories.
- After writing, the installer prints a non-fatal warning when the resulting root `AGENTS.md` is
  larger than 32 KiB, because Codex would cut the rules at the end of the file. The warning assumes
  the 32 KiB default and does not read a `project_doc_max_bytes` override from your configuration.

### `AGENTS.override.md`

In each directory Codex loads the first file it finds among `AGENTS.override.md`, `AGENTS.md`, and
its fallback names. A root `AGENTS.override.md` therefore hides the root `AGENTS.md` entirely, and
the rules in the block will not reach the session. The installer still writes the block and prints
a non-fatal warning when a root `AGENTS.override.md` exists. To get the rules, remove or rename the
override file, or move its content into `AGENTS.md`.

### Running Claude Code and Codex in the same project

The block's own text uses no runtime-specific syntax, so it reads correctly whichever tool loads
it. How Claude Code treats `AGENTS.md` (Claude Code v2.1.277 or later):

- By default, Claude Code reads `AGENTS.md` only when there is no `CLAUDE.md`, `.claude/CLAUDE.md`,
  or `CLAUDE.local.md` at or above the working directory. A `CLAUDE.local.md` alone is enough to
  stop `AGENTS.md` from loading.
- To load it alongside `CLAUDE.md`, add an `@AGENTS.md` import line to `CLAUDE.md`. That is the
  documented bridge.
- Alternatively, set the `claude-md-and-agents-md` mode, which loads both files and skips an
  `AGENTS.md` that `CLAUDE.md` already imports. It is configured under `pluginConfigs` for
  `cc-plugin-agents-md@builtin` and is honored only in user or managed settings, not in project
  settings.

When Claude Code loads both `.claude/rules/` (installed by the Claude harness) and the `AGENTS.md`
block, the five always-on rules arrive twice, adding about 14 KB of duplicated context to each
Claude session. This is documented rather than prevented.

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
