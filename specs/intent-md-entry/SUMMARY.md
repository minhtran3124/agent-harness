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

A person can now write `specs/<slug>/intent.md` from the new `templates/INTENT.template.md` (playbook fields plus Out of scope and success; `Status:` left empty with a note), set `Status: approved`, commit it with no SUMMARY, and hand the slug over. `/feature-intake` reads it before classifying, pins it by commit SHA (`Intent-source:` line in `### Intent`), and classifies from it; a re-run follows `skills/feature-intake/references/re-pin.md` (stop and show on a lane change or a deleted intent, otherwise move only the pin). `/intent-review` stops if intent.md changed after the pin, otherwise judges against the intent text plus the chat request. A hook regression test locks that an intent-only commit passes commit-gate.

### Rationale

The playbook's intent.md is an approved, human-written input; the harness only had a verbatim chat line. A file in `specs/` (not a GitHub issue — user: "quá phiền phức") keeps the intent beside its spec, pinned by SHA so the review oracle cannot move mid-work, and keeps agent prose out of the oracle (`### Intake notes`). No script, gate, or tool permission was added (user: keep it simple); the existing log and diff commands carry the pin and drift checks.

### Alternatives considered

- GitHub issue as the intent (option B in research §7) — rejected by the user: "ko cần lên github issue - quá phiền phức".
- Derived structured view under the chat request only (option A) — does not give a hand-off artifact someone else can write.

### Deviations

- User-directed (2026-10-10, after intent review), not Rule 1–3: (1) "intake sẽ đọc intent.md và sẽ quyết định đó là lane nào" — intake reads intent.md before Steps 2–4 and classifies from it; (2) "s2, ok update lại chỗ này ko cần bảo ghi nữa" — re-pin edits only the `Intent-source:` line and Intake notes, no SUMMARY rewrite or run_state init; (3) "s3: ko có chuyện đó" — merge-commit pin left unchanged; (4) "s4: template để trống status …" — template `Status:` left empty with a note, intake requires the exact value `approved`.
- SC-1 check changed to match decision (4): it no longer looks for `Status: draft `; it requires a `Status:` header and rejects a pre-filled `Status: approved` / `Status: draft`. SC-1 had passed before the change (not a failed-SC edit).
- Rule 3 — `skills/intent-review/SKILL.md` step 1 used a slash invocation (`/feature-intake <slug>`), which `scripts/check_runtime_neutral_sources.py` rejects in shared skill text; reworded to "ask for feature-intake to re-pin the slug". Found by the full suite after fix round 1. Commit 600c854.
- Rule 1 — re-pin that raises `Lane:` now also updates `Reason:`, `Flags:`, `Route:`, `Escalate:` so the header stays consistent (fix-round task review Minor). Commit 600c854.
- Rule 3 — `skills/feature-intake/SKILL.md` exceeded the 600-word skill ceiling (706, `scripts/audit_skill_prompts.py` via pytest); procedure tightened to 599 words with no behavior change, and the redundant `## References` list (it repeated Step 1) removed. Commit 17603e6.
- Regression from that trim, then repaired (fix round 3, 7041ff9): the trim had dropped the "intent.md exists" condition on the pin step, "header line", "ask for the intent to be committed", "in full", and "never in intent.md". Restored; the re-pin rules moved to `skills/feature-intake/references/re-pin.md` (not counted by the 600-word audit) to make room. Lesson recorded in Harness-Delta.
- User-directed (2026-10-10, after intent re-review): re-pin with a different lane → "Dừng, hỏi người" (stop, ask a person). A first implementation of that as an `ESCALATIONS.md` state machine (2a0ce6f) kept producing new contradictions across review rounds; the user then chose "Dừng và báo, người tự sửa" (stop and report, the person fixes SUMMARY) and "Chỉ khi lane đổi" (stop only when the lane changes). Implemented in 3654cde and 4f86475: no `ESCALATIONS.md` state; a lane change or `low` confidence stops, shows the full old/new classification lines, writes nothing; confidence/flags changes on the same lane are noted in Intake notes.
- Rule 1 — Step 1's re-pin route was ambiguous ("SUMMARY exists and has X or Y exists") and could send a first intake to re-pin; reworded with explicit grouping (a0a7221).

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| plan contract | `python3 scripts/check_plan_contract.py specs/intent-md-entry/PLAN.md` | 0 | plan-contract passed (pre-execution) | |
| intent template fields | `python3 -c "import sys;t=open('templates/INTENT.template.md').read();sys.exit(0 if all(s in t for s in ['Author: <name>','Status:','## Problem','## Proposed outcome','## Affected users and systems','## Constraints','## Out of scope','## Open questions','## What success looks like']) and 'Status: approved' not in t and 'Status: draft' not in t else 1)"` | 0 | wave 1, re-run by controller | SC-1 |
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

- Model behavior of the new intake Step 1/5 and intent-review step 1 — reached **truth, one trial**: a fresh-context agent followed the skill text literally in a scratch repo (scripts kept in the session scratchpad, not re-runnable from this repo) and all six scenarios matched: (A) terse chat + approved auth intent → read before classifying, lane `high-risk`, pin equal to `git log -1 --format=%H --diff-filter=AM`; (B) empty `Status:` → stop, no SUMMARY; (C) uncommitted intent → empty pin → stop; (D) intent edited after pin → drift check exit 1 → stop; (E) re-pin → SUMMARY diff exactly the `Intent-source:` line + one Intake notes line; (F) clean → exit 0. One trial is not a compliance rate.
- Second dogfood (fresh-context agent, scratch repo, after fix round 3): (G) chat-only → no `Intent-source:` line, request verbatim; (H) `Status: draft` → stop; (I) body-text `Status: approved` with an empty header → stop; (J) re-pin with a lane change → stop, SUMMARY byte-identical; (K) deleted intent → stop, SUMMARY unchanged; (L) re-pin, same lane → SUMMARY diff exactly the pin line + one note. All six matched — truth, one trial. Fix rounds 4–6 changed only the re-pin text after this trial (ESCALATIONS removed, same-pin stop, full classification shown); those were checked by an independent review pass, not re-run — traceability.
- The full suite `bash scripts/run-tests.sh` ended `ALL GREEN` (880 pytest passed) at 17603e6 — re-run, cited in prose because whole-suite rows are not allowed in `### Verify`.
- The feature-intake canaries (`skills/feature-intake/tests/intent-file-cases.md` IF-01..IF-10) are prose — traceability only; not run against a live intake beyond the dogfood trial above.
- Codex runtime behavior — not exercised; only rendered text is covered by `run-tests.sh`.

### Rollback

- `git revert <sha>` for each wave commit; no data or runtime state to migrate.

### Context-Propagation Audit

Result: **PASS** after one repair. Range `883593f..HEAD`. Consumer search surface: grep of `skills/`,
`agents/`, `scripts/`, `hooks/`, `rules/`, `templates/`, `adapters/` for `### Intent`,
`Intent-source`, `Intake notes`, `intent.md`, `terminology.md`; `code-review-graph` unavailable
(server not connected), so no graph evidence.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| feature-intake Step 5 (pin, Status, drift/clean, `Intent-source:`, re-pin) | feature-intake run | main session | skill body loaded on invocation | `skills/feature-intake/SKILL.md:29-40` |
| Step 6 "agent notes → `### Intake notes`, never `### Intent` or intent.md" | feature-intake run (writer of SUMMARY) | main session | skill body + explicit template read (`templates/SUMMARY.template.md`) | `skills/feature-intake/SKILL.md:41-42`; template comment under `### Intake notes` |
| intent-review step 1 drift check | intent-review controller | main session or SDD controller | skill body; SDD defers to the invoked skill ("do not copy it here") | `skills/intent-review/SKILL.md:14-18`; `skills/subagent-driven-development/references/review-chain.md:5-8` |
| Oracle = pinned intent.md text + chat request | intent reviewer | fresh `reviewer` subagent (blind) | pasted by controller per prompt INTENT input | `skills/intent-review/intent-reviewer-prompt.md:42-45` — **repaired** (see below) |
| terminology hard exclusion 1 covers intent.md | any agent applying terminology rules to spec prose | main / implementer | paths-triggered (`specs/**/PLAN.md`, `research-brief.md`, `SUMMARY.md`) and explicit Read in `writing-plans` | `rules/terminology.md:1-6`; the one writer near intent.md (feature-intake) carries the complete "never in intent.md" instruction inline |
| Same skill text for Codex | Codex plugin | Codex session | plugin manifest points at `./skills/` (same source, no copy) | `scripts/render_codex_adapter.py:149` |

Repair: the reviewer-prompt INTENT input left the no-`Intent-source:` path implicit ("plus the chat
request from the `### Intent` block"), so a controller could paste a partial block on the chat-only
path. Rewritten to name both paths: pinned intent.md text + chat request when `Intent-source:` is
present, otherwise the whole `### Intent` block. Closes task-review Minor 1.3 (first bullet).

### Correctness Review

Range `883593f..99254b3`; six FIND angles, 8 deduplicated locations, each scored by an independent
Re-review passes after each fix round (enclosing-function angle, independent reviewer): fix 1 (2 findings → fixed), fix 2 trim (6 → fixed in round 3), round 3 (4 → round 4), round 4 (6, mostly from the ESCALATIONS state machine → design simplified by the user), simplified re-pin (6 → 5 fixed in 4f86475, 1 kept as residual R1 per the user's decision).
scorer (threshold 75). **No finding reached the threshold — 0 blocking.** All are recorded below
as advisory.

### Advisory Findings

| ID | Location | Claim | Score |
| --- | --- | --- | --- |
| S1 | `skills/feature-intake/SKILL.md:20-35` | Steps 2–4 classify before Step 5 reads intent.md; on a first pin, hard-gate content only in intent.md can miss the lane decision (lane re-check only on re-pin) | 50 |
| S2 | `skills/feature-intake/SKILL.md:29-41` | Re-pin says keep every SUMMARY section, but Steps 6–7 (template write, run_state init) are not exempted | 50 |
| S3 | `skills/feature-intake/SKILL.md:31-33` | `--diff-filter=AM` skips merge commits; intent.md last set by a merge pins an older commit and the clean check fails on a committed file (reproduced by a finder in a scratch repo) | 50 |
| S4 | `templates/INTENT.template.md:6` | Unedited placeholder `Status: draft \| approved` contains "approved"; the check says only "says `approved`" | 50 |
| S5a | `skills/intent-review/SKILL.md:14-18` | An approved intent.md committed after a chat-only intake is ignored (no `Intent-source:` → no check) | 50 |
| S5b | `skills/intent-review/SKILL.md:14-18` | A pinned intent.md deleted and committed → intent-review stops; intake Step 5 is gated on "exists", so nothing clears the stale line | 50 |
| S6 | `skills/intent-review/SKILL.md:16` | Drift check compares the pin with the working tree only; a differing staged copy passes | 50 |
| S7 | `skills/intent-review/SKILL.md:14-18` | Rebase/squash + fresh clone → pin unreachable (128) → stop; deliberate fail-closed (design A7) | 25 |
| S8 | `skills/feature-intake/tests/confidence-escalation-cases.md:4` | "Step 4–5" reference now points at the pin step (should be Steps 4 and 6) — `unmodified-line`, scored 0 by rule | 0 |
| R1 | `skills/feature-intake/references/re-pin.md` step 4 | A re-pin on a `high-risk` lane whose confidence drops to `medium` re-pins with a note and leaves `Confidence:`/`Escalate:` as recorded; `rules/orchestration.md` escalates "`medium` on a high-risk task". Left as is: the user chose to stop only on a lane change. | residual (user decision) |
| R2 | `skills/feature-intake/SKILL.md` Step 4/6 | Whether a first-intake `low`-confidence stop writes SUMMARY before stopping is unstated (pre-existing); a SUMMARY left behind would later route to re-pin. | residual |

### Intent Findings

Intent review (plan-blind, `883593f..29d6c7f`) reported 6 findings:

| # | Class | Finding | Disposition |
| --- | --- | --- | --- |
| 1 | drift (different) | intake decided the lane before reading intent.md | fixed in fix round 1 (user decision 1) |
| 2 | drift | `Status: approved` is an approval step the playbook lacks | kept — user chose the Status field in brainstorming (design D2); template now leaves Status empty (decision 4) |
| 3 | drift (additive) | template adds Author/Status, Out of scope, What success looks like | kept — approved design; all five playbook sections present |
| 4 | gap | design SC-3–SC-5 (dogfood) and SC-7 (full suite) had no Verify row | closed before handoff by the dogfood run and `run-tests.sh` rows |
| 5 | excess | re-pin procedure, `### Intake notes` | report-only — in the approved design (re-pin, D5) |
| 6 | excess | drift STOP in intent-review, terminology exclusion widened to intent.md | report-only — in the approved design (D4, Architecture) |

### Task review findings (Minor, forwarded to final review)

- 1.1 — `rules/terminology.md` hard exclusion 1: one re-wrapped line is much longer than its neighbours (cosmetic).
- 1.2 — `skills/feature-intake/SKILL.md` Step 5: the intent.md text is not named as input to Steps 2–4 classification on the first pin; only the re-pin path re-checks the lane (plan-mandated placement).
- 1.3 — `intent-reviewer-prompt.md`: the no-`Intent-source:` path no longer says "paste the whole `### Intent` block" explicitly.
- 1.3 — `skills/intent-review/SKILL.md` step 1: two oracle statements in a row; one ~120-char line.

### Harness-Delta

- backlog → compound — trimming a skill to fit the 600-word ceiling silently dropped five instructions (caught only by a re-review). A before/after check of required instruction strings, or moving detail to `references/` first, would prevent it.
- backlog → compound — a prose-encoded escalation state machine (pending → decided → applied) accrued a new contradiction each review round; replacing it with "stop, show, let the person edit" ended the loop. Matches `docs/solutions/` "prose-encoded-state-logic-accrues-contradiction-chains".
- backlog — dogfood ambiguities, pre-existing in intake: intake never says to write `ESCALATIONS.md` when a hard gate fires (only the `Escalate:` field), and whether an approved intent.md counts as "narrowed by a human" is unstated; Step 6 lists `Route:`/`Escalate:` but `templates/SUMMARY.template.md` says "five header fields".
- backlog — a re-pin records no new chat request and cannot change `Confidence:`; harmless when the re-pin request only names the slug (dogfood E).
- backlog — the worktree guard refuses any Bash command whose text contains "git" inside a heredoc, compound command or `$?` chain, so plan grep checks had to run from script files.
- backlog — parallel implementers share one worktree git index, so one task's commit swept another task's staged files (commit 8f27359). The controller split it into 21be426 (task 1.2) and 05232e1 (task 1.4) before review. Fix candidates: serialize commits through the controller, or have implementers commit with `git commit -- <paths>` only.
