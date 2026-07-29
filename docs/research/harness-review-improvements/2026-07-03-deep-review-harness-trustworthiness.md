# Deep Review — Harness Trustworthiness Audit

- **Date:** 2026-07-03
- **Scope:** hooks/ + settings.json · scripts/ + CI · skills/ + agents/ · rules/ + templates/ + specs/ + docs governance
- **Method:** 4 review agents in parallel; every finding verified by reading the code or running it for real (no speculation). The bypasses in the Critical section were demonstrated live.
- **Status:** findings only — nothing fixed yet.

---

## Overall assessment

The repo's foundation is distinctly better than average: the merge logic in deploy/install has backups and real tests, CI runs exactly what the docs say it does, the review-chain benchmark has real results, and the Evidence Tiers table is honest. **But the "enforcement" layer — the thing that creates trust — is leaking in precisely the places that matter most**: every commit gate can be bypassed with a command prefix, the knowledge-base hook has died silently at its deployed location, and every mechanism that rests on prose alone (trust ledger, STATE.md, agent-memory decay) has rotted.

The repo proves its own thesis: *whatever is not mechanized will decay*.

---

## 🔴 Critical — fix immediately

### 1. Every commit gate can be bypassed with a command prefix

- **Location:** `hooks/commit-quality-gate.sh:11`, `hooks/risk-corroboration.sh:26`, `hooks/branch-guard.sh:14`
- All 3 gates filter with `grep -qE '^git commit'` (anchored at line start). **Demonstrated live:** `cd /tmp && git commit -m x` and `git -C . commit` pass all 3 gates with exit 0 and not a single line of output.
- Bypass forms: `cd x && git commit` · `git -C dir commit` · `git -c k=v commit` · `command git commit` · `echo done; git commit`.
- Secrets scan, debug-artifact check, pytest gate, lane corroboration — all of them are one `&&` away from silence.
- **On top of that:** the `"if": "Bash(git *)"` field in settings.json **does not exist in the Claude Code hooks schema** (the schema only has matcher/type/command/timeout) — it is silently ignored, so all 4 scripts run on *every* Bash call and the entire gating story depends on that very same broken self-filter. `statusMessage` is likewise not a valid field.
- `check-untracked-py.sh:9` uses a substring match, so it survives `cd x &&` but still loses to `git -C dir commit`.

### 2. `session-knowledge.sh` is dead at its deployed location

- **Location:** `hooks/session-knowledge.sh:17-19`
- The hook resolves the knowledge base via `$HOOK_DIR/../docs/solutions`, but the registered copy runs from `.claude/hooks/` → it looks for `.claude/docs/solutions` (which does not exist).
- **Tried it:** `bash .claude/hooks/session-knowledge.sh` emits nothing; the top-level copy emits all 5 INDEX entries.
- `exec 2>/dev/null` guarantees nobody notices — every session starts up **without** the knowledge base that CLAUDE.md claims is loaded. This is exactly the `not_observed != absent` failure the repo's own rules warn about.
- Every other hook avoids this bug with `git -C "$SCRIPT_DIR" rev-parse --show-toplevel`; this one alone does not.

---

## 🟠 High — distorts the safety model

### 3. `executing-plans` has no review gate at all

- The README (`skills/README.md`) and CLAUDE.md say executing-plans is "same as subagent-driven-development" (two-stage review per task + correctness-review + intent-review).
- In reality `skills/executing-plans/SKILL.md`: Step 2 runs the task, Step 3 hands off straight to finishing-a-development-branch. No spec review, no quality review, no correctness, no intent.
- **Consequence:** any plan that runs through the "parallel session" path ships entirely unreviewed while the harness believes it was reviewed.

### 4. The hard-gate list diverges across 4 sources

- `skills/feature-intake/SKILL.md` (Step 3, ~lines 78–86): 6 gates — **missing** *public contract*, *removing existing functionality*, *session/transaction scope*.
- `.claude/rules/orchestration.md` (Escalation): 8 gates, includes public contract.
- `rules/auto-correct-scope.md` Rule 4: adds removing-functionality + session/transaction scope.
- `hooks/risk-corroboration.sh:80`: mechanically **blocks** on the `public-contract` category (route-decorator regex).
- **Consequence:** intake legitimately classifies a route change as lane `normal` → the commit hook blocks with exit 2 → classifier and corroborator fight each other by design; exactly the kind of under-classification the trust ledger exists to catch, except it is self-inflicted by the docs.
- **Same class:** `risk-corroboration.sh:73` treats any change to `package.json`/`pyproject.toml`/`requirements*.txt` as the `external-provider` hard gate, in direct contradiction with Rule 3 (which permits auto-adding a dependency in any lane) → every normal-lane dependency bump is blocked unless re-classified as high-risk.

### 5. Lane corroboration is self-referential and fail-open

- **Location:** `hooks/risk-corroboration.sh:103,109,112`
- The parser requires a line beginning exactly with `Lane:`; this very repo has `specs/correctness-review-upgrade/SUMMARY.md:3` using `**Lane:** normal` → grep misses → no lane found → warn-and-allow (fail-open) even when the diff touches a hard gate.
- The fallback `ls -t specs/*/SUMMARY.md | head -1` picks the *most recently modified* SUMMARY → the lane being corroborated may belong to a different task.
- The block message only tells the agent how to unblock itself (write `Lane: high-risk` on its own; no human in the loop) → the hook enforces **consistency**, not **safety**.

### 6. The CI strict gate proves "a command ran", not "evidence"

- **Location:** `scripts/ci-strict-gate.sh:38-62`
- A PR touching a hard-gate path (`hooks/`, `settings.json`, `templates/`) can pass by shipping a new SUMMARY with `Lane: high-risk` plus the row `| x | \`true\` | 0 | |` — `verify_summary --check` runs `true`, exits 0, gate OK.
- A rollback left as the unedited template (`- \`git revert <sha>\``) is accepted by `check_lane_evidence.py:110-127` (**verified empirically** — zero errors): the sole requirement of the high-risk lane can be satisfied by *changing nothing*.
- **Side effect:** CI executes arbitrary shell taken from a SUMMARY.md written by the PR author (`verify_summary.py:112`, `shell=True`).

### 7. `test_verify_summary.py` is never run in CI

- **Location:** `scripts/run-tests.sh:33` — `PYTESTS` omits this file.
- **Verified:** the suite reports 102 passed; running the skipped file by hand adds 19 more passing tests. The parser the CI strict gate depends on is the one script with no coverage in CI. One-line fix.

### 8. `finishing-a-development-branch` is written on a false premise

- 4 places (lines ~77, 90, 115, 141) say "`specs/` is gitignored" — contradicting CLAUDE.md, plan-format.md, writing-plans, visual-planner (specs are tracked, and the `shipped` transition must be committed). An agent following this skill will leave `status: shipped` uncommitted → exactly the cross-machine drift the skill warns about.
- Step 1b hardcodes `cd apps/api && python -m pytest` (a different repo — the real suite is `scripts/run-tests.sh`); Step 3 hardcodes a remote named `github` (breaks on every clone that uses `origin`).

### 9. `agents/reviewer.md` — the "structurally read-only" guarantee no longer holds

- The frontmatter declares `tools: Glob, Grep, Read, Bash`, but the actual registry of the current session resolves reviewer with `Write, Edit` as well (almost certainly injected by `memory: project`).
- The core claim "review independence is enforced by the harness, not by instruction" is currently false — the reviewer can edit files.

### 10. The branch-isolation "hard block" covers only 2 write channels

- **Location:** `.claude/settings.json` matcher `Write|Edit`.
- Every Bash write (`echo >`, `tee`, `sed -i`, `python -c`, `patch`, heredoc) and `NotebookEdit` passes freely; the Bash hooks only inspect git commands.
- **Break-glass is unreachable mid-session:** `BRANCH_ISOLATION_REASON`/`PROTECTED_PATH_REASON` are read from the environment of the Claude Code process at launch — the model cannot set an env var for a single tool call. The only path is writing into `settings.json` `"env"` → which turns it into a **permanent** bypass with one stale log line. `RISK_CORROBORATION_STRICT`/`BLAST_RADIUS_STRICT` default off = deliberately fail-open, under the same launch-time constraint.

### 11. Per-task quality review dispatches an agent that does not exist

- `skills/subagent-driven-development/code-quality-reviewer-prompt.md` dispatches `Task tool (superpowers:code-reviewer)` with the template `requesting-code-review/code-reviewer.md` — neither the agent type nor the template exists in this environment (the README tiers it as documented-only).
- A mandatory gate ("Never skip reviews") with no fallback → the controller either errors out or improvises a passing review on its own.

---

## 🟡 Medium — decay & lifecycle

| # | Finding | Location / evidence |
|---|---|---|
| 12 | **Trust ledger dead for 3 weeks** — no mechanism appends to it; last row 2026-06-14 (still reading "done (uncommitted)"), PRs #26–#30 shipped 06-15→06-19 with 0 rows. A file created to "calibrate autonomy" goes stale the moment attention lapses | `docs/harness-experimental/trust-metrics.md` |
| 13 | **STATE.md has never worked correctly** — Active Spec is always `(none)` despite 19 spec dirs; `user_turns` is always 0 because `grep -c '"role": "user"'` does not match the transcript format; the Session End Log appends without bound (32 entries / 8 days, 232 of 258 lines). An agent resuming from STATE.md learns nothing more than `git log -1` would tell it | `specs/STATE.md`, `hooks/state-breadcrumb.sh:98-105` |
| 14 | **deploy-harness only adds, never removes** — a hook deleted/renamed upstream stays behind in the consumer's `.claude/`, and the old registration is classified "foreign" so it is **kept through the merge** → the dead hook keeps running, on every re-sync | `scripts/deploy-harness.sh:65-107` |
| 15 | **`python -m pytest` hardcoded** — stock macOS has no `python` binary → exit 127 → `exit 2` → blocks *every* commit in an adopting repo that has staged `app/` files (fail-closed for the wrong reason; `auto-test-on-change.sh:78-80` does the python3 fallback correctly) | `hooks/commit-quality-gate.sh:153` |
| 16 | **Command-injection primitive** — `eval "$CMD"` with `$FILE_PATH` interpolated; a path like `test_"; rm -rf x; ".py` executes arbitrary shell. Dormant today, but it is a hook the docs advise others to wire up | `hooks/auto-test-on-change.sh:107` |
| 17 | **blast-radius falls back to the wrong plan** — with no plan at `status: active` it picks the *newest* PLAN.md regardless of status → an already-shipped plan keeps producing scope-creep warnings (and false blocks under STRICT=1); line 34's unquoted `$(ls -t …)` breaks on paths with spaces | `hooks/blast-radius-check.sh:34,37` |
| 18 | **Placeholder rules diverge between the 2 checkers** — `verify_summary.py:33` has a duplicated em-dash in the set (size 3, one of them almost certainly a mistyped ASCII `-`); a row command of `-` is parsed as real and **gets executed**. The ci-strict-gate comment claims the placeholder rules "stay in one place" — untrue | `scripts/verify_summary.py:33` vs `check_lane_evidence.py:34` |
| 19 | **verify_summary semantics traps** — (a) a row that honestly declares exit ≠ 0 still FAILs even when `claimed == actual` (negative proof is inexpressible); (b) write mode stamps `Verified:` even when checks FAILED; (c) `_rewrite_table` maps by check name → duplicate names collide | `scripts/verify_summary.py:292,307-309,145` |
| 20 | **render_plan self-check passes on truncated output** — an unclosed ``` fence makes `md_to_html` swallow everything to EOF, the section disappears from the render, yet the self-check (non-empty, no `{{X}}`, slug, wave count) still passes | `skills/visual-planner/render_plan.py:262-277,1269-1290` |
| 21 | **Hygiene contradicts itself** — `settings copy.json` (a stale pre-branch-isolation-guard copy of the highest-blast-radius file), `.claude copy/` (~20 drifted files, hidden via `.git/info/exclude` — invisible to teammates), 3 `.harness-backup-*` dirs (06-09→06-11), REQ.md / PR_TEMPLATE.md / docs/research untracked for weeks | git status, repo root |
| 22 | **The agent-memory decay protocol is dead prose** — 0 entries after ~1 month; no script parses `confirmed:/review-by:` or downgrades confidence; it depends entirely on the agent remembering, and no agent has | `agent-memory/` |
| 23 | **feature-intake cites derived paths** — it cites `.claude/rules/...` and `.claude/hooks/*` (a gitignored tree, regenerated by deploy-harness) as the high-blast list, while CLAUDE.md and the corroboration hook key on top-level `hooks/`/`settings.json` → an agent editing the source tree gets contradictory path references | `skills/feature-intake/SKILL.md` |

## 🟢 Low

- `check_lane_evidence.py:73` — lane matched as a substring: `Lane: not-normal` resolves to `normal`; `Reason: —`/`Reason: TBD` pass as "filled".
- `render_plan.py:229` — `[x](javascript:...)` renders to `<a href="javascript:...">` living inside PLAN.html (quote breakout is blocked by escaping, the scheme is not).
- `render_plan.py:1257-1259` — sequential `template.replace`: prose containing a literal `{{TASKS}}` gets the whole tasks block substituted in; a different `{{UPPER}}` in prose causes a false self-check failure.
- `run-tests.sh:12` — unquoted glob under `set -u`: if `tests/scripts/` is empty the literal pattern is passed to `bash -n` → false failure.
- `check-untracked-py.sh:10` — `grep -v '/\.claude/'` never matches a repo-relative path (no leading slash) → the exclusion is dead; `git ls-files` runs in the session cwd, not the repo the commit targets.
- `create-pr` defaults the base to `dev` while `finishing-a-development-branch` defaults to `main` (this repo's main is `main`) → wrong diff in the PR body.
- `using-git-worktrees` claims "Called by: brainstorming (Phase 4) — REQUIRED", but brainstorming forbids it ("The ONLY skills you invoke after brainstorming are xia2 → writing-plans", line 72) — one of the two is wrong.
- Leftover copy-pasted Vietnamese sentences in `subagent-driven-development/SKILL.md:192` and `correctness-review/SKILL.md:22` — load-bearing rationale that is unreadable to an agent/user not configured for Vietnamese.
- `executing-plans` Step 3 describes finishing as "present options, execute choice" — stale (that skill now unconditionally pushes + opens a PR).
- "Never merges" is prose-only — no hook gates `gh pr merge`/`git merge` (in contrast to branch-isolation, which is hook-enforced).
- `subagent-driven-development` (433 lines, 2 DOT digraphs) and `compound` (469 lines) push instruction-following risk; the digraph is the only place the full control flow is specified.
- docs/solutions: all 5 entries have `confirmed_at` ≥ 30 days old as of 2026-07-03 → by the repo's own rule, every one of them is "potentially stale".
- state-breadcrumb: concurrent SessionEnd runs can interleave the multi-`printf` block; idempotency is only per session_id.

---

## ✅ What is genuinely good (verified)

- `install-harness.sh` / `deploy-harness.sh`: back up before merging, do not clobber on invalid JSON, do not stage at the target root, preserve foreign keys/hooks — with real tests (`tests/scripts/settings-merge.test.sh`).
- `bash scripts/run-tests.sh` → **ALL GREEN** (102 passed, 1 skipped, plus the hook/script suites). `.github/workflows/harness-ci.yml` genuinely runs run-tests on ubuntu + macos and ci-strict-gate on PRs with a correct base-ref fetch.
- Registration audit: the 11 hooks marked "wired ✅" in CLAUDE.md match `.claude/settings.json` exactly (event type + matcher); the 2 dormant ones are indeed unregistered.
- Templates match `check_lane_evidence.py` field by field (Lane/Confidence/Reason, Verify table header, Rollback) — no drift.
- Benchmark `benchmarks/review-chain/`: 5 real fixtures, 2 real result files (06-12 baseline; 06-14 reviewer-agent: 5/5 caught, 0 FP, ~354k tokens), exemplary claim discipline.
- The Evidence Tiers table is honest: it self-declares documented-only for every external skill/MCP; the single manually-verified claim (commit `a2a4349`) resolves to a real commit.
- The Python checker tests are real tests (tmp-file round-trip, exit codes, timeouts), not tautologies; the checkers correctly reject a raw template header and handle CRLF + bold headers.
- Spine routing (feature-intake → sdd → correctness-review → intent-review, the "three oracle" design, `subagent_type: reviewer` dispatch, residual gates) is specified concretely and executably.
- `docs/solutions/INDEX.md` (5 entries) matches the 5 real docs exactly.

---

## Recommended priorities (execution order)

1. **Fix command matching in the 3 commit hooks** — tokenize/normalize the command (catch `git … commit` in any segment after `&&`/`;`/`|`, accept `-C`/`-c`/`command`), and drop the bogus `"if"` field from settings.json. The biggest hole.
2. **Fix root resolution in `session-knowledge.sh`** using the `git rev-parse --show-toplevel` pattern its sibling hooks use; drop `exec 2>/dev/null` so errors become visible.
3. **Consolidate the hard-gate list into 1 machine-readable source** (YAML/JSON read by feature-intake, Rule 4, orchestration.md, and risk-corroboration.sh alike). This also resolves the dependency-bump conflict (Rule 3 vs hook line 73).
4. **Bring the review chain into `executing-plans`** — or fix the docs to stop claiming parity; fix the false premise + hardcoding in `finishing-a-development-branch`; fix or add a fallback for the nonexistent quality-reviewer dispatch; unify the base branch between create-pr and finishing.
5. **Tighten evidence checks:** a verify command must reference a file in the diff or sit on an allowlist (ban `true`); the rollback must differ from the template; add `test_verify_summary.py` to `run-tests.sh:33` (1 line); run verify commands in a sandbox instead of `shell=True` on CI; unify the placeholder sets into one module.
6. **Mechanize what is currently prose:** a hook that appends a trust-ledger row at PR merge; a drift check of `hooks/` vs `.claude/hooks/` in CI; teach deploy-harness to un-deploy (manifest-based); fix or delete the `user_turns` metric; rotation for the Session End Log.
7. **Extend branch-isolation coverage** to Bash writes + NotebookEdit; redesign break-glass so it is usable mid-session (e.g. a file-based flag with a TTL instead of an env var).
8. **Clean the working tree:** delete `settings copy.json`, `.claude copy/`, and the 3 backup dirs; commit or delete REQ.md / PR_TEMPLATE.md / docs/research.

> Lane note: groups 1, 2, and 7 touch `hooks/*` + `settings.json` = high-blast under the repo's own Rule 4 → run them in the **high-risk** lane with a full PLAN + Rollback.
