# agents — Project Configuration

Thin **index** consumed by the execution sub-agents (`coding.md`, `test-runner.md`). It does
**not** restate conventions — it points to the docs that already hold them, and carries only the
few execution facts no other doc reliably contains.

> Risk-classification signals are **not** here — they live in `rules/research-depth.md` and
> `skills/xia2/references/depth-classifier.md` (xia2 is zero-config; it has no `PROJECT.md` sibling).

---

## Convention sources (point, don't restate)

- **Architecture / layering:** `skills/README.md` (skill inventory + workflow/handoff map) and `CLAUDE.md` (stack, hooks table, gotchas)
- **Code style / naming / testing conventions:** `AGENTS.md` → *Coding Style & Naming Conventions* and *Testing Guidelines*. Agent behavior rules: `rules/behavior.md`
- **Project identity (name / stack / repo root):** `CLAUDE.md` (the meta-repo has no application stack; `techstacks/` is empty by design).

---

## Test execution (agent-specific — usually not in the docs above)

> This section describes the **harness repo itself** and is the default a fresh install ships.
> A consuming repo owns `agents/PROJECT.md` — replace these with your own stack's commands.

- **Test command (harness repo):** `bash scripts/run-tests.sh` (runs L1 syntax + doc-truth lint, L2 hook contract tests, L3 script integration tests — same suite as CI `harness-ci` on ubuntu + macos)
- **Targeted-run flags:** shell: run one suite directly, e.g. `bash tests/hooks/commit-gate.test.sh`; Python: `python3 -m pytest <test file> -q`
- **Source → test mapping (harness repo):** `hooks/<name>.sh` → `tests/hooks/<name>.test.sh`; `scripts/install-harness.sh` → `tests/scripts/install-harness.test.sh`; `settings.json` wiring → `tests/scripts/settings-wiring.test.sh`; `skills/visual-planner/render_plan.py` → `skills/visual-planner/test_render_plan.py` (pytest)
- **Markers / coverage:** none — bash suites assert via `tests/lib.sh` helpers; Python tests are plain pytest (the list is `PYTESTS` in `scripts/run-tests.sh`); no coverage gate

---

## Failure diagnosis hints (optional)

- **Doc-truth lint failure:** a doc references a missing path, or the CLAUDE.md hook table contradicts `settings.json` — fix the doc/table, not the lint
- **Hook test failure:** check the hook's exit-code contract (0 pass / non-zero block) and stdout wording — tests pin both
- **`bash -n` L1 failure:** syntax error in a hook/script — run `bash -n <file>` locally before the full suite

---

## Inline fallback (only if no convention doc exists above)

_(empty — convention sources above are filled)_

---

## Notes for maintainers

- The index **points**, it does not duplicate. If you catch yourself copying a doc's content here, link the doc instead.
- Update the convention-source paths when docs move; re-review the two agents after a layer or test-runner change.
- `rules/architecture.md` + `rules/guidelines.md` are thin pointers to a consuming project's `techstacks/` folder — agents working *on the harness itself* should follow `rules/behavior.md` + `skills/README.md` instead (this meta-repo has no application stack).
