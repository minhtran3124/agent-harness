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

