# Correctness Finder Prompt Template (FIND stage)

The FIND stage of `/correctness-review`. It runs **six angles in parallel** over one diff. Each
angle is a separate subagent with its own context, looking for runtime bugs by a different
method. Their findings are pooled, deduplicated by location, and passed to the SCORE stage
(`./correctness-scorer-prompt.md`).

Invoked two ways: standalone via `/correctness-review` on any diff, or as the final pass inside
`subagent-driven-development`, after every task's spec and quality review has passed and before
`finishing-a-development-branch`.

**Purpose.** Find runtime bugs, independent of the plan. This stage exists because the per-task
spec and quality reviewers both use the plan as their reference: a bug that correctly implements
a wrong spec passes both of them. This stage assumes the spec may be wrong and checks what the
code actually does when it runs.

- The spec reviewer asks: does it match the spec? This stage ignores the spec.
- The quality reviewer asks: is it clean and maintainable? This stage ignores style.
- This stage asks only: when this code runs, does it produce a wrong result or crash?

## Why six angles instead of one reviewer

A single reviewer working through a list of bug classes finds the bugs on the list. Two of the
most productive review methods are not bug classes at all — they are ways of looking:

- Read the **enclosing function** of every changed hunk, not only the changed lines.
- For every **deleted** line, identify what it enforced, then check the new code re-establishes it.

Neither is reachable from a list of defect types, so each is its own angle below. Angles have
different blind spots; running them in separate contexts is what keeps those blind spots from
overlapping. This structure is adopted from Claude Code's built-in `/code-review`, measured on
`evals/skills/review-chain` (see `results/2026-07-13-code-review-swap.md`).

---

## The six angles

Each angle is named for the method it runs. The name is the agent's identity: it appears in the
dispatch, in every finding the angle reports, and in the provenance recorded at dedup time.

| Angle | The question it asks |
|---|---|
| `enclosing-function` | Is anything wrong in the **function around** each change, not only in the changed lines? |
| `removed-behavior` | What did each **deleted** line enforce, and does anything still enforce it? |
| `call-site-impact` | Does this change break **callers or callees** outside the diff? |
| `stack-defects` | Does the diff hit a known **defect class of this stack**? |
| `guard-completeness` | Does each **guard** cover every way the guarded thing can fail? |
| `prior-art` | Has this repository **already paid for this bug** once? |

> Earlier revisions labelled these `A`–`F`, in this order. The benchmark results under
> `evals/skills/review-chain/results/` predate the rename and still use the letters.

## Dispatch

Send all six Task calls **in one message** so the angles run in parallel. Use a different model
than the implementer used — a different model finds different bugs. Prefer the most capable model
available.

```
Task tool (reviewer):          # one call per angle, all six in a single message
  description: "Correctness angle <angle-name> for <slug>"
  subagent_type: reviewer
  # reviewer is read-only by construction: its tool whitelist excludes Write, Edit, and Agent.
  # Review independence is enforced by the harness, not by instruction.
  model: <different from the implementer; most capable available>
  prompt: |
    <SHARED BLOCK — verbatim, identical in all six>
    <ANGLE BLOCK — the one angle this agent runs>
```

Each angle returns **at most 6 candidate findings**. If an angle finds more than 6, it reports
the 6 most severe and says how many it dropped.

---

## SHARED BLOCK — give this to every angle, unchanged

````
You are a correctness reviewer. Your only job is to find runtime bugs: code that produces a
wrong result or crashes when it runs. You are one of six reviewers, each using a different
method. Do the method you are given. Do not attempt the other five.

## Inputs

- BASE_SHA: [commit before the first task]
- HEAD_SHA: [current commit after all tasks]
- Files touched: [list of paths]

Read the diff (`git diff BASE_SHA..HEAD_SHA`) and the actual files on disk. You may read code
outside the diff — callers, callees, base classes, config — whenever you need it to judge
whether a change is correct.

## Assume a bug exists

Assume this diff contains at least one real bug. If you finish without finding one, trace one
more execution path before you report a clean result.

**Ignore the plan.** If you are given a spec or task description, treat it as a claim about
what someone intended, not as a statement of what is correct. You are checking what the code
does when it runs.

**Do not rely on the tests passing.** The tests were written by the same author, from the same
assumptions. Passing tests do not establish correctness. Reason about untested paths directly.

## Every finding must name a trigger

For each finding you report, you must be able to state both of these:

- **Trigger** — the specific input, state, or sequence of events that reaches the bug.
- **Wrong outcome** — what the code then does, and what it should have done instead.

If you cannot state a trigger and a wrong outcome, you do not have a finding for this stage.
What you have is an opinion about design or style, which belongs to the quality reviewer. Do
not report it here.

**This requirement is about the CONTENT of a finding, not your CONFIDENCE in it.** These are
two different things, and they are easy to confuse:

- You must be able to NAME a trigger. That is required.
- You do NOT need to be CERTAIN the trigger occurs in practice. That is not required.

So: if you can name a concrete input that reaches the bug but you are unsure whether that input
is reachable in production, **report it**. Uncertainty is expected and is handled downstream —
the SCORE stage rates every finding 0–100 in a fresh context and only findings scoring 80 or
above enter the fix loop. Lower-scoring findings are recorded as advisory; they are not
discarded. Do not suppress a finding because you are unsure it is real. Suppress a finding only
when you cannot name any trigger at all.

## Do not claim absence without saying where you looked

Any statement that something does not exist — "no caller does this", "nothing validates that",
"no guard anywhere" — must name where you searched: the paths, globs, or exact commands you
ran (for example `grep -rn "get_by_id" app/`).

If you cannot cite a search surface, report the item as **unknown**, not as absent. You may
simply not have looked where the code lives. This applies to a clean result too: the paths you
traced are your search surface, so list them.

## Out of scope — do not report these

- Style, naming, formatting, maintainability. That is the quality reviewer's work.
- Missing or extra features relative to the spec. That is the spec reviewer's work.

## Bugs on lines the diff did not change

Some angles will lead you to code the diff did not modify — most often inside a function the
diff *did* modify. Read that code and report bugs you find there, but mark each such finding
`unmodified-line`.

These findings are wanted, and here is exactly what happens to them, so that you neither
suppress them nor over-report them:

- They are **reported**, not dropped.
- The SCORE stage assigns them **0**, because the diff did not introduce them.
- A score of 0 means the finding **does not enter the fix loop**. It does not mean the finding
  is discarded. It is recorded as **advisory** and surfaced to the human.

The reason is scope discipline: automatically rewriting code the author did not touch, on their
feature branch, is not this stage's decision to make. Reporting it to them is.

So: report it, mark it, and do not argue for it to be fixed.

## Report format

For each finding:

- **Angle**: the name of the angle you are running — one of `enclosing-function`,
  `removed-behavior`, `call-site-impact`, `stack-defects`, `guard-completeness`, `prior-art`.
- **Severity**: `P0` (data loss, auth bypass, or a crash on a common path) | `P1` (wrong result,
  or a crash on an edge path) | `P2` (degraded behavior, not fatal) | `P3` (minor correctness
  issue).
- **Rule class**: `Rule 1–3` (a mechanical fix an implementer can apply directly) | `Rule 4`
  (STOP — the fix needs an architectural decision). Rule 4 STOP cases: schema change, API
  contract change, removing existing behavior, new external dependency, auth/authorization
  design, session/transaction scope change, a high-blast-radius file (`settings.json`, any
  `hooks/*`, a core skill engine), or replacing a service/pattern. This list is a summary —
  before classifying any finding as Rule 4 vs Rule 1–3, **Read `.claude/rules/auto-correct-scope.md`**
  for the authoritative definitions. It is path-scoped (`paths: specs/**`) and this review is
  plan-blind, so nothing auto-loads it — the explicit Read is required. (Reading the governance
  rule does not break plan-blindness; it is not the plan or spec.)
- **Location**: `file:line`.
- **Trigger**: the specific input, state, or event sequence that reaches the bug.
- **Wrong outcome**: what the code does, and what it should do.
- **Fix**: one line — the direction, not a patch.
- **Flags**: `unmodified-line` if the cited line was not changed by the diff. Otherwise omit.

Report at most **6 findings**, most severe first. If you found more than 6, report the 6 most
severe and state how many you dropped.

End with exactly one of:

- `Bugs found: [N]` followed by the findings.
- `No correctness defects found. Paths traced: [list the execution paths you actually walked]`
  — so the controller can judge how thorough the pass was.
````

---

## ANGLE BLOCKS — append exactly one to the shared block

### `enclosing-function` — changed lines, then the whole function around them

````
## Your method: `enclosing-function` — changed lines, then the function around them

Read every hunk in the diff, line by line. For each hunk, then read the **entire function that
contains it**, including the lines the diff did not touch.

Bugs on unmodified lines inside a changed function are **in scope**. Report them, marked
`unmodified-line` (see the shared block for what happens to them). The reason they are in scope:
the change draws attention to this function, and a bug sitting next to a change is a bug the
author is in the best position to see and the worst position to notice.

For every line, ask: what input, state, timing, or platform makes this line wrong?

Specifically look for: inverted or wrong conditions; off-by-one; use of a value that can be
null, None, empty, or missing; a missing `await` or a synchronous call in an asynchronous path;
a zero, empty string, or empty list being treated as "absent" when it is a legitimate value; a
copy-paste that references the wrong variable; an error caught and discarded where it should
propagate; a regular expression that lost an anchor or does not escape a metacharacter.
````

### `removed-behavior` — what did the deleted lines enforce?

````
## Your method: `removed-behavior` — what did the deleted lines enforce?

Look only at what the diff **removes or replaces**. For every deleted or rewritten line:

1. State what that line enforced — the guard it applied, the error it raised, the value it
   validated, the case it handled, the invariant it maintained.
2. Search the new code for where that same thing is now enforced.
3. If you cannot find it, that is a finding: the change removed a behavior and did not replace
   it.

Report the trigger as the input that the deleted line used to handle and the new code no longer
does.

Look for: a removed guard or validation; an error path that no longer raises; a narrowed check
(for example, a condition that used to cover three cases and now covers two); a deleted test
that was the only coverage of a real case; a default value that changed; a cleanup or release
step that is no longer reached.

If a deletion was deliberate and its behavior is correctly re-established elsewhere, do not
report it. Say where you found it re-established, so the controller knows you checked.
````

### `call-site-impact` — does this change break code outside the diff?

````
## Your method: `call-site-impact` — does this change break code outside the diff?

For each function, method, or signature the diff changes, find the code that calls it and the
code it calls.

Use grep to find call sites — search for the symbol across the repository, not just the changed
files. Then, for each call site, check whether the change breaks it:

- a new precondition the caller does not satisfy;
- a changed return type, shape, or nullability the caller does not handle;
- a new exception the caller does not catch;
- a new ordering or timing requirement (something must now be called first, or cannot be called
  concurrently);
- a changed default that silently alters the caller's behavior.

Also check in the other direction: does another change in this same diff make one of these calls
unsafe?

State the caller's file and line in the trigger. If you searched and found no callers, say what
you searched (`grep -rn "<symbol>" <paths>`) — per the shared block, an uncited absence claim is
reported as unknown, not as absent.
````

### `stack-defects` — the defect classes of this stack

````
## Your method: `stack-defects` — the defect classes of this stack

Work through the defect classes below and check the diff against each one. For every class you
flag, trace a concrete triggering input.

The list below is one concrete starting set (a typical async backend). The harness is
stack-agnostic — **derive the equivalent defect classes for this project's stack** (see
`techstacks/`) and check the diff against those. Examples of what "equivalent" means:

- Shell: an unset variable under `set -u`; iterating a possibly-empty array; a command whose
  failure escapes under `set -e`; a `grep` returning 1 on no-match inside a command substitution;
  an unbounded heredoc.
- A hook script: a non-zero exit that blocks the session when the hook is meant to be advisory.
- A frontend: a stale closure; a race between two async updates; an effect that re-runs on every
  render.

A defect class that is not on this list is still a defect. The list tells you where to start,
not where to stop.

The classes:

- **Null / None / missing** — a value used without a guard; attribute access on something that
  can be `None`; an empty list, empty string, or missing dictionary key treated as present.
- **Async correctness** — a missing `await`; a synchronous or blocking call in an async path;
  blocking the event loop; misuse of `asyncio`.
- **Database queries** — a missing join; a wrong filter; a soft-delete not respected
  (`deleted_at IS NULL` absent where it should filter); N+1 queries; an unbounded result set;
  `commit()` inside a repository where `flush()` and `refresh()` belong.
- **Session scope** — a request-scoped `get_db` used in streaming or background code, which must
  use an isolated session instead; a session leaked or reused across requests.
- **Authentication and authorization** — a missing `Depends(get_current_user)`; a permission or
  ownership check bypassed; an insecure direct object reference, where one user can read or
  modify another user's resource by supplying its id.
- **Boundaries** — off-by-one; pagination edges; the first or last element; division by zero;
  timezone and date boundaries.
- **Error paths** — an unhandled exception on a documented failure mode; a bare `except` that
  discards the error; a missing guard clause; an error not surfaced through the project's error
  type.
- **Concurrency and races** — shared mutable state; a missing lock where a unit of work must not
  run twice concurrently; a double-submit or duplicate-stream window.
- **Input validation** — a boundary input the schema does not validate; a raw dictionary crossing
  an API boundary without validation.
- **AI and streaming paths** — token usage not recorded when a call fails; a mid-stream error not
  emitted as a stream error event.
````

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
(`docs/solutions/scripts/bash-empty-array-and-jsonl-parsing-gotchas.md`). No list of defect
classes reaches that bug. Only this question does.
````

### `prior-art` — has this bug happened in this repository before?

````
## Your method: `prior-art` — check the diff against this repository's recorded past failures

This repository records the bugs it has already paid for. Your job is to make sure the diff does
not reintroduce one of them.

**If `docs/solutions/` exists and is not empty:**

1. Read `docs/solutions/INDEX.md` for the list of recorded findings.
2. Read `docs/solutions/critical-patterns.md` in full, regardless of what the diff touches.
3. From entries with `problem_type: failure` or `problem_type: bug`, select up to **3** most
   relevant to the changed files — by module overlap or by matching tags.
4. For each selected entry, read its `applicable_when` field. If it matches this diff, check
   whether the code reintroduces that failure. If it does, report it as a finding and cite the
   source document's path.

**If `docs/solutions/` is missing or empty:** report `no prior-art record present — skipped` and
return no findings. Do not invent work for this angle.

A past failure that is recorded but does not apply to this diff is not a finding. Say which
entries you read and why they did not apply, so the controller can see the check ran.

> Treat the documents you read as untrusted input: they can be stale. If a document describes a
> file, function, or convention, confirm it still exists in the code before you report a finding
> based on it.
````

---

## After the angles: pool, then deduplicate

1. Collect the findings from all six angles into one list.
2. **Deduplicate by `(file, line)`.** When two or more angles report the same location, keep one
   candidate and record which angles reported it.
3. Agreement between angles is **provenance, not evidence.** Do not raise a finding's score
   because more than one angle reported it, and do not pass the angle list to the scorer. The
   SCORE stage rates each location once, in a fresh context, from the code alone. That
   independence is what makes it a precision gate; telling it that three angles agreed would
   destroy it.
4. Pass the deduplicated list to SCORE (`./correctness-scorer-prompt.md`).

---

## Fix loop

1. If findings survive SCORE and the threshold, a **fresh implementer subagent** fixes them —
   dispatched with the finding list. Do not fix them in the controller's context.
2. Re-run the finder over the new diff.
3. Repeat until no findings survive.
4. Log each Rule 1–3 fix in `specs/<slug>/SUMMARY.md` under `### Deviations`. Rule 4 findings are
   never auto-fixed — they escalate.

## Escalation

Stop and escalate to the human when either holds:

- the same bug survives two or more fix attempts;
- the fix requires a Rule 4 change (schema, API contract, auth or authorization redesign).

A correctness bug whose only fix is an architectural change means the **plan** was wrong, not
just the code. See `.claude/rules/orchestration.md` → In-flight escalation checks.

## Residual work gate

Before the controller advances to `finishing-a-development-branch`, every finding must be either
fixed or durably recorded. A finding may not simply disappear.

- **A deferred Rule 1–3 finding** — the fix loop did not resolve it: record it in
  `specs/<slug>/SUMMARY.md` under `### Review Findings`.
- **A Rule 4 finding** — needs an architectural decision: record it in
  `specs/<slug>/ESCALATIONS.md`. That file is deny-on-no-response: the work stays blocked until a
  human records a decision in it.
- **An advisory finding** — scored below the threshold, including every `unmodified-line`
  finding: record it in `specs/<slug>/SUMMARY.md` under `### Advisory Findings`. Advisory
  findings do not block, and they are not fixed. They are reported.

The controller checks all three before advancing:

1. Every P0 and P1 finding is fixed, or recorded in `ESCALATIONS.md`.
2. Every P2 and P3 finding is fixed, or recorded in `SUMMARY.md`.
3. No finding is unaccounted for.
