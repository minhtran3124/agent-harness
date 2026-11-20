# When something is stuck

Part of `harness:pd-orchestrate`.

Stuck means: the same check failed twice after a fix; a worker and a reviewer used their 3 rounds;
an agent sent `escalate`; a session is silent past its budget; or you have tried two different
approaches yourself. Climb one step at a time:

1. **Think.** Read the evidence yourself: the `escalate` body carries the attempts and their
   output. Often the brief was wrong or a fact was missing: fix the brief and assign again, with a
   stronger model if the first one lacked depth.
2. **Advisor, in process.** One question to the `harness:advisor` agent (Opus 5.5, read-only), with
   the facts and what was tried. For a disputed finding its verdict is `accept`, `fix` or `owner`.
   When the escalating agent already asked this advisor and says so, that answer counts as this
   step; do not ask the same question again.
3. **Advisor session on Fable 5.2.** When the Opus advice did not unblock the work: make a new
   workspace, start a session there, set its model to `claude-fable-5-2`, and send an
   `advise-request` with "Follow the `harness:pd-advise` skill", your session name, and the brief
   that skill describes, including the checkout path and branch that hold the failing commit. It
   researches, may build a prototype, and returns a solution. Go straight to this step, without
   step 2, only for a high-stakes architecture decision or when the owner asks.
   You stay the decider: check the solution's key claims, stop the advisor session when no
   question is left, then write a new brief (`run.md`, the
   exception to "no steps") for the same worker when its context still helps, or for a new one.
4. **Owner.** A decision only a human can make, or nothing above worked. Bring the evidence, the
   options and your recommendation, as one question.

Only an advisor or the owner may accept an open finding. It stays in the receipt with
`accepted_by`, and you list it for the owner before the merge. You do not accept one yourself.

An agent that sent `escalate` waits. Always answer it: an `answer`, a new `assign`, or a message
that the ticket is closed.
