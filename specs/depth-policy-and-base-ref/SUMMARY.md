# depth-policy-and-base-ref — Summary

Lane: high-risk
Confidence: high
Reason: `rules/research-depth.md` trips the `workflow-engine` manifest hard gate (warn-mode at commit time, but intake still classifies it high-risk per harness-manifest.json); 4 flags fired.
Flags: existing-behavior, weak-proof, cross-platform, multi-domain
Affects: research-depth policy (xia2 consumer contract); run-tests.sh base-ref resolution (verify-row lint scope)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> we have some notes to improve harness now [screenshot: Gap A citation ledger / Gap B
> negative-scope / Gap C 3-tier principle]
> - make the deep research codebase again, thinking by yourself about it for design/adopt/etc
> - and let me know it is correct or not?
> - should we do it or not?
> - how we adopt it?
> - give high level design/spec
> - have any side effect if we apply it? do have anything will broken if we apply it?

> mục đích của check_research_brief.py là gì?

> lập bảng so sánh độ sâu, độ phức tạp, mức độ ảnh hưởng, khả năng hỏng hóc

> làm cả hai trong một branch

Scope resolved by two explicit human decisions at intake (`AskUserQuestion`):

1. **Policy variant** — "Có điều kiện": external sources required only when the change has an
   external surface; absence must be *stated*, not implied. (Rejected: drop the requirement
   entirely; keep it unconditional and only add a `- none` escape.)
2. **Base-ref variant** — "Fallback chain + sửa CI": fix all three causes, including
   `fetch-depth: 0` on the CI `test` job. (Rejected: local-only fix; fail-loud variant.)

## What changed

Two independent corrections shipped together because both stem from the same defect class —
a rule that asserts something no one checks.

1. `rules/research-depth.md` + `skills/xia2/SKILL.md` +
   `skills/xia2/references/research-brief-template.md` — Standard/Deep no longer demand external
   documentation unconditionally. External sources are required **when the change has an external
   surface** (new/upgraded dependency, external integration, version-specific API). When none
   exists, the brief must record `- none (local-only; no external surface)` in Source Pack —
   silence is no longer an acceptable answer. All three files are updated together: xia2 agents
   read `SKILL.md` and fill the template, so a rule-only edit would have changed nothing that any
   consumer context actually sees.
2. `scripts/resolve-base-ref.sh` (new) + `tests/scripts/resolve-base-ref.test.sh` (new) +
   `scripts/run-tests.sh` + `.github/workflows/harness-ci.yml` — the verify-row lint resolved
   its base ref from a hardcoded `origin/main` that resolves **nowhere**: not locally (this
   repo's remote is `github`, there is no `origin`), and not in CI (the `test` job used a
   shallow `actions/checkout@v4`). The lint has therefore never executed since it shipped.
   Resolution now comes from declared bases only — `VERIFY_ROWS_BASE`, then `GITHUB_BASE_REF`
   (as `origin/<ref>`), then the branch's `@{upstream}` — and an undeclared or unresolvable
   base exits nonzero with a named reason instead of falling back to a guess. On CI, the `test`
   job gains `fetch-depth: 0` plus an explicit `git fetch --no-tags origin <base_ref>` — the same
   two-step the `strict-gate` job already uses and which is proven to work in this repo's CI,
   rather than relying on whatever refspec `actions/checkout` happens to leave behind.
   `scripts/ci-strict-gate.sh` gets the same treatment for its local default: it used to fall
   back to `origin/main`, where a failed `git diff` yields an empty diff and the *strict* gate
   exits 0 having checked nothing. It now refuses with a named reason instead.

### Rationale

Both changes close the same gap from opposite ends. The depth policy demanded evidence that
13 of 21 briefs never supplied (12 of them citing zero external sources while declaring
Standard/Deep) — an unenforceable requirement that trains readers to ignore the field. The
verify-row lint claimed to enforce evidence quality and silently skipped 100% of the time.
Rather than add a new gate on top of an unhonored policy (the `sources.json` + `quote ⊆
evidence` proposal in the intake notes), scope the policy to what is actually checkable and
repair the check that already exists.

### Alternatives considered

- **`specs/<slug>/sources.json` ledger + `quote ⊆ evidence` script** (the note's proposal) —
  rejected. The evidence side of that comparison is written by the same agent that writes the
  quote, so a hallucinated document yields a matching hallucinated snippet and the gate passes.
  It would be traceability tier claiming provenance — the exact failure `CLAUDE.md` "Gate
  verifiability" forbids. It also drags the diff into `hooks/` (block tier in
  `ci-strict-gate.sh`) and trips `check_gate_modes_smoke.py`'s hardcoded `EXPECTED_WARN` set.
- **Transcript cross-check** (assert every Source Pack URL was really fetched via `WebFetch`) —
  the only design that reaches provenance tier, since the agent does not author the transcript.
  Rejected on economics: ~400 fragile lines for a 1-in-21 failure rate, and it breaks under this
  repo's `resume <slug>` flow where the originating transcript is gone.
- **`scripts/check_research_brief.py`** (enforce the Source Pack contract, warn-first) —
  deferred, not rejected. Worth reconsidering only after the corrected policy has run long
  enough to show how often `Deep` legitimately implies an external surface.
- **Gap B / Gap C from the notes** — no work done: both are already shipped
  (`templates/SUMMARY.template.md:75` + `verify_summary.py:250-305` for B;
  `CLAUDE.md:63-67` for C). Building them again would produce an empty diff.

### Deviations

- Rule 2 — Extracted the base-ref resolution into `scripts/resolve-base-ref.sh` and added
  `tests/scripts/resolve-base-ref.test.sh` (8 cases). Not in the intake scope, which said
  "fix the base ref in `run-tests.sh`". Justification: the defect being fixed is a *scope
  selector that died silently*; logic inline in a 100-line suite runner cannot be unit-tested,
  so an inline fix would be as unprotected against silent death as the code it replaces. Two
  of the eight cases are regression guards for the exact original failures.
- Rule 1 — Rejected the branch-name fallback chain (`origin/main` → `github/main` → `main`)
  that was approved at intake, after measuring it: on this branch it selects `main`, yielding
  36 changed spec files instead of 0 and surfacing 7 pre-existing violations in already-shipped
  specs — i.e. the approved variant would have turned CI red for work this branch never
  touched. Replaced with declared-bases-only + loud refusal. Same goal (the lint stops being
  dead), corrected mechanism.

### Verify

The full suite (`scripts/run-tests.sh`) is exercised by the CI `tests` job on both
ubuntu-latest and macos-latest; it is cited in prose rather than as a row because it
exceeds the 60s strict-gate cap. The targeted rows below are the ones re-run here.

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Base-ref resolution, 8 cases incl. the two regression guards | `bash tests/scripts/resolve-base-ref.test.sh` | 0 | covers shallow-CI absent ref + refusal to guess a branch name | |
| This SUMMARY passes the lint this branch re-enables | `python3 scripts/check_verify_rows.py specs/depth-policy-and-base-ref/SUMMARY.md` | 0 | dogfood: the check caught 3 violations in this file's first draft | |
| Base ref resolves for this branch's real base | `VERIFY_ROWS_BASE=simplify bash scripts/resolve-base-ref.sh` | 0 | prints `simplify` | |
| Resolution refuses to guess when nothing is declared | `bash tests/scripts/resolve-base-ref.test.sh` | 0 | case 6 — `main` exists and is still refused | |
| Doc-truth lint (paths named in the new files exist) | `bash scripts/lint-doc-truth.sh` | 0 | | |
| Shell syntax of both changed/added scripts | `bash -n scripts/run-tests.sh` | 0 | | |
| Shell syntax of the new resolver | `bash -n scripts/resolve-base-ref.sh` | 0 | | |
| Shell syntax of the strict gate | `bash -n scripts/ci-strict-gate.sh` | 0 | | |
| Strict gate still runs with an explicit base (the CI path) | `bash scripts/ci-strict-gate.sh simplify` | 0 | 17 contract tests also pass | |
| Depth rule reached the xia2 consumer context | `grep -q "external surface" skills/xia2/SKILL.md` | 0 | rule-only edit would reach no agent | |
| Depth rule reached the brief template | `grep -q "external surface" skills/xia2/references/research-brief-template.md` | 0 | | |
| xia2/brainstorming/doc-truth contract tests | `bash tests/scripts/brainstorming-contract.test.sh` | 0 | | |
| Doc-truth contract tests | `bash tests/scripts/lint-doc-truth.test.sh` | 0 | 7 passed | |
| CI workflow parses and the base-ref fetch step is present in the `test` job | `python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/harness-ci.yml')); assert any(s.get('name','').startswith('Fetch base ref') for s in d['jobs']['test']['steps'])"` | 0 | | |
| Strict-gate contract tests | `bash tests/scripts/ci-strict-gate.test.sh` | 0 | 17 passed | |

### Not auto-verified

- **The corrected depth policy is livable** — reached traceability; this branch's own
  `research-brief.md` records `- none (local-only; no external surface)` as a dogfood, but one
  brief does not prove the rule scales across future work.
- **`fetch-depth: 0` makes the lint fire in CI** — reached traceability at commit time (the YAML
  is valid, and case 3 of the resolver test simulates the `origin/<base>` ref that
  `actions/checkout` is expected to create); truth-tier confirmation requires the CI run on
  this PR, which cannot execute before the commit exists. Specifically unproven: that
  `actions/checkout@v4` with `fetch-depth: 0` populates `refs/remotes/origin/<base_ref>` — the
  test *stubs* that ref rather than observing the action produce it.
- **The lint now selects this branch's own changed files and no others** — reached truth for
  the local case (`VERIFY_ROWS_BASE=simplify` selects exactly this spec's SUMMARY, re-run
  above); reached traceability for the CI case, which depends on the unproven claim above.
- **No other gate depends on the hardcoded `origin/main`** — reached provenance; re-derived by
  grepping `scripts/ hooks/ .github/` for `origin/main`, which returned only `run-tests.sh` and
  `ci-strict-gate.sh` (the latter always receives an explicit base from CI, so its default is
  local-only convenience). Not re-run as an assertion in code.
- **Retiring the unconditional external-source requirement loses no real signal** — reached
  traceability; based on 19/21 briefs citing zero URLs, which measures past behavior, not
  whether that behavior was correct.

### Rollback

Graded, because the two halves fail independently. The live risk is half 2: a lint that has
never executed now executes, so it can block work that previously sailed through.

1. **Full undo** — `git revert <sha>`. Restores the hardcoded `origin/main` (lint dead again),
   the unconditional depth policy in all three files, and removes `scripts/resolve-base-ref.sh`
   + `tests/scripts/resolve-base-ref.test.sh`. No migration, no state, no consumer artifact is
   written by this change, so revert is complete.
2. **Neutralize the lint only, keep the policy fix** —
   `git checkout <sha>^ -- scripts/run-tests.sh` then commit. The runner returns to skipping;
   the resolver and its tests stay on disk unused; `rules/research-depth.md` and the xia2 files
   keep the corrected Coverage rule.
3. **Neutralize in CI only** — delete the `with: fetch-depth: 0` block from the `test` job in
   `.github/workflows/harness-ci.yml`. The lint then skips in CI with a named reason
   (`base ref 'origin/<base>' ... does not resolve`) while still running locally for anyone who
   sets `VERIFY_ROWS_BASE` or a branch upstream.
4. **Un-block a single run without changing code** — `VERIFY_ROWS_BASE=HEAD bash scripts/run-tests.sh`
   narrows the changed-set to uncommitted spec edits only; on a clean tree that is empty and the
   lint reports "no changed SUMMARY.md/PLAN.md" instead of failing. Verified: with this branch's
   SUMMARY staged but uncommitted it still selects 1 file, so this is a narrowing escape hatch
   for an urgent run, not a guaranteed bypass, and not a fix.

### Harness-Delta

- fix-direct — a gate can ship with tests, CI wiring, and a careful rationale comment and still
  never execute, because its *scope selector* (not its logic) is dead. Nothing in the suite
  reports "this check selected zero files, every time." Candidate for `/compound`: a gate that
  skips should be distinguishable from a gate that passes.
