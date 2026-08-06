# hook-surface-slim — Research brief

Date: 2026-08-06 (initial) · **Re-review: 2026-08-06 on branch `simplify` @ `30dc501`**  
Depth: Deep (high-risk intake; prior reviews + live latency bench ×2)

## 0. Re-review delta (`simplify` HEAD)

Branch tip includes PR merges through superpowers-6 review pipeline. **Hook wiring inventory is unchanged** (11 wired + 1 dormant). What *did* land on this branch that affects friction:

| Shipped on `simplify` | Effect on “too many hooks / stuck” |
|---|---|
| `simplify-gate-surface` — mode-as-data; `workflow-engine` + `weakening-validation` → **warn** | Fewer false commit blocks in **this** meta-repo only |
| `fix-hooks-gate-lane-divergence` — `hooks/lib/lane.sh`; scope-gate dedup; blast uses shared active-plan | Correctness + less nudge spam; **not** fewer process spawns |
| `slim-skill-surface` install fix — untracked `.claude/**/*.py` no longer blocks fresh consumers | Fixed one real consumer hard-stuck (commit deny after install) |
| SC coverage via commit-quality `--plan-dir` | **Stricter** commit gate when SUMMARY+PLAN staged |
| risk-corroboration diff-size **warn** (gh-159) | Extra advisory noise on large tiny/normal diffs |
| session-knowledge + active runs | Slightly heavier SessionStart |
| **Not hooks:** `require-claude-simplify-gate` + Superpowers-6 task-review pipeline | New **ceremony** stuck (finish/SDD/receipts) — feels like “gates” but is skills/scripts, not PreToolUse |

**Still true / still open (re-confirmed on this HEAD):**

1. `settings.json` still runs **4 Bash PreToolUse** on every Bash + **3 PostToolUse** on every Edit.
2. Deploy still **does not ship** root `harness-manifest.json` → consumer risk gate still **block-all categories** (comment still in `risk-corroboration.sh:25`).
3. `auto-test-on-change.sh` still dormant; commit-quality Checks 2/2.5/3 still `app/**`-only dead weight here.
4. `blast-radius-check.sh` still ~**127 ms**/edit with **0** active plans (paid `ls -t specs/*/PLAN.md` scan).

### Re-bench on `simplify` (2026-08-06)

| Path | Cost now | Prior bench |
|---|---|---|
| Non-commit Bash ×4 | **~62 ms** | ~118 ms |
| `git commit` ×4 | **~264 ms** | ~315 ms |
| Write\|Edit chain | **~184 ms** (blast ~127 ms) | ~245 ms |
| scope-gate / session-knowledge | ~138 / ~123 ms | ~155 / ~150 ms |
| Light session tax (20e/40b/15p) | **~8 s** | ~12 s |
| Heavy (80/120/40) | **~28 s** | ~40 s |

Faster machine variance likely; **structure unchanged** — biggest taxes remain multi-spawn Bash + blast scan + per-prompt scope-gate.

### Revised “stuck” split on `simplify`

| Symptom | Primary cause now | Hooks? |
|---|---|---|
| Slow every tool call | 4+3 process spawns always-on | **yes** |
| Cannot commit after fresh install | **Fixed** (gitignore + untracked-py anchor) | was hooks |
| Commit blocked under-classifying hard gates | risk-corroboration (by design) | yes |
| Consumer still stricter than meta-repo | missing deployed manifest → all categories block | **yes** |
| Feature work feels endless reviews | simplify-stage + task-review + correctness/intent receipts | **no** (skills) |
| Must branch before edit | branch-isolation-guard | yes (keep) |

**Implication:** cutting hooks alone improves perf; consumer parity needs Package B; the new “simplify branch heaviness” is mostly **review ceremony**, not hook count.

### Recommendation unchanged (default still **A+B**)

Package A (dispatcher + blast fast-path + dormant cleanup) still highest hook ROI.  
Package B (consumer manifest/modes) still highest “stuck in other repo” ROI — install-py fix did **not** close risk fail-closed.  
Optionally add Package E later: lane-scale simplify/task-review so tiny/normal don’t pay full Superpowers-6 stack (out of hooks scope).

## 1. Inventory (source of truth: `settings.json` + `harness-manifest.json`)

| Hook | Event | Matcher | Decision | Wired |
|---|---|---|---|---|
| `check-untracked-py.sh` | PreToolUse | Bash | **block** commit/push if untracked `.py` | yes |
| `commit-quality-gate.sh` | PreToolUse | Bash | **block** commit (secrets, escalations, lane evidence, app debug/tests) | yes |
| `risk-corroboration.sh` | PreToolUse | Bash | **block/warn** commit if Lane under-classifies hard gates | yes |
| `branch-guard.sh` | PreToolUse | Bash | **warn** commit on main/master | yes |
| `branch-isolation-guard.sh` | PreToolUse | Write\|Edit | **deny** code edits on shared branch | yes |
| `ruff-on-edit.sh` | PostToolUse | Write\|Edit | auto-fix `.py`, never blocks | yes |
| `blast-radius-check.sh` | PostToolUse | Write\|Edit | warn OOS vs active PLAN (strict opt-in) | yes |
| `render-plan-on-write.sh` | PostToolUse | Write\|Edit | render PLAN.html on PLAN.md only | yes |
| `scope-gate.sh` | UserPromptSubmit | * | nudge intake if impl-intent w/o plan | yes |
| `session-knowledge.sh` | SessionStart | * | inject KB + active runs | yes |
| `state-breadcrumb.sh` | SessionEnd | * | append STATE.md | yes |
| `auto-test-on-change.sh` | — | — | dormant | **no** |

**Already removed:** `protected-path-guard.sh` (PR #133).  
**Already loosened:** `workflow-engine` + `weakening-validation` → warn (2026-07-23 / simplify-gate-surface).  
**Already fixed:** lane resolution unified in `hooks/lib/lane.sh` (F1 from 2026-07-29 review).

## 2. Measured wall-clock (this machine, 2026-08-06)

| Path | Cost |
|---|---|
| Every non-commit Bash → 4 PreToolUse hooks | **~118 ms** (all early-exit after jq + matcher) |
| Every `git commit` → same 4 hooks full | **~315 ms** (commit-quality ~136 ms, risk ~74 ms) |
| Every Write\|Edit → isolation + ruff + blast + render | **~245 ms** (blast-radius alone ~132 ms even with 0 active plans) |
| Every UserPromptSubmit → scope-gate | **~155 ms** |
| SessionStart → session-knowledge | **~150 ms** |
| Light feature session (20 edits / 40 bash / 15 prompts) | **~12 s** pure hook tax |
| Heavy session (80 / 120 / 40) | **~40 s** |

Subprocess counts on commit path: commit-quality ~21 git/python lines under `bash -x`; risk ~19.

**Verdict on “perf”:** not multi-second per call, but **multiplied by every tool call**. Biggest always-on taxes: (1) 4 Bash PreToolUse spawns on *every* Bash including `ls`, (2) blast-radius on *every* edit scanning all PLAN.md files, (3) scope-gate on *every* prompt.

## 3. What actually causes “stuck” (vs slow)

### A. This meta-repo (harness-skills)

| Friction | Mechanism | Block? |
|---|---|---|
| Must branch before any non-`specs/` edit | `branch-isolation-guard` | **yes** deny |
| Commit needs SUMMARY lane evidence when specs staged | commit-quality Check 1.6 | **yes** |
| Under-declared Lane vs high-blast/hooks paths | risk-corroboration | **yes** |
| Combined `git add && git commit` | check-untracked-py / matcher | **yes** (documented gotcha) |
| Pending ESCALATIONS | commit-quality 1.5 | **yes** |
| scope-gate / blast-radius / branch-guard / session KB | advisory | no |
| commit-quality app/ debug+pytest (Checks 2/2.5/3) | only `app/**/*.py` | **dead here** (no `app/`) |

Historical review (2026-07-29): **zero** recorded Lane-gate commit rejections in this repo after loosening; break-glass log still empty.

### B. Consumer repo after install (primary “stuck elsewhere” hypothesis)

`risk-corroboration.sh` documents:

> Consumer repos have no manifest at their root, so every category blocks there.

Deploy copies hooks + derived `settings.json` but **does not ship `harness-manifest.json`** into the consumer root. Effects:

1. All 9 detectable categories fall back to **block** (no warn-mode for workflow-engine / weakening-validation).
2. Editing skills/rules/agents in a consumer (or anything matching keyword scanners) + Lane below high-risk → **commit blocked**.
3. Meta-repo-tuned loosenings **do not transfer**.

This matches the user’s report better than “too many hooks” alone.

Secondary consumer frictions:

- Same write-time branch isolation (correct, but surprising if they work on `main`).
- `check-untracked-py` on any untracked `.py` (correct for CI, noisy in greenfield).
- `session-knowledge` / `scope-gate` inject tokens every session/prompt (slow-ish, not stuck).
- `commit-quality` Check 3 runs pytest when `app/` exists — real cost in app repos (good), dead in harness.

## 4. Prior art (do not re-litigate blindly)

| Review | Conclusion still valid? |
|---|---|
| over-engineering 2026-07-16 | Yes for dead app/ paths, merge commit gates, dormant auto-test; branch-guard delete was **later refuted** |
| hooks-gate-review 2026-07-29 | Yes: not over-blocking in aggregate; keep branch-guard; fix F1 (**done** via lane.sh); scope-gate dedup (**done**) |
| simplify-gate-surface | Yes: mode-as-data + 2 warn categories shipped |

## 5. Cut / slim recommendations (ranked ROI)

### Package A — low risk, high always-on perf (recommended first)

| Change | Why | Risk |
|---|---|---|
| **Merge 4 Bash PreToolUse into 1 dispatcher** (`hooks/pre-bash.sh` → source untracked / quality / risk / branch-guard) | 4 process spawns → 1 on every Bash; keep all checks | medium (wiring + tests) |
| **Fast-path matcher once** in dispatcher before heavy work | avoid 4× jq + 4× source lib | low |
| **blast-radius: cache active-plan path or skip when no `specs/*/PLAN.md` with active** | still ~132 ms scanning; 0 active plans today still paid ls/grep cost | low |
| **Delete or keep-dormant `auto-test-on-change.sh`** | 120 LOC never wired; or wire opt-in only | low if delete |
| **Strip commit-quality Checks 2/2.5/3 from default hook** → stack template / `REQUIRE_APP_GATES=1` | ~110 lines never fire in harness; still useful in app consumers as opt-in | medium (consumer behavior change if they rely on default pytest-at-commit) |

Expected: non-commit Bash ~118 ms → ~30–40 ms; edit path −50–100 ms if blast fast-path improved.

### Package B — consumer “unstuck” (highest product ROI for install-elsewhere)

| Change | Why | Risk |
|---|---|---|
| **Deploy a consumer `harness-manifest.json` (or embed modes in hook)** with same warn/block modes as meta-repo | stops fail-closed block-all | high-blast / contract |
| **Or: missing manifest → warn-not-block for non-security categories** (keep auth/authz/secrets/high-blast block) | safer default for greenfield | needs design |
| **Document consumer break-glass** (`RISK_WARN_CATEGORIES`, settings.local env) in install README | already exists but invisible | docs only |
| **Optional “lite profile” settings** — commit gates only, no scope-gate / session-knowledge / blast-radius | for app repos that want safety without ceremony | product fork |

### Package C — remove / demote (selective; evidence-backed)

| Hook | Recommendation | Do not |
|---|---|---|
| `branch-guard.sh` | **KEEP** (only nudge for specs-only commits on main) | delete (refuted 2026-07-29) |
| `branch-isolation-guard.sh` | **KEEP** (structural branch rule) | loosen without alternate enforcement |
| `scope-gate.sh` | **KEEP** (dedup already); optional disable in lite profile | delete — cheap relative to token cost of bad routing |
| `blast-radius-check.sh` | keep warn-default; speed up; optional unwire in lite | make strict by default |
| `session-knowledge.sh` | trim payload or lazy-load; optional unwire in lite | block session |
| `state-breadcrumb.sh` | keep or make opt-in if STATE.md unused in consumers | — |
| `render-plan-on-write.sh` | keep (only PLAN.md path) | — |
| `ruff-on-edit.sh` | keep if Python project; no-op else | — |
| risk 7 block categories | **KEEP** until new FP metrics | loosen on vibes |
| `workflow-engine` / `weakening-validation` | already warn | re-tighten |

### Package D — out of hooks but same “stuck” feeling

Ceremony (skills/intake/plan/reviews) is larger than hook wall-clock. Slimming hooks alone will not make high-risk harness features feel “tiny.” Separate track: lane-scaled review chain (already noted in over-engineering review §5).

## 6. What not to remove (load-bearing)

- Secrets scan + untracked `.py` at commit  
- `branch-isolation-guard` write-time deny  
- risk-corroboration for true hard gates (auth, data-loss, high-blast, …)  
- lane evidence Check 1.6 when SUMMARY is staged  
- ESCALATIONS pending deny  

## 7. Suggested decision for human

Pick one:

1. **A only** — perf dispatcher + blast fast-path + delete dormant auto-test (+ optional strip app checks)  
2. **A + B** — also fix consumer manifest/modes (best answer to “stuck in other repo”)  
3. **Lite profile product** — two settings templates: `full` (current) vs `lite` (commit safety only)  
4. Research-only stop — no code

Default recommendation: **2 (A+B)** with design note on missing-manifest policy before coding.
