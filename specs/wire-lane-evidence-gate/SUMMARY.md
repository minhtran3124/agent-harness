# wire-lane-evidence-gate

Lane: high-risk
Confidence: high
Reason: Edits `hooks/commit-quality-gate.sh`, a high-blast file that auto-runs on every commit (Rule 4 hard gate). Human explicitly authorized the change and narrowed the scope to "wire check_lane_evidence into the hook", which satisfies the gate; confidence high because the blast radius was measured before writing code (52/52 existing specs pass) and the change is fail-open by construction.
Affects: hooks/commit-quality-gate.sh (commit path for every contributor), tests/hooks/commit-quality-gate.test.sh, docs (skills/README.md, CLAUDE.md, rules/auto-correct-scope.md)

## Intent

Wire `scripts/check_lane_evidence.py` into the commit gate, as a PR separate from #119.

## Context

`rules/auto-correct-scope.md` bills the script as the mechanized single source of truth for the
lane → evidence mapping. It was not mechanized: no hook, `settings.json` entry, or CI workflow
invoked it against a real `SUMMARY.md`; `run-tests.sh` registers only its unit tests. Surfaced by
the Codex review on PR #119.

## What changed

**Check 1.6 (Lane evidence)** in `hooks/commit-quality-gate.sh`, placed after Check 1.5 and
deliberately mirroring its semantics:

- **Scope** — only commits touching `specs/<slug>/`. A commit that touches no spec is untouched.
- **Staged-copy authoritative** — the staged `SUMMARY.md` is written to a temp file and passed to
  `check_lane_evidence.py` (which accepts a direct path via `_resolve_path`), so a commit that
  *adds* the missing evidence self-unblocks. Same self-unblock property as Check 1.5.
- **Always on, not opt-in.** Opt-in is precisely what produced a dead script. Safe to do because
  the blast radius was measured first: all 52 existing specs already pass.
- **Fail-open** on missing `python3` / missing script — a missing interpreter must never gate
  commits (matches Check 2.5's re-run convention).
- **Output re-labeled** — the script names the temp path, meaningless to a committer, so the
  hook substitutes the real `specs/<slug>/SUMMARY.md` path into the message.

## Rationale

Placed as 1.6 rather than folded into 2.5 because the two answer different questions and have
different trigger conditions: 1.6 asks *does the required evidence exist* (keyed on staged specs,
always on); 2.5 asks *are the claimed exit codes honest* (keyed on staged `app/` files, opt-in).
Merging them would have coupled an always-on structural check to an opt-in behavioral one.

## Alternatives

- **Opt-in via an env var** (e.g. `REQUIRE_LANE_EVIDENCE=1`) — rejected: identical to the status
  quo that produced the dead script. The measurement (52/52 pass) removed the usual reason to
  hedge.
- **Wire into CI instead of the commit hook** — rejected: CI feedback arrives after the commit is
  written, and the self-unblock property (fix evidence in the same commit) only works at commit
  time. CI remains a viable *addition* later.
- **Fold into Check 2.5** — rejected, see Rationale.

## Deviations

- Rule 2 — Added a guard for a slug directory containing no `SUMMARY.md` (e.g. only `PLAN.md`),
  which is legitimate and must not block. Not in the stated scope but required for correctness;
  covered by a test.

### Verify

| Check | Command | Exit | Notes |
|---|---|---|---|
| Hook syntax | `bash -n hooks/commit-quality-gate.sh` | 0 | |
| Hook contract suite (8 new Check-1.6 cases) | `bash tests/hooks/commit-quality-gate.test.sh` | 0 | 28 passed, was 20 |
| Full harness suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |
| Doc-truth lint (hook table vs settings.json) | `bash scripts/lint-doc-truth.sh` | 0 | |
| No retroactive breakage across every existing spec | `bash -c 'for d in specs/*/; do s=$(basename "$d"); test -f "$d/SUMMARY.md" || continue; python scripts/check_lane_evidence.py "$s" >/dev/null 2>&1 || exit 1; done'` | 0 | all 52 specs pass the new gate |
| Gate is load-bearing (mutation) | see Mutation note below | 2 | neutering `exit 2` kills 2 tests |

**Mutation note:** replacing the gate's `exit 2` with `exit 0` makes
`bash tests/hooks/commit-quality-gate.test.sh` report `26 passed, 2 FAILED`. The suite is not
vacuous (`docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md`). Not listed
as a re-runnable row because it requires an intentional source edit.

### Rollback

- Revert everything: `git revert <sha>`
- Disable the gate alone without a revert: delete the `Check 1.6` block from
  `hooks/commit-quality-gate.sh` (it is self-contained between the Check 1.5 and Check 2 banners
  and shares no state with any other check).
- Emergency bypass for a single commit: `git commit --no-verify` is **not** applicable (this is a
  PreToolUse harness hook, not a git hook); remove `python3` from PATH or temporarily rename
  `scripts/check_lane_evidence.py` to trigger the documented fail-open path.

## Harness-Delta

`fix-direct` — closes one of the two "documented guarantee with no enforcing call site" instances
recorded in `specs/skills-readme-truth-sync/SUMMARY.md`. The other (`lint-doc-truth.sh`'s `DOCS=`
allowlist not covering `agents/` or `rules/`) is still open.
