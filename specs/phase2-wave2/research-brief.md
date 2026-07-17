# Research Brief — Phase 2 Wave 2 (coordinated deletes)

Source: `docs/reviews/phase-2-deep-review-2026-07-16.md` Wave 2. Re-verified fresh 2026-07-17 on `feat/phase2-wave2` (branched from v3, synced with main post-#80).

## W2.1 — `check_plan_format.py` (198) + `test_check_plan_format.py` (242)

- **Why delete (stronger than audit):** validator is XML-only; PR #69 made markdown the sole authoring syntax, so wiring it would reject every new plan. Its `extract_tasks` also matches tasks *inside* fenced blocks — opposite of `render_plan.py` (masks fences) and plan-format.md ("fenced = illustration").
- **Coupled edits (both required, else CI red):**
  - `harness-manifest.json:68` — `artifact-schema-plan.consumers` lists `scripts/check_plan_format.py` alongside `render_plan.py`. Remove the first; `check_manifest.py` verifies manifest consumers exist on disk → deleting the file without editing manifest fails L1.
  - `scripts/run-tests.sh:40` — `PYTESTS` string lists `scripts/test_check_plan_format.py`. Remove it. **run-tests.sh is a CI-contract/high-blast file** — part of why this wave is high-risk.
- Prose mentions (specs/, CHANGELOG, docs/research) are inert — leave.

## W2.2 — `harness-audit.sh` check #4 (verify_never_rerun)

- **Why delete:** monotonic alarm-fatigue — audit-log.jsonl shows `verify_never_rerun` 20→29, now the majority of findings, band pinned "needs attention" forever; every merged spec adds a permanent unclearable finding. No consumer keys on the value.
- **Coupled edits inside `harness-audit.sh`:**
  - docstring numbered list L10-15: item 4 (`### Verify commands … never re-run`) → remove + renumber 5,6 → 4,5.
  - counter init L48 `VERIFY_NEVER_RERUN=0` → delete.
  - the check block L115-159 → delete whole.
  - **JSON emitter L211/219/226** (the fragile bit): `sys.argv[1:11]` unpacks 10 args incl. `vnr`; the dict has `"verify_never_rerun": int(vnr)`; the trailing `"$VERIFY_NEVER_RERUN"` arg. Shrink to `[1:10]`, drop the var from unpack + dict + arg list. Miscount here = runtime crash.
- **Test edits:** `tests/scripts/harness-audit.test.sh:54-79` — 3 cases assert `checks.verify_never_rerun`. Delete all three.
- **Consumers safe:** `bookkeeping.sh:111` pipes the JSON through untouched (adds `pr`, appends); `harness-status.sh` runs it human-readable. Old jsonl rows keep the key (append-only) — fine.

## W2.3 — `PR_TEMPLATE.md` (28, committed — holds PR #2's body)

- **Why delete:** stale scratch file wearing a template's name; committed in 1b95fc8. `.github/PULL_REQUEST_TEMPLATE.md` does NOT exist (no GitHub-native collision).
- **Coupled edits (create-pr must stop writing to a tracked root path):**
  - `skills/create-pr/SKILL.md:10,37,40` — "The sole output is a filled `PR_TEMPLATE.md`" / "Write the filled template to `PR_TEMPLATE.md` in the repo root" / the write command. Repoint to a gitignored path.
  - `skills/finishing-a-development-branch/SKILL.md:79` — "generate `PR_TEMPLATE.md`".
  - `skills/README.md:124` — output column `PR_TEMPLATE.md`.
- **Output-path decision:** `specs/<slug>/` is now tracked (can't use it for scratch). `.gitignore` already ignores `PLAN.html`, `.plan-review.json`. Cleanest: write to `.pr-body.md` at repo root and add it to `.gitignore` — a gitignored, predictable, non-polluting path. Update all 4 references to `.pr-body.md`.

## Lane / gate assessment

- Diff touches `scripts/run-tests.sh` + `harness-manifest.json` + `scripts/harness-audit.sh` — none are in `ci-strict-gate` HARD_GATE_RE (`settings.json|^hooks/|render_plan.py|^templates/`). **So strict-gate does NOT fire this wave** (wave 1 fired only because of `templates/`).
- BUT run-tests.sh + manifest are high-blast/CI-contract per repo convention → **Lane: high-risk** by judgment (not by the mechanical strict-gate trigger). Declare it; furnish a machine-verified Verify table regardless (good practice + the file is CI-critical).
- No hooks/ touched → risk-corroboration high-blast path category does not fire.
