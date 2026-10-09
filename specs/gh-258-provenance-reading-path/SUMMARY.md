# gh-258-provenance-reading-path — Summary

Lane: high-risk
Confidence: medium
Reason: workflow-engine hard gate. It changes the design template that the isolated design reviewer is required to read (skills/brainstorming/references/design-template.md) and the xia2 research-brief template, which steer every spec. The same surfaces were classified high-risk in batch 1 (gh-258-spec-evidence-rules).
Flags: workflow-engine, existing behavior, multi-domain
Affects: skills/brainstorming/references/design-template.md, skills/xia2/references/research-brief-template.md, and the design reviewer prompt if it gains a check
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Scope-deciding sentences, in chronological order:

> check issue https://github.com/minhtran3124/agent-harness/issues/258, xem thu da implement het cac item trong table rollout chua?

> ok, chạy tới PR luôn

(The last message answered "Theo rollout của #258, còn lại item 6 và 7 … template prose, batch \"later\"", together with the offer to open issues for two pre-existing problems; those became #276 and #277.)

Items 6 and 7 of GitHub issue #258 (https://github.com/minhtran3124/agent-harness/issues/258), as written in the issue:

> **Item 6 — Pinned provenance header on research and design docs.** Purpose: A reader (or a staleness check) knows exactly what state of the world the document describes and when it was written. Gap: `docs/solutions/` entries carry `confirmed_at` with a 30-day staleness rule, but `research-brief.md` and `design.md` have no machine-readable date or pin. Some have a free-text "Evidence refreshed" line. Target: The research-brief and design templates start with `Written <YYYY-MM-DD>. Pins: <repo sha / tool versions the claims were checked against>`. A later staleness check is optional.
>
> **Item 7 — Reading path and a worked trace for multi-document specs.** Purpose: An agent or reviewer loads the minimum context first, which matters for our context budgets. A worked trace exposes gaps between layers that a per-component description hides. Gap: Multi-document specs (e.g. `codex-support` with `design.md`, `ROADMAP.md`, `packaging-decision.md`, JSON inventories) have no stated entry point or reading order. Target: Optional design-template sections: `## Reading path` (only for specs with more than two documents) and `## Worked trace` (one concrete request followed end to end).

The rollout table lists items 6 and 7 together as the "later" batch ("template prose, small"). Other #258 items are out of scope. The branch is cut from `spec-format`; the PR targets `--base spec-format`.

Confidence is `medium`, not `high`: the targets are written in #258, but two details have a
documented default rather than a single reading, to be settled in brainstorming. (a) Whether the
design reviewer checks the new header. The default is that the reviewer reports a missing or
malformed `Written … Pins:` line, because item 6 says the templates *start with* it, and reviewer
checks are how batch 1 enforced template sections. (b) Whether the optional item-7 sections are
reviewed. The default is no check beyond "if present, it is not a placeholder", because the issue
calls them optional. The item-6 staleness check stays out of scope ("optional", "later").

## What changed

- **Item 6, provenance header.** The design template and the research-brief template each open with a fenced document skeleton: the document title, then `Written <YYYY-MM-DD>. Pins: <…>` as the first non-blank line after it. Pins names at least the repository short sha (HEAD's short sha plus `+ uncommitted` for uncommitted work), and tool versions only when a claim depends on them. A revision appends a `Revised <YYYY-MM-DD>. Pins: <…>` line and never edits earlier lines. In a research brief, Pins does not replace `Repo Snapshot`.
- **Item 7, optional sections.** The design template gains `## Reading path` (after `## Goal`, only for specs with more than two documents) and `## Worked trace` (after `## Architecture`). Both are left out when unused, with no `- none` line.
- **Reviewer.** `skills/brainstorming/spec-document-reviewer-prompt.md` gains two rows. `Provenance header` checks the header's position, date format and Pins (a value naming no repository short sha is an issue) and the order of `Revised` lines. `Optional sections` flags placeholder text or a `- none` line.
- **Test.** `tests/scripts/brainstorming-contract.test.sh` gains anchor cases for both templates and the reviewer, plus an awk line-position case per template that requires the `Written` line right after the skeleton title, inside the same fence.

### Rationale

This is the same mechanism batch 1 used: the templates carry the contract, and the design reviewer, which already Reads the design template through `CONTEXT_MATRIX`, enforces it in the existing review loop. Template prose alone was rejected because `rules/terminology.md` §2 measured that wording without a check does not hold. No script or hook changes, so no new gate and no gate-parity change.

### Alternatives considered

- Template prose only (the literal "template prose" in the rollout table): rejected, no enforcement.
- Template plus a staleness script: rejected, #258 calls the staleness check optional and later, and it would touch `scripts/`.
- A reviewer for research briefs: out of scope; recorded under "What we do not claim" in the design.

### Deviations

- Correctness fix round `3d092e1` (Rule 1, user-chosen "Fix the four 50s"): HEAD's short sha instead of the literal `HEAD` in both templates and `design.md` §1; the `Provenance header` row flags a Pins value naming no repository short sha; the `Optional sections` row flags a `- none` line (design §3 table updated to match); `skeleton_written_first` clears its state when the skeleton fence closes. The design edits clarify D1/D3/D4 wording and reopen no decision.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 .claude/scripts/verify_summary.py --lane gh-258-provenance-reading-path` | 0 | | |
| templates carry skeleton, header, optional sections; reviewer carries both rows; Written line position | `bash tests/scripts/brainstorming-contract.test.sh` | 0 | 15 passed, including two line-position cases | SC-1 |
| research-depth drift anchors intact | `bash tests/scripts/research-depth-drift.test.sh` | 0 | 11 passed | SC-2 |
| isolated-prompt delivery contracts hold | `python3 scripts/render_skill_prompt.py --check-all` | 0 | all contracts present | SC-3 |

After the fix round `3d092e1`, `brainstorming-contract.test.sh` still reports 15 passed. A scratch mutant (skeleton fence closing right after the title, a later fence starting with the `Written` line) exits 0 under the original awk and 1 under the fixed one.

The full suite is not a Verify row (`rules/plan-format.md` Guardrail 4). `bash scripts/run-tests.sh` reported ALL GREEN (pytest 836 passed) at `3d092e1` (controller run, 2026-10-09).

### Correctness Review

The six FIND angles ran over `744a72b..406b867` and produced 5 locations after dedup, each scored once by an independent scorer against a threshold of 75. None reached 75:
- the "pin `HEAD`" wording in both templates: 50;
- the `Provenance header` row: 50 (a Pins value with no repository sha passes); header-less older designs on revision 25; `Revised` ordering on same-day or before `Written` 25;
- the `Optional sections` row: 50 (a `- none` line passes); a reading path in a two-document spec 0 (documented in the design's "What we do not claim");
- the `skeleton_written_first` awk: 50 (`seen` survives the fence close); prefix title match and empty `Pins:` 25;
- the reviewer `has_all` anchoring only row labels: 25.

The user chose to fix the four 50s (`3d092e1`). The independent re-check closed 4/4, found no new defect (the valid header examples still pass, the required sections' `- none — <reason>` lines are unaffected, the adversarial awk input now exits 1), and reported 15 passed. Advisories recorded and not fixed:
- A revision pass on one of the 32 designs written before this change raises a missing-header issue; the author backfills a `Written` line from the file's `git log`. Rewriting existing specs stays a non-goal.
- "`Revised` dates not in ascending order" does not say that equal dates are fine or that `Written` takes part in the ordering.
- The reviewer `has_all` case anchors the row labels, not the defect clauses, so a gutted row keeps the test green.
- The awk title match is a prefix match and does not require text after `Pins:`; the function checks position only.

### Intent Findings

The intent review (plan-blind) over `744a72b..406b867` found no gap: both templates start their output with `Written <YYYY-MM-DD>. Pins: <…>`, and the design template has optional `## Reading path` (more than two documents) and `## Worked trace` sections. The staleness check and other #258 items are untouched.
- **drift (advisory, equivalent):** the `Written` line is the first non-blank line after the document title, shown inside a fenced skeleton, rather than literally the first line of the template file. The template's own instructions keep their `# … Template` title.
- **excess (report only):** the `Revised` line convention and `+ uncommitted`, traced to the approved design (D2, §1).
- **excess (report only):** the two reviewer rows, traced to the intake defaults (a) and (b) and D4.

### Context-Propagation Audit

**Result: PASS.** Range `744a72b..HEAD`. Search surface: `grep -rn "design-template.md\|research-brief-template.md\|spec-document-reviewer-prompt"` over `skills/brainstorming/SKILL.md`, `skills/brainstorming/references/spec-review-loop.md`, `skills/xia2/SKILL.md` and `scripts/render_skill_prompt.py`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `design-template.md` (skeleton, header rules, optional sections) | brainstorming controller writing `design.md` | main | `brainstorming/SKILL.md:34` names the template and writes to it | `brainstorming-contract.test.sh` (15 passed) |
| same | isolated design reviewer | subagent | `spec-review-loop.md` passes the absolute template path as `[TEMPLATE_FILE_PATH]`; `CONTEXT_MATRIX` requires the template Read | `render_skill_prompt.py --check-all`; `context-propagation-regression.test.sh` (11 passed, including the design-reviewer template-Read mutation) |
| `spec-document-reviewer-prompt.md` (Provenance header, Optional sections rows) | isolated design reviewer | subagent | the prompt text is pasted at dispatch | `brainstorming-contract.test.sh` reviewer case |
| `research-brief-template.md` (skeleton, header rules) | xia2 controller writing `research-brief.md` | main | `xia2/SKILL.md:36` fills the template | `brainstorming-contract.test.sh` brief cases; `research-depth-drift.test.sh` (11 passed) |
| deployed copies | consumer repos | main and subagent | `templates`/`skills` sync | `lint-doc-truth.sh` exit 0 |

### Rollback

- `git revert -m 1 <merge-sha>` of the PR into `spec-format`.

### Minor review findings

- Task 1.1 (`406b867`): after the skeleton title, the awk kept scanning into later fences. Fixed in `3d092e1` (the correctness 50 at the same location).
- Call-site review note: the design template cites "budget, from #258", an issue number that means nothing in a consumer repo. Left as is; the text reads as a rationale.

### Not auto-verified

- That the design reviewer applies the two new rows. Traceability only: the contract test checks the row text, not reviewer behaviour.
- That a pinned sha is the one the claims were checked at. Out of scope by design ("What we do not claim").
- That research briefs carry the header. No reviewer checks research briefs; the template is the only carrier.
- That agents fill the header from the fenced skeleton rather than copying the template title. Traceability only: SC-1 pins the template's skeleton, not generated documents.

### Harness-Delta

- none
