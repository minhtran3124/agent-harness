# Summary format

The draft is Markdown. In the harness repo, `scripts/check_release_summary.py <fact-list.json> <draft.md>` checks it, so keep the format exact.

## Layout

```markdown
# Release <version> summary

## Breaking changes

- <plain-language change> (#12).
  What you need to do: <steps>

## What's new

- <outcome for the reader> (#15).

## What to watch

- <limitation text> (#15).

## To confirm

- <suspect item> (#18). [NEEDS HUMAN]
```

## Rules the checker enforces

- Every `(#n)` is a PR in `breaking` or `groups` of the fact list. A PR in `excluded` fails.
- Every top-level bullet under `## Breaking changes` is followed by an indented line that starts with `What you need to do:`.
- Every bullet cites `(#n)` or carries `[NEEDS HUMAN]`.

## Rules the checker does not enforce

- Internal types, `excluded` and `no_pr_commits` stay out of the draft.
- A `needs_confirmation` item goes under `## To confirm`, never under Breaking changes.
- The words must match what the PR states. Check this by hand.
