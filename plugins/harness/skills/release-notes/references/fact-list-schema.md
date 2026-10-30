# Fact-list schema

The fact list is the JSON file written next to the release-notes draft. The `release-summary` skill reads it. Every value comes from a PR or a commit. Do not add a value that no PR or commit states.

```json
{
  "version": "1.4.0",
  "version_source": "flag | manifest | tag | needs-human",
  "source": { "type": "milestone | range", "value": "v1.4.0" },
  "breaking": [
    { "pr": 12, "title": "feat(api)!: drop v1 endpoints", "url": "https://github.com/o/r/pull/12" }
  ],
  "groups": {
    "feat": [{ "pr": 15, "title": "feat: add export", "url": "https://github.com/o/r/pull/15" }],
    "fix": []
  },
  "limitations": [
    { "pr": 15, "section": "Known issues", "text": "Export stops at 10000 rows." }
  ]
}
```

Rules:

- `breaking` holds the PR titles that contain `!:`, copied verbatim.
- `groups` keys are the conventional-commit types. A PR in `breaking` is not repeated in `groups`.
- `limitations` is an empty list when no PR has a Risk, Known issues or Limitations section.
- In a range run, `pr` is `null` and `url` is the commit hash.
