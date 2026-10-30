---
name: release-notes
description: Drafts technical GitHub Release notes and a fact-list JSON from a milestone or a git range. Use when the user asks for release notes, a changelog draft, or what shipped in a version. Draft only. It never tags, pushes, publishes or merges.
disable-model-invocation: true
allowed-tools: Read, Write, Grep, Glob, Bash(gh pr list *), Bash(gh pr view *), Bash(gh issue list *), Bash(gh issue view *), Bash(git log *), Bash(git describe *), Bash(mkdir *)
---

# Release Notes - draft only

## Input

- `--milestone <name>`: use GitHub through `gh`. This is the first choice.
- `<from>..<to>`: a git range. Use it when the user gives no milestone.
- Optional: `--version <x.y.z>`, `--out <path>`, `--exclude-label <name>`.
- Do not read Linear.

If neither is given, ask which one to use.

## Version

Take the first source that gives a value:

1. `--version`
2. The manifest: `package.json`, `pyproject.toml`, `Cargo.toml`, `VERSION`
3. The latest tag: `git describe --tags --abbrev=0`
4. The literal text `[NEEDS HUMAN]`

Never write or change a version.

## Collect

For a milestone, collect the union of (a) PRs tagged with the milestone and (b) PRs found through its issues: `gh issue list --milestone "<name>" --state all`, then a merged-PR search `<n> in:title,body` per issue. The commands and the match rule are in `references/fact-list-schema.md`. Build `tickets` from (b). When both give no PR, print `0 PRs found`, ask the user, and write no draft.

For a range, list the commits with `git log <from>..<to> --format='%h|%an|%aI|%s'`. Read a PR with `gh pr view <number> --json title,body,labels,author,mergedAt,closingIssuesReferences`.

Record the facts per item, map each ticket to its PRs, and list commits with no PR separately. The field list is in `references/fact-list-schema.md`.

Count the items found. Filter the noise first, by the rules in the reference, and record each reason.

## Rules for every entry

- Every bullet in the draft cites its PR number, for example `(#12)`. In a range run, cite the commit hash.
- Every claim comes from a PR title, PR body or commit message. No source: `[NEEDS HUMAN]`.

## Sections

Write these sections in order. Leave out an empty one, except Breaking changes, which says `None.`.

1. **Highlights**: the 3 to 5 most important user-facing changes, one line each.
2. **Breaking changes**: every item with a breaking signal (see the reference). Copy the title verbatim, one line each. A suspect goes in a `Needs confirmation` list. Under each title, write `Migration:` and the PR-body steps, or `[NEEDS HUMAN]`.
3. **Features**: `feat` PRs that are not breaking.
4. **Fixes**: `fix` PRs that are not breaking.
5. **Internal**: `perf`, `refactor`, `docs`, `test`, `chore`, `build`, `ci` PRs that are not breaking. A title with no type goes here too.
6. **Known limitations**: list each PR-body section `Risk`, `Known issues` or `Limitations` with its PR number. If none, omit this heading.

## Counts

End the draft with this line and print it:

`PRs in milestone: <n> | in notes: <m> | excluded: <k> (<reason>: <count>, ...)`


## Output

Write two files side by side. The default draft path is `docs/releases/v<version>.md`; `--out` overrides it. Make the folder if missing. With version `[NEEDS HUMAN]`, use `docs/releases/unversioned.md`.

- `<draft path>`: the draft.
- `<draft path without .md>.json`: the fact list. The shape is in `references/fact-list-schema.md`.

Report the two paths and the counts line.

## Never

This skill writes only the two files above. It does not:

- create a tag
- push to a remote
- create or edit a GitHub release
- merge a branch or a PR
- edit a version in any file
