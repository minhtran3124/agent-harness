# remove-bootstrap-xia2 — Summary

Lane: high-risk
Confidence: high
Reason: Redefines the risk-classification source of truth (per-project PROJECT.md → built-in common signals) — an escalation-class "redefine the system" change, owner-approved 2026-07-17. Diff also adds templates/structure/ (ci-strict-gate HARD_GATE_RE `^templates/`) and edits deploy-harness.sh (high-blast). Direction unambiguous (owner: "cắt sạch hoàn toàn").
Flags: high-blast (templates/, deploy-harness.sh), redefine-system (risk-classification model)
Affects: xia2 skill (config model), deploy-harness protected-file set, harness skill inventory, structural-scaffolding mechanism
Input-type: harness improvement

### Intent

"cắt sạch hoàn toàn, viết plan và thực thi" — remove bootstrap-xia2, make xia2 fully common (no per-project config, no optional override), preserve structural-file init, everything still works. Prior turns: research-brief.md + design.md (owner reqs: 1-3 users, adapt across many projects via common not per-project, keep init for solution critical-patterns/index/spec-state).

## What changed

xia2 goes zero-config: the `<PROJECT-CONFIG-GATE>` and every `PROJECT.md > …` reference in SKILL.md are replaced by a built-in "Common signals" section (generic cross-project patterns), with the two harness-convention signals hardcoded (knowledge base = `docs/solutions/INDEX.md`, decisions = `specs/`). `xia2/PROJECT.md` + `PROJECT.template.md` deleted; `skills/bootstrap-xia2/` deleted (370 lines). The 6 structural templates relocated `skills/bootstrap-xia2/templates/` → `templates/structure/`, and a new `scripts/init-structure.sh` (create-if-missing, tested) replaces bootstrap's scaffolding step. All references rewritten: harness-manifest.json inventory, skills/README.md (6 sites), CLAUDE.md, rules/architecture.md + guidelines.md, agents/README.md + PROJECT.template.md, README.md, xia2/README.md (full stale-section rewrite), xia2 structural-test framing.

### Rationale

Owner requirement: adapt across many projects by making everything common, not by generating per-project config. The two signals xia2 most needs (knowledge base, decisions) were already harness conventions → hardcodable; the risk-signals were already enumerated by bootstrap's heuristics → became xia2's built-in vocabulary. Precision on unusual project-specific high-blast files is traded for zero-config portability; risk-corroboration + reviews backstop.

### Alternatives considered

- Optional `.xia2-signals` override layer: rejected by owner ("cắt sạch hoàn toàn").
- Deterministic bootstrap script / fold into xia2: rejected in design (research Options B/C).

### Deviations

- Rule 1 — the plan's reference list missed `scripts/deploy-harness.sh` `BOOTSTRAP_OWNED_FILES` (listed the now-deleted `skills/xia2/PROJECT.md`) and `tests/scripts/resync-conflict.test.sh` (used it as the nested-protected-file fixture). Surfaced by the full suite (4 resync failures). Fixed: removed the dead entry + comment, repointed the test fixture to `agents/PROJECT.md` (a still-protected file inside a synced dir with a `.proposed` variant), updated stale example comments. Blast-radius hook flagged both files as outside the plan set — intentional, recorded here.
- Rule 1 — `skills/xia2/README.md` (live skill doc) was heavily coupled to PROJECT.md/bootstrap; the plan's Task 1.2 covered SKILL.md + tests but not README. Rewritten to the common-signals model.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| bootstrap-xia2 gone, templates relocated, init-structure works | `bash -c 'test ! -d skills/bootstrap-xia2 && test -d templates/structure && bash tests/scripts/init-structure.test.sh'` | 0 | 3 cases |
| xia2 fully config-free | `bash -c '! grep -q "PROJECT.md" skills/xia2/SKILL.md && ! grep -q "PROJECT-CONFIG-GATE" skills/xia2/SKILL.md && test ! -f skills/xia2/PROJECT.md && grep -q "docs/solutions/INDEX.md" skills/xia2/SKILL.md'` | 0 | |
| no live bootstrap-xia2 reference | `bash -c '! grep -rq "bootstrap-xia2" harness-manifest.json skills/README.md CLAUDE.md rules/ agents/ README.md skills/xia2/README.md'` | 0 | only historical/explanatory notes remain |
| init-structure round-trips in a bare repo | `bash -c 'D=$(mktemp -d); bash scripts/init-structure.sh --root "$D" > /dev/null && test -f "$D/docs/solutions/INDEX.md" && test -f "$D/specs/STATE.md" && rm -rf "$D"'` | 0 | 6 files created |
| manifest consistent, doc-truth lint clean | `bash -c 'python3 scripts/check_manifest.py && bash scripts/lint-doc-truth.sh'` | 0 | |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN (141 tests + all shell suites incl. new init-structure + fixed resync) |

### Rollback

- `git revert <wave commit>` — restores bootstrap-xia2, xia2/PROJECT.md + template, the deploy-harness protected entry, and all prose from history. Prose + one script + one relocation; no data/schema migration. xia2's Decision Procedure output contract is unchanged, so revert restores exact prior behavior.

### Harness-Delta

- Two couplings (deploy-harness protected set, xia2/README) were invisible to the research brief and only caught by running the suite — reinforces "verify before claiming complete" and that a skill's own README + the installer's protected-file list are reference surfaces easy to miss when deleting a skill.
