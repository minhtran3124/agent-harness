---
name: xia2
description: Portable research-first feature discovery — investigates what exists locally, upstream on GitHub, and in version-matched official docs before any implementation. Classifies risk from built-in common signals (no per-project config). Use before adding new features, capabilities, or integrations to answer what already exists and what is the lightest credible path forward.
allowed-tools: Glob, Grep, Read, Write, WebSearch, WebFetch, Bash(git log *), Bash(git show *), Bash(cat *), Bash(ls *)
---

# Xia2 — Research-First Feature Discovery (Portable)

Portable version of `xia`. All logic — including the risk-classification signals — lives here in `SKILL.md` as **common, built-in vocabulary**. The same skill works across projects with no per-project config file: signals are detected live per change against the common patterns below.

Answer five foundational questions before any implementation begins:

1. **What is this repo really?** Detect the actual tech stack from manifests, configs, and lockfiles — never guess from folder names or branding.
2. **What already exists locally?** Search for reusable code, abstractions, and extension points before proposing anything new.
3. **What does the ecosystem already support?** Check upstream GitHub repositories for established patterns that match the need.
4. **What do the current official docs actually recommend?** Query version-matched documentation, not generic web results.
5. **What is the lightest credible path from here?** Recommend: reuse existing > adapt upstream > use built-in > build from scratch.

<HARD-GATE>
Do NOT write code, edit files, or scaffold anything until the research brief is complete and delivered to the user. The brief is the deliverable — not implementation. This gate applies regardless of how simple the feature seems. If the user explicitly says "skip research" or "just implement it", note the waiver at the top of your response and proceed — but do not waive it yourself.

**Even when waived,** run the Decision Procedure mentally and surface any Deep signal that fired as a one-line risk warning at the top of your response (e.g., *"Note: this is a schema/migration change (Deep) — destructive operations like DROP COLUMN cannot be undone."*). The waiver covers the research workflow, not the duty to flag known risks.
</HARD-GATE>

---

## Common signals (built-in)

The Decision Procedure classifies against these generic, cross-project patterns — detected **live** per change, no config file. Match a change's files/description against them.

| Signal | Common definition (detect live) |
|---|---|
| **Dependency manifests** | `package.json`, `requirements*.txt`, `pyproject.toml`, `go.mod`, `Gemfile`, `Cargo.toml`, `pom.xml`, `build.gradle*`, `*.csproj` |
| **Data-loss / migration** | `migrations/`, `alembic/`, or `*.sql` containing DDL (`CREATE`/`ALTER`/`DROP TABLE`) |
| **Entry points** | `main.*`, `app.*`, `index.*`, and dirs `cmd/`, `routes/`, `controllers/`, `handlers/`, `pages/`, `api/` |
| **Auth surfaces** | path or identifier matching `auth`, `login`, `logout`, `session`, `jwt`, `oauth`, `password`, `token`, `rbac`, `permission` |
| **Public API contract** | OpenAPI / `*.proto` / GraphQL schema files; route decorators (`@app.`, `@router.`, `@Get`, `@Post`) |
| **High-blast (generic)** | CI config (`.github/workflows/`), settings/config files, hook scripts, DI containers, shared base classes — by common name, corroborated by "imported by many" via `code-review-graph` when available |
| **Shared runtime contract** | config/constant files a change alters that many modules read (e.g. a default-model constant, a feature-flag registry, a connection-pool config) |
| **Knowledge base** | `docs/solutions/INDEX.md` (harness convention — hardcoded) |
| **Recent decisions** | `specs/` (harness convention — hardcoded) |

A project with an *unusual* high-blast file that matches none of these won't be auto-flagged — the commit-time risk hooks and reviews are the backstop. Precision here is deliberately traded for zero-config portability.

---

## Depth Modes

Choose depth from **concrete signals**, not gut feel. Do not estimate "implementation time" before research — that is circular.

**Decision procedure (in order):**

1. Check **Deep** signals — *any one* triggers Deep.
2. If not Deep, check **Quick** conditions — *all must hold* to qualify as Quick.
3. Otherwise, choose **Standard**.

| Mode | Conditions | Coverage | Worked example |
|---|---|---|---|
| **Deep** *(any one triggers)* | • Schema or migration change (see Common signals › Data-loss / migration)<br>• Touches a high-blast file (see Common signals › High-blast)<br>• New external integration (third-party SDK, payment, auth, AI provider, broker, message queue, etc.)<br>• New runtime dependency added to a manifest (see Common signals › Dependency manifests)<br>• Changes a shared runtime configuration contract (see Common signals › Shared runtime contract)<br>• Changes auth flow or transaction/session-scoping rules (see Common signals › Auth surfaces) | Wide local coverage + multiple upstream repos + official changelogs + explicit risk analysis | *"Add a new column to a model and write the migration"* — schema change triggers Deep regardless of column type. |
| **Quick** *(all must hold)* | • No Deep signal triggered<br>• Touches ≤1 file **AND** adds no new public callable in a shared module (data access layer, service, helper, calculation that callers will use)<br>• No new dependency<br>• No public API contract change (see Common signals › Public API contract)<br>• Not inside any entry point (see Common signals › Entry points) | Local artifact scan + brief local search | *Add a debug `__repr__`/`Display`/`toString` to an internal model; tweak a log prefix string; reword a static template.* |
| **Standard** *(default)* | Anything not qualifying as Deep or Quick | Full local mapping + upstream patterns + version-matched docs | *"Add rate limiting to the API endpoints"* — new middleware, possibly new dep, no schema change, no high-blast-radius file. |

**Signals can be explicit or implicit.** A Deep signal triggers whether the prompt names it directly or implies it through a description:

- *Explicit* — prompt names the file path, dep name, or system (e.g., *"edit the connection-pool config"* or *"add `library-x` to the manifest"*).
- *Implicit* — description maps to a common high-blast signal (e.g., *"tweak the connection-pool retry"* → a shared runtime contract); a chosen library forces a new dep (e.g., *"add Library X as the Y backend"* → not stdlib, requires a manifest entry); a single-line config change alters a shared contract (e.g., *"change the default model"* → shared runtime contract).

Treat implicit signals the same as explicit ones — what matters is the underlying change, not whether the prompt names it. **If an implicit signal is uncertain, treat it as an uncertain signal and apply Tiebreaker #1 (→ Standard).**

**Tiebreakers (read in order):**

1. **If you cannot map to a mode in ~10 seconds with concrete signals, choose Standard.** Do not reason your way into Quick to save time.
2. **User urgency does not raise depth.** "It's important" / "ASAP" is not a Deep signal.
3. **Prompt brevity does not lower depth.** A one-line request can still be Deep.
4. **If the user explicitly requests a depth, honor it** — but if their request conflicts with a Deep signal, surface the conflict before proceeding.

---

## Mandatory Workflow Sequence

Execute in this order. Do not skip or reorder steps.

### Step 1 — Check for Research Waiver
If the user explicitly waived research, note it and stop the workflow. (HARD-GATE still requires surfacing Deep signals as risk warnings — see HARD-GATE block above.)

### Step 2 — Read the Repo Contract

**Sub-step 2a — Read contract docs**

Read the universal contract docs (if present at the repo root):
- `AGENTS.md`, `CLAUDE.md`, `README.md`

**Sub-step 2b — Search the knowledge base (harness convention)**

The knowledge base is `docs/solutions/` (built-in convention). Search for prior solutions in this domain using INDEX-first lookup:
1. Read `docs/solutions/INDEX.md` first (single read, O(1)) — it summarises all entries with module, tags, and applicable context. Scan for domain matches in-memory.
2. Read `docs/solutions/critical-patterns.md` regardless of domain — these are high-value learnings that apply broadly.
3. From Index matches, read at most **3 solution files**, prioritised by recency (most recent first per Index order). If more than 3 match, note remaining paths as `[Skipped — see Index]` in the brief without reading them.
4. **Fallback only** (if no `docs/solutions/INDEX.md` exists): grep `docs/solutions/` for the domain keywords, then read at most 3 results.

Treat any entries flagged as low-confidence (or an equivalent stale marker) as unverified — cross-check against current code before acting.

This tells you constraints, conventions, and what the team has already decided.

**Depth re-evaluation gate:** After reading docs, re-run the Decision Procedure with the new evidence. Do not stay locked to the initial choice. **Depth only moves up, never down** — fresh evidence cannot make a feature simpler than the prompt suggested.

- **Upgrade to Deep** if docs surface any Deep signal not visible from the prompt alone:
  - Knowledge base documents a prior migration or schema change in the same module
  - Docs name a high-blast file (per Common signals) as in-scope
  - Docs mention a new external integration or new dependency would be required
  - Docs reveal a shared runtime contract or session/transaction primitive is involved
- **Upgrade to Standard** if docs break any Quick condition:
  - Docs reveal the change must touch >1 file
  - Docs reveal a public API contract (per Common signals) is on the path
  - Docs reveal an entry-point pattern (per Common signals) is in scope
- **Treat low-confidence docs as unverified** — they may be stale. A low-confidence doc cannot, by itself, justify upgrading depth; cross-check against current code first.

Announce the upgrade: *"Upgrading depth to [mode] based on [specific signal] from [doc path]."*

### Step 2.5 — Scan Recent Decisions

Scan `specs/` (the harness decisions convention) for in-progress decisions on the same domain. This prevents re-researching something already decided.

```bash
ls -1t specs/ 2>/dev/null | head -20
```

For each recent directory, check for relevant files:

```bash
grep -rl "<domain>" specs/ --include="*.md" 2>/dev/null | sort -r | head -10
```

If relevant docs found:
- Read them
- Note decisions made, alternatives ruled out, constraints identified
- Label as `Local (decisions)` in the brief

**Stop condition:** If a decision doc fully answers the research question, note this in the brief and skip Steps 5-6 unless the user requests a second opinion.

If `specs/` does not exist, skip this step.

### Step 3 — Map the Repo from Real Artifacts
Detect the actual stack from manifests and configs — never infer from directory names.

Common manifests by ecosystem:
- Python: `pyproject.toml`, `requirements*.txt`, `setup.cfg`, `Pipfile`
- Node: `package.json`, `pnpm-lock.yaml`, `tsconfig.json`
- Rust: `Cargo.toml`, `Cargo.lock`
- Go: `go.mod`, `go.sum`
- Java/Kotlin: `pom.xml`, `build.gradle*`
- Ruby: `Gemfile`, `Gemfile.lock`
- DB/infra: `alembic/`, `migrations/`, `docker-compose.yml`, `*.env.example`
- CI/CD: `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`

Record: primary language + runtime, frameworks/platforms, relevant packages, detectable versions.

### Step 4 — Search Locally for Reuse
Use `Glob` and `Grep` to find existing code before proposing anything new:
- Existing abstractions, base classes, or extension points
- Similar patterns already implemented elsewhere
- Relevant tests that document existing behavior
- Config or feature flags that might already expose the capability

**Stop local search only when artifacts confirm absence** — not when the first search comes up empty.

### Step 5 — Check Upstream Patterns (Standard + Deep only)
After the local picture is clear, search GitHub for established patterns:
- Use `WebSearch` with queries like: `site:github.com <framework> <feature> implementation`
- Target repositories using the same stack and versions
- Look for: existing libraries, common patterns, reference implementations
- Label all upstream findings as `Upstream`

Treat upstream search as best-effort — a failed search does not block the brief.

### Step 6 — Check Official Docs (Standard + Deep only)
After targeting specific stack/versions, query version-matched documentation:
- Use `WebSearch` or `WebFetch` with explicit version constraints
- Check the official docs for the detected version, not "latest stable"
- Look for: built-in capabilities that already support the feature, recommended APIs, deprecation notices
- Label all doc findings as `Docs`

### Step 7 — Save and Deliver the Research Brief
Fill the template in `references/research-brief-template.md` with all findings, then:

1. **Save** the completed brief to `<spec-dir>/research-brief.md` — where `<spec-dir>` is the spec directory passed by the caller (e.g., `specs/YYYY-MM-DD/<topic>/`). If no spec directory was passed, save to `specs/research-brief.md` as fallback.
2. **Deliver** the brief in the conversation so the caller has immediate context.

Do NOT write code or edit any file other than `research-brief.md`.

---

## Tool Routing

| Task | Tool | Query pattern |
|---|---|---|
| Find manifests/configs | `Glob` | `pyproject.toml`, `requirements*.txt`, `package.json`, `Cargo.toml`, `go.mod` |
| Search local code | `Grep` | Pattern-match across source files |
| Read source files | `Read` | Direct file read |
| Scan recent decisions | `Bash(ls *)` + `Grep` | `ls -1t specs/` then grep the domain |
| Upstream GitHub patterns | `WebSearch` | `site:github.com <stack> <feature> example` |
| Official documentation | `WebSearch` | `<library> <version> <feature> site:<official-domain>` |
| Specific doc pages | `WebFetch` | Direct URL from known official source |
| Git history for context | `Bash(git log *)` | `git log --oneline --follow -- <path>` |

**Evidence labeling — required on every finding:**
- `Local` — found in this repository
- `Upstream` — found in external GitHub repo
- `Docs` — from official versioned documentation
- `Inference` — reasoned from available evidence (weakest — flag explicitly)

---

## Guardrails

- **Classify from the built-in Common signals** — no per-project config; detect the signals live per change.
- **Never guess the stack** from folder names, repo name, or branding — always verify from manifests.
- **Never stop local search early** — absent evidence is not proof of absence. Search multiple patterns before concluding something doesn't exist locally.
- **Always explain why alternatives lost** — if you recommend building over reuse, state why reuse was ruled out with evidence.
- **Version discipline** — extract actual versions from manifests or lockfiles. Never default to "latest stable" when you can read the real version.
- **Research before code** — do not interleave discovery with implementation. The brief comes first, always.
- **When docs conflict with local behavior** — surface both findings side-by-side. Do not privilege authority over observed reality.

---

## Arguments

- `$ARGUMENTS` — optional: the feature or capability to research. If omitted, ask the user to describe what they want to add before starting.
- Depth mode can be specified: `quick`, `standard`, or `deep` (default: `standard`).

---

## See also

- `## Common signals (built-in)` above — the cross-project vocabulary the Decision Procedure classifies against (no config file).
- `docs/solutions/INDEX.md` — the knowledge base (harness convention); `scripts/init-structure.sh` scaffolds it in a bare repo.
- `tests/structural/` — Decision Procedure regression tests against the common signals.
- `tests/behavioural/` — pressure scenarios validating HARD-GATE adherence.
