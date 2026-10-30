---
name: setup
description: "First-run setup for a project that installed the harness plugin. Scaffolds specs and docs, proposes a Run and test section for CLAUDE.md (and migrates an old agents/PROJECT.md), merges the permissions.deny rules into project settings, names the merge guard, ignores specs/, and offers to remove an old copied install. Use when the plugin was just installed in a project."
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Setup

Run once per project, after `claude plugin install harness@agent-harness`. Work in the project root
(`${CLAUDE_PROJECT_DIR}`). Say what each step did. Every step is safe to run twice.

1. **Scaffold.** Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/init-structure.sh --root ${CLAUDE_PROJECT_DIR}`.
   It creates `specs/` and `docs/solutions/` README files, and never overwrites.
2. **Run and test.** If `${CLAUDE_PROJECT_DIR}/CLAUDE.md` has no `## Run and test` section, propose
   one (test, targeted test, lint, full suite), detected from the manifests, and show it. Write it
   only after the owner agrees (AskUserQuestion), with Edit (or Write if `CLAUDE.md` does not
   exist). If an old `agents/PROJECT.md` exists, propose moving its *Test execution* into that
   section, and ask before deleting the file (`rm -- ${CLAUDE_PROJECT_DIR}/agents/PROJECT.md`). Running it twice is safe:
   skip the write when the section exists, and skip the migration when `agents/PROJECT.md` is gone.
3. **Deny rules.** A plugin cannot ship `permissions.deny`, so merge it into the project settings.
   Run `bash ${CLAUDE_SKILL_DIR}/scripts/merge-deny.sh --dry-run ${CLAUDE_PROJECT_DIR}/.claude/settings.json`
   and show the diff. After the owner agrees, run it again without `--dry-run`. It needs `jq`
   (exit 3 if missing) and refuses a file that is not valid JSON or whose permissions, allow or deny has the wrong type (exit 2, file untouched). It adds
   these rules and keeps every existing one: `.env` read and edit, force-push, push to main or master.
4. **Merge guard (nothing to install).** The plugin registers `merge-guard.sh`, a PreToolUse hook:
   `merge-guard.sh` blocks every merge whose PR base is not `feat/*`; it fails closed. Tell the owner
   that every PR into the base branch is a human merge, and that ticket PRs into `feat/<slug>` stay
   human-merged too unless they merge them: setup writes no allow rule for `gh pr merge`, because no
   command-text rule can see the PR base. Plugin hooks are not proven to fire for workflow agents, so
   the guard is a second line, not a reason to allow the merge.
5. **Ignore specs.** Add `specs/` to `${CLAUDE_PROJECT_DIR}/.gitignore` if no line already says
   `specs/`. Skip this if the project tracks files under `specs/`.
6. **Old install.** Run `bash ${CLAUDE_SKILL_DIR}/scripts/old-install.sh ${CLAUDE_PROJECT_DIR}`. An
   empty list means there is nothing to remove: stop here. Otherwise print the list and ask with
   AskUserQuestion whether to delete it (recommended answer: yes). Delete only after the owner
   says yes, with `rm -r -- <the listed paths>`, and only those paths. If `.claude/settings.json`
   has hook entries that point into `.claude/hooks/`, they would run twice: ask, then run
   `bash ${CLAUDE_SKILL_DIR}/scripts/old-install.sh --strip-hooks ${CLAUDE_PROJECT_DIR}/.claude/settings.json`.
   Ask separately about `.claude/rules/behavior.md`: the plugin now delivers that rule at session
   start, so a copy loads it twice.

Never touch: `specs/`, `docs/`, and any skill, agent or hook the
project wrote itself. Setup never writes `.claude/settings.local.json`.

Finish with a short list of what changed, what was skipped, and what the owner still has to do.
