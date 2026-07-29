# Task
Add a `--dry-run` flag and ensure it does not write files.

# Implementation
`run.py` parses `--dry-run` but always calls `write_output()`.
