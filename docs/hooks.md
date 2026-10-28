# Hooks and gates (legacy until #349 removes the hooks)

This page holds the detailed hook and gate description that used to live in `CLAUDE.md`. Harness v5
(epic #338) removes the commit gate and its companions in #349. Until then the text below stays
true. The short hook table is in `CLAUDE.md`; `scripts/lint-doc-truth.sh` keeps that table in
step with `hooks/` and `settings.json`.

## Hook details

Register hooks in `settings.json` under the matching trigger key. In the `CLAUDE.md` table, wired
(✅) means registered in `settings.json` and firing; dormant (⬜) means present on disk but not
registered.

### `commit-gate.sh` (PreToolUse, Bash)

The single `git commit`/`push` gate, one process per Bash call. Normalizes Claude shell input; non-git Bash exits 0 at once; unknown/partial shell input fails closed. `git push` runs only the untracked-`.py` check (strict). `git commit` runs, in order: untracked-`.py` deny (strict — it runs first and a deny ends the hook); secrets scan (all profiles); pending-escalation gate, lane-evidence gate (`verify_summary.py --lane` on each staged `SUMMARY.md`, whose advisories are relayed on the passing path too; for `Input-type: bug fix` it advises on a missing red/green `### Verify` pair or a missing code change after the red commit, blocking under `REQUIRE_RED_TEST=1`), run-state artifact gate (an untracked `RUN.json`/`events.jsonl` beside a staged `specs/<slug>/` file blocks; tracked-but-unstaged only warns; `REQUIRE_RUN_STATE_STAGED=0` downgrades the block), risk corroboration (the declared `Lane:` against the staged diff; per-gate mode from `harness-manifest.json` `hard_gates.detectable[].mode` — block-mode gates deny a below-`high-risk` lane, warn-mode gates `workflow-engine`/`weakening-validation` print a note and allow), and plan scope (staged paths outside the active plan's `Files` set warn; `BLAST_RADIUS_STRICT=1` blocks) — these under standard and strict; debug-artifact check + targeted pytest + the `### Verify` re-run when `REQUIRE_VERIFY=1` (strict, or `REQUIRE_APP_GATES=1` in any profile). Strict implies `RISK_CORROBORATION_STRICT=1`. The high-risk `### Not auto-verified` check is opt-in via `REQUIRE_NOT_AUTO_VERIFIED=1` (warn-only by default)

### `branch-isolation-guard.sh` (PreToolUse, Edit/Write)

Normalizes every Claude edit path and hard-blocks when any implementation path is touched on a shared branch (`HARNESS_SHARED_BRANCHES`, default `main`/`master`) — judged by where an absolute edit path lives, not the launch directory: the owning checkout's branch (so a linked worktree on a task branch is allowed), plus any enclosing checkout of a different repository (so a nested repo cannot shield a shared checkout's files); git-dir paths are judged by the HEAD in that git dir, unless break-glass `BRANCH_ISOLATION_REASON` is set. An edit is bookkeeping-exempt only when all known paths are under `specs/*`; partial/unknown input fails closed on shared branches.

### `session-knowledge.sh` (SessionStart)

Load `critical-patterns.md` (headings only above 40 lines), a one-line `docs/solutions/INDEX.md` pointer with its entry count, and active-run summaries into context when the store has data; silent when empty; never blocks

### `model-config.sh` (SessionStart, `startup` and `clear`)

Pipes the SessionStart payload to `scripts/apply_model_config.py --hook`, which applies the validated `harness-models.json` to the deployed agent and skill frontmatter; never blocks. `Verifies:` nothing at commit time — it applies the validated user file at session start. `Does not verify:` that the running session picks up a rewritten agent file (it may apply from the next session).

## Hook profiles

`scripts/install-harness.sh` and `scripts/deploy-harness.sh` take `--profile minimal|standard|strict` (default `standard`). `minimal` installs `branch-isolation-guard.sh` and `commit-gate.sh` running only the secrets scan; `standard` installs all four hooks with the standard commit-gate checks; `strict` installs all four with `commit-gate.sh --profile strict`, which adds the app gates and the untracked-`.py` deny. The chosen profile is stored in the target repo's `<target>/.claude/.harness-profile`, and a re-sync without `--profile` reuses it. Re-sync prunes retired harness hooks from the consumer's `.claude/settings.json`, drops event keys left empty, and preserves the consumer's own hooks. This repo's root `settings.json` registers the standard set with a bare `hooks/commit-gate.sh`.

## Gate verifiability (traceability ≠ provenance ≠ truth)

Every gate enforces exactly one evidence tier and must not claim a higher one: **traceability** (structure matches — an ID exists, a rendered artifact agrees with its ledger), **provenance** (evidence is re-derived from the source of truth — a receipt pinned at base, an INDEX rebuilt), or **truth** (behavior is re-run — a Verify row re-executes and exit codes are compared). When adding a gate or hook, document two lines: `Verifies:` what code checks, and `Does not verify:` the negative scope. Existing example — the lane-evidence gate verifies a `### Verify` row *exists*; it does not verify the row is *honest* (that is the opt-in `REQUIRE_VERIFY=1` re-run gate, active when `REQUIRE_VERIFY=1` is set and the app gates run — `--profile strict` or `REQUIRE_APP_GATES=1`). Second example — the optional SUMMARY runtime-metadata check inside `scripts/verify_summary.py`. `Verifies:` the `Runtime-mode`/`Runtime-evidence-id` pair is present as a complete pair and well-formed (valid mode, valid evidence-id shape). `Does not verify:` that the pair matches any real diagnosis. The local record lives in the gitignored, agent-writable `.harness-state/`, so a commit-time comparison could never be index-safe (`docs/solutions/harness/gate-config-must-read-index.md`); the check is deliberately format-only, and the doctor — not this gate — is the authority on the mode.

Each `SUMMARY.md` states its own negative scope in `### Not auto-verified`: the claims it makes that no gate checks, each labelled with the tier it reached. On the high-risk lane this is checked — **advisory by default**, blocking under `REQUIRE_NOT_AUTO_VERIFIED=1`. That check is itself traceability-tier: `Verifies:` the section exists and holds a non-placeholder bullet (or `- none`); `Does not verify:` that the claims are complete or their tier labels correct. `- none` satisfies it, deliberately — it forces the question to be answered, not answered truthfully.

## Rule-loading tiers

Rule loading is two-tier, and the tier is decided by the rule file itself. A file in `rules/` with `paths:` frontmatter is contextual and loads on demand. A file without it auto-loads every session. Contextual rules are injected when a matching `specs/**` file is read, plus explicit Read steps in consuming skills where needed (write-flows do not trigger `paths:`). Adding `paths:` to a rule that lacks it **removes** it from the always-on set. That is a behavior change, not a formatting fix.

Today the source tree contains five always-on files (`behavior.md`, `architecture.md`, `guidelines.md`, `orchestration.md`, `research-depth.md`) and five path-scoped ones (`plan-format.md`, `wave-parallelism.md`, `auto-correct-scope.md`, `terminology.md`, `review-policy.md`). `tests/scripts/rule-loading-tiers.test.sh` keeps this inventory synchronized with `rules/*.md`.

## Gate and re-sync notes

- Under `--profile strict` or `REQUIRE_APP_GATES=1`, a commit staging ≥5 `app/**/*.py` files, at least one mapped to a test, whose targeted pytest run passes prints a hint to run `/compound` — act on it
- Under `--profile strict`, stage and commit in **separate** Bash calls when untracked `.py` files exist — the `hooks/commit-gate.sh` untracked-`.py` check (PreToolUse, strict only) scans the whole command string before it runs, so `git add x.py && git commit ...` in one call still sees `x.py` as untracked and denies the commit. Run `git add`, then `git commit` in a second call (see `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md`)
- Re-sync (`scripts/install-harness.sh` / `scripts/deploy-harness.sh`) is conflict-guarded for protected files (e.g. `<path under rules/ or agents/>`, including any locally-generated per-repo files): a differing local copy is kept by default and the incoming version is written beside it as `<file>.harness-incoming` for review, instead of being silently overwritten. Pass `--overwrite-conflicts` to replace protected files with the incoming copy instead of keeping local
- Consumer gate modes are **not** block-all: a consumer's `commit-gate.sh` resolves each gate's block/warn mode from only two index-safe sources — `git show :harness-manifest.json` if the consumer opts into tracking a root `harness-manifest.json`, otherwise the embedded defaults shipped beside the hook in `hooks/lib/gate-modes.default.sh` (hand-mirrored from the manifest, CI-drift-guarded to **2 warn / 7 block** parity with this repo). A consumer with no tracked manifest falls back to that embedded parity, not deny-everything. The hook **never** reads `.claude/harness-manifest.json` or any worktree file — `.claude/` is gitignored in consumers, so an on-disk policy read would be agent-writable and un-index-checkable (the TOCTOU `docs/solutions/harness/gate-config-must-read-index.md` closed). Break-glass loosening: durable via the manifest `mode` field, session-scoped via `RISK_WARN_CATEGORIES` in the machine-local `settings.local.json` `env` block. Full rationale: `docs/solutions/harness/consumer-risk-modes-index-safe.md`
