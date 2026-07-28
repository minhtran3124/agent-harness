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

