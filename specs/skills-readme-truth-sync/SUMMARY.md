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
   *(Corrected post-review — see Deviations.)*
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

- Rule 1 (self-inflicted, caught in review) — my first description of Check 2.5 said the evidence
  gate requires "a non-placeholder `### Verify` row". False, and ironic in a truth-sync PR: I
  imported that guarantee from `rules/auto-correct-scope.md`, which describes
  `scripts/check_lane_evidence.py` — a **different** and, as it turns out, **unwired** script.
  The commit hook only greps for the `^### Verify` heading, then calls
  `verify_summary.py --check`, which skips placeholder commands and returns 0 with a
  `no checks ran` warning when nothing real remains. Verified empirically (placeholder-only
  table → exit 0) before rewriting. Flagged by the Codex reviewer on PR #119 as P2.

  The real gap this exposes: `check_lane_evidence.py` is referenced by `auto-correct-scope.md`
  as "mechanizes the lane → evidence mapping", but no hook, `settings.json` entry, or GitHub
  workflow ever invokes it against a real SUMMARY — `run-tests.sh` registers only its *unit
  tests*, which prove the script works while nothing ever runs it. Nothing enforces the
  lane→evidence contract at commit or CI time. Documented in `skills/README.md` as advisory;
  wiring it is a behavior change and out of scope here.

  (Second-order note: my first attempt at the verify row for this used a naive `grep` that hit
  the unit-test registration and returned 1. Caught by running it instead of trusting it — the
  same discipline that produced this PR's findings.)

### Verify

| Check | Command | Exit | Notes |
|---|---|---|---|
| Doc-truth lint (paths + hook table vs settings.json) | `bash scripts/lint-doc-truth.sh` | 0 | all referenced paths exist |
| Full harness suite (L1 syntax + L2 hooks/python + L3 scripts) | `bash scripts/run-tests.sh` | 0 | ALL GREEN; 150 python passed |
| No live dangling xia2 PROJECT.md ref outside history | `bash -c 'test -z "$(grep -rl "xia2/PROJECT.md" agents rules skills CLAUDE.md README.md 2>/dev/null)"'` | 0 | specs/ + docs/solutions/ excluded as historical |
| xia2 has no PROJECT.md on disk | `test ! -f skills/xia2/PROJECT.md` | 0 | confirms the zero-config claim |
| `check_lane_evidence.py` gates nothing (backs the "advisory" wording) | `bash -c '! grep -rq check_lane_evidence settings.json hooks .github 2>/dev/null'` | 0 | `run-tests.sh` registers only its *unit tests*, never a gate invocation |

The corrected Check 2.5 wording was additionally confirmed by an ad-hoc probe (temp slug with a
placeholder-only `### Verify` table → `verify_summary.py --check` exits 0 with `no checks ran`).
Not listed as a row: reproducing it needs a pipe-bearing markdown table, which cannot survive a
Verify cell (`docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`). Pinning it
as `tests/scripts/*.test.sh` would auto-enroll it in CI — a scope expansion left as follow-up.

### Rollback

- `git revert <sha>` — prose-only; no schema, script, or hook behavior change.

## Follow-up (backlog for /compound)

- `scripts/lint-doc-truth.sh` checks only 4 top-level docs; `agents/*.md` and `rules/*.md` can
  carry dangling paths indefinitely. Widening `DOCS=` would have caught drift #6 at commit time.
- `scripts/check_lane_evidence.py` has **no call site** — not in `settings.json`, `hooks/`,
  `run-tests.sh`, or `.github/`. `rules/auto-correct-scope.md` presents it as the mechanized
  single source of truth for lane→evidence, but nothing runs it. Either wire it into
  `commit-quality-gate.sh` / CI, or soften the rule's wording to "advisory".

## Harness-Delta

`backlog` — two instances of the same failure mode: **a documented guarantee with no enforcing
call site.** (1) the doc-truth lint's `DOCS=` allowlist is narrower than the docs agents actually
load at session start (`rules/` auto-loads via `.claude/rules/`); (2) `check_lane_evidence.py` is
described as mechanizing the evidence contract but is wired nowhere. In both cases the docs
describe a stronger system than the code implements — which is exactly the drift class this PR
set out to fix, found one level up.
