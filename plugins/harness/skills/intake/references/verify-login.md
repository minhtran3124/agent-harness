# Verify login check

Run this when a `Verify:` row logs in, before you judge the verdict.

## When the row logs in

The row, or the ticket's acceptance text, matches one of these (case-insensitive): log in, login,
sign in, `VERIFY_USER`, `VERIFY_PASSWORD`, password, credentials, a dashboard behind a login.

## Check the variables by name

Check only the variables the row mentions. If it only says login, check both
`VERIFY_USER` and `VERIFY_PASSWORD`. Run one check per variable. The command is read-only and
prints nothing; the exit code is the answer (0 = set, 1 = unset):

```bash
test -n "$VERIFY_USER"
```

No format check, like the `Verify:` row rule.

## Rules

- Never print a value. Do not echo, `env` or `printenv` a variable.
- Never read, grep or list `.env` or any secrets file. This is a rule in the text only: the repo
  `settings.json` denies `Read` of `.env`, but not `Grep`, `Glob` or `ls`. Follow the rule yourself.

## A variable is unset

This is one of the CONFIRM questions (it counts in the 1-3). Offer three answers, in this order:

1. Use throwaway credentials for a local test server (recommended).
2. The owner sets the variables, then the run starts.
3. Skip the login steps of the `Verify:` row.

The accepted answer goes into the Confirmed decisions comment, so the workflow does not stop at
the end.

## Mode: auto

Take answer 1 (throwaway credentials) and record it as a decision with `needs_review: true`.
