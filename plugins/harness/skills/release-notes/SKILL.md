---
name: release-notes
description: Drafts technical GitHub Release notes and a fact-list JSON from a milestone or a git range. Use when the user asks for release notes, a changelog draft, or what shipped in a version. Draft only. It never tags, pushes, publishes or merges.
disable-model-invocation: true
allowed-tools: Read, Write, Grep, Glob, Bash(gh pr list *), Bash(gh pr view *), Bash(git log *), Bash(git describe *)
---

# Release Notes - draft only

Write a draft and a fact list. A human reviews both and publishes the release.

## Input

- `--milestone <name>`: use GitHub through `gh`. This is the first choice.
- `<from>..<to>`: a git range. Use it when the user gives no milestone.
- Linear is a later follow-up. Do not read it.

If the user gives neither input, ask which one to use.

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
gh pr list --state merged --search 'milestone:"<name>"' --json number,title,body,url --limit 200
```

For a range, list the commits with `git log <from>..<to> --format='%h %s'`. Read a PR with `gh pr view <number> --json title,body`.

## Breaking changes

Every PR title that contains `!:` is a breaking change. Copy the title verbatim, one line each. Do not reword it.

## Groups

Put every other PR under its conventional-commit type: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `chore`. A title with no type goes under `other`. Leave out an empty group.

## Known limitations

Read the PR-body sections `Risk`, `Known issues` and `Limitations`. List each one with its PR number. If no PR has such a section, omit this heading.

## Output

Write two files side by side:

- `release-notes-<version>.md`: the draft.
- `release-notes-<version>.json`: the fact list. The shape is in `references/fact-list-schema.md`.

Report the two paths. Do not publish them.

## Never

Do not run any of these. Each one is outside this skill:

- git tag (create a tag)
- git push
- gh release (create or edit a release)
- git merge
- Edit a version in any file
