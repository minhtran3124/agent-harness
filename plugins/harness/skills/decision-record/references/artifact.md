## The artifact

If the user-level `ink-artifact` skill and the Artifact tool exist, build ONE artifact per run with
`ink-artifact`: one section per ticket, `needs_review` decisions first. Keep it private. The ADR
files are the source of truth, because a private artifact may not open for reviewers.
If the Artifact tool is unavailable, skip it and link `docs/adr/` in the PR body.
