# skills-readme-truth-sync

Lane: tiny
Confidence: high
Reason: Docs-only truth-sync. No hook, script, or skill logic changes; no hard gate tripped. Every claim fixed was verified against ground truth on disk before editing.
Affects: skills/README.md (workflow SoT), agents/PROJECT.md, agents/PROJECT.template.md, agents/README.md, rules/orchestration.md

## Intent

Check and update `skills/README.md` so the documented workflow matches the current code, and
update all other places that describe skills/workflow.

## What changed

Skill **inventory** was already correct — all 14 `skills/*/SKILL.md` on disk are listed, and the
"two standalone READMEs" claim holds. The drift was in the *claims about* those skills:

1. **xia2 is zero-config, docs said otherwise.** `skills/xia2/PROJECT.md` was deleted when xia2
   went config-free (`specs/remove-bootstrap-xia2/`, 2026-07-17), but `skills/README.md` still
   documented it in 4 places (workflow diagram, skills table, rationale one-liner + mermaid,
   maintenance discipline) and referenced a `PROJECT-CONFIG-GATE` that no longer exists in
   `SKILL.md`. Replaced with the built-in Common-signals model + a dated historical note
   explaining why `PROJECT.md >` strings survive in the xia2 structural tests.
2. **PLAN.html rendering is a hook, not a sub-agent dispatch.** `hooks/render-plan-on-write.sh`
   (PostToolUse, wired in `settings.json:56`) runs `render_plan.py --summarize` on every
   `PLAN.md` save. Docs claimed `/writing-plans` "dispatches a visual-planner sub-agent".
   Corrected in `skills/README.md` (4 sites) and `rules/orchestration.md` decision table.
3. **Empty "Setup" table** in `skills/README.md` — replaced with the actual mechanism
   (`scripts/init-structure.sh`, which is a script, not a skill).
4. **Handoff map was missing 3 skills** — added `/executing-plans`, `/review-diff`, `/create-pr`.
5. **Commit-hook section listed 3 checks; the hook has 5** — added Check 1.5 (pending-escalation
   deny) and Check 2.5 (evidence gate, `REQUIRE_VERIFY=1`), verified against the script.
6. **Dangling `skills/xia2/PROJECT.md` pointers in `agents/`** — `agents/` is not covered by the
   doc-truth lint (which reads only CLAUDE.md, README.md, HARNESS.md, skills/README.md), so this
   drift survived. Fixed in `PROJECT.md`, `PROJECT.template.md`, `README.md`.

Left alone deliberately: `specs/*` (historical records), `docs/research-*.md` (predate the repo
and over-claim — see memory), and `docs/solutions/*` (already carry dated status notes).

## Rationale

Ground truth on disk was checked before every edit rather than trusting the prior docs — the
`remove-bootstrap-xia2` SUMMARY claims `skills/README.md` was updated at "6 sites", yet stale
`PROJECT.md` references were still present. `not_observed != absent` cuts both ways: a recorded
fix is not proof the fix is still in place.

## Alternatives

- *Extend `scripts/lint-doc-truth.sh` to cover `agents/`* — would have caught drift #6
  mechanically. Not done here: it changes a CI-gating script (high-blast, Rule 4 territory) and
  is out of scope for a docs truth-sync. Logged below as follow-up.

## Deviations

- None. All edits trace to the stated request.

### Verify

| Check | Command | Exit | Notes |
|---|---|---|---|
| Doc-truth lint (paths + hook table vs settings.json) | `bash scripts/lint-doc-truth.sh` | 0 | all referenced paths exist |
| Full harness suite (L1 syntax + L2 hooks/python + L3 scripts) | `bash scripts/run-tests.sh` | 0 | ALL GREEN; 150 python passed |
| No live dangling xia2 PROJECT.md ref outside history | `bash -c 'test -z "$(grep -rl "xia2/PROJECT.md" agents rules skills CLAUDE.md README.md 2>/dev/null)"'` | 0 | specs/ + docs/solutions/ excluded as historical |
| xia2 has no PROJECT.md on disk | `test ! -f skills/xia2/PROJECT.md` | 0 | confirms the zero-config claim |

### Rollback

- `git revert <sha>` — prose-only; no schema, script, or hook behavior change.

## Follow-up (backlog for /compound)

- `scripts/lint-doc-truth.sh` checks only 4 top-level docs; `agents/*.md` and `rules/*.md` can
  carry dangling paths indefinitely. Widening `DOCS=` would have caught drift #6 at commit time.

## Harness-Delta

`backlog` — the doc-truth lint's `DOCS=` allowlist is narrower than the set of docs agents
actually read at session start (`rules/` is auto-loaded via `.claude/rules/`).
