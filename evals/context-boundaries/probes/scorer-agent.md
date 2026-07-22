# Probe — scorer agent

**Context:** the correctness **scorer** — a cheap-model subagent (e.g. haiku) that scores findings
against the threshold. It is the leanest context in the chain: a small model, a fresh window, and
typically the least prompt scaffolding, which makes it the context most likely to silently miss an
instruction that was only referenced. Probe it on its own; do not assume it inherits anything the
main session or a larger reviewer saw.
**How to invoke:** dispatch via a cheap-model subagent (the scorer's real model, e.g. haiku), the
same way the correctness scorer is run.

## Dispatch prompt (paste verbatim, dispatched to the scorer's cheap model)

```
You are the correctness scorer for a probe. Answer only; write nothing.

1. POSITIVE — FIRST: Read the file rules/auto-correct-scope.md. Then quote its exact top-level
   markdown heading line.

2. NEGATIVE — The scoring brief refers to "the STOP-gate list in rules/wave-parallelism.md" (a
   deliberately planted reference). Using ONLY what is in your context right now, and WITHOUT
   opening, Reading, cat-ing, or grepping wave-parallelism.md, quote that file's exact top-level
   markdown heading line. If it is not already in your context, answer literally "NOT IN CONTEXT".
   Do not reconstruct it from memory.

Report both answers verbatim and nothing else.
```

> Cheap-model caveat: a small model is more prone to *hallucinate* a plausible heading rather than
> admit absence. Treat any quoted heading for item 2 that it did not actually Read as a
> reconstruction, not delivery — if in doubt whether the model read the file or guessed, record
> `unconfirmed`, never `delivered`. `unconfirmed` on this load-bearing boundary blocks (see the
> README Claim discipline), it is not "mitigated."

## Positive marker

The dispatch explicitly instructs `Read rules/auto-correct-scope.md`. The scorer must quote its
heading exactly:

```
# Auto-Correction Scope
```

Echoing this — and only if the model actually performed the Read — = **delivered**.

## Negative control

`rules/wave-parallelism.md` is path-scoped (`paths: ["specs/**/PLAN.md"]`), only referenced, never
Read, with no `specs/**` file read. It must be **absent** from the fresh scorer context. Expected
answer for item 2:

```
NOT IN CONTEXT
```

`not-delivered` is the **expected** negative. A cheap model that instead emits `# Wave Parallelism
Rule` (or any confident heading) without reading the file is the failure mode to watch for — that
is reconstruction/hallucination, not delivery; record `unconfirmed` and investigate.

## Results-recording stanza (fill on run — Task 3.2, not here)

| Field | Positive | Negative |
|---|---|---|
| Context | scorer-agent (cheap model) | scorer-agent (cheap model) |
| Probe | auto-correct-scope heading after explicit Read in dispatch | wave-parallelism heading, referenced-not-Read, fresh context |
| Expected | delivered (`# Auto-Correction Scope`) | not-delivered (`NOT IN CONTEXT`) |
| Observed | _fill_ | _fill_ |
| Verdict (delivered / not-delivered / unconfirmed) | _fill_ | _fill_ |
| Model (e.g. haiku) | _fill_ | _fill_ |
| `claude --version` | _fill_ | _fill_ |
| HEAD sha (`git rev-parse HEAD`) | _fill_ | _fill_ |
