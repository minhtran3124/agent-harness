# Research Brief — plan-at-a-glance (issue #54, scope A+B)

**Depth mode:** Deep — touches high-blast-radius files (`skills/visual-planner/render_plan.py` core
skill engine; `hooks/render-plan-on-write.sh`) and changes a `render_plan.py` CLI flag (a declared
public-contract type in `xia2/PROJECT.md`).

---

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | **Reuse existing** — extend `render_plan.py`'s parser with three new functions + one opt-in `--summarize` flag; wire it through the existing hook. No new dependency, no new file. |
| **Why this is the lightest credible path** | The parser already extracts every field the block needs, and the PostToolUse hook already fires on every `PLAN.md` save — the only genuinely new capability is a markdown-writeback, which is a self-contained sentinel-region injection. |
| **Confidence** | 90% |
| **Next step** | `/writing-plans` — the design + this brief are sufficient to author the task plan. One anchor refinement below must fold into the plan. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Claude Code harness meta-repo (skills + hooks + rules + Python engines) |
| Primary language + runtime | Python 3 (stdlib only) + Bash hooks |
| Frameworks / platforms | None — `render_plan.py` is 1360 lines, **zero third-party imports** |
| Relevant packages | pytest (test runner, via `scripts/run-tests.sh`) |
| Detectable versions | No version pins relevant; GitHub-flavored Markdown + native Mermaid on the consuming side |
| Important constraints | `render_plan.py` is a hard-gate high-blast file; its CLI flags are a machine contract consumed by `render-plan-on-write.sh` and `view_plan.py`; hook exit-code contract (0=pass); determinism required (no LLM transcription) |

---

## Feature Understanding and Assumptions

- **Requested feature:** an additive, deterministic "At a glance" block (wave×task table +
  wave-subgraph Mermaid + count line + progress checkboxes) written into tracked `PLAN.md` by
  `render_plan.py`, refreshed on every save.
- **Success:** opening any `PLAN.md` on GitHub / in an editor / via `cat` shows scope, order, and
  progress with no tooling; the `<task>` blocks remain the source of truth; re-saving is a no-op diff.
- **Assumptions from the request:** scope is A+B only (C/D deferred); Approach 1 (opt-in `--summarize`
  flag) is decided; Mermaid = wave subgraphs; "est. steps" omitted.
- **Assumptions still needing confirmation:** the first-insertion **anchor** — see Local Findings #5
  and Risks. This is the one item the design's "insert after H1 line" gets wrong for real files.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `parse_task_block` (`render_plan.py:191`) returns `{id,wave,files,action,verify,done}`; `wave` defaults to `"—"` when absent (`:215`). |
| `Local` | `attach_titles` (`:1202`) sets `title` **only** when a `### Task <id> — Title` heading exists — no key otherwise → fallback required. |
| `Local` | `_done_task_ids` (`:467`) derives completed ids from `## Status Log` — the checkbox source of truth already exists. |
| `Local` | `extract_tasks` (`:162`) returns `(tasks, spans)` where `spans` are char offsets; `mask_fences` (`:128`) masks ``` fences before scanning — the established idiom for "ignore a region of the body." |
| `Local` | Only writer today is `main()` (`:1342`, `out_path.write_text(html)`); CLI is a hand-rolled arg loop (`:1299`) that currently rejects unknown `--` flags. **No markdown-writeback exists.** |
| `Local` | **9 of 17** existing `specs/*/PLAN.md` have 12–23 lines between the H1 and the first `## ` — usually a `> **For Claude:** REQUIRED SUB-SKILL…` directive blockquote (e.g. `correctness-review-scorer`, `harness-adoptions-execution`). |
| `Local` | `test_render_plan.py` = 43 pytest cases (frontmatter/task/status parse + HTML render); `tests/hooks/render-plan-on-write.test.sh` = 3 contract cases (non-PLAN silent-exit, no-engine silent-exit, real render → PLAN.html). |
| `Upstream` | Managed-region-via-sentinel injection is a proven, widely-copied pattern: `doctoc` (`<!-- START doctoc -->…<!-- END doctoc -->`), `markdown-toc`, `terraform-docs` (BEGIN/END markers in README), `ssh`/`husky` managed blocks. Validates the idempotent sentinel approach. |
| `Docs` | GitHub renders ` ```mermaid ` fenced blocks natively (GA since Feb 2022) — a Mermaid block in tracked `PLAN.md` needs zero tooling to view. |
| `Inference` | HTML de-duplication: strip the `AT-A-GLANCE:BEGIN…END` region from the body with a regex before rendering, mirroring how `mask_fences` neutralizes fence regions. |

---

## Local Findings

- **Relevant files:** `skills/visual-planner/render_plan.py`, `hooks/render-plan-on-write.sh`,
  `skills/visual-planner/test_render_plan.py`, `tests/hooks/render-plan-on-write.test.sh`,
  `rules/plan-format.md`, `skills/writing-plans/SKILL.md`.
- **Existing abstractions / extension points:** the full parser (`parse_frontmatter`,
  `extract_tasks`, `parse_task_block`, `attach_titles`, `_done_task_ids`) — **all data A+B needs is
  already produced**. New code = a *writer*, not a parser.
- **Conventions worth preserving:** stdlib-only; hand-rolled arg loop (add `--summarize` in the same
  style, don't introduce argparse); pure-function/IO split as seen in the existing helpers;
  determinism (no timestamps/randomness); hooks always `exit 0` (non-blocking).
- **What can be reused:** parser end-to-end; the hook's existing dispatch; `mask_fences`-style region
  neutralization for the HTML strip; the count math already computed for HTML stats
  (`render_plan.py:539-542` computes tasks/waves/files counts — mirror for the markdown count line).
- **What is missing locally:** (a) any markdown-writeback path; (b) the sentinel-region insert/replace
  logic; (c) a Mermaid emitter (HTML view is bespoke divs, not Mermaid — the markdown Mermaid is new);
  (d) **a correct first-insertion anchor** — see #5.
- **#5 — Anchor (the one design correction):** the design says "insert after the first H1 line." For
  9/17 real plans that would wedge the block *between* the H1 and its `> For Claude` directive
  blockquote, separating a load-bearing instruction from its title. **Recommend anchoring insertion
  immediately before the first `## ` heading** (i.e. just above `## 1. Motivation`), so the H1 +
  directive stay intact and the block sits at the top of the human-readable body. Regeneration still
  keys on the sentinels, so the anchor only matters on first insertion.

---

## Upstream Findings

- **Repositories/patterns inspected (from established knowledge; best-effort per Deep):** `doctoc`,
  `markdown-toc`, `terraform-docs`, `pre-commit`-style managed blocks.
- **Pattern already present upstream:** the exact "generate a derived region inside a tracked
  markdown file, delimited by HTML-comment sentinels, replace-in-place idempotently" pattern. This is
  the canonical solution to the idempotency + no-clobber requirement.
- **Worth modeling:** doctoc's discipline of (1) explicit BEGIN/END sentinels, (2) treating a
  half-present marker pair as "regenerate fresh," (3) a "do not edit this region" banner in the
  BEGIN comment — all already reflected in the design.
- **How closely it matches:** very closely; the only divergence is that we own the generator inside an
  existing engine rather than adding a new tool — strictly less surface.
- **Upstream gaps:** none adopted — no library is imported; the pattern is reused, not the code.

---

## Docs Findings

- **Official sources:** GitHub Docs — "Creating diagrams / Mermaid" (native fenced-block rendering).
- **Version status:** not version-sensitive; native Mermaid is stable on github.com and in most IDE
  Markdown previews (VS Code needs the built-in Markdown Preview Mermaid support or renders on GitHub).
- **Built-in capability that supports the feature:** GitHub's native Mermaid means the wave diagram is
  viewable with zero tooling — satisfying the issue's core "without running any tooling" goal.
- **Caveats:** some Markdown viewers don't render Mermaid (they show the code block); acceptable — the
  table + checklist + count line remain fully readable as plain Markdown, so the block degrades
  gracefully.

---

## Recommendation

- **Primary:** **Reuse existing** — three new functions in `render_plan.py`
  (`render_summary_block` pure, `inject_summary_block` pure string, `summarize_plan_file` I/O) + a
  `--summarize` flag + one hook-arg change. Adopt the sentinel-region pattern (Upstream) rather than
  any library.
- **Why lightest credible path:** all parsing already exists (Local); the hook already fires on every
  save (Local); the only new logic is a well-established, self-contained injection pattern (Upstream);
  zero new dependencies; strictly additive and reversible.
- **Why next-best lost:** folding injection into the default invocation (design Approach 2) was ruled
  out — it silently changes `render_plan.py`'s read→HTML contract and would ripple through the 43
  regression tests and `view_plan.py`. An LLM-authored block (Approach 3) violates the determinism
  constraint. A separate new script adds surface for no gain over a flag.
- **What would change this:** if a future direction (C) needs the rendered HTML published, that is a
  separate external surface and out of scope here.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - *Anchor splits a directive blockquote* (9/17 files) → mitigation: anchor before first `## `, not
    after H1. **Fold into the plan.**
  - *`title`/`wave` defaults* → `render_summary_block` must default missing `title` to the id and
    handle all-`"—"` waves (already in design §5.2 after review hardening).
  - *HTML duplication* → strip sentinel region before HTML render (mirror `mask_fences`).
  - *Diff churn* → determinism + write-only-if-changed (design §4.2/§5).
- **Evidence gaps:** the exact line where `render()` removes task spans from prose was not pinpointed,
  but the mechanism (`spans` + `mask_fences`) is confirmed and sufficient to model the HTML strip.
- **Version uncertainties:** none.
- **Follow-up questions for the user (max 2):**
  1. Confirm the anchor change: insert the block **before the first `## ` heading** (keeps the
     `> For Claude` directive attached to the H1) rather than immediately after the H1. *(Recommended.)*
  2. Should existing shipped plans be back-filled on next save (they will be, automatically, the first
     time each is edited), or is that acceptable as lazy/on-touch? *(Default: lazy on-touch.)*

---

## Source Pack

- **Local files read:** `skills/visual-planner/render_plan.py` (parser + main + HTML stats),
  `hooks/render-plan-on-write.sh`, `skills/writing-plans/SKILL.md`, `rules/plan-format.md`,
  `skills/visual-planner/test_render_plan.py`, `tests/hooks/render-plan-on-write.test.sh`,
  `specs/*/PLAN.md` (top-of-file scan across 17 files), `.claude/skills/xia2/PROJECT.md`.
- **Upstream checked:** doctoc / markdown-toc / terraform-docs managed-region pattern (knowledge).
- **Docs checked:** GitHub native Mermaid rendering (knowledge; stable since 2022).

---

## Evidence Boundary

> **Confirmed from artifacts:** parser produces all A+B fields; `_done_task_ids` reads Status Log;
> only `main()` writes (HTML only); hand-rolled arg loop rejects unknown flags; 9/17 PLAN.md have
> inter-H1/`##` directive content; 43 pytest + 3 hook contract cases; hook is PostToolUse non-blocking.
> **Inferred from patterns:** sentinel-region injection is the right idempotency mechanism (strong,
> from widespread upstream precedent); HTML strip via a `mask_fences`-style regex; no infinite loop
> (subprocess write ≠ tool invocation — corroborated by the spec reviewer against the hook source).
> **Not checked:** the precise `render()` line that strips task spans (mechanism confirmed, exact site
> not needed for planning); live web fetch of GitHub Mermaid docs (treated as stable known fact);
> behavior in non-GitHub Markdown viewers that lack Mermaid (accepted graceful degradation).
