# intent-md-entry — Summary

Lane: high-risk
Confidence: high
Reason: Hard gate workflow-engine (changes skills/feature-intake and skills/intent-review SKILL.md, their allowed-tools, and the workflow entry point) plus templates/ (SUMMARY template contract, new INTENT template), which ci-strict-gate.sh blocks without a high-risk SUMMARY; it also redefines the workflow's entry artifact (system-redefinition escalation trigger).
Flags: existing-behavior, weak-proof, multi-domain, cross-platform
Affects: templates/SUMMARY.template.md (contract read by verify_summary.py and commit-gate.sh), skills/feature-intake, skills/intent-review, Codex adapter render (allowed-tools), scripts/install-harness.sh
Input-type: harness improvement
Route: /brainstorming -> /xia2 (Deep) -> /writing-plans -> /using-git-worktrees -> /subagent-driven-development -> /context-propagation-audit -> /correctness-review -> /intent-review -> /compound -> /finishing-a-development-branch
Escalate: no (E001 decided by the user 2026-10-10: option A)

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Scope-deciding sentences, in chronological order:

> ko, tôi đang nghĩ tới việc tạo file intent.md trong spec luôn, tức là ai đó có thể viết 1 intent theo chuẩn playbook xong transfer cho team và start wworkflow, ko cần lên github issue - quá phiền phức

> ok, ko cần summary khi tạo intent, chay feature-intake cho intent.md đi

### Intake notes

<!-- Agent-written, NOT part of the intent oracle. Dogfoods the separation this spec proposes. -->

- Source design: `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §7 (agent-written
  sketch the user reacted to; it is a secondary input, the verbatim lines above win on conflict).
- Reading of "ko cần summary khi tạo intent": creating and committing `specs/<slug>/intent.md`
  must not require a `SUMMARY.md`; SUMMARY is still written by `/feature-intake` when the workflow
  starts. Already true of today's `commit-gate.sh` (checked 2026-10-10 in a scratch worktree, exit
  0 under standard and strict); this spec must lock it with a regression test.
- Slug: no ticket source → plain `intent-md-entry` (`templates/structure/specs-README.md`).
- Confidence started `medium` (two scope edges had only a default) and is `high` after E001:
  the user chose option A — template + `/feature-intake` and `/intent-review` support, shipped to
  consumer repos via `scripts/install-harness.sh`; no authoring helper in this change.
- Assumed defaults, to be confirmed in brainstorming: approval is a `Status: approved` field that
  intake requires; chat-only requests keep today's verbatim flow; `/intent-review` reads the intent
  file pinned at a commit SHA.

## What changed

<filled at completion>

### Rationale

<filled at completion>

### Alternatives considered

- GitHub issue as the intent (option B in research §7) — rejected by the user: "ko cần lên github issue - quá phiền phức".
- Derived structured view under the chat request only (option A) — does not give a hand-off artifact someone else can write.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| plan contract | `python3 scripts/check_plan_contract.py specs/intent-md-entry/PLAN.md` | 0 | plan-contract passed (pre-execution) | |

### Not auto-verified

- <filled at completion>

### Rollback

- `git revert <sha>` for each wave commit; no data or runtime state to migrate.

### Harness-Delta

- none
