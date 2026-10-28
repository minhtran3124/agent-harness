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

Skills are Markdown prompt programs you summon with `/skill-name`. They run a change from a ticket to a reviewed pull request, and a human merges it.

## How a change flows

```
ticket -> /intake -> verdict + depth -> build -> review -> ship
```

- `/intake` returns a verdict (READY, CONFIRM, GRILL or BLOCKED) and a depth (S, M or L).
- Depth S goes straight to `implement`. Depth M adds `writing-plans`. Depth L adds `brainstorming` and `xia2` first.
- A bug fix first runs `diagnosing-bugs`: the root cause is proved before any fix.
- `/code-review` and `intent-review` check the diff. `finishing-a-development-branch` pushes and opens the PR.
- `/autopilot` asks the owner every open question once, then runs the whole flow for one or more tickets.

One principle drives it: **ceremony scales with the size of the change, and human interruption scales with ambiguity.**

See [HARNESS.md](HARNESS.md) for the model, [skills/README.md](skills/README.md) for every skill and handoff, and
[docs/hooks.md](docs/hooks.md) for what the three hooks enforce.

## Installation

### Add to an existing project

```bash
curl -fsSL "https://raw.githubusercontent.com/minhtran3124/agent-harness/main/scripts/install-harness.sh?$(date +%s)" | bash -s -- --yes
```

This clones the harness and builds a gitignored `.claude/` (skills, agents, hooks, the rule, templates, a consumer subset of `scripts/`, settings). At the project root it only adds missing scaffold folders (`specs/`, `docs/solutions/`); it never overwrites or deletes anything there. To update, run the one-liner again. A protected file that differs from the incoming copy is kept, and the incoming copy is written beside it as `<file>.harness-incoming`.

Needs `git`, [jq](https://jqlang.github.io/jq/) and `python3`. Flags: `--directory <path>`, `--branch <name>`, `--source <local checkout>`, `--keep-sources`, `--dry-run`, `--overwrite-conflicts`. Restart Claude Code afterwards so it loads the skills, agents and hooks.

### Develop on this repo

The editable source is at the repo root; Claude Code loads from the derived `.claude/`. Rebuild it after editing `skills/`, `agents/`, `hooks/`, `rules/`, `templates/` or `settings.json`:

```bash
bash scripts/deploy-harness.sh
```

### Test

`bash scripts/run-tests.sh` runs what CI runs: syntax checks, the doc-truth and markdown-link lints, the frontmatter and tool-conformance checks, hermetic hook and script tests, and the Python unit tests when `pytest` is available. The `harness-ci` workflow runs it on ubuntu and macOS.

## Author

**Minh Tran** - [@minhtran3124](https://github.com/minhtran3124) - <tranhuuminh3124@gmail.com>. See [`CONTRIBUTORS.md`](CONTRIBUTORS.md).
