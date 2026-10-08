# gh-258-spec-evidence-rules — Summary

Lane: high-risk
Confidence: medium
Reason: workflow-engine hard gate — the change edits skill prose and templates (skills/brainstorming, skills/xia2/references, skills/compound) that steer every spec; multi-domain across three skills
Flags: workflow-engine, multi-domain, existing behavior
Affects: skills/brainstorming (design.md shape), skills/xia2/references/research-brief-template.md, skills/compound
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Scope-deciding sentences, in chronological order:

> now, we have the spec format standard but i'm thinking to find way improve it more
> let check repo https://github.com/tamnd/rupg/tree/main/spec
> review the way spec was written and understand structure, purpose, ...
> what we can learn from it? distill? etc ...

> write the research to the github issue first - in 1 github issue
> - seperate for each item
> - detail purpose
> - clean explaination
> - target
>
> after that run "/feature-intake" for 1, 2, 4

Items 1, 2 and 4 refer to GitHub issue #258 (https://github.com/minhtran3124/agent-harness/issues/258):

- Item 1 — "What must be true" and "What we do not claim" sections in `design.md`
- Item 2 — A change rule for settled decisions
- Item 4 — Label numbers as predictions or measurements, and keep the prediction

Items 3, 5, 6 and 7 of #258 are out of scope for this spec.

Confidence is `medium`, not `high`: the targets are written in #258, but two details have a
documented default rather than a single reading. (a) Item 2 says where a decision-change entry
lives before the item-3 register exists; the default is a decision-change note in the spec
(`### Deviations` style). (b) Item 4's label set is `prediction | budget | measured <date> <source>`;
the default applies it to load-bearing numbers only, not every number in prose.

## What changed

<filled at finishing-a-development-branch>

### Rationale

<filled at finishing-a-development-branch>

### Alternatives considered

- none

### Deviations

- Decision change after approval — DC1 in `design.md` reopens D1 (no `scripts/` change) for D12 (register the design reviewer in `CONTEXT_MATRIX`). Raised by research brief F1; the user chose it on 2026-10-08. This pointer line is the design-template convention for a post-approval decision change, not a Rule 1–3 auto-fix.

### Context-Propagation Audit

**Result: PASS** (after one repair, `7aba506`). Search surface: `grep -rn` over `skills/ scripts/ tests/ agents/ rules/` for `design-template`, `Assumption coverage`, `research-brief-template`, `design.md`; the code-review-graph MCP server was not connected (`uvx` missing), so no graph query was used.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `design-template.md` (§5.1–§5.4 rules, sections, labels) | brainstorming | main | explicit Read (`SKILL.md` step 5) | `brainstorming-contract.test.sh` "design template exists and brainstorming reads it" |
| `design-template.md` | design reviewer | reviewer subagent (isolated) | path passed by `spec-review-loop.md` step 1 + explicit one-line Read in `spec-document-reviewer-prompt.md` | `CONTEXT_MATRIX` `spec-document-reviewer` (`render_skill_prompt.py --check-all`) + mutation case in `context-propagation-regression.test.sh` |
| §6.1 design checks | design reviewer | reviewer subagent | pasted (rows inside the dispatched prompt) | `brainstorming-contract.test.sh` "design reviewer gets the template and its checks" |
| Reopen pointer (change rule) | writing-plans | main, post-approval | pasted into every `design.md`; writing-plans Reads `design.md` (required input) | `writing-plans-contract.test.sh` "requires design and research brief"; template anchor in check 2 |
| Reopen pointer (change rule) | SDD controller / implementer | main + implementer, post-approval | **not delivered** — neither reads `design.md`; Rule 4 STOP (explicit Read of `auto-correct-scope.md`) is the only guard | Accepted, declared gap: design D10 + `What we do not claim` row; not a load-bearing claim of this change |
| Assumption coverage instruction (§5.5) | writing-plans | main | in `SKILL.md` step 5 (loaded with the skill) | `writing-plans-contract.test.sh` check 4 |
| Assumption coverage check (§6.2) | plan reviewer | reviewer subagent (isolated) | pasted (row inside the dispatched prompt); design reachable via existing `[SPEC_FILE_PATH]` | `writing-plans-contract.test.sh` check 4; `[SPEC_FILE_PATH]` pre-existing in prompt |
| Number-label rule | xia2 | main | inline copy in `research-brief-template.md`, which xia2 step 6 fills | **Repaired:** check 5 now anchors the full set (`measured <YYYY-MM-DD> <source>`, `prediction`, `budget`, `load-bearing`); mutation (strip `` `budget` ``) shown to break the anchor set |
| Number-label rule | design reviewer | reviewer subagent | via the template Read above | as row 2 |
| prediction → measured source | compound | main | in `SKILL.md` | `compound-contract.test.sh` check 6 |
| All of the above | Codex advisory alpha | Codex sessions | same skill files via the Agent Harness plugin; relative `references/` paths unchanged | Not separately exercised (advisory runtime, `CLAUDE.md` "Runtime support boundary"); recorded, not claimed |

Failed row and repair: the research-brief inline copy of the label rule was complete but anchored by one label only (an unanchored inline subset) → check 5 extended, commit `7aba506`.

Recorded per design §7: the `### Deviations` pointer line for a post-approval decision change extends `rules/auto-correct-scope.md` "Reporting" (Rule 1–3 only) without editing that rule; the template states the extension explicitly.

### Correctness Review

Range `b0d2a92..HEAD` via `.harness-state/sdd/package-branch.md`. Six FIND angles (enclosing-function, removed-behavior, call-site-impact, stack-defects, guard-completeness, prior-art); 9 locations after dedup; one independent scorer each; threshold 75.

**Fixed (commit `61179e7`):**
- `tests/scripts/context-propagation-regression.test.sh:133` — score 75, Rule 1. The design-reviewer mutation deleted the prompt's only `design-template.md` line, so the plain `required` check failed on its own and the case stayed green with `required_reads` removed. Now strips only the bold Read verb. Re-verified (truth tier): mutated copy → `--check-all` exit 1 ("missing required policy Read"); same copy with `required_reads` removed from the matrix → exit 0.
- `scripts/test_render_skill_prompt.py:43` — score 0 (`unmodified-line`), but a blocking Rule 3 break: the hard-coded `CONTEXT_MATRIX` key set lacked `spec-document-reviewer`, so the pytest step would fail. Added. Re-verified: `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_render_skill_prompt.py` → 7 passed.

### Advisory Findings

Seven findings scored below threshold. The user chose (2026-10-08) to fix the cheap ones in this PR: commit `0f82b9e`, plus `22da980` for a re-review P3. A focused re-review of `0f82b9e` returned `pass` with findings 1–6 closed.

- **Fixed** `spec-document-reviewer-prompt.md:37` (50) — DC check now accepts a new decision later superseded in a chain of reopenings.
- **Fixed** `spec-document-reviewer-prompt.md:34` (50) — number-label check counts values; a kept `prediction → measured` pair is two.
- **Fixed** `design-template.md:132` (50) — worked example uses the canonical `measured <YYYY-MM-DD> <source>`.
- **Fixed** `design-template.md:55` (50) — tier definitions inlined (consumer installs do not ship `CLAUDE.md`).
- **Fixed** `spec-document-reviewer-prompt.md:32` (25) — a bare `none yet` is valid in both the template and the reviewer row.
- **Fixed** `skills/writing-plans/SKILL.md:31` (50) — `- A<n> → retired by DC<n>` coverage form, accepted by the plan reviewer; the template's *Proven by* rule lists it too (re-review P3).
- **Stated limit, not fixed** `spec-review-loop.md:5` (50) — a revision-pass reviewer sees only the current design, so it cannot detect a settled row edited in place without a `DC<n>`. The template now says so; giving the reviewer the approved baseline would change its input contract.
- **Open, P3 (re-review)** — `plan-document-reviewer-prompt.md:34` accepts `- A<n> → retired by DC<m>` without checking `DC<m>` against the spec's row, and `spec-document-reviewer-prompt.md:37` accepts `superseded by DC<m>` without checking that `DC<m>` reopens that row. Cross-reference gaps in a traceability-tier check.

### Minor review findings

<!-- Non-blocking per-task reviewer findings, forwarded to the final review chain. -->

- Task 1.1 (`50d1343`) — `design-template.md` Decisions example shows only a `settled` row; design §5.3 also shows a `superseded by DC1` row and a DC naming the new decision. Optional second example row.
- Task 1.1 (`50d1343`) — `skills/brainstorming/SKILL.md:40` runs ~101 columns and "write `design.md` to that template. Write the approved result…" overlaps slightly; optional merge into one sentence.
- Task 1.3 (`908f750`) — `skills/compound/SKILL.md` grew 54 → 56 lines, past the 45–54 range the plan cited, to keep label anchors on one line.
- Task 1.2 (`8fe2736`) — `skills/writing-plans/SKILL.md` step 5 tail line is ~200 columns (new self-check sentence joined onto the pre-existing long line); optional rewrap at ~100 columns.
- Task 1.2 (`8fe2736`) — step 5 addition is ~4 sentences vs the plan's "two or three"; all content is required by design §5.5.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane gh-258-spec-evidence-rules` | 0 | intake-time check only | |
| design template, brainstorming Read, reviewer checks, brief labels | `bash tests/scripts/brainstorming-contract.test.sh` | 0 | 7 passed | SC-1 |
| writing-plans Assumption coverage + plan reviewer row | `bash tests/scripts/writing-plans-contract.test.sh` | 0 | 4 passed | SC-2 |
| compound prediction → measured source; pinned anchors kept | `bash tests/scripts/compound-contract.test.sh` | 0 | 4 passed | SC-3 |
| research-depth drift guard still holds | `bash tests/scripts/research-depth-drift.test.sh` | 0 | 11 passed | SC-4 |
| CONTEXT_MATRIX registers the design reviewer | `python3 scripts/render_skill_prompt.py --check-all` | 0 | all contracts present | SC-5 |
| design-reviewer template Read mutation detected | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | 11 passed | SC-6 |

### Not auto-verified

- none

### Rollback

- The change is prose and template only (no hook, script or gate). Undo it with `git revert -m 1 <merge-sha>` of the PR that ships it.
- Consumers that already re-synced keep the new template text until their next re-sync after the revert (`scripts/install-harness.sh` / `scripts/deploy-harness.sh`); a locally edited copy is kept and the reverted one lands beside it as `<file>.harness-incoming`.
- Specs written with the new sections need no migration: the sections are additive and no gate reads them.

### Harness-Delta

- `feature-intake` was not deployed under `.claude/skills/` in this repo, so `/feature-intake` was not invocable as a skill; intake was run by following `skills/feature-intake/SKILL.md` directly. fix-direct: ran `bash scripts/deploy-harness.sh --yes` (standard profile) on 2026-10-08; the deployed `SKILL.md` differs from the source only in rewritten helper paths. The skills load after a Claude Code restart.
- `rules/plan-format.md` "Success Criteria schema" example uses `verify_summary.py --lint specs/<slug>`, but `verify_summary.py` has no `--lint` flag (exit 2, 2026-10-08). The example is fenced/illustrative, so nothing breaks, but it teaches a command that does not exist — backlog.
- Subagent tool policy refuses implementer writes to `.harness-state/sdd/report-*.md` (both Write and a Bash heredoc were denied for Tasks 1.1–1.3), so the SDD report-file handoff in `implementer-prompt.md` cannot work as written; the controller transcribed each returned report to the path — backlog.
- `hooks/branch-isolation-guard.sh` refused a Write to the session scratchpad root (`unsafe-path:outside-root`, judged against the launch checkout on `main`) while the session was isolated in a worktree; the same file under a non-shared-branch clone inside the scratchpad was accepted. Paths outside every checkout fail closed even when they are the harness-designated scratchpad (2026-10-08, side task: herdr-sidekick PR #3) — backlog.
