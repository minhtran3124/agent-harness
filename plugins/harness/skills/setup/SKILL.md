---
name: setup
description: "First-run setup. Use when a project has just installed the harness plugin. Scaffolds specs, docs and techstacks, creates agents/PROJECT.md, merges the permissions.deny rules into project settings, ignores specs/, and offers to remove an old copied install."
disable-model-invocation: true
allowed-tools: Read, Bash, AskUserQuestion
---

# Setup

Run once per project, after `claude plugin install harness@agent-harness`. Work in the project root
(`${CLAUDE_PROJECT_DIR}`). Say what each step did. Every step is safe to run twice.

1. **Scaffold.** Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/init-structure.sh --root ${CLAUDE_PROJECT_DIR}`.
   It creates `specs/`, `docs/solutions/` and `techstacks/` README files, and never overwrites.
2. **Agent index.** If `agents/PROJECT.md` does not exist, copy
   `${CLAUDE_SKILL_DIR}/resources/PROJECT.template.md` to it. Never overwrite an existing file.
   Tell the owner to fill in its *Test execution* section.
3. **Deny rules.** A plugin cannot ship `permissions.deny`, so merge it into the project settings.
   Run `bash ${CLAUDE_SKILL_DIR}/scripts/merge-deny.sh --dry-run ${CLAUDE_PROJECT_DIR}/.claude/settings.json`
   and show the diff. After the owner agrees, run it again without `--dry-run`. It needs `jq`
   (exit 3 if missing) and refuses a file that is not valid JSON (exit 2, file untouched). It adds
   these rules and keeps every existing one: `.env` read and edit, force-push, push to main or master.
4. **Ignore specs.** Add `specs/` to `${CLAUDE_PROJECT_DIR}/.gitignore` if no line already says
   `specs/`. Skip this if the project tracks files under `specs/`.
5. **Old install.** Run `bash ${CLAUDE_SKILL_DIR}/scripts/old-install.sh ${CLAUDE_PROJECT_DIR}`. An
   empty list means there is nothing to remove: stop here. Otherwise print the list and ask with
   AskUserQuestion whether to delete it (recommended answer: yes). Delete only after the owner
   says yes, with `rm -r -- <the listed paths>`, and only those paths. If `.claude/settings.json`
   has hook entries that point into `.claude/hooks/`, they would run twice: ask, then run
   `bash ${CLAUDE_SKILL_DIR}/scripts/old-install.sh --strip-hooks ${CLAUDE_PROJECT_DIR}/.claude/settings.json`.
   Ask separately about `.claude/rules/behavior.md`: the plugin now delivers that rule at session
   start, so a copy loads it twice.

Never touch: `specs/`, `docs/`, `techstacks/`, `agents/PROJECT.md`, `.claude/settings.local.json`,
and any skill, agent or hook the project wrote itself.

Finish with a short list of what changed, what was skipped, and what the owner still has to do.
