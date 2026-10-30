---
name: release-notes
description: Drafts technical GitHub Release notes and a fact-list JSON from a milestone or a git range. Use when the user asks for release notes, a changelog draft, or what shipped in a version. Draft only. It never tags, pushes, publishes or merges.
disable-model-invocation: true
allowed-tools: Read, Write, Grep, Glob, Bash(gh pr list *), Bash(gh pr view *), Bash(git log *), Bash(git describe *), Bash(mkdir *)
---

# Release Notes - draft only

Write a draft and a fact list. A human reviews both and publishes the release.

## Input

- `--milestone <name>`: use GitHub through `gh`. This is the first choice.
- `<from>..<to>`: a git range. Use it when the user gives no milestone.
- `--version <x.y.z>` and `--out <path>`: optional.
- Linear is a later follow-up. Do not read it.

If the user gives neither a milestone nor a range, ask which one to use.

## Version

Take the first source that gives a value:

1. `--version`
2. The manifest: `package.json`, `pyproject.toml`, `Cargo.toml`, `VERSION`
3. The latest tag: `git describe --tags --abbrev=0`
4. The literal text `[NEEDS HUMAN]`

Never write or change a version.

## Collect

For a milestone:

```bash
gh pr list --state merged --search 'milestone:"<name>"' --json number,title,body,url,labels,author,mergedAt --limit 200
```

For a range, list the commits with `git log <from>..<to> --format='%h %s'`. Read a PR with `gh pr view <number> --json title,body,labels,author,mergedAt`.

Record one fact per item: PR number, title, labels (names), author login, merge date (`mergedAt`) and a `breaking` flag. The `breaking` flag is set by the rules in Breaking changes below. In a range run, the author and date come from `git log --format='%h|%an|%aI|%s'`, and labels are empty.

Count the items found. Drop each item that is not a user-facing change (for example `revert`, `duplicate`) and record its reason. Keep an item when you are unsure.

## Rules for every entry

- Every bullet in the draft cites its PR number, for example `(#12)`. In a range run, cite the commit hash.
- Every claim comes from a PR title, PR body or commit message. A claim with no source becomes `[NEEDS HUMAN]`.

## Sections

Write these sections in this order. Leave out an empty section, except Breaking changes, which says `None.`.

1. **Highlights**: the 3 to 5 most important user-facing changes, one line each.
2. **Breaking changes**: every PR title that contains `!:`. Copy the title verbatim, one line each. Do not reword it. Under each title, write `Migration:` and the steps from the PR body, or `[NEEDS HUMAN]` if it has none.
3. **Features**: `feat` PRs that are not breaking.
4. **Fixes**: `fix` PRs that are not breaking.
5. **Internal**: `perf`, `refactor`, `docs`, `test`, `chore`, `build`, `ci` PRs that are not breaking. A title with no type goes here too.
6. **Known limitations**: read the PR-body sections `Risk`, `Known issues` and `Limitations`. List each one with its PR number. If no PR has such a section, omit this heading.

## Counts

Put one line at the end of the draft and print it:

`PRs in milestone: <n> | in notes: <m> | excluded: <k> (<reason>: <count>, ...)`

The fact list holds the excluded items.

## Output

Write two files side by side. The default draft path is `docs/releases/v<version>.md`; `--out` overrides it. Make the folder if it is missing. With version `[NEEDS HUMAN]`, use `docs/releases/unversioned.md`.

- `<draft path>`: the draft.
- `<draft path without .md>.json`: the fact list. The shape is in `references/fact-list-schema.md`.

Report the two paths and the counts line. Do not publish them.

## Never

This skill reads GitHub and git and writes only the two files above. It does not:

- create a tag
- push to a remote
- create or edit a GitHub release
- merge a branch or a PR
- edit a version in any file
