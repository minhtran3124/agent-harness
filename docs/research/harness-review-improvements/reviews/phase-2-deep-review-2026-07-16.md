# Phase 2 Deep Review — verify before delete

- **Date:** 2026-07-16 · **Scope:** every file issue #67 Phase 2 proposes deleting/trimming
- **Method:** three parallel agents read each file IN FULL and traced every live wire (settings.json, harness-manifest.json ↔ `check_manifest.py`, CLAUDE.md hook table ↔ `lint-doc-truth.sh`, tests, CI). The main session independently re-verified every audit-reversing claim. This supersedes the Phase 2 line items of `over-engineering-review-2026-07-16.md` where they conflict.
- **Headline:** the original audit was right about *what is dead* but wrong or stale on **six** load-bearing details — three items flip verdict (branch-guard, deploy-harness backup policy, category_mode), one option is now invalid (wiring check_plan_format), and two "facts" were outdated (agents/PROJECT.md render, PR_TEMPLATE state). Deleting per the original list without this pass would have broken CI once and silently removed two human-approved safety mechanisms.

---

## Verdict summary

| Item | Audit said | Deep review says | Why it changed |
|---|---|---|---|
| `scripts/context-monitor.py` (298) | delete | **DELETE** ✅ zero refs confirmed exactly | — |
| `scripts/check_plan_format.py` + test (440) | wire or delete | **DELETE only** — wiring is now actively wrong | PR #69: markdown-only authoring; validator is XML-only and rejects every new plan; also parses fenced blocks (opposite of render_plan.py semantics) |
| `hooks/branch-guard.sh` (31) | delete (subsumed) | **KEEP** — subsumption claim is false | branch-isolation-guard only sees Edit/Write tool calls; Bash-mediated edits (`sed -i`, `git apply`, heredoc) + external changes only branch-guard catches, at commit time. Also: gate-integration.test.sh uses it as canary |
| `hooks/protected-path-guard.sh` (51) | delete (duplicate) | **KEEP DORMANT** (or delete WITH doc supersede) | Not a duplicate: covers `run-tests.sh` + `SUMMARY.template.md` which risk-corroboration does not; write-time deny blocks even declared-high-risk lanes; dormancy is a recorded high-confidence decision (gap-closure-decisions.md D2) |
| `risk-corroboration category_mode()` | delete (constant in function costume) | **KEEP** | `check_manifest.py:85-87` regex-parses the case branches from the hook source; deleting → 8 slugs fail CI. RISK_WARN_CATEGORIES is functional and test-pinned. 18 lines vs a 4-file coordinated edit — not worth it |
| `commit-quality-gate` app/ checks (2, 2.5, 3, hint) | move to templates/stacks/ | **KEEP AS-IS** (self-skip); "move" not actionable | No per-stack hook mechanism exists — templates/stacks/ holds only architecture/guidelines md; deploy copies hooks/ wholesale. Checks are dead HERE but live in consuming repos with app/. Optional later: `APP_DIR` env |
| `harness-audit.sh` check #4 | delete check | **DELETE check** ✅ confirmed worse | Findings 20→29 monotonic (now 29 of 34 total = permanent "needs attention"); consumers safe (bookkeeping/harness-status don't key on the field) |
| `deploy-harness.sh` spinner (~20) | delete | **DELETE** ✅ purely decorative, zero test pins | — |
| `deploy-harness.sh` backup policy + 4-way prompt | delete (~50-70) | **KEEP** — human-approved escape hatch | resync-protected-files-decisions.md D3 (confidence high): batch conflict resolution was approved BY the human specifically because `[b]ackup` is the compensating control. Deleting it removes the documented basis of an approved compromise |
| `templates/TEST_MATRIX.template.md` (34) | delete | **DELETE** ✅ 0/33 specs confirmed; intent-review-stage even *deferred* it consciously | Checklist: template + orchestration.md:62 + HARNESS.md:53 + README.md:64 (+ .claude redeploy). Doc-truth lint won't force these (bare tokens) — edit for truth |
| `templates/stacks/{nextjs,node,django}` (~780, not 640) | cut unless distributing | **CUT leaning** — stronger evidence found, but product call stays with owner | bootstrap-xia2 has **no detection markers** for Next.js/Django at all (SKILL.md:237-242) — nothing can ever route to 2 of the 3 profiles; `_skeleton` fallback keeps JS/Django consumers functional. Keep-evidence: install/deploy genuinely ship templates/ to consumers |
| `REQ.md` (22) | delete | **DELETE** ✅ zero mechanized refs | Courtesy: paste its 6 questions into research-harness-req-assessment.md, whose subject vanishes |
| `agents/PROJECT.md` | fill or delete | **FILL — a rendered draft already exists** | `.claude/agents/PROJECT.md.proposed` (3.1KB, 2026-07-15) is a complete render for this repo awaiting review — audit's "never rendered" is outdated. Runtime readers: agents/coding.md + test-runner.md. Shipping caveat: promoting it ships meta-repo facts in the install payload (deploy protects filled copies; consumers' bootstrap skips create-if-missing) — pick (a) promote or (b) untrack from payload |
| `agent-memory/` (README only) | delete/fold | **KEEP (default)** — deletion costs more than it saves | Bootstrap scaffolds target repos from the *skill-local* template, so deletion doesn't break consumers — but README.md:65 + skills/README.md:15,210 are linted docs needing rewording. One 1-file dir vs two doc edits |
| `PR_TEMPLATE.md` (28) | "investigate; polluting git status" | **DELETE + fix create-pr output path** | Two audit facts wrong: it holds **PR #2**'s body (not compound-ddr) and is **committed** (1b95fc8), not dirtying status. create-pr/SKILL.md:10,37,40 writes it to repo root — change to a gitignored path; update finishing-a-development-branch:79 + skills/README.md:124. No .github/PULL_REQUEST_TEMPLATE.md conflict |

---

## The three CI tripwires (why "just delete" fails)

Any Phase 2 execution must satisfy these invariants per deletion:

1. **`harness-manifest.json` ↔ disk ↔ settings.json** — `check_manifest.py` (run by CI via run-tests.sh, plus harness-audit) fails on any drift, in both directions. Deleting a hook/script ⇒ remove its manifest entry (`hooks` array; `contracts.*.consumers` for check_plan_format at manifest:68).
2. **CLAUDE.md hook table ↔ settings.json ↔ hooks/*.sh** — `lint-doc-truth.sh` check 3 fails on a table row for a missing hook, a missing row for an existing hook, or a wrong wired-flag. Every hook deletion ⇒ delete its table row.
3. **check_manifest §B regex-parses `risk-corroboration.sh` SOURCE** — `add_cat` calls and `category_mode` case branches must both cover every manifest `hard_gates.detectable` slug. This is why category_mode cannot be deleted in isolation.

Plus one soft tripwire: **knowledge-base contradiction**. Two Phase 2 targets (protected-path-guard dormancy, deploy-harness backup policy) are recorded as deliberate decisions in `docs/solutions/` with high confidence. Deleting them without editing those docs (supersede note) makes the knowledge base assert things disk contradicts — the exact failure mode the KB exists to prevent.

## Stale docs found incidentally (fix in Phase 2 regardless)

- **CLAUDE.md:54 + settings.json:35 statusMessage** still say branch-isolation-guard blocks "while a plan is `status: active`" — the hook explicitly removed that condition (branch-isolation-guard.sh:17-20; test pins tiny-lane-no-plan → DENY). Verified in main session.
- `specs/entropy-trend/PLAN.md` pins "6 checks" for harness-audit (inert, shipped prose — leave).
- check #4 deletion must also shrink harness-audit's `--json` python heredoc (10 positional args) and delete 3 test cases in tests/scripts/harness-audit.test.sh:54-79.

## Recommended execution order (safe waves)

- **Wave 1 — zero-coupling deletes:** context-monitor.py · REQ.md (+ paste questions) · TEST_MATRIX template + 3 prose mandates · deploy-harness spinner. No manifest/table entries involved except doc edits.
- **Wave 2 — coordinated deletes:** check_plan_format.py + test (+ manifest:68 + run-tests.sh:40 — run-tests.sh is CI-contract, declare lane) · harness-audit check #4 (+ JSON emitter + 3 tests) · PR_TEMPLATE.md (+ create-pr path change + 2 skill doc edits).
- **Wave 3 — decisions needed from owner, then mechanical:**
  1. stacks/{nextjs,node,django} — cut (recommended: no detection can reach 2 of 3) or keep for distribution optics;
  2. agents/PROJECT.md — promote `.proposed` (recommended) or untrack from payload;
  3. protected-path-guard — keep dormant (recommended) or delete + supersede gap-closure D2;
  4. agent-memory/ — keep (recommended).
- **Not doing (reversed from audit):** branch-guard deletion · category_mode deletion · deploy-harness backup/prompt deletion · commit-quality-gate app/-check relocation (no mechanism; revisit if a per-stack hook layer ever exists).

**Net effect vs original Phase 2 estimate:** ~1,700 lines → realistically **~1,150–1,300 lines** deleted (waves 1-2 + stacks if cut), with zero enforcement loss and zero CI breakage — the difference is the three reversed items, which were load-bearing.
