# opus-5-5-prompt-audit — Design

Status: approved (user selected all four edit groups, 2026-09-29).

## Decisions

1. **Where Opus 5.5 behavioral guidance lives.** Options: per-agent copies (`agents/coding.md`,
   implementer prompt) vs one always-on rule. Chosen: `rules/behavior.md` §4/§5, appended so
   §1–§3 keep their numbers (cited by `agents/reviewer.md` and the scorer). The implementer keeps
   only its task-specific completion bar (SC + `<verify>`). One wording, every role.
2. **Review caps.** Options: raise the caps vs remove them. Chosen: remove in the finder and task
   reviewer (the scorer is the precision stage; severity already routes blocking), and bound the
   scorer fan-out at 20 parallel dispatches — the documented delegation ceiling.
3. **Compound extraction.** Options: keep 3–4 subagents and paste a session digest, or run the
   passes in the session that holds the transcript. Chosen: in-session passes, with dispatch kept
   only for a solutions tree too large to screen from `INDEX.md`. The `subagents/` directory name
   stays (deploy manifests and tests reference it); its files become output schemas.
4. **Implementer dispatch.** Dispatch the `coding` subagent type with `model_stage: implementer`,
   matching the task-reviewer template, so the Opus 5.5 / effort-medium binding applies.
5. **Out of scope.** Deployed `.claude/` copies are not redeployed (needs explicit confirmation);
   `evals/context-boundaries/probes/*` still describe the old implementer/scorer dispatch and are
   recorded runs, not assertions.
