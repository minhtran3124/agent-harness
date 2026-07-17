# techstacks-decoupling — Summary

Lane: high-risk
Confidence: high
Reason: Redefine-system (architecture direction) + shrinks auto-loaded rules + deletes templates/stacks/ (templates/ is in ci-strict-gate HARD_GATE_RE → high-risk forced). Owner-approved all 4 design decisions 2026-07-17; direction unambiguous.
Flags: high-blast (templates/ via strict gate), redefine-system (stack-coupling model)
Affects: rules/architecture+guidelines (thin pointers), rules/plan-format+wave-parallelism+auto-correct-scope (neutralized), templates/stacks (removed), techstacks/ (new project-owned folder), agents/PROJECT*, init-structure
Input-type: harness improvement

### Intent

"rules, skills, templates đang bị ràng buộc với nhau ... tách biệt ra, folder mới 'techstacks/', mỗi dự án tự put rule techstack của mình vào đó, độc lập ... rule/skills chỉ mention folder techstacks đó, ko cần detail từng file" — decouple tech-stack from core; owner approved all 4 design decisions.

### What changed

New project-owned root folder **`techstacks/`** (like specs/, docs/solutions/): ships only `README.md` (the convention), scaffolded create-if-missing by init-structure.sh. Core is now stack-agnostic: `rules/architecture.md` + `guidelines.md` collapsed to ~5-line pointers to `techstacks/` (was placeholder + FastAPI content, auto-loaded every session); FastAPI examples in `rules/plan-format.md` / `wave-parallelism.md` / `auto-correct-scope.md` neutralized to stack-agnostic illustrations; `templates/stacks/{fastapi,_skeleton}/` deleted; `agents/PROJECT.template.md` + `agents/PROJECT.md` + the executing-plans / correctness-review examples repointed/neutralized. Core carries zero FastAPI tokens.

### Rationale

The stack now lives in exactly one place (`techstacks/`), pointed at from the few auto-loaded rules — one canonical home. A new installer inherits no stack baggage and fills `techstacks/` (or leaves it empty). Also lands the 2026-07-16 review's "shrink architecture.md/guidelines.md to pointers" and finishes the wave-3 instinct to drop bundled stack profiles (net context drops).

### Alternatives considered

- Keep templates/stacks/ + ship an example stack: rejected by owner (ship zero stack content).
- techstacks/ inside .claude/: rejected — it is project-owned content (like specs/), belongs at root, survives harness re-sync untouched.

### Deviations

- Rule 1 — also fixed a stale FastAPI claim in agents/PROJECT.md:46 ("target FastAPI projects") the plan didn't list; it contradicted the new thin-pointer model.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| core rules carry zero stack tokens | `bash -c '! grep -rniE -e fastapi -e alembic -e pydantic -e asyncpg -e "@app\." -e "@router\." rules/'` | 0 | agnostic fence (no pipe) |
| architecture + guidelines are techstacks pointers | `bash -c 'grep -q techstacks rules/architecture.md && grep -q techstacks rules/guidelines.md'` | 0 | thin pointers |
| templates/stacks deleted, no live reference | `bash -c '! test -d templates/stacks && ! grep -rq "templates/stacks" rules/ skills/ agents/ CLAUDE.md README.md'` | 0 | |
| techstacks/README exists + init-structure scaffolds it | `bash -c 'test -f techstacks/README.md; a=$?; D=$(mktemp -d); bash scripts/init-structure.sh --root "$D" >/dev/null; test -f "$D/techstacks/README.md"; b=$?; rm -rf "$D"; test "$a" = 0 -a "$b" = 0'` | 0 | create-if-missing |
| init-structure test (now 7 files) | `bash tests/scripts/init-structure.test.sh` | 0 | 3 passed |
| doc-truth lint + manifest | `bash -c 'bash scripts/lint-doc-truth.sh && python3 scripts/check_manifest.py'` | 0 | |

> Full suite (`bash scripts/run-tests.sh`) is covered by the CI `tests` job (ubuntu + macos, both green) — deliberately NOT a Verify row here: the strict gate re-runs each row under a 60s per-command cap, which the whole suite exceeds on a cold CI runner.

### Rollback

- `git revert <commit>` — restores templates/stacks/, the full architecture/guidelines profiles, and the FastAPI examples; removes techstacks/. Prose + folder move; no data/schema migration.

### Harness-Delta

- none
