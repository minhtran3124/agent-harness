# intent-draft-from-chat — Research Brief

Written 2026-10-10. Pins: repo a2b148c + uncommitted; git 2.x (local)

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing — extend `skills/feature-intake` with one `references/` file, the PR #284 pattern |
| **Why this is the lightest credible path** | Every mechanism needed (template, pin, re-pin, commit-gate tolerance of an intent-only commit) already exists; only a drafting step, two tool grants and canary updates are new |
| **Confidence** | 85% |
| **Next step** | writing-plans: one wave of prose edits (SKILL.md pointer + Step 6 wording + allowed-tools, new reference, template comment, terminology/specs-README lines, canaries), then a real-install trial |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Claude Code harness (skills, rules, hooks, scripts) — meta-repo, no app stack |
| Primary language + runtime | Markdown prompts; Bash hooks; Python 3 scripts (stdlib) |
| Frameworks / platforms | Claude Code 2.1.296 (local); Codex advisory adapter renders skill text |
| Relevant packages | none |
| Detectable versions | none load-bearing |
| Important constraints | SKILL.md ≤600 words (budget, `scripts/audit_skill_prompts.py`); runtime-neutral lint forbids `/skill` invocations in skill prose; `check_skill_tool_conformance.py` requires every instructed shell command to match `allowed-tools`; user preference: lean prompts |

---

## Feature Understanding and Assumptions

- **Requested feature:** a chat-only request on a new slug makes intake draft `specs/<slug>/intent.md` from the template and the chat, then ask the user to approve or edit; tiny + high is auto-approved.
- **What success appears to mean:** every new slug ends with a committed, approved intent.md and a SUMMARY pinned to it; non-tiny slugs wait for a human reply.
- **Assumptions from the request:** design D1–D8 (approved 2026-10-10).
- **Assumptions still needing confirmation:** none blocking; A3 (cross-session re-entry from files) is proven only by the real-install trial.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `skills/feature-intake/SKILL.md` = 599 words (measured 2026-10-10 `audit_skill_prompts.py`); ceiling 600 (budget). The pointer sentence must be paid for by trimming. |
| `Local` | `SKILL.md:4` allowed-tools: `Read, Write, Grep, Glob, Bash(git log *), Bash(git diff *), Bash(ls *), Bash(python3 scripts/verify_summary.py *), Bash(python3 runtime/run_state.py *)` — no `git add`/`git commit`. |
| `Local` | `scripts/check_skill_tool_conformance.py` scans SKILL.md **and `references/*.md`** for runnable commands (fenced bash, or inline spans starting with `git`, `python3`, …) and fails if no `Bash(...)` pattern matches. The new reference's `git add`/`git commit` lines therefore require the grants, and a missing grant fails `run-tests.sh` (A4 is checkable). |
| `Local` | Probe 2026-10-10 (scratch repo): with `other.txt` staged, `git add -- specs/x/intent.md` then `git commit -m … -- specs/x/intent.md` committed only `specs/x/intent.md`; `other.txt` stayed staged. Re-running the commit with nothing to commit exits 1. |
| `Local` | `hooks/commit-gate.sh:154` reads `git diff --cached --name-only` — the **whole index**, not the commit pathspec. With other files staged, the gate judges them too: it can over-block an intent commit, never under-block. |
| `Local` | `hooks/branch-isolation-guard.sh:166` exempts edits when every path is under `specs/*`; it does not inspect commits. `commit-gate.sh` has no branch check. An intent commit on `main` is allowed (as PR #284 intended for people). |
| `Local` | `tests/hooks/commit-gate-evidence.test.sh:224-239` — an intent-only commit with no SUMMARY passes standard and strict (A1). |
| `Local` | `skills/feature-intake/tests/intent-file-cases.md` IF-00, IF-02, IF-03, IF-04, IF-05, IF-09 assume a new slug with no or unapproved intent.md either goes chat-only (IF-00) or "stops"; under the new entry rule these become the draft procedure. Its Notes line "Agent notes go … never … intent.md" also changes. These canaries must be rewritten, not just appended to. |
| `Local` | `tests/scripts/deploy-worktree-isolation.test.sh:51-60` asserts the deployed feature-intake SKILL.md has rewritten helper paths (`python3 .claude/scripts/verify_summary.py`); a reference using `templates/INTENT.template.md` is rewritten the same way (`rewrote helper paths in 16 derived doc(s)` at deploy, 2026-10-10). |
| `Local` | `rules/terminology.md:79` "the human-written intent"; `templates/structure/specs-README.md:32` author "a human (optional)". `skills/README.md` has no such wording (grep `human`, 2026-10-10). |
| `Local` | `docs/solutions/` critical pattern `prose-encoded-state-logic-accrues-contradiction-chains` (2026-07-27) — re-observed in this design's review: three rounds of patching state rules until the procedure was restructured into two file-keyed cases. |
| `Inference` | A later session re-enters from files alone: the entry rule keys on "no SUMMARY + intent.md not approved-and-committed", and the request survives in `## Original request`. Proven only by real-install scenario 3. |

---

## Local Findings

- **Reuse:** template (`templates/INTENT.template.md`), pin/drift commands and re-pin (`skills/feature-intake/`), commit-gate tolerance (A1). Nothing to build in scripts or hooks.
- **Extension point:** `skills/feature-intake/references/` (already holds `re-pin.md`, read by explicit pointer). A second reference follows the same delivery path, so the context-propagation audit row is "explicit Read".
- **Word budget:** Step 1 already names re-pin; adding one clause for the draft procedure and shortening Step 5/6 wording is the expected trade.
- **Tests:** canaries are prose (traceability); the real-install trial (`install-harness.sh` + `claude -p`) is the truth-tier proof, as for PR #284.

## Upstream Findings

- Skipped: no external surface. The playbook's "brainstorm until concrete, then the originator approves" step (Claude Academy *capture-intent*, read 2026-10-10 for `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md`) is the source of the draft-then-approve shape; no new upstream reading needed.

## Docs Findings

- none (local-only; no version-specific API).

## Recommendation

Reuse and extend intake (design approach A). Rejected: a separate skill (more surface, Codex render, audit) and template-comment-only (not mandatory). Build nothing in hooks or scripts; the only new permission is `Bash(git add *)`, `Bash(git commit *)` on feature-intake.

## Risks, Unknowns, and Follow-Up Questions

- **Commit-gate judges the whole index** — an unrelated staged file can block the intent commit. Behavior: stop and report (design error table). Over-blocking only.
- **Canary rewrite scope** — six existing cases change meaning; the plan must rewrite them, or the canaries contradict the skill.
- **Word budget** — if the pointer cannot fit in 600 words, move more of Step 1 into `references/` (fallback, not expected).
- **A3** — cross-session re-entry is inference until scenario 3 runs.
- **Prose state** — keep the reference to the two file-keyed cases; any new case discovered in review goes to "What we do not claim" before adding branches.

## Source Pack

- none (local-only; no external surface)

## Evidence Boundary

Read: `skills/feature-intake/SKILL.md`, `references/re-pin.md`, `tests/intent-file-cases.md`, `templates/INTENT.template.md`, `scripts/check_skill_tool_conformance.py` (docstring), `hooks/commit-gate.sh` (staged-path lines), `hooks/branch-isolation-guard.sh:166`, `rules/terminology.md:76-81`, `templates/structure/specs-README.md:32`; greps over `scripts/`, `tests/` for `feature-intake` and `allowed-tools`. Not read: the Codex adapter renderer source (A4 relies on `run-tests.sh` coverage instead).

Depth: **Deep** (from intake high-risk); re-run with evidence — no upgrade or change.
