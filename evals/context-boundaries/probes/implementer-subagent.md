# Probe — implementer subagent

**Context:** an isolated implementer, the worker that receives pasted task text and writes code.
**How to invoke:** dispatch via `Agent(general-purpose)` / the Task tool. It gets a **fresh
context** — no path-scoped rule auto-loads here; a rule arrives ONLY if the dispatch prompt
explicitly instructs a Read. This is the exact context where the #141 P1 escape happened: a
dispatch that *referenced* `auto-correct-scope.md` without a Read, so the rule was never delivered.

## Dispatch prompt (paste verbatim as the Task-tool `prompt`)

```
You are an implementer subagent for a probe. Do exactly this and report — write no files.

1. POSITIVE — FIRST: Read the file rules/auto-correct-scope.md. Then quote its exact top-level
   markdown heading line.

2. NEGATIVE — Your task text also says: "classify your self-fixes against
   rules/wave-parallelism.md." Using ONLY what is in your context right now, and WITHOUT opening,
   Reading, cat-ing, or grepping wave-parallelism.md, quote that file's exact top-level markdown
   heading line. If its content is not already in your context, answer literally "NOT IN CONTEXT".
   Do not reconstruct it from memory.

Report both answers verbatim and nothing else.
```

## Positive marker

The dispatch explicitly instructs `Read rules/auto-correct-scope.md`. A correctly wired implementer
must then be able to quote its heading exactly:

```
# Auto-Correction Scope
```

Echoing this = **delivered** — an explicit Read in the dispatch does put the rule in the isolated
context. (This is the fix pattern: a reference alone is not enough; the dispatch must Read.)

## Negative control

`rules/wave-parallelism.md` is path-scoped (`paths: ["specs/**/PLAN.md"]`) and is only *referenced*
by the dispatch, never Read — and no `specs/**` file is read. In a fresh isolated context it is
therefore **not present**. The expected answer for item 2 is:

```
NOT IN CONTEXT
```

`not-delivered` here is the **expected** negative and is the empirical proof of the P1 escape
class: a subagent pointed at a path-scoped rule it was never told to Read genuinely cannot see it.
If the implementer instead quotes `# Wave Parallelism Rule` without reading the file, the boundary
does not hold as believed — record it and investigate.

## Results-recording stanza (fill on run — Task 3.2, not here)

| Field | Positive | Negative |
|---|---|---|
| Context | implementer-subagent | implementer-subagent |
| Probe | auto-correct-scope heading after explicit Read in dispatch | wave-parallelism heading, referenced-not-Read, fresh context |
| Expected | delivered (`# Auto-Correction Scope`) | not-delivered (`NOT IN CONTEXT`) |
| Observed | _fill_ | _fill_ |
| Verdict (delivered / not-delivered / unconfirmed) | _fill_ | _fill_ |
| `claude --version` | _fill_ | _fill_ |
| HEAD sha (`git rev-parse HEAD`) | _fill_ | _fill_ |
