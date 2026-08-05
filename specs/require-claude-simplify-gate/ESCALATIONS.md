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

---

## E004

- raised_by: agent (round-4 `/correctness-review`, `guard-completeness` angle, fresh context)
- date: 2026-08-05
- trigger: Rule-4 (architectural — changes what a fail-closed push gate accepts, and invalidates
  already-recorded receipts)
- question: `check_review_receipt.py`'s `--require-simplify-if` validates a `type: simplify`
  entry's *internal* chain — `base_sha → pre_sha → post_sha` ancestry, and
  `post_sha == reviewed_head_sha` — but never anchors `base_sha` to the range it is gating. The
  recorded cleanup may therefore cover a strictly narrower range than the branch, down to an empty
  one, while the gate reports the required stage as satisfied. Should the entry's `base_sha` be
  required to equal the gated base?
- context: Reproduced independently in a throwaway repo, twice:

  1. Branch `B→c1→c2→pre→post` (4 reviewable commits). Entry with `base_sha = c2` — skipping two
     commits of unreviewed code. `check_review_receipt.py <slug> --require-simplify-if B` → **exit 0**.
  2. Degenerate: entry with `base_sha == pre_sha == post_sha`, `outcome: no_op`, covering an
     **empty** range, on the same 4-commit branch → **exit 0**.

  Nothing filters the empty case: `is_ancestor` is documented "ancestor of, **or identical to**",
  and `simplify_shape_error` never requires `base_sha != pre_sha`. `simplify_record.begin()` does
  reject `base == target`, but this gate is explicitly the fail-closed consumer that re-derives
  rather than trusting the recorder — it ignores the entry's self-reported `result` for exactly
  that reason. The base anchor is the one thing it re-derives nothing about. Search surface:
  `grep -rn "base_sha" scripts/ skills/ hooks/ rules/` — read only at `check_review_receipt.py`
  ancestry, written at `simplify_record.py`; nothing compares it to `require_simplify_if`.

  This blocks: the central guarantee of this feature. A branch can satisfy the mandatory stage
  with evidence covering no code at all.
- options:
  - A) **Require exact equality** — resolve `require_simplify_if` to a SHA and require the
    covering entry's `base_sha` to equal it, and reject `base_sha == pre_sha`. Strongest and
    simplest to reason about, but **invalidates every already-recorded receipt** whose entry was
    written against a different base — including this branch's own, forcing a re-run of the stage
    before this PR can push.
  - B) **Require coverage, not identity** — accept an entry whose `base_sha` is an ancestor of the
    gated base (so a wider cleanup still counts) while rejecting a narrower one and the empty
    range. More permissive on resume cycles; slightly more logic to get right.
  - C) **Reject only the degenerate empty range** — add `base_sha != pre_sha` to
    `simplify_shape_error` and leave the narrowing case. Cheapest, keeps existing receipts valid,
    but leaves case 1 (skipping real commits) open, so it fixes the extreme and not the class.
- default_if_no_response: BLOCK
- decision: A — require exact equality. `check_receipt` now resolves `--require-simplify-if` to a
  SHA (`_resolve_sha`) and requires the covering entry's `base_sha` to equal it, and
  `simplify_shape_error` rejects `base_sha == pre_sha` outright as an empty range. The anchor is
  enforced only when the stage is actually required, so an unrequired historical entry cannot
  block a push it was never gating; the empty-range check is shape-level and applies to every
  entry, matching what `simplify_record.begin()` already refuses. Both original reproductions now
  fail closed. Accepted cost: this branch's own receipt is invalidated and the stage must re-run
  before push — a cost E006 forces anyway.
- decided_by: Minh Tran
- decided_at: 2026-08-05

---

## E005

- raised_by: agent (round-4 `/correctness-review`; `removed-behavior`, `enclosing-function`, and
  `call-site-impact` converged on it independently in separate fresh contexts)
- date: 2026-08-05
- trigger: Rule-4 (architectural — decides whether a lane that is documented to need no review
  must nonetheless produce a review artifact)
- question: `finishing-a-development-branch/SKILL.md:32` claims the tiny-lane invocation "is
  already internally conditional — a no-op when the diff has no reviewable path". It is not.
  `check_receipt` returns `missing: no review receipt` at its first statement, long before
  `require_simplify_if` is consulted. Which is correct — the claim, or the code?
- context: Reproduced: a tiny-lane branch with `specs/<slug>/PLAN.md` and a docs-only diff, no
  receipt file → `missing: no review receipt at specs/demo/.review-receipt.json`, exit 1. Same
  repo with an empty-`reviews` receipt present → exit 0, which isolates the receipt-existence
  precheck as the blocker rather than the simplify conditional.

  The operator has no legitimate exit. Tiny lane grants "full auto — direct patch on a fresh
  branch" with no plan chain, so the SDD review chain never runs and `.review-receipt.json`
  (gitignored, machine-local) is never written. `SKILL.md:36` says *"never edit the receipt to
  pass"*, and `references/simplify-stage.md:19-21` says *"do not call `simplify_record.py` at
  all"* for a diff with no reviewable path. Nothing in the documented workflow creates the file.

  Introduced by this branch: `af7b014` (E002 option A) deleted "Tiny/no-plan work skips it" and
  replaced it with a premise the code does not implement. The deletion also silently widened
  scope — the tiny invocation now additionally imposes the stale-SHA check and the "every
  recorded review must pass / `blocking_open == 0`" checks, none of which the replacement prose
  mentions.

  This blocks: any compliant tiny-lane branch that happens to have a plan directory.
- options:
  - A) **Make the code match the claim** — evaluate the conditional requirements before the
    receipt-existence check when `--require` is empty, so a diff with no reviewable path exits 0
    with no receipt. Matches what SKILL.md already promises operators; the receipt stays required
    the moment anything reviewable appears.
  - B) **Make the claim match the code** — drop "internally conditional" from SKILL.md and state
    that tiny plan-backed work must produce a receipt. Honest, no code change, but imposes a
    review artifact on a lane the harness defines as needing none, and no documented step creates
    one.
  - C) **Key the skip on the lane, not the plan dir** — restore a tiny-lane skip in the finishing
    gate. Simplest, but re-opens exactly the hole E002 option A was chosen to close.
- default_if_no_response: BLOCK
- decision: A — make the code match the claim. `check_receipt` now resolves the conditional
  requirements *before* demanding the receipt file, and returns success when a **purely
  conditional** invocation finds nothing owed.

  The relaxation is deliberately narrow, and the existing suite caught the first attempt at it:
  returning success whenever `required` was empty also let a **bare** `check_review_receipt.py
  <slug>` pass with no receipt, breaking `test_missing_receipt_fails`. A caller naming no
  requirement at all is asking "is this receipt valid?", and the answer to that is still no. The
  shipped condition therefore requires that `--require` be empty *and* at least one `*_if` flag
  be present *and* nothing fire. The moment a reviewable path appears, the receipt is required
  again — pinned by `test_conditional_only_invocation_still_fails_once_something_is_owed`.
- decided_by: Minh Tran
- decided_at: 2026-08-05

---

## E006

- raised_by: agent (round-4 `/correctness-review`, `stack-defects` angle, fresh context)
- date: 2026-08-05
- trigger: Rule-4 (redefines the gate's validation scope — authoritative policy in
  `rules/simplify-stage.md`, the manifest contract, and every consuming repo)
- question: `classify_path` returns `documentation` for every Markdown path, so
  `skills/*/SKILL.md`, `skills/*/references/*.md`, `skills/*/prompts/*.md`, `agents/*.md`, and
  `rules/*.md` are all excluded from the reviewable set. In this repository those files **are the
  program** — CLAUDE.md defines skills as "Markdown prompt documents … invoked as `/skill-name`".
  Should the documentation exclusion be narrowed so prompt documents stay reviewable?
- context: Reproduced end-to-end. A throwaway repo, `high-risk` lane, 1,402 changed lines across
  `skills/foo/SKILL.md` and `rules/behavior.md`, receipt carrying correctness/intent/audit but no
  `type: simplify` entry:

  ```
  {"reason": "documentation_only", "required": false, "changed_source_lines": 0,
   "reviewable_paths": [], "excluded_paths": ["rules/behavior.md", "skills/foo/SKILL.md"]}
  ```

  `check_review_receipt.py --require correctness,intent --require-audit-if B --require-simplify-if B`
  → **exit 0**. The mandated stage is skipped on 1,402 lines of program text.

  The same file already disagrees with itself about this: `_RECEIPT_NEUTRAL_CATEGORIES`
  (`check_review_receipt.py:73`) deliberately keeps `documentation` **out** of its neutral set,
  with the comment "documentation is prose a human reads (intent drift hides there)". So the
  staleness gate treats `.md` as reviewable while the requirement gate does not.

  This is precisely the change class `_WF_INCLUDE` flags as highest-risk and routes to
  `/context-propagation-audit`. It is also the change class of this very branch — the stage fired
  here only because the diff happens to carry `.py` files alongside the skills.

  This blocks: nothing mechanically (the gate fails open, quietly), which is why it needs a
  decision rather than a patch. Search surface for the no-second-gate claim:
  `grep -rn -e '--require-simplify-if' -e 'check_claude_simplify' .` excluding
  `specs/ evals/ .claude/ .git/ test_*` — only the manifest, the finishing skill, and one
  contract test.
- options:
  - A) **Subtract the `_WF_INCLUDE` surface from the documentation exclusion** — a Markdown file
    that matches the workflow-engine signal stays reviewable; ordinary prose stays excluded. Uses
    a signal the repo already defines and keeps one meaning of "workflow engine". Portable: a
    consumer repo with no `skills/` simply never matches.
  - B) **Make the exclusion project-scoped** — let a repo declare which paths are program text.
    Most correct across consumers, but adds a configuration surface the checker has deliberately
    avoided (it takes no implicit input today).
  - C) **Exclude only by directory, not by suffix** — treat `.md` under `docs/` as documentation
    and everything else by location. Simple, but reclassifies README/CHANGELOG-style files
    throughout the tree and would surprise consumers.
  - D) **Accept and document** — record that the simplify stage does not cover prompt-document
    changes, and rely on `/context-propagation-audit` plus the per-task quality reviewer for that
    surface. No code change; but the feature's headline guarantee then does not hold for the
    repository that ships it.
- default_if_no_response: BLOCK
- decision: A′ — option A, widened to cover the whole surface. Checking what `_WF_INCLUDE`
  actually matches showed plain A would have been a **half fix**: it covers `skills/*/SKILL.md`,
  `*prompt*.md`, `agents/*.md`, and `rules/*.md`, but **not** `skills/*/references/*.md` or
  `skills/*/prompts/**` — which includes `references/simplify-stage.md`, this stage's own
  instructions, and the six angle prompts that found every defect in this round.

  Shipped instead: Markdown under `skills/`, `agents/`, or `rules/` classifies as `reviewable`,
  with `README.md` and `*.template.md` still excluded as prose about the surface rather than
  instructions an agent executes. Matched case-insensitively, unlike the exclusion authorities —
  the exact-case rule exists so a case variant can never *shrink* coverage, and here folding only
  grows it. Portable: a repository without those directories never matches. `templates/` is
  deliberately not included; it ships forms for consumers to fill in.

  This also resolves the contradiction inside `check_review_receipt.py`, where
  `_RECEIPT_NEUTRAL_CATEGORIES` already kept `documentation` out of the staleness gate's neutral
  set ("intent drift hides there") while the requirement gate excluded it.
- decided_by: Minh Tran
- decided_at: 2026-08-05

<!-- copy the E0xx block for each new escalation -->
