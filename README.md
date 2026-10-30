<p align="center">
  <img src="docs/assets/skill-harness-hero.jpg" alt="A miniature papercraft workshop moving coding tasks through discovery, design, planning, execution, review, and shipping gates" width="100%">
</p>

<div align="center">

# Skill Harness

**A ready-to-use toolkit of skills, agents, and hooks for the [Claude Code](https://claude.com/claude-code) CLI**

*Prompt-powered workflows that carry a change from brainstorm to ship.*

📖 **[Read the Guide →](https://skill-harness-guide.vercel.app)**

</div>

---

Skills are Markdown prompt programs you summon with `/harness:skill-name`. The harness is a Claude Code plugin, so every skill carries the `harness:` prefix. They run a change from a ticket to a reviewed pull request, and a human merges it.

## How a change flows

```
ticket -> /harness:intake -> verdict + depth -> build -> review -> ship
```

- `/harness:intake` returns a verdict (READY, CONFIRM, GRILL or BLOCKED) and a depth (S, M or L).
- Depth S goes straight to `implement`. Depth M adds `writing-plans`. Depth L adds `brainstorming` and `xia2` first.
- A bug fix first runs `diagnosing-bugs`: the root cause is proved before any fix.
- `/code-review` and `intent-review` check the diff. `finishing-a-development-branch` pushes and opens the PR.
- `/harness:autopilot` asks the owner every open question once, then runs the whole flow for one or more tickets.

One principle drives it: **ceremony scales with the size of the change, and human interruption scales with ambiguity.**

See [HARNESS.md](HARNESS.md) for the model, [plugins/harness/skills/README.md](plugins/harness/skills/README.md) for every skill and handoff, and
[docs/hooks.md](docs/hooks.md) for what the five hooks enforce, including `merge-guard.sh`, which blocks any `gh pr merge` whose PR base is not `feat/*` and fails closed.

## Installation

### Add to a project

```bash
claude plugin marketplace add minhtran3124/agent-harness
claude plugin install harness@agent-harness
```

Then, in the project, run `/harness:setup`. It scaffolds `specs/` and `docs/solutions/`, proposes a `## Run and test` section for your `CLAUDE.md` if it has none, merges the `permissions.deny` rules into `.claude/settings.json` (needs [jq](https://jqlang.github.io/jq/)), and adds `specs/` to `.gitignore`. Every step is safe to run twice. A plugin cannot ship `permissions.deny`, which is why setup does it. Restart Claude Code after installing so it loads the skills, agents and hooks.

Needs `git` and `python3`. The ship workflow also needs the `Workflow` tool.

### Upgrading from 2.x

Version 5.0.0 is a breaking change: skills become `/harness:<name>`, hook profiles and several rules are gone. Follow the Migration steps in the 5.0.0 entry in [CHANGELOG.md](CHANGELOG.md).

### Move from the old copied install

Earlier versions copied the harness into the project's `.claude/` with `install-harness.sh`. That script is gone. Run `/harness:setup`: it lists the old copied files (by the names this plugin ships) and deletes them only after you approve. Keep both copies and every hook would run twice.

### Known limits

- Not verified yet (tracked for the dogfood run, #352): an unattended `ship.js` run from the plugin cache, the hooks firing in a live session, and a git-sourced marketplace install.
- Merge policy: the workflow merges only gated ticket PRs into `feat/<slug>`; every PR into the base branch is a human merge, and `merge-guard.sh` enforces that. Setup offers no allow rule: the owner who wants ticket PRs merged by the run must allow `gh pr merge` into `feat/<slug>*` (for example a `Bash(gh pr merge *)` allow rule; the guard still blocks other bases). In default permission mode the merge stage is otherwise denied; the run then reports the missing permission as the reason and does not work around it.
- `/harness:autopilot` launches the `autopilot-run` workflow by name (`harness:autopilot-run`), which works from any working directory. If a session does not know the name, the Workflow tool refuses a `scriptPath` it cannot read: add the plugin directory with `/add-dir`, or pass `ship.js` inline through `script`.
- After a plugin update, a running session can keep a stale `harness:autopilot-run`. Restart Claude Code (the main fix; `/reload-plugins` is named by the plugin CLI help but not confirmed here). Or, when `plugins/harness/workflows/ship.js` of this repo is inside the working directory or an added directory (`/add-dir`), launch it with `scriptPath`. The completion report names the script that ran, from the `Script file:` line of the Workflow result.
- The workflow was renamed from `ship` to `autopilot-run` (PR 509). The by-name launch is not yet verified under the new name: after a restart, run a `--no-ask` dry run and confirm the Workflow tool finds `harness:autopilot-run`. `docs/adr/0001-workflow-capabilities.md` still records the earlier `harness:ship` check.

### Develop on this repo

The plugin source is `plugins/harness/`. Load it straight from the checkout, with no copy step:

```bash
claude --plugin-dir plugins/harness
```

Check it with `claude plugin validate plugins/harness --strict` and `claude plugin validate . --strict`.

### Test

`bash scripts/run-tests.sh` runs what CI runs: syntax checks, the doc-truth and markdown-link lints, the frontmatter and tool-conformance checks, hermetic hook and script tests, and the Python unit tests when `pytest` is available. The `harness-ci` workflow runs it on ubuntu and macOS.

## Author

**Minh Tran** - [@minhtran3124](https://github.com/minhtran3124) - <tranhuuminh3124@gmail.com>. See [`CONTRIBUTORS.md`](CONTRIBUTORS.md).

## License

MIT. See [LICENSE](LICENSE).
