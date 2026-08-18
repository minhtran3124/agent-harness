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

