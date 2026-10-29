---
name: setup
description: "First-run setup for a project that installed the harness plugin. Scaffolds specs and docs, proposes a Run and test section for CLAUDE.md (and migrates an old agents/PROJECT.md), merges the permissions.deny rules into project settings, offers an allow rule for gh pr merge, ignores specs/, and offers to remove an old copied install. Use when the plugin was just installed in a project."
disable-model-invocation: true
allowed-tools: Read, Bash, AskUserQuestion
---

# Setup

Run once per project, after `claude plugin install harness@agent-harness`. Work in the project root
(`${CLAUDE_PROJECT_DIR}`). Say what each step did. Every step is safe to run twice.

1. **Scaffold.** Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/init-structure.sh --root ${CLAUDE_PROJECT_DIR}`.
   It creates `specs/` and `docs/solutions/` README files, and never overwrites.
2. **Run and test.** If `${CLAUDE_PROJECT_DIR}/CLAUDE.md` has no `## Run and test` section, propose
   one (test, targeted test, lint, full suite), detected from the manifests, and show it. Write it
   only after the owner agrees (AskUserQuestion). If an old `agents/PROJECT.md` exists, propose
   moving its *Test execution* into that section, and ask before deleting the file.
3. **Deny rules.** A plugin cannot ship `permissions.deny`, so merge it into the project settings.
   Run `bash ${CLAUDE_SKILL_DIR}/scripts/merge-deny.sh --dry-run ${CLAUDE_PROJECT_DIR}/.claude/settings.json`
   and show the diff. After the owner agrees, run it again without `--dry-run`. It needs `jq`
   (exit 3 if missing) and refuses a file that is not valid JSON or whose permissions, allow or deny has the wrong type (exit 2, file untouched). It adds
   these rules and keeps every existing one: `.env` read and edit, force-push, push to main or master.
4. **Merge allow rule (optional).** Offer one rule, `Bash(gh pr merge *)`, in the owner's untracked
   `${CLAUDE_PROJECT_DIR}/.claude/settings.local.json`. Run
   `bash ${CLAUDE_SKILL_DIR}/scripts/merge-allow.sh --dry-run ${CLAUDE_PROJECT_DIR}/.claude/settings.local.json`,
   show the diff, and ask with AskUserQuestion. Run it again without `--dry-run` only after the owner
   says yes. It has the same exit codes as step 3. Say plainly that auto mode may still deny the
   merge (run 1 did), and that the run then reports the missing permission (#389).
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
project wrote itself. Only step 4 may write `.claude/settings.local.json`, and only after the owner
says yes.

Finish with a short list of what changed, what was skipped, and what the owner still has to do.
