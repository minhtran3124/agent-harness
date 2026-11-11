# Issue #700: Add tally.sh

Add `tally.sh`, a small calculator CLI, at the root of the repository.

## Acceptance criteria

- AC1: `bash tally.sh add 2 3` prints `5` and exits 0.
- AC2: `bash tally.sh mul 2 3` prints `6` and exits 0.
- AC3: `bash tally.sh` with no arguments prints a line that starts with `usage:` to stderr and exits 2.
