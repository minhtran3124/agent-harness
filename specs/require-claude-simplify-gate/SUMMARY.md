# require-claude-simplify-gate — Summary

Lane: high-risk
Confidence: high
Reason: This proposal changes workflow-engine sequencing, mutation authority, review receipts, and the final push gate.
Flags: workflow-engine
Affects: subagent-driven-development, final review chain, review receipt, finishing gate
Input-type: harness improvement

### Intent

> "hãy lên plan cho việc require skill "simplify" vào workflow hiện tại. hãy research và cho tôi
> biết suy nghĩ của bạn về request này, có đúng ko? có hợp lý ko? có đáng làm ko?"
>
> "ok, hãy viết plan vào doc trước cho tôi"

## What changed

Started as a research brief, approved design, and executable proposed plan for adding Claude
Code's bundled `/simplify` as a signal-gated cleanup stage before final review — the user's
verbatim request above. After that planning phase, the user explicitly directed continuing into
implementation ("continue implementation from the exact checkpoint until completion", their
own words opening a later session on this branch) and, mid-implementation, made two further
explicit decisions that only a human could make (`ESCALATIONS.md` E001, E002). This is a durable
record of that authorization chain, since the verbatim `### Intent` quote above captures only the
original planning request, not the later continue-to-implementation instruction.

**Runtime workflow behavior now IS changed** (this sentence used to say the opposite — stale
planning-era text, corrected during final intent review): the diff ships real enforcement, not
just docs. `skills/finishing-a-development-branch/SKILL.md` requires `--require-simplify-if <base>`
before every push (unconditionally for non-tiny work, and — after `ESCALATIONS.md` E002 — for
tiny-lane plan work too); `skills/subagent-driven-development/SKILL.md` inserts a required
`/simplify` stage before the final review chain; `scripts/check_review_receipt.py` validates that
evidence; `hooks/risk-corroboration.sh`, `harness-manifest.json`, `CLAUDE.md`, and
`skills/README.md` are synchronized to describe the same, now-live contract.

### Rationale

The current pipeline lacks a branch-wide owner for reuse, simplification, efficiency, and
abstraction-altitude cleanup. Because `/simplify` mutates code and has version-sensitive vendor
semantics, the plan requires a shadow eval, a minimum client version, post-mutation verification,
and final reviews over the resulting HEAD.

### Alternatives considered

- Require `/simplify` after every task — rejected as duplicate fixed ceremony.
- Require it for every branch — rejected for tiny and non-code changes.
- Keep the existing warning only — rejected because it is not a durable workflow guarantee.
- Create a repository skill named `simplify` — rejected because it may shadow the bundled skill.

### Deviations

- Rule 3 — Relative `--fixtures`/`--output`/`--claude` paths weren't resolved absolute before a
  subprocess `cwd` change (`git bundle create`), breaking `run_simplify_stage_eval.py` from any
  caller cwd other than repo root. Commit `0eb1287`.
- Rule 3 — Sandboxed candidate collection failed 100% on `~/.claude/session-env` EPERM (Bash tool
  needs it regardless of `$TMPDIR`); fixed via `CLAUDE_CONFIG_DIR`, verified empirically not to
  touch the real `~/.claude`. Commit `8c51780`.
- Rule 3 — After the above, `git` itself failed inside the sandbox (`/dev/null` write-deny,
  unallowed git-common-dir) — pre-existing Wave-1 gaps never exercised until a real multi-step
  agentic run; scoped only to the eval's own disposable synthetic repo and universally-safe
  devices, not the security boundary from the Rule-4 case below. Commit `50e3470`.
- Rule 3 — An independent adversarial review of `6ac6d65` found `simplify-stage.md`'s "not
  required" skip path had no valid `simplify_record.py finish --begin-state` to pass; re-keyed the
  bookkeeping decision on `reviewable_paths` instead of `required`. Commit `0611dbb`.
- Rule 1 — Assorted unused-variable removals and lint fixups caught by `ruff`/mutation-review
  passes across waves 1-5 (no behavior change, folded into each wave's own commit).
- Rule 3 — Wave 6's real, production `/simplify` invocation over this branch's own diff (Global
  Constraint requires shipping this feature to eat its own dogfood) surfaced a context-propagation
  audit FAIL: `simplify-stage.md`'s delta-review dispatch said "with the plan's Global Constraints
  as context" but had no delivery mechanism for a non-task delta (`task_brief.py` required a
  `### Task N.N` id). Added a `--delta-description` mode to `task_brief.py` reusing the same
  `Global Constraints` extraction, wired it into `simplify-stage.md`, and added a mutation-tested
  drift check. Independently re-verified the FAIL is closed. Not committed as its own numbered
  wave — a final-review-cycle fix required before the receipt/PR, per the same Rule-3 authority as
  the other entries above.
- Rule 3 — The final `/correctness-review` pass (6 independent FIND angles) found and fixed:
  (1) [enclosing-function + stack-defects, converged independently] `check_review_receipt.py`'s
  `--require-simplify-if` deep-validation loop required *every* `type: simplify` entry to have
  `post_sha == reviewed_head_sha` — but `simplify-stage.md` documents *appending* a fresh entry on
  each resume cycle, so a legitimate second cycle would leave a superseded first entry that
  permanently fails that check, deadlocking an otherwise-valid receipt. Reproduced independently by
  both finders. Fixed: only an entry whose `post_sha` matches `reviewed_head_sha` is required to
  pass freshness/verdict checks; every entry (current or historical) still has its shape/ancestry
  validated, so a corrupt historical entry is still caught. Two new tests added (a valid two-cycle
  receipt now passes; a malformed superseded entry still fails).
  (2) [guard-completeness, P2] `check_simplify_adoption.py` never checked
  `finishing-a-development-branch/SKILL.md` despite the manifest naming it a contract consumer —
  added `_check_finish_gate` plus two tests.
  (3) [stack-defects, P2] The four Python test files added to `run-tests.sh`'s `PYTESTS` list in
  wave 5 didn't include `skills/subagent-driven-development/scripts/test_task_brief.py` (added
  after wave 5, in the audit-repair fix above) — added it.
  (4) [prior-art, P1] This SUMMARY's own `### Verify` table had two whole-suite rows
  (`bash scripts/run-tests.sh`, measured ~130s) — over `verify_summary.py --check`'s 60s re-run
  cap, which would make CI's strict gate fail-closed on this very SUMMARY despite the suite
  actually passing. Fixed per `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`:
  removed the two rows, cited the full-suite result in prose instead.
  [P1, guard-completeness] `finishing-a-development-branch/SKILL.md`'s pre-existing "Tiny/no-plan
  work skips it" exemption was keyed only on intake lane label, not on `check_claude_simplify.py`'s
  actual `required`/`oversized_tiny_source_change` signal — an oversized-but-mislabeled-tiny diff
  would never hit `--require-simplify-if` at all. This exemption predates this diff (already
  applied identically to `correctness,intent`), so fixing it was a genuine scope/design decision,
  not a mechanical patch — escalated as `ESCALATIONS.md` E002 with 3 options; user chose A: narrow
  only `--require-simplify-if` to run for tiny-lane plan work too (it already no-ops on a
  non-reviewable diff), leaving the pre-existing correctness/intent/audit exemption untouched.
  Fixed with 2 new contract checks + 2 mutation tests.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Planning contract | `python3 scripts/check_plan_contract.py specs/require-claude-simplify-gate/PLAN.md` | 0 | Contract passed on 2026-07-30 | |
| Plan render | `python3 skills/visual-planner/render_plan.py specs/require-claude-simplify-gate/PLAN.md` | 0 | Parsed 8 tasks across 6 waves | |
| Capability/policy tests | `python3 -m pytest scripts/test_check_claude_simplify.py -q` | 0 | 119 passed (was 103; +16 pinning exact-case directory authorities vs case-folding file names, round 3) | SC-1 |
| Policy self-test | `python3 scripts/check_claude_simplify.py --self-test-policy` | 0 | `simplify-policy: self-test passed` | SC-2 |
| Evidence recorder tests | `python3 -m pytest skills/subagent-driven-development/scripts/test_simplify_record.py -q` | 0 | 27 passed; dirty-worktree, symbolic/short SHA, ancestry all rejected | SC-3 |
| SDD ordering contract | `bash tests/scripts/sdd-simplify-stage-contract.test.sh` | 0 | 31 passed, incl. 13 mutation checks; round 3 added the adoption-checker wiring check | SC-4 |
| Receipt validation tests | `python3 -m pytest scripts/test_check_review_receipt.py -q` | 0 | 52 passed (was 39; round 3 added the case-variant bypass and non-ASCII-path regressions, both verified failing on the pre-fix code) | SC-5 |
| Receipt self-test | `python3 scripts/check_review_receipt.py --self-test-simplify` | 0 | `check-review-receipt: simplify self-test passed` | SC-6 |
| Finishing contract | `bash tests/scripts/finishing-branch-contract.test.sh` | 0 | 6 passed, incl. simplify-clause mutation check | SC-7 |
| Shadow-eval quality gate | `python3 scripts/score_simplify_stage_eval.py --compare evals/skills/simplify-stage/results/baseline.json evals/skills/simplify-stage/results/candidate.json --fixtures evals/skills/simplify-stage/fixtures --quality-gate` | 0 | Round 4 (HEAD `f5f135c`): `quality_pass: true`, 8/8 fixtures matched `truth.json`. Round 3's evidence (HEAD `5a34cae`) went digest-stale once the branch's own `/simplify` self-application (`e90413b`) edited the eval harness's own source; re-collected, identical result. Rounds 1-2 rejected first (`comparison.md`) | SC-8 |
| Shadow-eval value gate | `python3 scripts/score_simplify_stage_eval.py --compare evals/skills/simplify-stage/results/baseline.json evals/skills/simplify-stage/results/candidate.json --fixtures evals/skills/simplify-stage/fixtures --value-gate` | 0 | `value_pass: true`, `value_score: 4` ≥ `minimum_value_score: 3` (round 4) | SC-9 |
| Adoption/deployed parity | `python3 scripts/check_simplify_adoption.py` | 0 | `consistent` — policy, ordering, receipt, hook, docs, deployed harness all agree (post `deploy-harness.sh`, re-run at final HEAD). Re-run this bare form after any re-sync; the local `.claude/` mirror is stale until then | SC-10 |
| Adoption drift, as CI runs it | `python3 scripts/check_simplify_adoption.py --skip-deployed-parity` | 0 | `consistent` — checks A-F. Round 3 wired this into `run-tests.sh`; it had never been invoked by any suite | SC-10 |
| Adoption checker's own tests | `python3 -m pytest scripts/test_check_simplify_adoption.py -q` | 0 | 22 passed (was 19; +3 for the skip flag) | |
| Eval runner tests | `python3 -m pytest scripts/test_run_simplify_stage_eval.py -q` | 0 | 20 passed | |
| Eval scorer tests | `python3 -m pytest scripts/test_score_simplify_stage_eval.py -q` | 0 | 7 passed | |
| Task-brief delta-description tests | `python3 -m pytest skills/subagent-driven-development/scripts/test_task_brief.py -q` | 0 | 6 passed | |
| Hook contract tests | `bash tests/hooks/risk-corroboration.test.sh` | 0 | 39 passed | |
| Install/deploy contract (E003) | `bash tests/scripts/install-harness.test.sh` | 0 | 12 passed (was 10). New: the deployed skill helper loads its dependency; a consumer's own `scripts/` is not flagged as legacy. Both verified failing against the pre-fix scripts | |

The full suite (`GOCACHE=/tmp/harness-skills-go-cache bash scripts/run-tests.sh`, all L1-L3 layers,
measured ~130s — over the 60s `verify_summary.py --check` re-run cap, so it is cited here in prose
rather than as a Verify row per `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`)
passed at intake (278 Python tests, all shell contracts green) and passes at every checkpoint since:
473 passed at the final HEAD (up from 278 — the wave-5 fix closed a real CI-registration gap for
four Python test files that existed but were never in `run-tests.sh`'s `PYTESTS` list), zero
regressions. After the round-3 fixes: **513 passed, ALL GREEN** (up from 493 at `f62fcc0`; the 20
new tests are the round-3 regressions and their mutation pairs). The 493-green run before those
fixes is itself evidence — none of the round-3 defects was caught by the suite as it stood.

### Plan Review

- Independent review — PASS. Same-wave files are disjoint; shadow evaluation precedes hard-gate
  wiring; `/simplify` runs before the branch package and final oracles; changed outcomes require
  verification plus spec/quality delta review; receipt freshness covers the post-simplify HEAD.

### Context-Propagation Audit

- FAIL then repaired (see `### Deviations`): `simplify-stage.md`'s delta-review dispatch said
  "with the plan's Global Constraints as context" with no actual delivery mechanism for a
  non-task delta. Fixed via `task_brief.py --delta-description`, mutation-tested. Re-audited:
  PASS.
- Round 2 (receipt-refresh chain at `8e6eca5`, fresh-context auditor): FAIL on one row, then
  repaired. `SKILL.md`'s Resume-first gate ("read resume.md only when its returned action
  requires a manual transition or repair") let a fresh resumed session plausibly skip
  `references/resume.md` for `resume-review-chain` — skipping the simplify-evidence re-check
  that this branch made load-bearing there. Repaired in `ac161a0`: the read gate now names
  `resume-repair`/`resume-review-chain`/`rebuild` explicitly, with a mutation-verified contract
  check (`skill_resume_read_gate_ok`). Independently re-verified CLOSED by a second
  fresh-context reviewer, including an adversarial search for bypass routes into
  `review-chain.md` (none found: all references route through Execute-waves-after-simplify,
  simplify-stage.md itself, or resume.md's re-check). All other matrix rows PASS with
  file:line/test proof.

### Correctness Review

- Six FIND angles over the branch diff (`29a5419..af7b014`, excluding pure-data eval results).
  Two independent angles converged on the same real, reproduced bug (receipt validator deadlock
  on a resumed session's superseded simplify entry) — fixed. Three more real findings fixed
  (missing adoption-checker coverage of the finishing gate, a missing PYTESTS registration, two
  whole-suite Verify rows over the 60s CI cap). One finding (finishing gate's tiny-lane exemption
  ignoring the actual diff-size signal) required a human decision — `ESCALATIONS.md` E002,
  decided and fixed. Full detail in `### Deviations` above.
- Round 2 (receipt-refresh chain, package at `ed77172`). **Coverage is partial and this is
  deliberate, not a pass:** of the six FIND angles, `removed-behavior`, `prior-art`, and
  `enclosing-function` reported; `call-site-impact`, `stack-defects`, and `guard-completeness`
  did not — the first dispatch died on a session usage limit and the re-dispatch was stopped by
  the user. Per `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md` a
  non-reporting angle is *unknown*, never clean; those three angles remain owed on this range.
  - **Fixed — real bug, `ed77172`:** `removed-behavior` found the round-2 staleness exemption
    inherited `classify_path`'s case folding. On a case-sensitive filesystem a post-review commit
    of `Specs/payload.py` or `evals/Raw/tool.py` (distinct directories) classified
    receipt-neutral and shipped unreviewed, where the replaced byte-exact `startswith("specs/")`
    guard had staled it. `_carries_reviewable_surface` now corroborates the exact-case spelling
    after the category match; two tests pin both directions.
  - **Fixed — doc drift:** the module docstring said the neutral eval paths were
    "results/transcripts" while `_EVAL_OUTPUT_PARTS` also grants `result`/`raw`; docstring now
    names all four. `.gitignore`'s `.harness-state/` anchored to `/.harness-state/`.
  - **Advisory, recorded, no action:**
    - The `evaluation` exemption is path-shape-based, so a post-review commit that *edits*
      stored eval JSON (not just re-collects it) rides the existing receipt. Deliberate in
      `a2e34c9`; the per-path rule still stales any code riding along
      (`test_eval_evidence_plus_code_advance_still_stale`).
    - `simplify-stage.md` step 6 enumerates delta-review rejections but not the
      reviewer-returns-nothing case, and the receipt schema still has no `independent` field —
      the guardrail proposed by `no-report-reviewer-dispatch-is-not-a-pass.md` is unimplemented
      repo-wide (not a regression of this branch). Bounded `--delta-verdict` vocabularies mean
      silence cannot serialize as a pass without a controller fabricating a verdict.
    - `task_brief.py`'s missing-`--task` exit code moved 2 → 1 (argparse usage error → explicit
      XOR `SystemExit`). Still fails closed; no caller branches on the code.
    - `check_simplify_adoption.py`'s load-once passes `None` through on load failure, so the
      per-check fallback retries; harmless (both retries also return `None`) and the fallback is
      what lets the tests call each check directly.
  - **Carry-over to the base branch, not this range:** `prior-art` flagged worktree-side
    `Lane:`/`status:` reads in `hooks/lib/lane.sh` as a policy-TOCTOU contradicting
    `docs/solutions/harness/gate-config-must-read-index.md`. That file arrived in `75dcc9f` on
    `feat/superpowers-6-review-pipeline` (PR #183), this branch's base — the finder diffed
    against `main`, which spans both. Real finding, wrong branch; it belongs to PR #183.
- Round 3 (2026-08-04/05, range `29a5419..8bfacc1`) — **the three angles round 2 left owed**
  (`call-site-impact`, `stack-defects`, `guard-completeness`) were run and are no longer owed.

  The bulk of the pass covered `29a5419..f62fcc0`. Three commits (`c1dafb5`, `1385496`, `8bfacc1`
  — +25/-2, eval tooling and test-harness portability) landed after that, two of them while the
  pass was running, so the range was re-checked to `8bfacc1` before this was written. Nothing in
  that delta is a defect: `_run` sets `capture_output=True, text=True`, so the widened
  `CollectionError` interpolation cannot hit `None.strip()`; `shutil`/`sys`/`pytest` are all
  imported at module level, so the new non-darwin `pytest.skip` guard in `invoke()` cannot
  `NameError` on Linux despite `sys.platform != "darwin"` short-circuiting past `shutil.which`
  on the machine where it was tested.

  The round-3 fixes landed as `a0ccb63` (E003 deploy contract), `dda9b2d` (exact-case authorities),
  and `57650be` (NUL-delimited changed paths). Three further eval-harness commits — `b2d6816`,
  `46b6765`, `d01af39` — landed alongside them from concurrent work and are **outside** the
  reviewed range; they are not covered by this pass.

  **Independence caveat, recorded because it changes how much this pass is worth.** The subagent
  dispatch channel failed: two `reviewer` agents spawned and went idle in ~7s without returning any
  findings text (three times, including after a direct request), and every further spawn failed with
  `fork failed: Device not configured`. The angles were therefore run by the controller thread,
  which had already read this SUMMARY and the PR body — so this pass is **not plan-blind and not
  context-independent**. Every finding below carries a re-runnable reproduction so the claim does
  not rest on that pass's judgment; the independence property itself is simply absent. Per
  `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md`, the silent agents
  contributed nothing and are not counted.

  - **Fixed — P1, `guard-completeness`:** the round-2 exact-case repair landed on
    `_carries_reviewable_surface` (the staleness exemption) but not on `_simplify_required` (the
    requirement trigger), and `classify_path` itself still folded case. Real source under `Docs/`,
    `Specs/`, or `Evals/Raw/` — different directories on a case-sensitive filesystem — answered
    "no reviewable path", so `--require-simplify-if` exited 0 against a receipt with an empty
    `reviews` list and the required stage was skipped entirely. Reproduced end-to-end in a
    throwaway repo. Fixed at the root: `classify_path` now matches **directory authorities**
    exact-case while file names and suffixes keep folding case (`README`, `.MD`, `PLAN.html` are
    the same file however spelled). This also closes the same hole in `evaluate_policy`, the
    standalone checker. The in-code comment claiming case folding was "fine for the simplify
    policy, whose lenient direction merely skips a cleanup" was true before `f1a9e8f` and stale
    after it — that commit made the lenient direction skip a push-blocking gate.
    `rules/simplify-stage.md` now states the rule; 16 parametrized cases pin both directions, and
    the e2e test fails on the pre-fix code.
  - **Fixed — P2, `stack-defects`:** `_changed_files` ran `git diff --name-only` without `-z`, so
    Git's default `core.quotePath` quoted any non-ASCII path (`"src/caf\303\251.py"`).
    `classify_path` rejects the backslash spelling, so `_simplify_required` returned `None` and the
    gate failed closed with `stale-sha: cannot diff simplify base ... — re-check with a valid base
    ref`: a branch containing one non-ASCII filename became unpushable, with a message blaming the
    base ref, and no base ref could fix it. Now `-z` with NUL-delimited parsing. Fail-closed
    throughout, so this was lost work rather than a bypass.
  - **Fixed — P2, `guard-completeness`:** `scripts/check_simplify_adoption.py` — SC-10's whole
    drift guard — was **never invoked**. `run-tests.sh` ran `check_manifest.py`,
    `check_gate_modes_smoke.py`, and `check_slim_surface.py`; CI runs only `run-tests.sh`; only the
    checker's *own* unit tests ran, and those build synthetic roots that never look at this
    repository. A `MINIMUM_VERSION` bump without the matching `rules/simplify-stage.md` edit would
    have shipped green. Now wired into `run-tests.sh` with a paired mutation check.

    Wiring it surfaced a second problem and changed the fix: check G (deployed parity) compares
    against `.claude/`, which is untracked local state, so the shared suite failed on any source
    edit made before a re-sync — while CI, having no mirror, never enforced it at all. The suite
    now runs checks A–F via a new `--skip-deployed-parity` flag; a bare manual invocation keeps
    check G. This is the one place the fix went beyond restoring the intended behavior, and it is
    a deliberate narrowing, not an oversight.
  - **Advisory, recorded, no action:**
    - `simplify_record.py:251` catches only `SimplifyRecordError`, so a `--begin-state` path that is
      missing, malformed JSON, or missing a key escapes as `OSError` / `JSONDecodeError` /
      `KeyError` — a traceback instead of the clean `simplify-record: <error>` line. Exit stays
      nonzero, so it fails closed; cosmetic only.
    - ~~`run_simplify_stage_eval.py:753` (from `1385496`) interpolates up to 400 chars of the
      sandboxed client's stderr and 200 of its stdout into the auth-preflight `CollectionError`,
      which can be captured into stored eval evidence — unbounded third-party text this repo does
      not control.~~ **Moot:** `d01af39` reverted that diagnostic (to restore the eval digest, for
      unrelated reasons); the message is back to `returncode` only. Recorded because the concern
      applies again if the diagnostic is ever reinstated.
    - `check_simplify_adoption.py:48` `exec_module`s the checked root's own
      `check_claude_simplify.py`, writing `__pycache__` into that tree. An edit that preserves byte
      size within the same mtime second is then served from stale bytecode — observed live: the
      `2.1.154` → `2.1.999` mutation reported `consistent` until `__pycache__` was removed. This
      one fails **open**, but cannot fire in CI (fresh checkout, no cache) and needs an
      equal-length same-second edit locally.
  - **Fixed after escalation — P1, `call-site-impact`, `ESCALATIONS.md` E003 (decision A):**
    `simplify_record.py` resolves `check_review_receipt.py` through `parents[3]/scripts/`, but
    `deploy-harness.sh` mirrored only `skills|agents|hooks|rules|templates|runtime`, so a deployed
    copy looked for a `.claude/scripts/` that never exists and died at import with
    `FileNotFoundError` before argparse — in any consuming repo the required stage could not
    record evidence at all. Rule 4, so it went to the human: decision A adds `scripts/` to
    `SYNCED_DIRS_RE`, the deploy loop, and the installer `PAYLOAD`. That also makes
    `scripts/check_review_receipt.py` reachable, so the finishing gate itself is runnable in a
    consuming repo for the first time. The installer's legacy-root scan was split onto its own
    list in the same change, or every project owning a `scripts/` dir would have been told to
    delete it. Full rationale, the prune-safety argument, and the distribution-contract scope note
    are in E003.

### Intent Review

- Round 2 (receipt-refresh chain, package at `491c396`, plan-blind, read-only). Verdict:
  **PASS** — no Critical or Important finding against the verbatim request on any axis.
  - **Missing** — none above advisory. The request's research/advisory half (*có đúng ko / có
    hợp lý ko / có đáng làm ko*) is answered durably in `research-brief.md` §8 and `design.md`
    §9. Advisory, already self-disclosed: §9's explicit cost statement was added during round-1
    intent review, i.e. after the bulk of implementation, not before the user authorized it.
  - **Drift** — both interpretive forks judged defensible *and* disclosed: bundled `/simplify`
    rather than a repo skill of that name (rejected alternative recorded at `### Alternatives
    considered`; the no-shadowing rule is enforced in `rules/simplify-stage.md`), and "require"
    becoming lane/size-conditional (the research's own conclusion that universal invocation is
    not justified — narrowing answers the question asked rather than dodging it).
  - **Excess** — Important but plan-scoped and traceable: ~3.9k lines of enforcement core
    against ~21k lines of surrounding evidence apparatus, of which stored eval results are
    524 files / ~16.9k lines. The shadow eval was the authorized precondition for enabling the
    gate, so the bulk is in scope. Thin spot, recorded as advisory: ~6.7k of those insertions
    are superseded or infrastructure-rejected runs (expired-OAuth transcripts, sandbox EPERM
    partials, pre-commit superseded generations) preserved under this branch's own
    `evals/.../README.md` "preserve rejected first runs" policy. The reviewer proposed pruning
    the infrastructure-failure artifacts and keeping `baseline/`, `candidate/`, the accepted
    round-3/4 pair and `comparison.md`. Not applied here — deleting stored evidence is a
    deliberate call for the branch owner, not a review-cycle cleanup.
  - Reviewer also independently surfaced the partial round-2 correctness coverage recorded
    above and left the ship/no-ship call to the orchestrator.

- Round 1 — independently reviewed blind to `PLAN.md`/`research-brief.md` (Opus, ensemble diversity from
  the Sonnet implementer), against the verbatim `### Intent` quote above plus the PLAN §3 SC
  table and this file's own `### Verify` table. Verdict: CHANGES REQUESTED, then addressed:
  - **Fixed**: the adoption checker's deployed-parity check had gone stale (more commits landed
    after the last `deploy-harness.sh` run, without a re-deploy) — re-deployed, re-verified SC-10
    passes at the true final HEAD (`### Verify` row updated).
  - **Fixed**: `## What changed` and `### Harness-Delta` still carried pre-implementation
    "proposed" / "no runtime behavior changed" language from before Wave 1 — rewritten to
    describe what's actually shipped, and to durably record the continue-to-implementation
    authorization (the verbatim `### Intent` above captures only the original planning request,
    not the later "continue implementation... until completion" instruction that started the
    implementation session, nor the two explicit mid-implementation decisions in
    `ESCALATIONS.md` E001/E002).
  - **Fixed**: four new test files (`test_check_simplify_adoption.py`,
    `test_run_simplify_stage_eval.py`, `test_score_simplify_stage_eval.py`, `test_task_brief.py`)
    and the extended `risk-corroboration.test.sh` were only attested in prose — added explicit
    per-file `### Verify` rows (each well under the 60s cap).
  - **Recorded as advisory, already addressed at design time, no further action** (per the
    intent-review skill's own routing: advisory drift/excess goes here, not to a new
    escalation):
    - The literal "require skill simplify" was interpreted as Claude Code's *bundled* skill, not
      a new repository skill named `simplify` — the single largest interpretive fork in this
      diff. Already disclosed and reasoned in `### Alternatives considered` above and
      `design.md` §1/§8 (never creating a shadowing local skill was itself an explicit
      non-goal from intake).
    - "Require" became conditional on a 150-line tiny-lane threshold and several non-code
      exclusions, rather than an unconditional requirement — disclosed in
      `### Alternatives considered` ("Require it for every branch — rejected for tiny and
      non-code changes") and `rules/simplify-stage.md`'s signal-policy table.
    - The `type: simplify` receipt entry's `changed_files`/`post_sha` were extended across
      several post-simplify correctness-review fix commits rather than staying scoped to only
      the original `/simplify` mutation commit (`e90413b`) — intentional per `design.md` §6
      ("a final reviewer change re-runs the affected review and refreshes the receipt") and the
      receipt validator's own freshness contract (`post_sha == reviewed_head_sha`); the delta
      review's spec/quality verdict covers the full extended range, not just the original
      mutation.
    - `specs/STATE.md`'s active-spec pointer and this slug's durable-run tracking were not
      updated during this session — `specs/STATE.md` is explicitly a user-owned file this
      session was instructed to preserve untouched throughout (see `HANDOFF.md`), and no
      durable-run (`RUN.json`) was ever initialized for this slug to begin with, so there is
      nothing to reconcile.
  - The intent-review's own "worth doing" question (`có đáng làm ko?`) noted no artifact stated
    the cost side explicitly (diff size, new vendor version dependency, ongoing per-branch
    invocation cost) — added a `design.md` "Assessment" section stating it, alongside the
    benefit the shadow-eval's ACCEPT verdict already demonstrated.

### Rollback

- Whole feature: `git revert --no-commit 29a5419..<final-HEAD> && git commit` (revert range against the
  branch's actual base, `feat/superpowers-6-review-pipeline` at `29a5419` — never `main`, which has
  229 unrelated commits ahead of this branch's true fork point).
- Sandbox-only rollback (keep the harness policy/receipt/SDD wiring, drop only the eval-harness
  sandbox widening): `git revert <f5ecf89> <50e3470>` — reverts the `/tmp/claude-<uid>` and
  git-common-dir/safe-devices sandbox exceptions (`specs/require-claude-simplify-gate/ESCALATIONS.md`
  E001) without touching the required-gate machinery itself.
- Hard-gate-only rollback (keep the shadow-eval evidence, drop enforcement): revert `cba0b71`,
  `f1a9e8f`, `6ac6d65`, `0611dbb`, `c8b7840` — removes `simplify_record.py`, the
  `--require-simplify-if` receipt/finishing gates, the SDD wiring, and the doc/manifest/hook sync,
  leaving the accepted shadow-eval result as a standalone research artifact.
- After a push: prefer `git revert` over history rewriting; never force-push over `origin/main` or
  this branch once shared.

### Harness-Delta

- shipped — a capability-pinned, signal-gated `/simplify` cleanup stage is now required before
  push (subject to policy) without weakening existing final oracles; see SC-1..SC-10 for the
  proof and `evals/skills/simplify-stage/results/comparison.md` for the shadow-eval evidence that
  justified enabling the hard gate.
