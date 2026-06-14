---
name: bootstrap-xia2
description: Auto-bootstrap or update PROJECT.md for the xia2 skill by scanning the repository. Use this before invoking /xia2 for the first time in a project, or after major architectural changes (new auth system, framework migration, new high-blast modules). Outputs a draft PROJECT.md with auto-detected values plus a human-review checklist, drafts the companion agents/PROJECT.md (the execution-agents' convention index — points at detected architecture/guidelines docs + test command), and scaffolds missing structural files (specs/, docs/solutions/, agent-memory/) from bundled templates (create-if-missing).
allowed-tools: Glob, Grep, Read, Write, Edit, Bash(git log *), Bash(ls *), Bash(cat *), Bash(wc *)
---

# Xia2 Init Project — Bootstrap PROJECT.md from a Repo Scan

Companion skill to `xia2`. Scans the repo, detects signal mappings, and produces draft config for
human review: `xia2/PROJECT.md` (risk-classification signals) and `agents/PROJECT.md` (the
execution-agents' convention index — see [agents/PROJECT.md](#convention-sources--test-command-for-agentsprojectmd)).

**Philosophy:** automation first, human-review last. Auto-detection covers the obvious cases (manifests, entry-point folders, common contract names). Human review handles judgement calls (which files are *really* high-blast, which contracts are *really* shared).

---

## When to invoke

| Trigger | Mode |
|---|---|
| First time using `xia2` in a project — `PROJECT.md` does not exist | **Init** |
| After a major architectural change (new auth system, new framework, repo restructure) | **Update** |
| Periodic refresh (every few months) to catch drift | **Update** |
| After resolving an `xia2` finding that suggested adding/removing PROJECT.md entries | **Update** |

---

## Modes

### Mode A — Init (no `PROJECT.md` exists)

1. Confirm `xia2/PROJECT.md` does **not** exist (else switch to Update mode).
2. Read `xia2/PROJECT.template.md` for structure.
3. Run all detection heuristics (see below).
4. Render `PROJECT.md` from template, filling each section with auto-detected values. Mark every auto-filled entry with an HTML comment: `<!-- auto: <reasoning> -->`.
5. Write to `xia2/PROJECT.md`.
6. **Render `agents/PROJECT.md`** (the execution-agents' convention index) from `agents/PROJECT.template.md` — only when `agents/` exists and `agents/PROJECT.md` does not. Fill *Convention sources* with detected doc paths and *Test execution* with the detected command/mapping; leave *Inline fallback* empty when a convention doc was found. Mark auto-filled entries with `<!-- auto: ... -->`. It is an **index** — point at docs, never copy their content in.
7. **Render the stack architecture profile** — create-if-missing `rules/architecture.md` and `rules/guidelines.md`:
   - Use the stack detected in step 3 (from manifest/framework heuristics).
   - If `templates/stacks/<stack>/architecture.md` (and `guidelines.md`) exists for the detected stack, copy those files to `rules/architecture.md` and `rules/guidelines.md` as a **human-reviewed draft**. Mark each file's top with `<!-- auto: rendered from templates/stacks/<stack>/ — review before use -->`.
   - If no bundled `templates/stacks/<stack>/` matches the detected stack (or no stack was detected), copy `templates/stacks/_skeleton/architecture.md` and `templates/stacks/_skeleton/guidelines.md` as the **generic skeleton** — the stack-neutral placeholder — plus a note at the top of each: `<!-- auto: no stack profile found for <stack>; fill this or add templates/stacks/<stack>/{architecture,guidelines}.md -->`. NEVER emit a wrong-stack profile (e.g. do not render the FastAPI profile into a Node project because it was the only bundled option).
   - Create-if-missing only. If `rules/architecture.md` or `rules/guidelines.md` already exist, **skip** them and report `exists`.
8. **Scaffold missing structural files** — create-if-missing only (see [Scaffolding structural files](#scaffolding-structural-files) below).
9. Output a **review checklist** to the user listing every auto-filled entry that needs verification, plus a scaffolding report.

### Mode B — Update (`PROJECT.md` exists)

1. Read existing `xia2/PROJECT.md`.
2. Run detection heuristics.
3. **Diff:** compare detected values against current `PROJECT.md`. For each section, list:
   - **Stale entries** — files that no longer exist
   - **New candidates** — files matching heuristics not currently listed
   - **Consistent entries** — no change
4. **Do NOT overwrite `PROJECT.md`.** Write proposals to `xia2/PROJECT.md.proposed`.
5. **Refresh `agents/PROJECT.md`** if present: re-detect convention-doc paths + test command; when they drift from the current file, write proposals to `agents/PROJECT.md.proposed` (never overwrite). If `agents/PROJECT.md` is missing but `agents/` exists, render it per Init step 6.
6. **Refresh the stack architecture profile** — re-detect the stack and compare against the current `rules/architecture.md` and `rules/guidelines.md`:
   - If the detected stack has a bundled profile under `templates/stacks/<stack>/` and the current `rules/architecture.md` or `rules/guidelines.md` is the generic skeleton (or missing), write the proposed profile to `rules/architecture.md.proposed` / `rules/guidelines.md.proposed` for human review. Never overwrite a customized file silently.
   - If either rules file is missing, apply the create-if-missing logic from Init step 7 (correct profile or generic skeleton, with auto-detection comment).
   - If neither file has changed (still matches the bundled profile or the human has customized it), skip and report `exists / customized`.
   - NEVER silently emit a wrong-stack profile. If the detected stack does not match any bundled `templates/stacks/<stack>/`, leave the current file untouched and note the mismatch in the diff summary.
7. **Scaffold any missing structural files** — create-if-missing only (see [Scaffolding structural files](#scaffolding-structural-files) below). Useful if a structural file was deleted since first setup; never touches existing ones.
8. Output a diff summary for human review. User merges manually.

---

## Scaffolding structural files

The workflow needs a few structural files to exist. This skill bundles them in `templates/`
and copies each to its destination **only if the destination does not already exist** —
real content is never overwritten.

For each row below: if the destination is missing, `Read` the template and `Write` it to the
destination (this creates parent dirs). If it already exists, **skip** it and report `exists`.

| Template (`skills/bootstrap-xia2/templates/`) | Destination | Purpose |
|---|---|---|
| `specs-README.md` | `specs/README.md` | Spec-folder convention + lifecycle |
| `specs-STATE.md` | `specs/STATE.md` | Active-spec tracker (updated by skills + `state-breadcrumb.sh`) |
| `agent-memory-README.md` | `agent-memory/README.md` | Per-agent memory format (use the repo's actual agent-memory path) |
| `docs-solutions-README.md` | `docs/solutions/README.md` | Knowledge-base schema |
| `docs-solutions-INDEX.md` | `docs/solutions/INDEX.md` | KB index (rebuilt by `/compound`) |
| `docs-solutions-critical-patterns.md` | `docs/solutions/critical-patterns.md` | Always-read critical patterns |
| `templates/stacks/<stack>/architecture.md` (or generic skeleton) | `rules/architecture.md` | Stack architecture profile — rendered from the detected stack's bundled profile; falls back to the generic skeleton when no `templates/stacks/<stack>/` match exists (see Init step 7) |
| `templates/stacks/<stack>/guidelines.md` (or generic skeleton) | `rules/guidelines.md` | Stack engineering guidelines — same detection + fallback logic as `rules/architecture.md` |

> **Note:** the two stack-profile rows above are sourced from the repo-root `templates/stacks/` directory (e.g. `templates/stacks/fastapi/` or `templates/stacks/_skeleton/`), **not** from the skill-local `skills/bootstrap-xia2/templates/` directory that the rest of this table uses.

**Guards:**

- **Create-if-missing only.** Never clobber an existing file — `docs/solutions/INDEX.md` and
  `critical-patterns.md` are regenerated by `/compound`; an existing copy holds real data.
- **`STATE.md` lives at `specs/STATE.md`** (the `specs/` root), **not** inside any `specs/<slug>/`.
- The `state-breadcrumb.sh` hook that maintains `STATE.md` is **dormant** by default — register it
  in `settings.json` (SessionEnd) if you want automatic updates.
- Use the project's actual `agent-memory/` location for the agent-memory README destination.

---

## Detection heuristics

Run each section's heuristic. Confidence label every result:

- `high` — strong signal, likely correct
- `medium` — heuristic match, needs human verification
- `low` — weak signal, agent's best guess

### High-Blast-Radius Files

Multi-pronged scan:

1. **Most-imported files** — for each source file, count inbound imports across the codebase:
   ```bash
   # For Python
   grep -r "from app.database.session_manager" --include="*.py" -l | wc -l
   ```
   Files with >20 inbound imports → candidate.

2. **Most-tested files** — files referenced by many test files:
   ```bash
   grep -rl "<module-path>" tests/ --include="*.py" | wc -l
   ```
   Files referenced by >10 tests → candidate.

3. **Most-changed files (recent)** — git log churn:
   ```bash
   git log --since="6 months ago" --pretty=format: --name-only | sort | uniq -c | sort -rn | head -20
   ```
   Top 20 most-changed → candidate (if also in source dirs, not generated/lock files).

4. **Keyword scan** — files matching common high-blast names:
   - `streaming`, `connection_pool`, `session_manager`, `auth_middleware`, `event_bus`, `dispatcher`, `lifespan`, `app_state`, `db_pool`

5. **Dedupe + rank** — files appearing in 2+ heuristics get `high` confidence; 1 heuristic gets `medium`.

Output: ranked list with reasoning.

### Dependency Manifests

Glob common manifest names:

- Python: `requirements*.txt`, `pyproject.toml`, `Pipfile`, `setup.cfg`, `setup.py`
- Node: `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`
- Rust: `Cargo.toml`, `Cargo.lock`
- Go: `go.mod`, `go.sum`
- Ruby: `Gemfile`, `Gemfile.lock`
- Java: `pom.xml`, `build.gradle`, `build.gradle.kts`

Distinguish runtime vs dev/test:
- `requirements-test.txt`, `requirements-dev.txt`, `pyproject.toml [tool.poetry.dev-dependencies]` → dev/test
- Files in `devDependencies` (package.json) → dev/test

Confidence: `high` for found manifests.

### Shared Runtime Contracts

Heuristic scans:

1. **Config classes** — files containing class definitions matching `*Config`, `*Settings`, `*Env`, `*AppState`:
   ```bash
   grep -rE "class \w+(Config|Settings|Env|AppState)\b" --include="*.py" --include="*.ts" -l
   ```

2. **Pydantic Settings subclasses** (Python):
   ```bash
   grep -rl "BaseSettings" --include="*.py"
   ```

3. **Files in `config/` directory:**
   ```bash
   find . -type d -name "config" -not -path "*/node_modules/*"
   ```

Output: list with class name + file path. Confidence: `medium` (not all matches are project-wide contracts).

### Session/Transaction Primitives

Pattern scan:

```bash
grep -rE "(get_db|get_session|with_session|sessionmanager|session_factory|transaction|begin\(\))" --include="*.py" --include="*.ts" --include="*.go" -l | head -10
```

Look for function/method definitions (not just usage). Read top candidates to confirm they're actual primitives.

Output: function names + file paths. Confidence: `medium`.

### Auth Surfaces

Keyword scan in file names AND content:

```bash
# Filename-based
find . -type f -iname "*auth*" -not -path "*/node_modules/*" -not -path "*/.git/*"
find . -type f -iname "*jwt*" -o -iname "*oauth*" -o -iname "*clerk*" -o -iname "*cognito*"

# Content-based
grep -rl "Authentication\|current_user\|require_auth\|verify_token" --include="*.py" --include="*.ts" -l | head -10
```

Confidence: `high` if filename matches; `medium` if content-only.

### Knowledge Bases (Step 2 reads)

Glob universal docs at repo root + common project-doc paths:

- `AGENTS.md`, `CLAUDE.md`, `README.md` — root only
- `.claude/rules/*.md`
- `.cursor/rules/*.md`, `.cursor/rules/*.mdc`
- `docs/architecture.md`, `docs/guidelines.md`, `docs/conventions.md`
- `docs/solutions/`, `docs/decisions/`, `docs/adr/`
- `CONTRIBUTING.md`

Detect search keys for solved-problems folders by scanning a sample file for YAML frontmatter (e.g., `module:`, `confidence:`, `affects:`).

Confidence: `high` for found files.

### Recent Decisions Folder

Glob common patterns:

- `specs/` (project convention)
- `decisions/`, `adr/`
- `docs/decisions/`, `docs/adr/`

Sample subfolder names to detect schema:

- Date-based (`YYYY-MM-DD/` or `YYYY-MM-DD-name/`)
- Numbered ADR (`0001-xxx.md`)
- Flat (`*.md` directly under)

Confidence: `medium`. Lookback default: 60 days.

### Public API Contract Types

Detect framework + entry-point patterns:

- FastAPI: presence of `from fastapi import`, `APIRouter`, `Depends`
- Express: `app.get`, `app.post`, `router.get`
- Spring: `@RestController`, `@GetMapping`
- Rails: `controllers/` directory
- gRPC: `*.proto` files
- GraphQL: `*.graphql`, `schema.graphql`

Confidence: `high` for framework match.

### Entry Point Patterns

Glob common entry-point directories:

- `routers/`, `controllers/`, `handlers/`, `views/`
- `middleware/`
- Background services: anything ending in `_service/` at repo root
- Lifecycle: `lifespan.py`, `startup.py`, `shutdown.py`, `app.py`, `main.py`

Confidence: `high` for found dirs.

### Convention sources & test command (for `agents/PROJECT.md`)

Feeds the agents' pointer index. Two parts:

1. **Convention-doc paths** — reuse the **Knowledge Bases** scan, but keep only the docs that
   describe *how to write code here* (not the KB/decisions folders):
   - Architecture / layering: first existing of `.claude/rules/architecture.md`,
     `docs/architecture.md`, `ARCHITECTURE.md`, `.cursor/rules/*architecture*`.
   - Style / error / validation / logging: first existing of `.claude/rules/guidelines.md`,
     `docs/guidelines.md`, `docs/conventions.md`, `CONTRIBUTING.md`.
   - None found → record `none`; populate the template's *Inline fallback* from the layering
     inferred via **Entry Point Patterns** + **Public API Contract Types**.
2. **Test command** — derive from the detected manifest/runner:
   - `pyproject.toml` / `requirements*.txt` → `python -m pytest` (note any `[tool.pytest.ini_options]` config location)
   - `package.json` → its `test` script, else the runner in `devDependencies` (vitest / jest)
   - `go.mod` → `go test ./...` · `Cargo.toml` → `cargo test` · `pom.xml` / `build.gradle` → `mvn test` / `./gradlew test`
   - Full table: `agents/test-runner.md → Common Test Runners`.

Confidence: `high` for a doc path that exists or a single unambiguous runner; `medium` otherwise.

---

## Output format

### After Init mode

Write `PROJECT.md`. Then output to user:

```
PROJECT.md drafted at <path>. Auto-detection summary:

✓ High-Blast-Radius Files: 3 candidates (1 high-confidence, 2 medium)
✓ Dependency Manifests: 2 found
✓ Shared Runtime Contracts: 1 candidate (medium)
⚠ Session/Transaction Primitives: 0 found — REQUIRES MANUAL ENTRY
✓ Auth Surfaces: 2 candidates (1 high, 1 medium)
✓ Knowledge Bases: 4 docs found
✓ Recent Decisions Folder: detected at `specs/` (date-based)
✓ Public API Contract Types: detected (FastAPI)
✓ Entry Point Patterns: 3 dirs found
✓ agents/PROJECT.md: rendered — linked architecture.md + guidelines.md; test cmd `python -m pytest`
✓ Stack profile: detected `fastapi` → rendered from `templates/stacks/fastapi/` → `rules/architecture.md`, `rules/guidelines.md` (created)

Scaffolded (create-if-missing):
  + specs/README.md, specs/STATE.md, agent-memory/README.md (created)
  ~ docs/solutions/INDEX.md, docs/solutions/critical-patterns.md (exist — skipped)

REVIEW CHECKLIST (verify before invoking /xia2):
1. High-Blast-Radius Files — confirm all 3 candidates are actually high-blast (false positives push too many cases to Deep)
2. Shared Runtime Contracts — only 1 candidate found; you may have more not matching name patterns. Walk through `app/config/` manually.
3. Session/Transaction Primitives — empty. Find your project's DB session functions and add them.
4. Auth Surfaces — verify the medium-confidence one is truly an auth surface.
5. Stack profile — confirm the auto-detected stack (`fastapi`) is correct and the rendered `rules/architecture.md` + `rules/guidelines.md` match your project's conventions. If the stack is wrong or no profile was bundled, either correct the profile manually or add `templates/stacks/<stack>/{architecture,guidelines}.md`.

Once reviewed, edit `PROJECT.md` to remove `<!-- auto -->` markers from confirmed entries.
```

### After Update mode

Write `PROJECT.md.proposed`. Then output to user:

```
Detection vs current PROJECT.md:

NEW CANDIDATES:
- High-Blast: `app/services/new_module.py` (high-confidence — 25 inbound imports, 12 tests)
- Dependency Manifests: `requirements-prod.txt` (newly detected)

STALE ENTRIES:
- High-Blast: `app/services/old_module.py` — file no longer exists; remove from PROJECT.md
- Knowledge Bases: `docs/architecture.md` — no longer present at expected path

UNCHANGED: 7 entries consistent with detection.

STACK PROFILE:
  ~ rules/architecture.md — exists and appears customized; no proposal written
  ! rules/guidelines.md — missing; rendered from `templates/stacks/fastapi/` → `rules/guidelines.md` (created)

Diff written to `PROJECT.md.proposed`. Review and merge selectively into `PROJECT.md`.
Stack profile proposals (if any) written to `rules/architecture.md.proposed` / `rules/guidelines.md.proposed` — merge manually.
```

---

## Important rules

- **Never overwrite `PROJECT.md` in Update mode.** Always write to `PROJECT.md.proposed` so the human can review.
- **Never delete entries automatically.** Stale-entry detection is a *suggestion*, not an action.
- **Always include reasoning per auto-detected entry.** Use HTML comments: `<!-- auto: 25 inbound imports, 12 test references -->`.
- **Never run `/xia2` from this skill.** This skill bootstraps; it doesn't classify. The user invokes `/xia2` separately after PROJECT.md is reviewed.
- **Scaffold create-if-missing only.** Never overwrite an existing structural file (`specs/README.md`, `specs/STATE.md`, `docs/solutions/*`, `agent-memory/README.md`) — skip and report `exists` when present.
- **`agents/PROJECT.md` is index-not-copy.** Create-if-missing in Init, proposed-only in Update — same guard as the rest. Fill its *Convention sources* by **pointing** at detected docs; never copy doc content into it (that recreates the drift this design removes).

---

## Limitations (v1)

This is a first iteration. Known gaps:

- **Cannot judge "high-blast" intent** — heuristics catch popular files but not necessarily *fragile* ones. Human review essential.
- **No language-specific AST analysis** — pure grep/glob. Misses some shared contracts hidden in language-idiomatic patterns.
- **No git churn for new repos** — heuristic 3 fails on repos <6 months old. Falls back to other heuristics.
- **No cross-project learning** — each invocation starts fresh; doesn't reuse insights from previous projects.

Future improvements (out of scope for v1):
- Read PROJECT.md files from sibling projects to suggest patterns
- Optional LSP integration for richer import graphs
- Confidence scoring tuning based on user feedback (which suggestions get accepted/rejected)

---

## Arguments

- `$ARGUMENTS` — optional: `init` or `update`. If omitted, the skill auto-detects mode by checking whether `PROJECT.md` exists.
