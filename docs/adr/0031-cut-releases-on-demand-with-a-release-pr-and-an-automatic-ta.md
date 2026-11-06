---
ticket: 594
stage: design
status: accepted
confidence: high
decided_by: owner
date: 2026-11-06
---

# 0031. Cut releases on demand with a release PR and an automatic tag

## Context

This supersedes ADR 0022 (never hand-edit VERSION or CHANGELOG.md) and ADR 0029 (append the audit-log line in the bookkeeping script). Until now a workflow ran after every merged PR, bumped VERSION and the plugin manifest, and opened a bookkeeping PR. That made one version per PR, it needs a bot write path into main, and it breaks once main is protected (#530). The owner decided on 2026-11-06 that every VERSION is a deliberate release with a tag and a GitHub release.

## Options

- A bot commit to main after each merge (the old flow, kept).
- Fully manual: the author edits VERSION, plugin.json and CHANGELOG.md and tags by hand.
- On-demand release PR (workflow release.yml with a bump input) plus an automatic tag and GitHub release when that PR merges (release-tag.yml).

## Decision

Remove the post-merge bookkeeping workflow, its script and its test. Add scripts/release.sh and the release workflow to open one release PR on demand, and scripts/release-tag.sh and the release-tag workflow to tag and publish when VERSION changes on main. VERSION and plugin.json change only in the release PR; the bump (patch, minor, major) is chosen when releasing.

## Why

A release PR is reviewed like any other PR, so it works with a protected main. The tag step is automatic, so no release is forgotten, and it refuses to move an existing tag. Both scripts need no network except the tag push and gh, so tests run offline.

## Consequences

Enables: one version per deliberate release, a tag and a GitHub release for each, review of the CHANGELOG section before it ships. Constrains: nobody gets a version bump from a merge any more; an owner must run the Release workflow. A PR opened with the workflow token does not start other workflows, so the release PR needs a manual re-run or an owner token for CI. The audit-log and trust-metrics lines of the old script were already gone from it before this change.

## How to reverse

Restore the removed workflow, script and test from git history (the commit before the one that removed the bookkeeping flow, #594), and delete the release and release-tag workflows and scripts.
