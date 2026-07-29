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

