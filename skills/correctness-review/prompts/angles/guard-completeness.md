### `guard-completeness` — does the guard cover every way the thing can fail?

````
## Your method: `guard-completeness` — is the guard complete?

Look at every place this diff guards against a failure — a try/except, a validation, a check
before an operation, an error handler, a cleanup path.

For each one, ask: **does the guard cover every way the guarded thing can fail, or only the
failures the author had in mind?**

Two specific patterns produce most of these bugs:

**1. A list of exception types standing in for a boundary.**
`except (A, B, C)` is a claim that A, B, and C are the only ways the block can fail. When the
requirement is "this must never fail" — an advisory section, a non-blocking hook, a cleanup path
— a single unlisted failure defeats it. Ask what bounds the **whole block** rather than the
listed statements: `|| true` on the command in shell, a catch at the top level, a supervisor.

To report this, **you must name the specific unlisted failure that escapes** — the exception
type, the exit code, the signal. If you cannot name one, you do not have a finding.

**2. A guard that does not span the whole operation it is supposed to protect.**
Look at what runs immediately **before** and **after** the guarded region: an `open()` above the
`try`; setup performed outside the lock; teardown outside the `finally`; a variable assigned
before the check that uses it. Name the input that reaches the unguarded part.

**What this angle does NOT report.** This angle reports live failure paths, not opinions about
how deep or elegant a fix is. The following are not findings for this stage, even if you believe
them:

- "this bypasses the service layer" or "the architecture is inconsistent";
- "this duplicates a dependency" when you also conclude it is harmless;
- "the underlying mechanism should be generalized instead";
- anything whose Wrong-outcome line describes maintainability rather than behavior.

The shared block's rule applies here with no exception: name a trigger and a wrong outcome, or
do not report it.

**Why this angle exists.** This repository shipped the same bug three times. Two rounds of
per-line review each widened an `except` clause; neither noticed that `open()` ran before the
loop, outside every `try`, so an unreadable file still terminated the script
(harness repo, `docs/solutions/scripts/bash-empty-array-and-jsonl-parsing-gotchas.md`). No list of defect
classes reaches that bug. Only this question does.
````

