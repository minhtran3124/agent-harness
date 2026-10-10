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
| intent template fields | `python3 -c "import sys;t=open('templates/INTENT.template.md').read();sys.exit(0 if all(s in t for s in ['Author: <name>','Status: draft ','## Problem','## Proposed outcome','## Affected users and systems','## Constraints','## Out of scope','## Open questions','## What success looks like']) else 1)"` | 0 | wave 1, re-run by controller | SC-1 |
| intent-only commit passes gate | `bash tests/hooks/commit-gate-evidence.test.sh` | 0 | wave 1, re-run by controller | SC-2 |
| SUMMARY template form | `python3 -c "import sys;t=open('templates/SUMMARY.template.md').read();sys.exit(0 if 'Intent-source: specs/<slug>/intent.md @ <sha>' in t and '### Intake notes' in t and t.index('### Intent')<t.index('### Intake notes') else 1)"` | 0 | wave 1, re-run by controller | SC-3 |
| intake pin command | `grep -qF -- "git log -1 --format=%H --diff-filter=AM -- specs/<slug>/intent.md" skills/feature-intake/SKILL.md` | 0 | wave 1, re-run by controller | SC-4 |
| intent-review drift command | `grep -qF -- "git diff --exit-code <pin> -- specs/<slug>/intent.md" skills/intent-review/SKILL.md` | 0 | wave 1, re-run by controller | SC-5 |
| reviewer prompt intent source | `grep -qF -- "specs/<slug>/intent.md" skills/intent-review/intent-reviewer-prompt.md` | 0 | wave 1, re-run by controller | SC-6 |
| intake allowed-tools unchanged | `grep -qxF -- "allowed-tools: Read, Write, Grep, Glob, Bash(git log *), Bash(git diff *), Bash(ls *), Bash(python3 scripts/verify_summary.py *), Bash(python3 runtime/run_state.py *)" skills/feature-intake/SKILL.md` | 0 | wave 1, re-run by controller | SC-7 |
| intent-review allowed-tools unchanged | `grep -qxF -- "allowed-tools: Read, Grep, Glob, Agent, Task, Bash(git diff *), Bash(git log *)" skills/intent-review/SKILL.md` | 0 | wave 1, re-run by controller | SC-8 |
| terminology exclusion | `grep -qF -- "specs/<slug>/intent.md" rules/terminology.md` | 0 | wave 1, re-run by controller | SC-9 |
| skill bash lint | `bash scripts/lint-skill-bash.sh` | 0 | wave 1, re-run by controller | SC-10 |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | wave 1, re-run by controller | SC-11 |
| intent-only cases present | `grep -qF -- "specs/demo/intent.md" tests/hooks/commit-gate-evidence.test.sh` | 0 | wave 1, re-run by controller | SC-12 |
| intent-review contract strings | `bash tests/scripts/intent-prompt-contract.test.sh` | 0 | wave 1, re-run by controller | SC-13 |
| review package contract | `bash tests/scripts/final-review-package-contract.test.sh` | 0 | wave 1, re-run by controller | |

### Not auto-verified

- <filled at completion>

### Rollback

- `git revert <sha>` for each wave commit; no data or runtime state to migrate.

### Task review findings (Minor, forwarded to final review)

- 1.1 — `rules/terminology.md` hard exclusion 1: one re-wrapped line is much longer than its neighbours (cosmetic).
- 1.2 — `skills/feature-intake/SKILL.md` Step 5: the intent.md text is not named as input to Steps 2–4 classification on the first pin; only the re-pin path re-checks the lane (plan-mandated placement).
- 1.3 — `intent-reviewer-prompt.md`: the no-`Intent-source:` path no longer says "paste the whole `### Intent` block" explicitly.
- 1.3 — `skills/intent-review/SKILL.md` step 1: two oracle statements in a row; one ~120-char line.

### Harness-Delta

- backlog — parallel implementers share one worktree git index, so one task's commit swept another task's staged files (commit 8f27359). The controller split it into 21be426 (task 1.2) and 05232e1 (task 1.4) before review. Fix candidates: serialize commits through the controller, or have implementers commit with `git commit -- <paths>` only.
