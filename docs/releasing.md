# Releasing

`VERSION` and `plugins/harness/.claude-plugin/plugin.json` change only in a release PR. No other PR edits them, and no other PR edits `CHANGELOG.md` below the `[Unreleased]` heading.

## Cut a release

1. Open Actions, choose **release**, and run it from `main` with a bump: `patch` (fixes, docs), `minor` (new skill or hook, changed contract) or `major` (breaking change). The workflow refuses to start while a release PR is open or a `release/` branch exists that `main` does not contain: merge or close that PR, delete its branch, then run **release** again. The branch of a release that is already in `main` does not block, so you do not have to delete it before the next release.
2. The workflow opens one PR named `chore(release): vX.Y.Z`. Its body is the new CHANGELOG section. Read the section and fix the wording in the PR if needed.
3. Merge the PR. The **release-tag** workflow then creates the tag `vX.Y.Z` and the GitHub release from that CHANGELOG section.

The **release-tag** workflow tags whenever `VERSION` changes on `main`, `plugin.json` equals `VERSION`, and a `## [X.Y.Z]` section exists in `CHANGELOG.md`, whichever PR changed `VERSION`. So only the release PR should touch `VERSION`.

PR titles flow into the release notes. Read the CHANGELOG section in the release PR before you merge it: an `@name` in a title would mention that user when the release is published.

A PR opened with the workflow token does not start other workflows. If the release PR shows no CI checks, push an empty commit to its branch, or close and reopen it.

If **release** stops with `another release is in progress` (an open release PR, or a `release/` branch that `main` does not contain; the message names each one), merge or close the PR and delete the branch. If it stops with `Branch release/vX.Y.Z already exists` or `Tag vX.Y.Z already exists`, an earlier release PR for that version was closed without merging, or the version was tagged by hand. Delete the leftover branch (`git push origin --delete release/vX.Y.Z`) and run **release** again. The repository setting that lets Actions open pull requests is already on.

## What each script does

- `scripts/release.sh <patch|minor|major> [--dry-run]` raises the version in `VERSION` and `plugin.json`, then adds a dated `## [X.Y.Z]` section to `CHANGELOG.md`. The section holds the bullets that were under `[Unreleased]`, then one `- <PR title> (PR #N)` bullet for each PR merged since the last `v*` tag. It reads only the first-parent line of `main`: merge commits, and squash or rebase commits whose subject ends in `(#N)`. It refuses a dirty tree, an unknown bump word, and a version heading that already exists. `--dry-run` prints the next version and writes nothing.
- `scripts/release-tag.sh [--no-release]` checks that `plugin.json` equals `VERSION`, then creates the annotated tag `vX.Y.Z` at HEAD, pushes only that tag, and creates the GitHub release. It never moves, deletes or overwrites a tag: an existing tag must already point at a commit whose `VERSION` matches, or the script stops. A second run changes nothing.

Run `bash scripts/release.sh minor --dry-run` to preview a release. ADR 0031 records why the flow works this way.
