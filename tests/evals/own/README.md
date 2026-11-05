# Evals for /harness:own

Each folder is one case, in the layout `claude plugin eval` reads: `prompt.md` (settings block,
then the owner's prompt), `case.yaml` (expected outcome), `graders/` (one assertion per file) and
`files/` (inputs, copied into the run directory by `place-files.sh`).

The cases live here, not under `plugins/harness/skills/own/`, so they do not ship with the plugin.
Runs cost model usage, so CI does not run them. Results are not committed.

`/harness:own` is interactive, and an eval run has no live owner. So each `prompt.md` carries the
owner's answers and a "Test rules" block: no `AskUserQuestion`, every question and reply goes to
`transcript.md`, files only under the run directory.

| Case | Checks |
|---|---|
| `grill-asks-owner-first-on-big-decisions` | At most 3 big decisions; open question first; recommendation, counter-argument and final choice after the owner's answer; extra lines in `decision.md` |
| `brainstorm-asks-sketch-then-teach-back` | Sketch before approaches; breaking assumptions with checks; teach-back with gaps, no grade; sections in `design.md` |
| `refuses-no-ask-run` | `--no-ask` stops the skill |
| `asks-for-mode-when-missing` | A missing mode is asked for first |

## Run with the CLI

From the repo root:

    bash tests/evals/own/run.sh --runs 1
    bash tests/evals/own/run.sh --case 'grill-*'

`run.sh` copies the plugin and these cases to a temp directory, because `claude plugin eval`
reads cases only from below the plugin. It prints the results path. The CLI adds a baseline arm
without the plugin, so the baseline here is "no skill".

## Run with sub-agents (skill-creator loop)

Ask Claude to run the evals in `tests/evals/own` with the skill-creator skill. For each case, a
sub-agent reads `plugins/harness/skills/own/SKILL.md`, runs the prompt in a fresh directory that
holds the case's `files/`, and saves `transcript.md` and the written files there. A useful
baseline is the base skill alone: the same prompt with `/harness:grilling` or
`/harness:brainstorming` in place of `/harness:own <mode>`. It shows what `own` adds.
