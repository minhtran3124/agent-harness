# Fact-list schema

The fact list is the JSON file written next to the release-notes draft. The `release-summary` skill reads it. Every value comes from a PR or a commit. Do not add a value that no PR or commit states.

```json
{
  "version": "1.4.0",
  "version_source": "flag | manifest | tag | needs-human",
  "source": { "type": "milestone | range", "value": "v1.4.0" },
  "breaking": [
    { "pr": 12, "title": "feat(api)!: drop v1 endpoints", "url": "https://github.com/o/r/pull/12", "labels": ["breaking"], "author": "alice", "merged_at": "2026-01-05T10:00:00Z", "breaking": true }
  ],
  "groups": {
    "feat": [{ "pr": 15, "title": "feat: add export", "url": "https://github.com/o/r/pull/15", "labels": [], "author": "bob", "merged_at": "2026-01-06T09:00:00Z", "breaking": false }],
    "fix": []
  },
  "limitations": [
    { "pr": 15, "section": "Known issues", "text": "Export stops at 10000 rows." }
  ],
  "tickets": [
    { "ticket": 40, "prs": [12, 15] }
  ],
  "no_pr_commits": [
    { "commit": "a1b2c3d", "title": "chore: bump lockfile", "author": "alice", "merged_at": "2026-01-04T08:00:00Z" }
  ],
  "counts": { "total": 3, "included": 2, "excluded": 1 },
  "excluded": [
    { "pr": 14, "title": "chore: revert #13", "reason": "revert" }
  ]
}
```

Rules:

- `tickets` maps each ticket (issue) number to the PRs that close it. Take it from `closingIssuesReferences` and from `Closes #n`, `Fixes #n` or `Resolves #n` in the PR body. A ticket with no merged PR in the set is not listed.
- `no_pr_commits` is used in a range run only. A commit belongs to a PR when its subject ends with `(#n)` or is a `Merge pull request #n` line. Every other commit goes to `no_pr_commits`, not to `groups`. In a range run, each commit with a PR is one item with that `pr`. It is an empty list in a milestone run.

- Every item in `breaking`, `groups` and `excluded` carries `labels` (list of names), `author` (login), `merged_at` (ISO date) and `breaking` (true or false). In a range run, `labels` is an empty list and `merged_at` is the commit date.

- `breaking` holds the PR titles that contain `!:`, copied verbatim.
- `groups` keys are the conventional-commit types. A PR in `breaking` is not repeated in `groups`.
- `limitations` is an empty list when no PR has a Risk, Known issues or Limitations section.
- In a range run, an item with no PR has `pr` set to `null` and `url` set to the commit hash.
- `counts.total` equals `counts.included` plus `counts.excluded`. `counts.included` is the number of PRs in the draft.
- `excluded` lists every PR left out of the draft, each with a `reason`. It is an empty list when none is left out.
- In `groups`, the keys `perf`, `refactor`, `docs`, `test`, `chore`, `build`, `ci` and `other` make up the Internal section of the draft.
- A value that has no source is the text `[NEEDS HUMAN]`.

## Noise filter

Run the filter on the collected facts, before any section is written. Exclude an item when one rule matches, and record the rule as its `reason`:

- `bot`: the author login ends with `[bot]` or is `dependabot` or `renovate`.
- `label:<name>`: a label is in the excluded list. The default list is `skip-changelog`, `duplicate`, `invalid`, `wontfix`, `no-release-notes`. The user can pass `--exclude-label <name>` to add more.
- `revert`, `duplicate`: the title says so (judged from the title).

Do not exclude an item when you are unsure. The counts line states how many items each reason removed.
