# Probe — reviewer agent

**Context:** the read-only `reviewer` agent (`agents/reviewer.md`) — the context that runs
`/correctness-review` and `/intent-review`. Its tools whitelist is `Glob, Grep, Read, Bash`;
Write/Edit/Agent are excluded, so review independence is structural. It still has **Read**, so an
explicit Read in the dispatch can deliver a rule — but, like any child context, it gets a fresh
context and no path-scoped rule auto-loads.
**How to invoke:** dispatch via the Task tool with `subagent_type: reviewer`.

## Dispatch prompt (paste verbatim as the Task-tool `prompt`, `subagent_type: reviewer`)

```
You are a reviewer subagent for a probe. Produce findings only; write nothing.

1. POSITIVE — FIRST: Read the file rules/auto-correct-scope.md. Then quote its exact top-level
   markdown heading line.

2. NEGATIVE — The review brief also refers you to "the Rule-4 STOP criteria in
   rules/wave-parallelism.md" (a deliberately planted reference). Using ONLY what is in your
   context right now, and WITHOUT opening, Reading, cat-ing, or grepping wave-parallelism.md,
   quote that file's exact top-level markdown heading line. If it is not already in your context,
   answer literally "NOT IN CONTEXT". Do not reconstruct it from memory.

Report both answers verbatim and nothing else.
```

> Note: the reviewer agent has Read, so it *could* open wave-parallelism.md if told to. The
> negative control deliberately forbids the Read — the question is whether the rule is ALREADY in
> the fresh context (it must not be), not whether the Read tool works.

## Positive marker

The dispatch explicitly instructs `Read rules/auto-correct-scope.md`. The reviewer must be able to
quote its heading exactly:

```
# Auto-Correction Scope
```

Echoing this = **delivered** — an explicit Read in the review dispatch delivers the rule even in
the read-only reviewer context.

## Negative control

`rules/wave-parallelism.md` is path-scoped (`paths: ["specs/**/PLAN.md"]`), only referenced, never
Read, with no `specs/**` file read. It must be **absent** from a fresh reviewer context. Expected
answer for item 2:

```
NOT IN CONTEXT
```

`not-delivered` is the **expected** negative — it confirms the reviewer does not silently inherit
path-scoped rules, so a review brief that merely *names* a rule (rather than instructing a Read or
pasting it) leaves the reviewer blind to it. If the reviewer quotes `# Wave Parallelism Rule`
without reading the file, record it and investigate.

## Results-recording stanza (fill on run — Task 3.2, not here)

| Field | Positive | Negative |
|---|---|---|
| Context | reviewer-agent | reviewer-agent |
| Probe | auto-correct-scope heading after explicit Read in dispatch | wave-parallelism heading, referenced-not-Read, fresh context |
| Expected | delivered (`# Auto-Correction Scope`) | not-delivered (`NOT IN CONTEXT`) |
| Observed | _fill_ | _fill_ |
| Verdict (delivered / not-delivered / unconfirmed) | _fill_ | _fill_ |
| `claude --version` | _fill_ | _fill_ |
| HEAD sha (`git rev-parse HEAD`) | _fill_ | _fill_ |
