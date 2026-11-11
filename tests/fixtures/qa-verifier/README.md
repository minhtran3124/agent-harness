# qa-verifier fixture

`clean/tally.sh` is a small shell CLI that meets the three acceptance criteria in
`tests/evals/qa-verifier/*/files/issue.md`. `broken/tally.sh` is the same file with `mul` changed so
that it adds: AC2 fails. Both are inputs to the evals in `tests/evals/qa-verifier/`. Nothing in the
suite runs them.
