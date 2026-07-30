# Research brief — Require Claude Code `/simplify` in the workflow

> Date: 2026-07-30  
> Scope: Claude Code bundled `/simplify` behavior, the current harness review chain, and a safe
> policy for making cleanup review mandatory without weakening existing proof.

## 1. External behavior verified

Claude Code documents `/simplify [target]` as a bundled, prompt-based skill that reviews changed
code and applies fixes. Four review agents cover:

- reuse of existing helpers;
- simplification;
- efficiency;
- whether the change is at the right abstraction level.

Since Claude Code 2.1.154, `/simplify` is cleanup-only and does not look for correctness bugs.
Correctness remains the responsibility of `/code-review` or this repository's
`/correctness-review`. The installed client used during research is 2.1.220.

The behavior is version-sensitive:

- 2.1.147 temporarily renamed `/simplify` to `/code-review` and removed the old cleanup behavior;
- 2.1.152 restored `/simplify` as `/code-review --fix`;
- 2.1.154 separated it into the current cleanup-only workflow.

Sources:

- [Claude Code commands](https://code.claude.com/docs/en/commands)
- [Claude Code skills](https://code.claude.com/docs/en/slash-commands)
- [Claude Code changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)

## 2. Current repository state

The current final sequence is:

```text
task implementation + per-task verify/review
  → optional context-propagation audit
  → correctness review
  → intent review
  → review receipt
  → finishing / PR
```

Relevant authorities:

- `skills/subagent-driven-development/SKILL.md`
- `skills/subagent-driven-development/references/review-chain.md`
- `skills/finishing-a-development-branch/SKILL.md`
- `scripts/check_review_receipt.py`

The repository already mentions `/simplify`, but does not execute or require it:

- `hooks/risk-corroboration.sh` emits a warn-only suggestion for a staged tiny diff over 150
  changed lines or a normal diff over 600 lines;
- `skills/intent-review/intent-reviewer-prompt.md` distinguishes cleanup mutation from the
  read-only intent oracle.

The Superpowers 6 adoption consolidated per-task spec and quality review. That reviewer sees one
task at a time. No current final oracle owns branch-wide reuse, cross-task duplication, efficiency,
or abstraction-altitude cleanup:

- correctness review hunts runtime bugs;
- intent review checks gap, drift, and excess against the original request;
- context-propagation audit checks instruction delivery;
- none is authorized to perform cleanup.

## 3. Value hypothesis

A branch-wide `/simplify` pass may catch issues that per-task review cannot observe:

- two tasks independently introduce helpers that should be shared;
- abstractions that only become excessive once the cumulative diff is visible;
- repeated work or avoidable allocations across task boundaries;
- branch-level cleanup opportunities that are not correctness or intent defects.

The value is plausible but not yet measured in this repository. Making the step mandatory before a
quality-first shadow evaluation would turn a vendor prompt into an unproven hard dependency.

## 4. Main risks

### Mutation invalidates prior evidence

`/simplify` applies fixes. If it runs after final review or receipt creation, the review evidence is
stale. It must run before the branch review package and all final oracles.

### Cleanup can change behavior

The skill is not a read-only reviewer. A cleanup may remove plan-mandated behavior, change a public
contract, alter error handling, or introduce a regression. A changed result therefore needs:

1. targeted verification;
2. an independent spec + quality delta review;
3. a distinct commit;
4. the existing full final review chain over the post-simplify HEAD.

### Vendor behavior drifts

The command changed meaning across three nearby releases. The workflow needs a minimum supported
version and an explicit capability failure, not silent fallback.

### Invocation is prompt-driven

Claude Code bundled skills run through the Skill tool. A shell hook cannot safely execute the skill
and a prose instruction alone is weak evidence. The harness can enforce sequencing and durable
metadata, but cannot cryptographically prove what the vendor prompt did. This is the same trust
boundary as other model reviews and should be recorded honestly.

### Fixed ceremony can outweigh value

Running four cleanup agents for tiny or documentation-only changes adds cost with little expected
benefit. The requirement should be signal-driven.

## 5. Recommended policy

Run `/simplify` exactly once over the cumulative branch change when:

| Lane / diff | Policy |
| --- | --- |
| normal or high-risk with reviewable non-documentation source changes | required |
| tiny with more than 150 changed source lines | required |
| tiny below the threshold | advisory |
| documentation-only, generated-only, vendor-only, or bookkeeping-only | skip with reason |

Required cases fail closed when:

- `claude` is unavailable;
- Claude Code is older than 2.1.154;
- `/simplify` cannot be invoked;
- the worktree is not clean at the pre-simplify checkpoint;
- a changed result lacks passing verification or delta review.

The commit-time hook remains advisory. Blocking normal development commits until a final cleanup
stage exists would deadlock the workflow. Enforcement belongs in the final receipt/finishing gate.

## 6. Proposed evidence

Extend the existing `.review-receipt.json` with a `type: "simplify"` entry rather than creating a
second receipt. The entry records:

- policy decision and reason;
- Claude Code version;
- exact base, pre-simplify, and post-simplify SHAs;
- `changed` or `no-op` outcome;
- changed paths;
- verification result;
- delta-review verdicts when code changed.

`scripts/check_review_receipt.py` should gain `--require-simplify-if <base>` and validate the entry
when policy requires it. The final `reviewed_head_sha` must remain at or after the post-simplify
source SHA, with only the existing specs-only bookkeeping exception.

## 7. Evaluation decision

Use a version-pinned, isolated-worktree shadow corpus before wiring the hard gate. Quality gates
precede value/efficiency gates:

1. zero test or contract regressions;
2. zero newly introduced blocking correctness/intent findings;
3. no edit on negative/no-op fixtures;
4. at least one independently accepted cleanup in each positive fixture class;
5. record runtime and token overhead without treating savings as a safety target.

If quality fails, retain the results and leave `/simplify` advisory. If quality passes but useful
cleanup is rare, prefer a narrower signal policy rather than universal invocation.

## 8. Research conclusion

Requiring `/simplify` is justified for cumulative, code-bearing changes because it owns a real gap
in the current review chain. Universal invocation is not justified. The safe design is a
signal-gated, pre-oracle mutation stage with version pinning, delta verification, durable evidence,
and a quality-first shadow rollout.
