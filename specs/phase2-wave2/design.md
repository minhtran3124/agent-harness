# Design — Phase 2 Wave 2: coordinated deletes

Status: proposed · Companions: `research-brief.md`, `PLAN.md`. Source: deep-review Wave 2; parent issue #67 Phase 2. Branch flows to **v3** (staging), then batched to main.

## Goal

Delete three dead items that each require a *coordinated* multi-file transaction (~470 lines net), with zero CI breakage. The value over Wave 1 is precisely the coupling: each deletion has a manifest/CI/skill wire that must go in the same commit or the tree is inconsistent.

## Decisions

1. **`check_plan_format.py` + test — delete both, edit the two wires atomically.** Remove `scripts/check_plan_format.py` from `harness-manifest.json:68` consumers (keep `render_plan.py` — still the live plan parser) and from `run-tests.sh:40` PYTESTS. Rejected: reworking it to validate markdown — it would duplicate render_plan.py's `_extract_md_tasks` and executing-plans Step-0, the exact "one canonical home" violation the whole review targets.

2. **`harness-audit.sh` check #4 — delete the check + shrink the JSON emitter carefully.** The renumber (docstring 5,6→4,5) is cosmetic-correct; the load-bearing edit is the `sys.argv[1:11]`→`[1:10]` shrink with `vnr` dropped from unpack + dict + trailing arg — verified as one atomic set. Delete the 3 test cases. Rejected: keeping the check behind a flag — it is noise by construction (monotonic, unclearable), not a tunable.

3. **`PR_TEMPLATE.md` — delete + repoint create-pr to a gitignored `.pr-body.md`.** The file is a tracked scratch artifact; create-pr overwrites the repo-root path on every run, which is why it kept reappearing in git status historically. New target `.pr-body.md` (gitignored, root, predictable). Update all 4 references. Rejected: `specs/<slug>/` (now tracked — would just move the pollution).

4. **Lane: high-risk by judgment, not by strict-gate.** The diff does NOT trip `ci-strict-gate` (no settings/hooks/render_plan/templates path), but `run-tests.sh` + `harness-manifest.json` are CI-critical. Declare high-risk and machine-verify the Verify table anyway — a CI-contract change deserves the same proof bar even when the mechanical gate is silent.

5. **PR targets v3, not main.** Continues the staging model; promoted to main in the next batch.

## Ordering (single wave, disjoint files — but one dependency)

Tasks 1.1 (check_plan_format), 1.2 (harness-audit #4), 1.3 (PR_TEMPLATE) touch disjoint files → parallel-safe. Task 2.1 (regression + evidence) is the barrier. No task deletes a file another task still references.

## Risks

- **JSON emitter miscount** (W2.2) is the one real hazard — a wrong `argv` slice crashes `harness-audit.sh --json`, which `bookkeeping.sh` calls in CI. Mitigated by Task 1.2's own verify running `harness-audit.sh --json | python3 -c 'json.load'` and the harness-audit test suite.
- `run-tests.sh` edit is one line (remove a filename from a space-joined string) — low, but it is the CI entrypoint; the full-suite gate in Task 2.1 is the backstop.
- create-pr repoint could leave a stale reference → Task 1.3 greps for any surviving `PR_TEMPLATE` mention in skills/.

## Out of scope

Wave 3 owner decisions; the three reversed items; Wave 1 (already on main). `.claude/` deployed copies (local, re-synced later).
