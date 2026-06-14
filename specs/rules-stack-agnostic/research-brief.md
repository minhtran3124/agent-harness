# Research Brief — stack-agnostic `rules/` (MIN-25)

> Depth: **Deep** (changes a shared governance contract — the `rules/` layer synced by `deploy-harness.sh` — and touches the `bootstrap-xia2` skill engine). Coverage is **local-only by design**: this is a bespoke harness pattern; no upstream library or framework doc applies (Step 5/6 = N/A, best-effort, not blocking).
> Spec: `specs/rules-stack-agnostic/design.md`. Intake: `SUMMARY.md` (high-risk).

## 1. What this repo really is `[Local]`

A **Claude Code harness toolkit** — bash hooks + python scripts + markdown skills/rules. No app manifest at root (`package.json`/`pyproject.toml` absent); "code" is `hooks/*.sh`, `scripts/*.{sh,py}`, `skills/*/SKILL.md`, `rules/*.md`. CI: `.github/workflows/harness-ci.yml` runs `scripts/run-tests.sh` (bash contract tests + pytest) + `ci-strict-gate.sh` on ubuntu+macos. Tests: `tests/hooks/*.test.sh`, `scripts/test_*.py` (the latter listed explicitly in `run-tests.sh`).

## 2. What already exists to reuse `[Local]`

The lightest path **reuses three established mechanisms** — almost nothing is net-new machinery:

1. **`bootstrap-xia2` scan→draft→review + scaffold-from-template** — `skills/bootstrap-xia2/SKILL.md` already: (a) renders config from bundled templates, (b) **detects and points at architecture/guidelines docs** for `agents/PROJECT.md`, (c) scaffolds missing structural files **create-if-missing** from `skills/bootstrap-xia2/templates/`. Extending it to render a stack profile (`rules/architecture.md` + `rules/guidelines.md`) is the *same* render-from-template + scaffold pattern it already runs. This is the Phase-2 engine — no new paradigm.
2. **`templates/` ships automatically** — `templates/` is in both `install-harness.sh:29` PAYLOAD and `deploy-harness.sh:94` sync set. Nesting `templates/stacks/<stack>/` ships with zero installer change (confirmed).
3. **The "map literal category → harness analog" precedent** — `docs/solutions/harness-bootstrap/meta-repo-signal-remapping-decisions.md` already decided how to handle a meta-repo whose rules describe *target* projects: point harness-working agents at `skills/README.md` + `behavior.md`, not at `architecture.md`. The skeleton in §4.1 of the design is a direct application of that decision — not a new call.

## 3. Impact / blast radius `[Local]`

`deploy-harness.sh:94` syncs the **whole** `rules/` dir → `.claude/`, so `rules/architecture.md` + `rules/guidelines.md` must remain present + valid (design §4.1 handles this: skeleton replacement, not deletion).

References to `architecture.md` / `guidelines.md` to review (grep, excluding `.claude copy/` junk + historical PLANs):

| Path | Nature | Action |
|---|---|---|
| `rules/auto-correct-scope.md`, `rules/orchestration.md` | universal rules cross-linking the profile | verify links still resolve / point generically |
| `agents/PROJECT.md` (+ `.proposed`, `.template.md`) | execution-agent convention index → architecture/guidelines | already overridden to `skills/README.md`+`behavior.md` per the meta-repo decision; confirm consistency |
| `benchmarks/review-chain/fixtures/soft-delete-filter/truth.md` | cites `.claude/rules/architecture.md → Soft Deletes` | FastAPI-specific fixture assumption — flag, decide if it stays |
| `skills/xia2/PROJECT.md` (+ `.template.md`) | describe the two files as "for target FastAPI projects" | update prose to reflect the profile model |
| `docs/solutions/…/meta-repo-signal-remapping-decisions.md`, `critical-patterns.md` | reference the files in decision prose | leave (historical record) |

No **core doc** (`CLAUDE.md`/`README.md`/`HARNESS.md`/`skills/README.md`) references the two files **by path** → `lint-doc-truth` won't break on the move; no lint-script edit needed (confirmed; lint skips `<>`-placeholders).

## 4. Lightest credible path (recommendation)

Reuse > build. Two phases, matching the design:

- **Phase 1 (move + tag + skeleton):** move FastAPI content → `templates/stacks/fastapi/{architecture,guidelines}.md` (byte-equal to pre-refactor `rules/` versions); replace `rules/architecture.md`+`guidelines.md` with the generic skeleton; tag the illustrative FastAPI blocks in `plan-format`/`auto-correct-scope`/`wave-parallelism`; refresh the prose dependents above. Portable immediately; `deploy` still ships a valid `rules/`.
- **Phase 2 (generator):** extend `bootstrap-xia2` to detect stack → render `rules/architecture.md`+`guidelines.md` from the matching `templates/stacks/<stack>/` (or skeleton fallback), exactly like its existing render+scaffold flow.

## 5. Open questions for `/writing-plans`

1. **Profile template location:** root `templates/stacks/<stack>/` (design's choice, ships via PAYLOAD) **vs** `skills/bootstrap-xia2/templates/stacks/` (bootstrap already owns a `templates/` dir). Recommend root `templates/stacks/` for discoverability + because it's a deploy artifact, not bootstrap-internal — but reconcile with bootstrap's existing template convention.
2. **Pin the git baseline sha** for the byte-equivalence check (the `v2` commit just before relocation) so the diff is reproducible in CI.
3. **Whether to seed a second profile** (e.g. a generic `node`/`frontend` skeleton) now or leave Phase 2 to generate on demand — design says on-demand (YAGNI); confirm.
4. **`agents/PROJECT.md` / `xia2/PROJECT.md` prose**: how much rewording vs leaving the meta-repo override as-is.

## 6. Risks `[Local]`

- **Shipping a broken `rules/` to consumers** if the skeleton step is skipped in Phase 1 — mitigated by design §4.1 + the §10 success criterion ("rules/ still valid skeletons after Phase 1").
- **High-blast adjacency:** if the plan ends up editing `run-tests.sh`/`lint-doc-truth.sh`/`deploy-harness.sh`, those are Rule-4 / CI-contract — declare high-risk SUMMARY + Verify/Rollback (already the lane). Current analysis says **no** edit to those scripts is required (templates already shipped, lint keys on literal paths).
- **`.claude copy/` noise:** a stray duplicate dir holds parallel copies of these files; ignore it (already git-excluded locally).

## Evidence labels
All findings `[Local]` (repo files, grep, script line numbers). `[Upstream]`/`[Docs]`: none applicable — bespoke harness pattern.
