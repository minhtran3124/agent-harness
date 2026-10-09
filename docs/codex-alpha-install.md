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

The installer does not directly edit `.codex/config.toml`, project trust, hook trust, project
hooks, unrelated marketplaces/plugins, custom agents, or content outside its `AGENTS.md` markers.
Marketplace and plugin registration go through the Codex CLI so Codex can merge its own state.
Outside `.codex/`, it writes three things: the managed section of the root `AGENTS.md` (and,
on a conflict, `AGENTS.md.harness-incoming`), the `.gitignore` line described above, and the
workflow files that `init-structure.sh` creates when they are missing (see "What the installer
prints after an install" below). The `.gitignore` and `init-structure.sh` steps never overwrite
an existing file; the `AGENTS.md` section follows the conflict rules described above.

### What the installer prints after an install

After a successful install, the installer runs three more steps. They never run under `--dry-run`
or `--remove`, and none of them can make the install fail.

1. **Workflow structure.** It runs `scripts/init-structure.sh` from the harness source against the
   project. That script creates each of these files only if it is missing, and prints a `created`
   or `exists` line for each one:

   - `specs/README.md` and `specs/STATE.md`;
   - `docs/solutions/README.md`, `docs/solutions/INDEX.md`, and
     `docs/solutions/critical-patterns.md`; and
   - `techstacks/README.md`.

   The session-start hook loads `docs/solutions/critical-patterns.md` and a pointer to
   `docs/solutions/INDEX.md`, and the workflow skills write their records under `specs/<slug>/`,
   so these files give them somewhere to start. The files are yours: they are not recorded in the
   deployment manifest, a reinstall never overwrites them, and `--remove` leaves them in place.
   When the source checkout has no `init-structure.sh`, the installer prints this line and moves
   on:

   ```text
   codex-install: init-structure.sh not in this source checkout; skipping the workflow structure.
   ```

2. **Doctor mode.** It runs the harness doctor once with `--no-persist`, so the install writes no
   runtime-mode record, and prints the mode with its reasons (or `(none)` when there are none):

   ```text
   codex-install: doctor mode: <mode> (<reason>, <reason>, …)
   ```

   Expect `advisory` (or `unsupported` if a precondition is missing), never `enforced`: no Codex
   release checked so far (0.147.0 and 0.162.0) reports hook trust to the doctor, so one of
   `TRUST_UNKNOWN`, `TRUST_CONFIG_ONLY`, or `HOOKS_UNTRUSTED` is among the reasons (see "Trust the hooks" below). If the doctor cannot run, the installer prints this instead:

   ```text
   codex-install: doctor could not run (exit <n>); run it yourself (below)
   ```

   If the doctor exits 0 but prints something other than a mode record, the line reads
   `codex-install: doctor output was not a mode record; run it yourself (below)`.

3. **Next step.** It tells you to trust the hooks and then re-run the doctor yourself:

   ```text
   codex-install: next: start Codex in <target>, choose "Review hooks" (or run /hooks and press t on each Agent Harness hook); hooks do not run until trusted.
   ```

   With `--source`, the follow-up command uses that checkout:

   ```text
   codex-install: then run: python3 <source>/scripts/codex_harness_doctor.py --root <target>
   ```

   Without `--source`, the installer worked from a temporary clone that it deletes afterwards, so
   the follow-up command clones the same repository and branch again:

   ```text
   codex-install: then run: git clone --depth 1 --branch <branch> <repo-url> agent-harness && python3 agent-harness/scripts/codex_harness_doctor.py --root <target>
   ```

   `<branch>` and `<repo-url>` are the values the install used (`CS_BRANCH`/`--branch` and
   `CS_REPO_URL`). In both forms every path is shell-quoted, so the line can be pasted even when a
   path contains spaces, and the command ends with the same `--codex-bin` and `--codex-home` the
   install was given (made absolute), so the follow-up checks the same Codex. An exported
   `CODEX_BIN` is honoured when `--codex-bin` is not given.

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

## Trust the hooks

The plugin registers three hooks (`adapters/codex/plugin/hooks/hooks.json`): `commit-gate.sh` and
`branch-isolation-guard.sh` before tool calls, and `session-knowledge.sh` at session start. Codex
runs a hook only after you trust it. Until then, the commit gate and the branch-isolation guard do
not block anything, and the session-start knowledge is not loaded. Installing the plugin does not
trust its hooks, and the harness never edits trust configuration for you.

The Codex 0.147.0 behaviour below was read from the Codex terminal UI source and its test
snapshots (`codex-rs/tui/src` at `rust-v0.147.0`), not yet observed in a running session.

When you start Codex in the project with new or changed hooks, it shows a "Hooks need review"
prompt: "N hooks are new or changed. Hooks can run outside the sandbox after you trust them." It
offers three choices:

1. **Review hooks** — review each hook and trust it.
2. **Trust all and continue** — trust every new or changed hook at once.
3. **Continue without trusting (hooks won't run)** — start the session with the hooks inactive.

If you skipped the prompt, or want to check later, run the `/hooks` command ("view and manage
lifecycle hooks"). It lists each hook; an untrusted one shows "Trust: New hook - review required"
and "Press t to trust". Select each Agent Harness hook and press `t`. A hook whose definition
changes (for example after a reinstall that changes it) needs review again.

After trusting the hooks, re-run the harness doctor (the command the installer printed, or the one
in the next section).

## Review trust and runtime mode

Review the project and user trust configuration in Codex itself; do not copy or delete trust entries
to make the adapter pass. Then run the harness doctor outside any hook:

```bash
python3 scripts/codex_harness_doctor.py --root /path/to/project
```

The wrapper consumes the redacted machine-readable `codex doctor --json` report and persists only a
sanitized record under `.harness-state/codex-runtime.json` (the installer's own run passes
`--no-persist` and writes none):

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

### Hook trust and hook dependency reasons

`codex doctor --json` has no hook-trust field, in the pinned 0.147.0 evidence or in the Codex
0.162.0 source. The harness doctor therefore cannot see whether you trusted the hooks, and it keeps
the result at `advisory` even after you do. Trusting the hooks is still required for them to run;
it just does not change the doctor's answer yet. A follow-up (#269) will read each hook's trust
status from the Codex app-server `hooks/list` request, which carries it in both versions.

| Reason | What it means | How to clear it |
|---|---|---|
| `TRUST_UNKNOWN` | The doctor has no trust signal at all: `codex doctor --json` carries none, and the doctor found no `trust_level` it could read safely for this project in the user-level Codex `config.toml`. That includes a config that does set `trust_level`, when the doctor declines to parse the file (a multi-line array or triple-quoted string anywhere in it) or the `[projects."…"]` key is not exactly the resolved project path (for example a symlinked path). It is also reported whenever the doctor cannot get a `codex doctor --json` report. | Trust the hooks in Codex (see "Trust the hooks"). This reason cannot be cleared by the doctor today; it stays until the `hooks/list` follow-up lands. |
| `TRUST_CONFIG_ONLY` | The user-level Codex `config.toml` sets `trust_level = "trusted"` for this project. That is project approval, not proof that the hooks run, so the result stays `advisory`. | Make sure the hooks themselves are trusted in `/hooks`. The reason itself stays until the doctor can read per-hook trust. |
| `HOOKS_UNTRUSTED` | The trust signal says untrusted: the config `trust_level` for this project is set to something other than `trusted`. | Review the project's trust in Codex itself, then trust the hooks. Do not edit or copy trust entries to make the doctor pass. |
| `HOOK_DEPENDENCY_MISSING` | A hook cannot find the Python helper it needs. `commit-gate.sh` needs `verify_summary.py` in `scripts/`, `.claude/scripts/`, or `.codex/.agent-harness/payload/scripts/`; `session-knowledge.sh` needs `runtime_mode.py` in `runtime/`, `.claude/runtime/`, or `.codex/.agent-harness/payload/runtime/`. The record's `diagnostic_summary.hook_dependencies_missing` names the affected hooks, separated by commas. It is not checked when the install is missing or its manifest is invalid, because those already make the result `unsupported`. | Reinstall; that restores the payload under `.codex/.agent-harness/payload/`. |

Two limits of the `HOOK_DEPENDENCY_MISSING` check:

- The hooks look for their helpers in the directory Codex runs them in (`CLAUDE_PROJECT_DIR`, or
  else the git top level), while the doctor looks under `--root`. When the project is a
  subdirectory of a larger git repository, the two can differ, and the doctor can report the
  helpers as present while the hooks cannot find them, or the other way round.
- `session-knowledge.sh` also looks for `runtime/run_state.py`, but only at the repository root,
  not in the payload. In a Codex install its active-runs section is therefore empty. The doctor
  does not report this.

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
`.gitignore` line, so delete it by hand if you no longer want it. The workflow files created by
`init-structure.sh` (`specs/`, `docs/solutions/`, and `techstacks/` files listed under "What the
installer prints after an install") are also left in place, because they are yours and are not in
the deployment manifest.

The deployer stages a complete render before changing target state. If marketplace or plugin
registration fails, it removes the partial registration and restores the previous persistent
marketplace before returning an error. Re-run the install after correcting the Codex CLI or source
problem; do not delete `.codex/config.toml` or trust entries as a recovery step.
