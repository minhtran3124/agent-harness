<!--
  Escalation channel. Copy to specs/<slug>/ESCALATIONS.md.
  Default is DENY-ON-NO-RESPONSE: if `decision:` stays `pending`, the work stays BLOCKED.
  The agent appends an escalation block and stops; a human appends the decision.
-->

# require-claude-simplify-gate — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-quality-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: agent (Wave 2 continuation)
- date: 2026-07-30
- trigger: hard-gate
- question: Should the shadow-eval sandbox profile in `scripts/run_simplify_stage_eval.py` (`_sandbox_profile()`) be widened to allow filesystem writes/reads under `/tmp/claude-<uid>/`, an undocumented Claude Code internal path that the Bash tool requires to function at all — and if so, how narrowly?
- context: Task 2.1 (run the pinned shadow candidate). After fixing the relative-path bug (commit `0eb1287`) and the `~/.claude/session-env` EPERM (commit `8c51780`, via `CLAUDE_CONFIG_DIR`), a real candidate run still fails on every fixture's first Bash tool call with:
  ```
  EPERM: operation not permitted, mkdir '/private/tmp/claude-501/-private-var-folders-...-worktree'
  ```
  This is a second, distinct hardcoded scratch path (`/tmp/claude-<uid>/<dashed-absolute-cwd>/`) that the Bash tool writes to on every invocation — confirmed it does **not** honor `$TMPDIR` (already set to a sandbox-writable dir; the mkdir still targeted real `/tmp`). I independently verified (own empirical test, plus a `claude-code-guide` docs sweep) that **no documented environment variable, CLI flag, or setting redirects this path** in Claude Code 2.1.x — unlike `~/.claude`, which `CLAUDE_CONFIG_DIR` cleanly relocates. Without an exception, the Bash tool cannot run a single command inside the sandbox, so candidate collection cannot proceed at all.

  This blocks: Task 2.1's real candidate run (`evals/skills/simplify-stage/results/candidate.json`), and therefore SC-8/SC-9 and every downstream wave (3–6) that the plan gates on a passing shadow-eval quality/value verdict.

  First raw evidence from the pre-`CLAUDE_CONFIG_DIR` run is preserved (not deleted) as:
  - `evals/skills/simplify-stage/results/candidate-rejected-sandbox-session-env-eperm.json`
  - `evals/skills/simplify-stage/results/artifacts/candidate-rejected-sandbox-session-env-eperm/`
  - `evals/skills/simplify-stage/results/transcripts/candidate-rejected-sandbox-session-env-eperm/`

  No new candidate.json/artifacts have been written for this second failure mode (only reproduced via a throwaway smoke test outside the immutable-output contract, so nothing to preserve there).

- options:
  - A) **Allow the exact computed literal path** — derive `/tmp/claude-<uid>/<dashed(worktree)>` from `worktree` (string-replace `/`→`-`, matching the observed pattern) and add it as an extra allowed_root (read+write) in `_sandbox_profile()`, scoped per-run since each `worktree` is a fresh random tempdir. Narrowest possible exception, but relies on reverse-engineering an undocumented internal naming scheme that could silently change in any point release, breaking the eval invisibly (mkdir would then fail again with the same opaque EPERM, or worse, resolve to an unintended path if the scheme changes shape rather than just breaking).
  - B) **Allow the whole `/tmp/claude-<uid>/` tree** — coarser, more resilient to internal path-shape changes, but this is a per-uid directory Claude Code may use across *all* concurrent sessions on this machine (multiple real `claude` processes are running right now per `ps aux`), so it widens the sandboxed candidate's read/write reach beyond this eval run's own scratch space — a real (if hard to characterize) cross-session exposure, and a genuine loosening of the previously audited "home/.claude/Keychain unreachable" sandbox contract's spirit even though `/tmp` itself isn't literally in that list.
  - C) **Do not widen the sandbox; treat "real Claude Code candidate collection in a Seatbelt sandbox" as currently infeasible** on this OS/client-version combination, and either (i) fall back to a weaker isolation strategy (e.g. a disposable per-run macOS user account, a Linux container/VM, or dropping the sandbox requirement and relying solely on the disposable git worktree + `--dangerously-skip-permissions` scope for isolation), or (ii) hold Task 2.1 open and keep the hard-gate rollout (Waves 3–6) blocked until Anthropic ships a documented override (a feature request was already effectively identified during investigation: something analogous to `CLAUDE_CONFIG_DIR` but for this Bash-tool scratch path).
- default_if_no_response: BLOCK
- decision: B — allow the whole `/tmp/claude-<uid>/` tree (read+write) in `_sandbox_profile()`, accepting the coarser, more version-resilient exception over the narrower literal-path option
- decided_by: Minh Tran
- decided_at: 2026-07-30

---

## E002

- raised_by: agent (final `/correctness-review` pass, guard-completeness angle, before push)
- date: 2026-07-30
- trigger: judgment-ambiguous (Rule-4: architectural — changes when a mandatory review gate applies)
- question: `skills/finishing-a-development-branch/SKILL.md`'s step 2 says "Tiny/no-plan work skips it" for the whole receipt-gate invocation (`--require correctness,intent --require-audit-if <base> --require-simplify-if <base>`), keyed purely on the intake `Lane: tiny` label. But `scripts/check_claude_simplify.py` (this feature) explicitly defines an `oversized_tiny_source_change` reason — a tiny-lane diff whose reviewable lines exceed `TINY_SOURCE_LINE_THRESHOLD` (150) is `required: true` regardless of its lane label. Since the finishing gate's skip is keyed on the label alone, an oversized-but-mislabeled-tiny diff never reaches `--require-simplify-if` at all — the exact case that reason value exists to catch. Should this exemption be narrowed?
- context: Found and reproduced by one of six independent correctness-review FIND angles (`guard-completeness`) over this branch's own diff. This exemption **predates** this diff — it already applied identically to `--require correctness,intent` before `--require-simplify-if` was added (commit `f1a9e8f`, Task 4.2) — so this diff didn't introduce a NEW bypass, it added a new required-review type into an EXISTING bypass whose scope this diff never re-examined. `check_claude_simplify.py`'s own `evaluate_policy()` already computes the right answer (`required`/`reason`) for the ACTUAL diff at hand; `finishing-a-development-branch/SKILL.md` just never consults it — it only asks "what lane was this classified at intake," which can drift from the diff's real, current size (intake happens once, before all commits land).

  This blocks: nothing about *this* PR (this branch's own diff is `Lane: high-risk`, never hits the tiny-skip path at all — confirmed via `resolve_finish_context.py` output for this branch). It's a residual-risk finding about the shipped mechanism's own completeness, not a defect in this branch's own commits.
- options:
  - A) **Narrow the finishing-gate exemption**: change step 2 so `--require-simplify-if <base>` runs unconditionally (it's already internally conditional — see E001-era design notes: it independently no-ops when the diff has no reviewable path) regardless of lane, while `--require correctness,intent --require-audit-if <base>` keeps the existing tiny/no-plan skip as-is. This targets the fix precisely at the one flag this diff introduced, without touching the pre-existing correctness/intent/audit exemption's own semantics — smallest blast radius, but means "tiny" work now always pays the (usually free, since `_simplify_required` no-ops on non-reviewable diffs) cost of one more subprocess call.
  - B) **Re-derive the exemption from the diff, not the label**: change finishing-a-development-branch's tiny/no-plan check itself to ask `check_claude_simplify.py` (or `resolve_finish_context.py`, if extended to expose it) whether the diff is actually reviewable/oversized, for ALL required-review types at once — a deeper, more correct fix, but touches the shared exemption logic multiple other gate types already rely on and needs its own dedicated design/test pass, not a quick patch this late in this branch's own review cycle.
  - C) **Leave as-is; accept the residual risk**: this exemption pattern (lane-label-only, not diff-size-aware) already existed for `correctness,intent` before this feature; treat "is the tiny-lane skip itself diff-size-aware" as a pre-existing, separately-scoped harness question rather than this feature's responsibility to fix, since `check_claude_simplify.py`'s own SIZE_THRESHOLD constant and the harness's tiny-lane conventions elsewhere (e.g. `hooks/risk-corroboration.sh`'s advisory note) already assume tiny-lane diffs stay genuinely small in practice.
- default_if_no_response: BLOCK
- decision: A — narrow only `--require-simplify-if <base>` to run for tiny-lane plan work too
  (it's already internally conditional, no-ops on a non-reviewable diff); leave the pre-existing
  `--require correctness,intent --require-audit-if <base>` tiny-lane exemption untouched. Fixed in
  `skills/finishing-a-development-branch/SKILL.md` + `tests/scripts/finishing-branch-contract.test.sh`
  (2 new checks, 2 new mutation tests).
- decided_by: Minh Tran
- decided_at: 2026-07-30

---

## E003

- raised_by: agent (owed `call-site-impact` FIND angle, run 2026-08-04 after the PR was opened)
- date: 2026-08-04
- trigger: Rule-4 (architectural — the deploy contract / a core skill-engine dependency edge)
- question: `skills/subagent-driven-development/scripts/simplify_record.py` (new in this branch)
  resolves its dependency as `_REPO_ROOT / "scripts" / "check_review_receipt.py"`, where
  `_REPO_ROOT = Path(__file__).resolve().parents[3]`. That works in this meta-repo, where the file
  is run from the source tree. It does **not** work anywhere the harness is installed:
  `scripts/deploy-harness.sh:106` mirrors only `^(skills|agents|hooks|rules|templates|runtime)/[^/]+$`
  into `.claude/`, so the deployed copy resolves `_REPO_ROOT` to `.claude/` and looks for a
  `.claude/scripts/` directory that is never created. How should a deployed `skills/**/scripts/`
  helper reach a `scripts/` module?
- context: Reproduced twice, read-only. (1) The already-deployed copy in this checkout:
  `python3 .claude/skills/subagent-driven-development/scripts/simplify_record.py --help` →
  `FileNotFoundError: .../.claude/scripts/check_claude_simplify.py`. (2) The current source copied
  into a fresh `.claude/skills/subagent-driven-development/scripts/` tree → the same crash, naming
  `.claude/scripts/check_review_receipt.py`. The failure is at module import, before argparse, so
  every subcommand dies.

  This blocks: the required simplify stage in any consumer repo. `references/simplify-stage.md`
  step 3 tells the controller to run `simplify_record.py begin`, and there the stage can never
  record its evidence. It does **not** block this repo's own use of the stage, and it does not
  affect any gate's fail-closed direction — a crash is a hard stop, not a bypass.

  Related pre-existing scope: `scripts/check_review_receipt.py` itself is likewise undeployed, so
  `finishing-a-development-branch`'s receipt gate has the same reach problem in a consumer repo.
  That predates this branch; only the new `simplify_record.py` edge is this branch's own.
- options:
  - A) **Add `scripts/` to the deploy payload** — extend `SYNCED_DIRS_RE` so `scripts/` mirrors into
    `.claude/scripts/`. Fixes the whole class at once (including the pre-existing
    `check_review_receipt.py` reach gap), but widens the deploy surface for every consumer and
    changes what `deploy-harness.sh` owns, with its own conflict-guard/prune implications.
  - B) **Deploy a named subset** — mirror only the scripts the deployed skills actually invoke.
    Narrower blast radius, but introduces a second dependency list that can drift from the imports.
  - C) **Vendor the dependency under `skills/`** — move or copy the shared helpers into the skill's
    own `scripts/` dir so a deployed skill is self-contained. No deploy-contract change, but
    duplicates `check_review_receipt.py`/`check_claude_simplify.py` logic, which the branch has
    deliberately kept single-sourced.
  - D) **Scope the stage to this repo** — accept that the simplify stage is meta-repo-only for now
    and say so in `references/simplify-stage.md`, deferring consumer support. Honest, cheap, but
    ships a documented gap in a stage this branch makes mandatory.
- default_if_no_response: BLOCK
- decision: A — add `scripts/` to the deploy payload. `SYNCED_DIRS_RE` and the sync loop in
  `scripts/deploy-harness.sh` now include `scripts`, and `PAYLOAD` in `scripts/install-harness.sh`
  carries the whole `scripts` directory instead of two named files. This also closes the
  pre-existing reach gap for `scripts/check_review_receipt.py`, so the finishing gate is runnable
  in a consuming repo for the first time.

  Two consequences handled as part of the fix:
  - **Legacy-scan false positive.** `install-harness.sh` scanned `PAYLOAD` for root-level paths
    left by an older installer layout. With `scripts` in `PAYLOAD`, every project that has its own
    `scripts/` would be told its directory is harness leftovers to remove. The scan now reads a
    separate `LEGACY_ROOT_PATHS` list that keeps the two script *files* an old layout really did
    stage, and omits `runtime`/`scripts` as whole directories.
  - **Prune safety.** `prune_orphans` is gated on the *previous* deploy manifest, which has never
    contained a `scripts/` entry, so no first deploy after this change can prune anything under
    `scripts/`. A consumer's own files are never in the manifest and stay ineligible, unchanged.

  Verified against a throwaway target (`--target <tmp> --yes`, never the real `.claude/`): 64
  entries land in `.claude/scripts/`, and the deployed
  `.claude/skills/subagent-driven-development/scripts/simplify_record.py --help` now runs instead
  of dying at import. Two regression tests added to `tests/scripts/install-harness.test.sh`, each
  verified failing against the pre-fix code.

  **Scope note, recorded rather than hidden:** this repo's own precedent treats a `SYNCED_DIRS_RE`
  change as its own high-risk feature — adding `runtime/` got a dedicated design, plan, and test
  pass (`specs/gh-129-durable-run-state-phase-b/`), and `specs/durable-run-state/design.md:41`
  records that `scripts/` was deliberately never synced as a unit. Option A was chosen with that
  trade-off stated in the options above; it changes the distribution contract for every consuming
  repo and now ships all 64 files in `scripts/` (test files and eval runners included, matching how
  `skills/` already deploys its own tests). If that surface is unwanted, option B (a named subset)
  is the narrower alternative and this decision can be revisited without touching the callers.
- decided_by: Minh Tran
- decided_at: 2026-08-05

<!-- copy the E0xx block for each new escalation -->
