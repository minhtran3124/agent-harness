---
name: release-summary
description: Turns the release-notes fact-list JSON into a cited summary draft for a team, a client or stakeholders. Use when the user asks for a release summary or a stakeholder update of a version. Draft only. It never tags, pushes, publishes or merges.
disable-model-invocation: true
allowed-tools: Read, Write, Glob
---

# Release Summary - draft only

Write a plain-language summary of one release. The only source is the fact-list JSON that `/harness:release-notes` wrote. Do not collect PRs, read git, or call `gh`.

## Input

- `<path>`: the fact-list JSON. Without it, use `docs/releases/v<version>.json` (find it with Glob).
- If the file is missing, stop and ask the user for the path or to run `/harness:release-notes` first. Never collect PRs yourself.
- Optional: `--out <path>`, `--audience team|client|stakeholder` (default `stakeholder`).
- Read `references/audiences.md` for the tone and `references/summary-format.md` for the line format.

## Output

Write one file: `docs/releases/v<version>-summary.md`. `--out` overrides the path. When `version` is `[NEEDS HUMAN]`, use `docs/releases/unversioned-summary.md`. Report the path.

## What to include

- Include `breaking` items and the `groups` types `feat` and `fix`.
- Leave out the Internal types (`perf`, `refactor`, `docs`, `test`, `chore`, `build`, `ci`, `other`), `excluded` and `no_pr_commits`.
- The audience changes tone and detail only. It never changes which facts appear.

## Sections

Write these in order. Leave out an empty one, except Breaking changes, which says `None.`.

1. **Breaking changes**: one bullet per item in plain language. Under each, an indented line `What you need to do:` with the steps. No steps in the facts: `[NEEDS HUMAN]`.
2. **What's new**: group `feat` and `fix` items by the outcome for the reader, not by type.
3. **What to watch**: each entry in `limitations`, with its PR number.
4. **To confirm**: each item with `needs_confirmation` set, tagged `[NEEDS HUMAN]`. Never show it as breaking.

## Rules for every statement

- Every bullet cites a PR number from the fact list, for example `(#12)`.
- A claim with no PR in the facts carries `[NEEDS HUMAN]`. Do not invent a date, a metric or a benefit.
- Write for a human reader. Short sentences, active voice, no jargon, no PR titles copied as text. You may use the `asd-ste100` STE-flavored mode for a check, but do not apply its rules word for word.

## Never

This skill writes only the file above. It does not:

- create a tag
- push to a remote
- create or edit a GitHub release
- merge a branch or a PR
