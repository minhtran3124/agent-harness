# fix-hook-project-root-resolution — Summary

Lane: high-risk
Confidence: high
Reason: hard gate `high-blast` (mode=block) — the diff touches `hooks/*`; no other gate fires
Flags: high-blast, existing-behavior
Affects: hook repo-root resolution contract (every git-reading gate)
Input-type: harness improvement
Route: high-risk — design.md (real fork on the unset-var fallback) → PLAN.md → direct execution on this branch
Escalate: no — the human narrowed the hard-gated scope explicitly in-session (see Intent)

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- verbatim, in chronological order of the scope-deciding turns -->

> chạy spike đợt 4 trước đi

> #0 là làm gì? giải thích dễ hiểu lại

> ok , xúc

Scope as presented to the user before authorization, and thereby the narrowed hard-gate scope:
move 8 named hooks (`blast-radius-check`, `branch-guard`, `commit-quality-gate`,
`render-plan-on-write`, `risk-corroboration`, `ruff-on-edit`, `scope-gate`, `check-untracked-py`)
to `CLAUDE_PROJECT_DIR` as the repo-root source, keep `SCRIPT_DIR` only for locating each hook's
own libs, and add a fail-closed guard when the project root cannot be determined unambiguously.
Estimated half a day, high-risk lane, on its own branch.

## What changed

Seven hooks stopped deriving the repository root from their own file location and now take it from
`CLAUDE_PROJECT_DIR`, falling back to git-from-CWD. Two blocking gates
(`commit-quality-gate`, `risk-corroboration`) block with a named reason when no root can be
determined; the five non-blocking hooks note it and exit 0, preserving the posture `CLAUDE.md`
documents for each. `SCRIPT_DIR` is retained everywhere, but only to locate each hook's own libs.

A ratchet (`scripts/check-hook-root-source.sh`, wired into `run-tests.sh` L1) prevents the pattern
from returning, and `tests/hooks/repo-root-resolution.test.sh` re-runs the original failure.

Scope note: `check-untracked-py.sh` is **not** part of this change. My first count said 8 hooks;
re-reading showed it uses CWD-relative `git ls-files` by design and was never affected. Seven.

### Rationale

Seven of eleven hooks resolved the repository root from the hook's own location
(`git -C "$SCRIPT_DIR" rev-parse --show-toplevel`). That is correct only because
`deploy-harness.sh` copies hooks *into* the project. A spike run on 2026-09-09 measured two
failure modes when the hook lives outside the project: with the hook's directory outside any git
repo the command exits 128 and `REPO_DIR` is empty (loud); with the hook's directory *inside* any
git repo it exits **0** and returns that repo — so a gate audits the wrong repository and reports
success. `claude plugin marketplace add` clones, so the second mode is the normal install path,
not an edge case. `CLAUDE_PROJECT_DIR` is supplied by the runtime and was observed set in the
spike; two hooks already use it.

### Alternatives considered

- **Keep `SCRIPT_DIR` and compare against CWD, warn on mismatch** — rejected: a warn on a
  block-mode gate is the same silent-pass this change exists to close.
- **Fall back to `$PWD` when `CLAUDE_PROJECT_DIR` is unset** — partially adopted; see design.md.
  `$PWD` is right for the real runtime but wrong under `tests/lib.sh`, which runs hooks with CWD
  set to a temp repo — so the fallback must be ordered, not either/or.
- **Do nothing until the plugin decision is made** — rejected: the defect is reachable today by
  anyone whose harness checkout sits inside another git repo.

### Deviations

- **Rule 2 (missing prerequisite, auto-fixed):** SC-1 in `PLAN.md` named
  `scripts/check-hook-root-source.sh` as its checker, but no such script existed. Created it and
  wired it into `run-tests.sh` L1, then added task 2.2 to `PLAN.md` to cover the two files. Caught
  by `hooks/blast-radius-check.sh`, which flagged `scripts/run-tests.sh` as outside the plan's
  `<files>` set — the hook did its job on this change's own author.
- **Corrected scope before implementing:** the research report and this SUMMARY's first draft said
  8 hooks. `check-untracked-py.sh` resolves nothing from `SCRIPT_DIR` except its lib path, so the
  real count is 7. No code was written against the wrong number.

### Verify

<!-- Rows are pipe-free and <60s: ci-strict-gate.sh re-runs each one under a 60s cap, and a
     whole-suite invocation is banned as a row (docs/solutions/harness/
     verify-row-must-be-pipe-free-and-under-60s.md). The full suite is cited in prose below. -->

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| No hook derives its root from SCRIPT_DIR | `bash scripts/check-hook-root-source.sh` | 0 | Ratchet proven to bite: re-introducing the old line in `scope-gate.sh` made it exit 1 | SC-1 |
| Scenario-B regression suite | `bash tests/hooks/repo-root-resolution.test.sh` | 0 | 11 passed | SC-3 |
| risk-corroboration contract suite | `bash tests/hooks/risk-corroboration.test.sh` | 0 | 38 passed; largest suite over a changed blocking gate | SC-2 |
| commit-quality-gate contract suite | `bash tests/hooks/commit-quality-gate.test.sh` | 0 | 34 passed; the other changed blocking gate | SC-2 |
| blast-radius contract suite | `bash tests/hooks/blast-radius-check.test.sh` | 0 | 17 passed; representative non-blocking hook | SC-2 |

Full suite, cited not tabled: `bash scripts/run-tests.sh` printed `ALL GREEN` and exited 0 —
677 shell assertions plus 582 pytest cases (14.47s for the python half). It is deliberately not a
row: at ~3.5 minutes it would TIMEOUT the strict gate's 60s per-command cap, and CI's `tests` job
already runs it on ubuntu and macos.

One-time discriminating observation, not re-runnable as a row: the SC-3 suite was also executed
against the **pre-fix** hooks (`git show HEAD:hooks/<h>.sh` into a temp tree). It reported
**5 FAILED, 6 passed**, including `commit-quality-gate` printing `Secrets scan... PASSED` and
`Escalations... PASSED` while resolved to the foreign repo. That is what makes SC-3 proof rather
than a suite that passes vacuously. It cannot be a Verify row because the pre-fix tree no longer
exists after the commit.

### Not auto-verified

- **The fix is only proven on macOS, in one runtime.** Every result here comes from this laptop and
  one Claude Code CLI build. `CLAUDE_PROJECT_DIR` was observed set for `PreToolUse`/Bash during the
  spike; I did **not** confirm it is set for every hook event this repo registers (PostToolUse,
  UserPromptSubmit, SessionStart/End). Reached **truth** tier for PreToolUse/Bash only; **unknown**
  for the others. The git-from-CWD fallback covers them if the variable is absent, but that is an
  argument, not an observation. CI runs ubuntu + macos, which will cover the OS half.
- **No plugin-packaged installation was tested end to end.** The spike proved the *failure* mode
  with a throwaway plugin; the *fixed* hooks were then verified in-tree and under
  `tests/hooks/repo-root-resolution.test.sh`, which simulates a foreign host repo rather than being
  a real plugin install. Reached **truth** tier for the simulated case, **not observed** for a real
  marketplace install.
- **The ratchet is traceability tier, deliberately.** `scripts/check-hook-root-source.sh`
  `Verifies:` no non-comment line in `hooks/` resolves a root from `$SCRIPT_DIR`.
  `Does not verify:` that the replacement resolution is correct, or that a hook uses `REPO_DIR` at
  all. A hook could pass the ratchet and still resolve wrongly by some other means; only
  `tests/hooks/repo-root-resolution.test.sh` re-runs behaviour.
- **`render-plan-on-write.sh` has no case in the new regression test.** The other six changed hooks
  each have one. Its own suite (9 cases) passes and the hook was additionally observed working in
  the live runtime during this task — it auto-rendered `PLAN.html` on each edit to `PLAN.md`.
  Reached **traceability** plus one incidental live observation; the foreign-host scenario is
  inferred for this hook, not measured.

### Rollback

- `git revert <sha>` — single branch, no migration, no external or persistent state. The change is
  confined to in-repo shell; reverting restores the previous resolution order exactly.

### Harness-Delta

- **fix-direct:** SC-1 was first written as a bare `grep` for the banned pattern. That grep matched
  the *explanatory comments* this change added, so the criterion reported failure on a correct tree.
  A success criterion that greps for a string must exclude comment lines, or it measures prose.
  Fixed in `PLAN.md` §3 and encoded in `scripts/check-hook-root-source.sh`.
- **backlog (-> compound):** the deeper pattern is worth a `docs/solutions/` entry — *a hook must
  never infer the thing it audits from its own install location*. This defect was invisible for the
  life of the repo because the deployed layout made the wrong inference produce the right answer.
