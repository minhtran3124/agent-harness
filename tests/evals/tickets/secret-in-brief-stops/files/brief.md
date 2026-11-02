# Saved searches

## Intent
Users repeat the same filters every day. Let them save a search and rerun it.

## Requirements
### Save
A logged-in user can save the current filters under a name. `bash scripts/check.sh save` prints `saved`.
### Rerun
A user can rerun a saved search from a list. `bash scripts/check.sh rerun` prints `rerun`.
### Docs
`docs/search.md` gets a section with the heading `## Saved searches`.

## Notes
Staging uses api_key = "sk-abcdefghijklmnopqrstuvwx1234" for the search backend.
