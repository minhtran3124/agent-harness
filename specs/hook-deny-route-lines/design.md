# hook-deny-route-lines — Design

Written 2026-10-14. Pins: repo 94682f9
Revised 2026-10-14. Pins: repo cc93f17 + uncommitted

## Goal

Every blocking path in the harness hooks tells the agent or person both **why** it blocked and
**what clears it** (play 10: "reason + route"), so nobody has to read hook source to find the way
forward. Message text only — no gate changes what it blocks.

## Current state

Blocking paths live in `hooks/commit-gate.sh` (exit 2 + stderr, except the untracked-`.py` JSON
deny) and `hooks/branch-isolation-guard.sh` (JSON `permissionDecision: deny`). `hooks/lib/`
(`git-command.sh`, `lane.sh`, `gate-modes.default.sh`, `normalize-tool-input.py`) has no deny path
of its own — searched with `grep -n -E "exit 2|deny|exit 1" hooks/lib/*`; a missing lib is blocked
by `commit-gate.sh` (G2, G3).

Inventory at 94682f9: 21 blocking paths (measured 2026-10-14 `grep -n -E "exit 2|permissionDecision|deny" hooks/*.sh hooks/lib/*` — 18 `exit 2` sites in `commit-gate.sh` plus 3 JSON denies):

**Already reason + route — 10 (measured 2026-10-14, the grep plus a read of each message) — unchanged:** untracked `.py` (`commit-gate.sh:116`), pending
escalation (`:217`), lane evidence (`:284`), untracked run-state (`:321/:333`), risk
corroboration below high-risk (`:498`), strict no-Lane (`:509`), bare `print()` (`:598`),
`### Verify` missing (`:613`), Verify re-run mismatch (`:627`), shared-branch edit
(`branch-isolation-guard.sh:176`).

**Missing or vague route — 11 (measured 2026-10-14, the grep plus a read of each message):**

| ID | Path | Today |
|---|---|---|
| G1 | `commit-gate.sh:57` unclassifiable Bash payload | "redeploy/update the harness normalizer" |
| G2 | `commit-gate.sh:70` git-command matcher lib missing | "redeploy harness" |
| G3 | `commit-gate.sh:136` lane lib missing | "redeploy harness" |
| G4 | `commit-gate.sh:147` project root undeterminable | reason only |
| G5 | `commit-gate.sh:152` `cd "$REPO_DIR" \|\| exit 2` | no message at all |
| G6 | `commit-gate.sh:186` potential secrets | "Run 'git diff --cached' to review" |
| G7 | `commit-gate.sh:194` `.env` staged | reason only |
| G8 | `commit-gate.sh:591` `breakpoint()`/pdb | reason only |
| G9 | `commit-gate.sh:690` targeted tests fail | "Fix test failures" |
| G10 | `commit-gate.sh:572` strict blast radius | "escalate, or add the files to the plan" |
| G11 | `branch-isolation-guard.sh:157` unclassifiable edit payload | "updating/redeploying the harness normalizer" |

## Approaches considered

- **A. Inline route line per gap (chosen).** Add a `Route:` line to each of the 11 messages in
  place; leave the 10 complete messages untouched. Smallest diff, follows existing style, stays
  inside "message text only".
- **B. Shared `hook_deny <reason> <route>` helper in `hooks/lib/`.** Uniform format, but G2/G3
  fire *because* a lib is missing, so they cannot depend on one; and it rewrites the 10 messages
  the intent says stay as they are.
- **C. A + a static lint that every `exit 2` has a `Route:` nearby.** Enforces future denies, but
  it matches spelling, not that the route is real (`ratchet-matches-spelling-not-property`), and
  is unrequested scope.

## Architecture

No new component. Each gap gains one `  Route: <action>` line (G11: appended to the JSON
`permissionDecisionReason` string after `\n`), on the channel the message already uses. Route
text — every command, variable and file named exists in the deployed harness today:

- **G1, G2, G3 (redeploy):** `Route: redeploy the harness from its source checkout:
  bash <harness>/scripts/install-harness.sh --source <harness> -d <project> --yes`. Without
  `--source` the installer clones `main` instead of using the checkout (`install-harness.sh`
  "resolve source"). G1 may also fire on a genuinely malformed payload, so its route adds "if the
  payload itself is malformed, re-issue the command". A consumer installed by the README `curl …
  | bash -s -- --yes` one-liner has no local checkout, so the route also names "or re-run the
  installer one-liner from the harness README". In the harness repo itself `settings.json` runs
  `hooks/` directly and the installer does not restore `hooks/lib/`, so the route adds "(in the
  harness repo itself: git restore hooks/lib/)".
- **G11 (unclassifiable edit on a shared branch):** this deny fires only on a shared branch, so the
  first route is the one that always clears it: `Route: cut a task branch (git checkout -b
  <type>/<slug>, or the using-git-worktrees skill) and re-apply the edit; if the normalizer is
  stale, redeploy with the G1 command; break glass with BRANCH_ISOLATION_REASON=<why>.`
- **G4 (project root):** `Route: run the commit from inside the project's git work tree, or set
  CLAUDE_PROJECT_DIR to the project root.`
- **G5 (`cd` fails):** new reason line `[COMMIT GATE] BLOCKED — cannot enter project root <dir>.`
  plus the G4 route.
- **G6 (secrets):** `Route: remove the value from the staged change (read it from an env var
  instead), then re-stage. There is no override — if you believe
  it is a false positive or a fake test value, stop and ask a human.` The scan's path exclusions
  (including `*.example`) are deliberately not named: naming them tells an agent where to move a
  flagged string.
- **G7 (`.env`):** `Route: unstage it (git restore --staged <file>), add it to .gitignore, and
  commit a .env.example instead. Untracking an already-tracked .env (git rm --cached) stages a
  deletion that this check also blocks — a human decides that commit.` (Revised in correctness
  review: the first wording offered `git rm --cached` as a route, but `git diff --cached
  --name-only` lists the staged deletion, so the check blocks it again.)
- **G8 (breakpoint/pdb):** `Route: remove the breakpoint()/pdb lines, re-stage, and commit again.`
- **G9 (tests):** `Route: reproduce with python -m pytest <files> -x -q, fix, re-stage.` with the
  real `$TEST_FILES` substituted.
- **G10 (blast radius):** `Route: if the paths belong to this work, add them to the task's Files
  in the active PLAN.md and re-stage; otherwise unstage them. If the scope change needs a human,
  escalate in specs/<slug>/ESCALATIONS.md — the commit stays blocked until the plan is updated.
  This block is on because BLAST_RADIUS_STRICT=1.` Only updating the plan (or unstaging) clears
  it; an escalation is how the decision to update it is made.

Exact wording may be tightened during implementation; the named command/variable/file per gap is
the contract.

## Error behavior

Unchanged for every path: same exit code (2 for stderr blocks; 0 + JSON deny for the JSON paths),
same deny decision, same profile and mode membership. G5 gains a message but stays exit 2.

## Tests

In the existing `tests/hooks/*.test.sh` files using `assert_rc_contains` (truth tier — the hook
is executed):

- Each of G1–G4 and G6–G11 already has a test asserting its reason (`commit-gate.test.sh`,
  `branch-isolation-guard.test.sh`, `repo-root-resolution.test.sh`); add an assertion on its route
  text.
- G5: new test — `CLAUDE_PROJECT_DIR` points at a directory that exists but cannot be entered
  (`chmod 000`), asserting exit 2 + reason + route. Skipped when running as root (root can enter
  it); the test restores `chmod 755` before temp-dir cleanup.
- G9's existing test runs only when `ensure_pyenv` succeeds (`commit-gate.test.sh`), so on a
  machine without the pytest env it is skipped, not passed; a skip is recorded as such, not as
  route coverage.
- None of the 10 complete messages has a route-text assertion today (measured 2026-10-14
  `grep -nF` of each route phrase in `tests/hooks/*.sh`). Each gains one: untracked `.py`
  ("git add"), escalation ("records the decision"), lane evidence ("See rules/auto-correct-scope.md"),
  run-state ("Stage them by name"), risk below high-risk ("Re-classify"), strict no-Lane
  ("Declare a Lane"), `print()` ("Use logger"), Verify missing ("Record the command"), Verify
  mismatch ("Fix the commands"), branch-isolation ("git checkout -b").
- `bash scripts/run-tests.sh` green.

## Success criteria

- Every one of the 21 (measured 2026-10-14) blocking paths has a test that asserts its route text — check: the hook test
  files.
- The 11 gap messages print a route naming an existing command, variable or file — check: the new
  assertions.
- No exit code or deny decision changes — check: existing `assert_rc*` assertions still pass in
  `bash scripts/run-tests.sh`.

## Non-goals

- Warn-only messages and PASS/skip notices.
- `scripts/ci-strict-gate.sh` and other CI scripts.
- Adding, removing, or loosening any gate; any new override variable.
- Relabelling the 10 complete messages to a uniform `Route:` prefix.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | The 21 paths listed are all the blocking paths in the three locations | provenance: Local, 2026-10-14, `grep -n -E "exit 2\|permissionDecision\|deny" hooks/*.sh hooks/lib/*` | xia2 re-sweep + per-path test SC | a missed path keeps no route; xia2 adds it to the gap list |
| A2 | `hooks/lib/` has no deny path of its own | provenance: Local, 2026-10-14, `grep -n -E "exit 2\|deny\|exit 1" hooks/lib/*` | xia2 re-sweep | add any found path as a new gap |
| A3 | Stderr of an exit-2 PreToolUse hook and the JSON `permissionDecisionReason` both reach the agent, so a route line there is seen | none yet: Inference, 2026-10-14, the existing complete messages rely on the same channels | accepted risk: same channel the 10 complete messages already use | the route is invisible on that runtime; out of scope (channel, not text) |
| A4 | A `chmod 000` directory makes `cd` fail for a non-root test runner on both ubuntu and macOS CI | none yet: Inference, 2026-10-14, POSIX permission semantics | G5 test SC | test G5 by another means or mark it Not auto-verified |
| A5 | `install-harness.sh --source <harness> -d <project> --yes` redeploys from the local checkout | provenance: Local, 2026-10-14, `scripts/install-harness.sh` "resolve source" block and `--help` | accepted risk: the source read is the evidence; route assertions prove only that the text is printed | swap in the correct installer invocation |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| Future deny paths will carry a route | No lint enforces it (approach C rejected); only the 21 current paths are tested |
| A route always clears the block | The route names the action; whether the fix is correct (e.g. a real secret removed) is the actor's judgment |
| Deny text is identical across Claude and Codex | Text is identical in the hook; how each runtime renders it is not tested here |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Approach A: inline `Route:` line per gap, no shared helper | Lib-missing paths stay self-contained; 21 messages keep their own wording | settled |
| D2 | The 10 complete messages are not edited; only their tests gain a route assertion | No uniform `Route:` marker across all 21; tests assert each message's own route text | superseded by DC1 |
| D3 | Secrets scan gets no override; the route says remove the value or ask a human, and deliberately does not name the scan's path exclusions | Honors "no new override or break-glass variable" | settled |
| D4 | No lint ratchet for future denies | Future denies can regress; listed under What we do not claim | settled |
| D5 | The 10 complete messages are not edited, except the untracked-`.py` deny (`commit-gate.sh:117`), whose route gains "in a separate Bash call, then commit"; every test asserts its message's own route text | One complete message is edited; the other 9 stay byte-identical | settled |

## Decision changes

- DC1 — 2026-10-14 — reopens D2 — evidence: `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md` (the untracked-`.py` deny scans the whole command string, so its route "Run: git add <files>" followed in the same Bash call as `git commit` is denied again; found in xia2, `research-brief.md` Q1; user approved 2026-10-14) — new decision: D5

