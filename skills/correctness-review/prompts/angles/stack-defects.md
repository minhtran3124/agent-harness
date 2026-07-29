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

