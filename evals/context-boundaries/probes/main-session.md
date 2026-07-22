# Probe — main session

**Context:** the interactive main session (the top-level coordinator thread).
**How to invoke:** run the prompt below directly in the main session. No dispatch.

The main session is the one context that DOES receive path-scoped rules automatically — but only
when it **reads a matching `specs/**` file** into context. This probe confirms that mechanism
works here, and the negative control confirms the trigger is genuinely path-scoped (not
always-on). The load-bearing warning at the bottom is the whole reason this subtree exists: this
positive result is **valid only for main** and must never be assumed for a child context.

## Dispatch prompt (paste verbatim into the main session)

```
Read the file specs/gh-143-context-propagation/SUMMARY.md (this is a specs/** file, but NOT a
PLAN.md).

Then, using ONLY what is now in your context — do NOT open, Read, cat, or grep either rules file
for this — answer both:

1. POSITIVE: Quote the exact top-level markdown heading line of rules/auto-correct-scope.md.
2. NEGATIVE: Quote the exact top-level markdown heading line of rules/wave-parallelism.md.

If a rule's content is not present in your context, answer literally "NOT IN CONTEXT" for that
item. Do not guess or reconstruct from memory.
```

## Positive marker

`rules/auto-correct-scope.md` has frontmatter `paths: ["specs/**"]`. Reading
`specs/gh-143-context-propagation/SUMMARY.md` (a `specs/**` path) should inject it. The context
must echo its heading exactly:

```
# Auto-Correction Scope
```

Echoing this line = **delivered**. The path-scoped injection fired for main.

## Negative control

`rules/wave-parallelism.md` has frontmatter `paths: ["specs/**/PLAN.md"]` — it triggers ONLY on a
`PLAN.md` read. This probe reads `SUMMARY.md`, not `PLAN.md`, so the rule must **not** be present.
The expected answer for item 2 is:

```
NOT IN CONTEXT
```

Absence here (`not-delivered`) is the **expected** negative — it proves the injection is genuinely
path-scoped and not handing every rule to main unconditionally. If the context DOES quote
`# Wave Parallelism Rule`, the probe is compromised (a stale PLAN.md read earlier in the session,
or the scoping does not hold) — record it and investigate before trusting the positive.

## Load-bearing warning (main → child does NOT transfer)

A negative control per child context is not framed the same way, because the mechanism differs:
main gets path-scoped rules via its own file reads; an isolated child (implementer / reviewer /
scorer) gets a **fresh context** and receives a rule ONLY if its dispatch prompt explicitly Reads
it. **This main-session `delivered` result therefore says nothing about any child context.**
Generalizing it to a subagent is exactly the P1 escape from #141. Each child must be probed
independently — see the sibling probe files.

## Results-recording stanza (fill on run — Task 3.2, not here)

| Field | Positive | Negative |
|---|---|---|
| Context | main-session | main-session |
| Probe | auto-correct-scope heading present after `specs/**` read | wave-parallelism heading absent (no PLAN.md read) |
| Expected | delivered (`# Auto-Correction Scope`) | not-delivered (`NOT IN CONTEXT`) |
| Observed | _fill_ | _fill_ |
| Verdict (delivered / not-delivered / unconfirmed) | _fill_ | _fill_ |
| `claude --version` | _fill_ | _fill_ |
| HEAD sha (`git rev-parse HEAD`) | _fill_ | _fill_ |
