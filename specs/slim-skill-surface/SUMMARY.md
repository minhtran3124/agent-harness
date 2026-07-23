# slim-skill-surface — Summary

Lane: high-risk
Confidence: high
Reason: the diff edits and deletes `skills/*/SKILL.md` — the `workflow-engine` hard gate (workflow-as-code: instruction delivery, routing, review gates) — and removes three registered skills from `harness-manifest.json`.
Flags: workflow-engine, existing-behavior
Affects: skill registry (harness-manifest.json ↔ skills/ ↔ skills/README.md) and the execution-path routing documented in CLAUDE.md / rules
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> vì model ngày càng thông minh (nhất là vs repo đang hoạt động vs claude code). hãy review lại cẩn thận những phần nào chúng ta đang làm bị thừa, ko cần thiết, làm quá mức
>
> hay doc ky tung skill (bo qua visual-planner - toi muon giu no lai) de hieu ro hon ve tung skill, truong hop su dung, cach su dung, ... sau do moi viet spec
>
> viet spec cho muc 1-6 truoc

Items 1–6 of the post-read cut list, verbatim as delivered:

1. Xoá visual companion của brainstorming (giữ HARD-GATE) — 1.084 dòng
2. `using-git-worktrees` → ~60 dòng — 255 dòng
3. `subagent-driven-development` bỏ boilerplate + DOT — 265 dòng
4. Gộp `executing-plans` vào subagent-driven — 126 dòng
5. `brainstorming` bỏ DOT + Key Principles — 82 dòng
6. Gộp `create-pr` vào finishing; xoá `review-diff` — 135 dòng

Explicitly out of scope by the user's instruction: `visual-planner` ("toi muon giu no lai").

## What changed

Net **−1.700 lines** across 23 files (345 insertions, 2.045 deletions). The registered skill
count went 15 → 12, and `SKILL.md` text (excluding `visual-planner`, retained) went 2.817 → 2.065
lines (−27%).

| Change | Before | After |
|---|---:|---:|
| `skills/brainstorming/scripts/` + `visual-companion.md` (incl. a hand-written RFC 6455 WebSocket server) | 1.085 | **deleted** |
| `skills/using-git-worktrees/SKILL.md` | 315 | 74 |
| `skills/subagent-driven-development/SKILL.md` (absorbed `executing-plans`) | 484 | 292 |
| `skills/brainstorming/SKILL.md` | 172 | 108 |
| `skills/executing-plans/` · `review-diff/` · `create-pr/` | 276 | **deleted** (create-pr's template inlined into `finishing`, ~30 lines) |
| Skills carrying >20% boilerplate | 4 | **0** |

No gate was removed. Every constraint that lived only inside a deleted `Red Flags` section was
moved into the section that owns it, and SC-5/SC-6/SC-7 pin three of them mechanically.

**Plus one out-of-original-scope fix (Task 5.1, user-authorised).** A 52-check sandbox walk — a
fresh consumer install, an old-consumer re-sync + prune, the hook chain, and a full workflow run
from intake to the push gate — found that a **fresh consumer could not commit at all**:
`check-untracked-py.sh` excluded the deployed harness with `grep -v '/\.claude/'`, which needs a
leading slash and so misses the root-level `.claude/skills/...` paths `git ls-files` returns, and
`install-harness.sh` never gitignored the derived tree. Both fixed, both pre-existing, both
pinned by a new mutation-checked test. The existing hook suite only covered a *nested*
`app/.claude/` — the exact case the broken pattern handled — which is why it survived.

### Rationale

Measured across the 14 non-visual-planner skills: 463 of 2.817 lines are boilerplate written
to persuade or hand-hold a weaker model (`Advantages`, `Example Workflow`, `Red Flags`,
`Quick Reference`, DOT process graphs), and the distribution is extreme — 54% of
`subagent-driven-development`, 48% of `brainstorming`, and **0% across eight newer skills**.
The repo already learned this lesson; the older skills were never updated. Separately,
`skills/brainstorming/scripts/` carries 1.084 lines including a hand-written RFC 6455
WebSocket server to show mockups in a browser — a capability Artifacts now provide natively.
Cutting is scoped to duplication and dead weight: every review oracle, `feature-intake`, and
`evals/` stay untouched because reading them showed each is backed by measured evidence.

### Alternatives considered

- **Cut the three review skills** (`correctness-review` / `intent-review` /
  `context-propagation-audit`) as redundant with native `/code-review` — **rejected after
  reading them.** They are three mutually-blind oracles, and `correctness-review` records a
  measured experiment (`evals/skills/review-chain/results/2026-07-13-code-review-swap.md`)
  where swapping in `/code-review` matched recall but produced 3 false positives against a
  baseline of 0 at 10–15× the tokens.
- **Delete `evals/`** as maintenance overhead — **rejected**: its 7 result files drove real
  deletions (FIND-B removed, swap rejected, threshold set to 75). It is the most
  evidence-grounded part of the repo.
- **Delete `xia2`'s depth classifier** (it duplicates `feature-intake`'s lane over 5 of 9
  identical signals) — **deferred** to a follow-on spec; it requires re-running
  `skills/xia2/tests/structural/` and is medium-risk, unlike items 1–6.
- **Keep `executing-plans` as a separate skill** — rejected: its distinguishing feature is
  "a separate session", which is not a property of the skill but of how it is invoked.

### Deviations

- **Scope widened, user-authorised.** The plan's non-goals said "no hook, script, or CI gate
  changes". The sandbox walk then proved a fresh consumer **cannot commit at all** after
  installing the harness, and the user authorised fixing it on this branch. Added Task 5.1:
  `hooks/check-untracked-py.sh` (anchor the `.claude/` exclusion) and
  `scripts/install-harness.sh` (gitignore the derived tree), each with a mutation-checked test.
  Both bugs are pre-existing — the hook pattern is identical at the branch point `f97764e` and
  in the repo's initial commit.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| browser companion retired | `test ! -e skills/brainstorming/scripts` | 0 | 1.085 lines removed incl. server.js | SC-1 |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | no linted doc references a retired skill | SC-2 |
| registry ↔ disk ↔ settings.json | `python3 scripts/check_manifest.py` | 0 | skills[] 15 → 12, bidirectional | SC-3 |
| three skills retired, both halves | `python3 scripts/check_slim_surface.py` | 0 | guards against a half-revert | SC-4 |
| receipt ship gate survived the trim | `grep -q check_review_receipt skills/subagent-driven-development/SKILL.md` | 0 | moved, not deleted | SC-5 |
| worktree harness-deploy step survived | `grep -q "deploy-harness.sh --target" skills/using-git-worktrees/SKILL.md` | 0 | without it a worktree has no .claude/ | SC-6 |
| parallel-session path survived the merge | `grep -qi "parallel session" skills/subagent-driven-development/SKILL.md` | 0 | absorbed from executing-plans | SC-7 |
| deploy prunes the retired skills | `bash scripts/deploy-harness.sh --dry-run` | 0 | reports all three as "would prune stale ... (removed from source)" | |
| root-level .claude/ no longer denies a commit | `bash tests/hooks/check-untracked-py.test.sh` | 0 | 7 cases; reverting the anchor fails the new one | SC-8 |
| fresh install gitignores the derived tree | `bash tests/scripts/install-gitignore.test.sh` | 0 | 7 cases incl. re-install, pre-existing entry, missing trailing newline | SC-9 |

The full harness suite (`scripts/run-tests.sh` — L1 syntax + doc-truth + manifest + verify-row
lint, L2 hook contract tests, L3 script integration tests, 185 python unit tests) was run after
wave 3 and reported **ALL GREEN**. It is cited here rather than tabled because a whole-suite
invocation exceeds the strict gate's 60s per-command cap
(`docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`); CI's `tests` job runs it.

### Review Findings

Three oracles run 2026-07-23 on `f97764e..226fc6b` as isolated `reviewer` subagents (read-only by
tool whitelist, models different from the implementer).

- **`/intent-review`** (blind to PLAN/design) — **PASS**, no gap / excess / drift. It flagged in
  passing that `harness-manifest.json` had changed 139 lines for a 3-line edit; verified and
  fixed — a `json.dumps` round-trip had escaped em-dashes to `\u2014` and reflowed the file.
  Nothing mechanical caught it (valid JSON, checker green): a diff-reading oracle did.
- **`/context-propagation-audit`** — **PASS**, 14 matrix rows, no failing delivery. Confirmed all
  four constraints that lived only in the deleted `## Red Flags` reach the isolated contexts that
  rely on them, and that the rewritten "loaded via the explicit Read step in X" sentences in
  `rules/plan-format.md` / `rules/wave-parallelism.md` are now true of the named skill.
- **`/correctness-review`** (3 angles: `removed-behavior`, `stack-defects`+`enclosing-function`
  +`guard-completeness`, `call-site`+`prior-art`) — **8 findings, all fixed**, each reproduced by
  the reviewer before reporting:

| # | Finding | Sev | Fix |
|---|---|---|---|
| 1 | Installer would ignore a `.claude/` the consumer **tracks**, hiding the ~90 files the deploy just wrote | P1 | Detect tracked `.claude/`; warn and leave `.gitignore` alone |
| 2 | Guard missed `.claude/*` + `!.claude/settings.json`; appending `.claude/` makes the negation unreachable | P2 | Widened match to any `.claude`-bearing line → skip |
| 3 | Unwritable `.gitignore` aborted the installer **after** the deploy, swallowing the success banner | P2 | Bounded the whole block; warns instead |
| 4 | `using-git-worktrees` kept the gitignore *check* but lost its *remediation* branch — repro: `git add -A` commits the worktree as an embedded gitlink | P2 | Restored "add the pattern, commit it, then create" |
| 5 | Same skill lost the directory-selection priority (existing dir / CLAUDE.md / ask) | P3 | Restored as one numbered step |
| 6 | `executing-plans`' "review the plan critically before starting" never reached the merged skill | P3 | Added to Step 0, before `status: active` |
| 7 | `check_slim_surface.py` was invoked by nothing — the half-revert guard could not fire | P3 | Wired into `run-tests.sh` beside `check_manifest.py` |
| 8 | Two install tests consulted the machine's global `core.excludesFile`, so they passed with the fix deleted | P3 | Pinned `-c core.excludesFile=/dev/null`; added 4 regression cases |

Findings 1–3 and 8 are defects in *this branch's own* hook/installer fix — the sandbox proved the
original bug was gone but not that the fix was safe. Every new guard is mutation-checked: reverting
the tracked-`.claude` detection fails case 8, and narrowing the pattern back fails cases 9–10.

### Rollback

- `git revert <sha>` — the change is source-only (skills, docs, manifest); no migration and no
  deployed state beyond `.claude/`, which `scripts/deploy-harness.sh` re-derives from source
  and whose per-deploy manifest prunes the deleted skills. To restore one deleted skill without
  reverting the whole change: `git checkout <sha>^ -- skills/<name>/` then re-add its entry to
  `harness-manifest.json`.

### Harness-Delta

- backlog — two structural signals worth compounding: (a) newer skills carry 0% boilerplate
  while older ones carry ~50%, so skill age predicts bloat better than skill purpose;
  (b) a per-skill capability that duplicates a native harness feature (worktree tool,
  Artifacts) survives because the skill text says "prefer the native tool" instead of
  deleting the fallback. → `/compound`.
