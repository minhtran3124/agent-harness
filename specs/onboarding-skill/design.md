# onboarding-skill — Design

Written 2026-10-16. Pins: repo 96380df; OpenWiki 0.7.2 (output format, `openwiki/` generated at 996f50d)
Revised 2026-10-16. Pins: repo 03fb103

## Goal

Give a new team member on a consumer project a fast, resumable, guided tour of the codebase. The
tour reads the repo's generated OpenWiki when it exists, falls back to harness context when it
does not, and never teaches a wiki claim that no longer matches the code.

## Current state

- No onboarding skill exists. Searched: `ls skills/`, and `grep -i "onboard|codebase-tour|orient"
  skills/README.md` (no match).
- This repo carries a generated OpenWiki at `openwiki/` (55 files, 9 sections; measured
  2026-10-16 `find openwiki -type f`). Its observed layout:
  - `openwiki/quickstart.md`: entrypoint with a "Task-routing map" table (`I want to change… |
    Read first | Then also`).
  - `openwiki/index.md` and `openwiki/<section>/index.md`: page lists, one description per page.
  - Page frontmatter: `type`, `title`, `description`, `tags`, `verified`, `sources`.
  - `openwiki/.claims/<section>/<page>.json` (and `openwiki/.claims/quickstart.json` at the
    root): `{schemaVersion, pageVersion, claims[], verification}`. Each claim has `statement` and
    `evidence[]`. Evidence comes in two formats (measured 2026-10-16, sweep of
    `openwiki/.claims/**/*.json`: 772 line-range items and 23 whole-file items):
    - line range: `{resource: "repo://<path>#L<a>-L<b>", version:
      "repo-lines-v1:sha256:<hex>:<base64 meta>"}`;
    - whole file: `{resource: "repo://<path>", version: "repo-file-v1:sha256:<hex>"}`.
  - `openwiki/.last-update.json`: `{updatedAt, command, gitHead, model, status}`.
  - `openwiki/.page-manifest.json`: per page `gitHead` and `sourceFingerprint`.
- Skills register in `harness-manifest.json` `skills` and in `skills/README.md`. Static checks in
  `scripts/run-tests.sh` cover frontmatter, `allowed-tools` conformance
  (`scripts/check_skill_tool_conformance.py`), and the SKILL.md word ceiling
  (`scripts/audit_skill_prompts.py`). Python tests under `skills/**/test_*.py` are collected
  automatically.
- `.harness-state/` is gitignored here (`.gitignore:30`) but not in consumers: the installer adds
  no such line (`scripts/install-harness.sh:198-281`, read 2026-10-16). The branch-isolation guard
  denies a Write outside `specs/` on a shared branch (`hooks/branch-isolation-guard.sh:74-82`).
  Both facts led to DC1: the skill saves no progress.
- `AGENTS.md` (OpenWiki block) tells agents not to preload the wiki at task start. A user-invoked
  tour is the explicit exception that block allows ("when the user asks for it").

## Approaches considered

1. **SKILL.md plus one claim-check script (chosen).** The prose drives the tour. A stdlib script
   recomputes each claim's `repo-lines-v1` or `repo-file-v1` hash and reports stale claims.
   Verification is deterministic and testable; the prose stays short.
2. **SKILL.md plus `references/` per mode.** Same script, with the tour, focus mode, and fallback
   split into on-demand files. More room, more files; not needed while the prose fits the ceiling.
3. **Prose only.** The agent reads each cited range and judges it by eye. No code to test, but
   verification becomes judgment-tier and costs one read per claim.

## Architecture

| Component | Role |
|---|---|
| `skills/onboarding/SKILL.md` | Tour procedure. Runtime-neutral. At most 600 words (budget, `SKILL_WORD_CEILING`). `allowed-tools`: `Read, Grep, Glob, Bash(python3 *), Bash(git *)`. It names the script by its deployed path, `.claude/skills/onboarding/scripts/check_claims.py` (D8) — checked by `scripts/check_skill_tool_conformance.py`. |
| `skills/onboarding/scripts/check_claims.py` | Stdlib. `--status`: wiki `gitHead`, `HEAD`, commits behind. `<page>`: verify that page's claims. |
| `skills/onboarding/scripts/test_check_claims.py` | Unit tests, collected by `run-tests.sh`. |
| `harness-manifest.json` `skills`, `skills/README.md` | Registration and inventory row. |

**Claim check (`check_claims.py <page>`).** `<page>` is a path relative to `openwiki/`, such as
`enforcement/commit-gate.md` or the root page `quickstart.md`. The claims file is the same path
under `openwiki/.claims/` with `.json` in place of `.md`. For each evidence item:

- `repo-lines-v1`: read `<path>` lines `a..b`, join them with `\n`, add a trailing `\n`, and
  compare `sha256` to `<hex>`.
- `repo-file-v1`: compare `sha256` of the raw file bytes to `<hex>`.
- Any other prefix: result `unknown`.

A claim takes its worst evidence result. Results: `ok`; `stale` (hash differs); `missing` (file
absent or range past end of file); `unknown` (unrecognized format). The base64 metadata (context
hashes) is not used; a moved block reads as `stale`, which is the safe direction.

Exit codes (specific to this mode): 0 every claim `ok`; 1 at least one claim not `ok`; 2 no
`openwiki/` directory; 3 no claims file for the page; 4 the page itself is missing. The page check
runs before the claims-file check, so a page with neither returns 4. Output is one line per claim:
result, `path` or `path#La-Lb`, statement.

**Drift check (`check_claims.py --status`).** Reads `openwiki/.last-update.json`. Exit codes
(specific to this mode; they do not share meanings with `<page>` mode) and output:

- 0 `current`: `gitHead` equals `HEAD`.
- 1 `behind <N>`: `gitHead` is an ancestor of `HEAD`; N = `git rev-list --count <gitHead>..HEAD`.
- 2 `no-wiki`: `openwiki/` absent.
- 3 `unknown-drift <reason>`: `.last-update.json` absent or unparseable, its `status` is not
  `complete`, or `gitHead` is not an ancestor of `HEAD` (another branch, rewritten history, or a
  shallow clone).

**No saved progress (D7).** The skill writes no file. Each run starts fresh. Within one run the
agent offers pages in wiki order, and the newcomer can name any page or section to jump to.

**Modes, chosen by argument text.** Empty: status, the section list, then the first page.
`status`: status and the section list only. A page or section name: start there. Any other text: a focus area or ticket. The agent, following SKILL.md prose,
matches it to the quickstart routing-table row (or rows) whose "I want to change…" cell fits
best. Sessions are the pages linked in "Read first", then "Then also", in listed order. A cell
that says "X or Y" yields both pages, in order. No script does this match.

## Worked trace

A newcomer runs the skill with the argument "I will change a hook" in this repo.

1. `check_claims.py --status` exits 1 with `behind 3` (measured 2026-10-16
   `git rev-list --count 996f50d..96380df`). The skill warns that the wiki is 3 commits old,
   suggests `openwiki code --update`, and continues.
2. Focus text matches the routing row "a hook (`hooks/*.sh`, `hooks/lib/`)". Sessions:
   `enforcement/commit-gate.md`, `enforcement/branch-isolation-and-session-hooks.md`, then
   `enforcement/ci-gates-and-doc-truth.md` and `testing/test-suite.md` from "Then also".
3. `check_claims.py enforcement/commit-gate.md` returns 21 `ok` (measured 2026-10-16 claim count;
   the hash rule is proven on all 772 line-range items, see A1).
4. The agent reads the page and presents it for a person: why the hook exists, what breaks when it
   is touched, where its tests live, and `docs/solutions/` entries whose tags match.
5. The newcomer says done. The agent names the next page in the focus list. Nothing is written.

## Error behavior

| Condition | Behavior |
|---|---|
| `openwiki/` absent (exit 2) | Say the path checked; run the fallback tour. |
| `--status` exit 1 (`behind N`) | Warn with N; continue; suggest `openwiki code --update`. |
| `--status` exit 3 (`unknown-drift`) | Say the reason; treat every page as unverified unless its claim check passes; continue. |
| Claims file missing for a page (exit 3) | Present the page marked unverified. |
| Page missing from the wiki (exit 4) | Say the page is not in the wiki; skip it; offer the next page or the section list. |
| Claim `stale`, `missing`, or `unknown` | List it under "verify before relying"; never state it as fact. |
| code-review-graph server not connected | Skip it without blocking. |
| Focus text matches no routing row | Say so and offer the section list. |

**Fallback tour order (no wiki).** `CLAUDE.md`; `techstacks/*.md`;
`docs/solutions/critical-patterns.md`; `rules/`; then the 5 (budget) top-level directories with the
most commits in the last 90 days (budget) from `git log`; plus the code-review-graph architecture
overview when connected. No claim check applies; the skill says so.

## Tests

- **Unit (truth tier):** `test_check_claims.py` builds a temp repo with a claims file and checks:
  matching lines give `ok`; an edited line gives `stale`; a matching and an edited whole file
  (`repo-file-v1`) give `ok` and `stale`; a deleted file and a range past end of file give
  `missing`; an unknown prefix gives `unknown`; no `openwiki/` gives exit 2; no claims file gives
  exit 3; a missing page gives exit 4, also when its claims file is missing; `--status` gives
  `current`, `behind N`, and `unknown-drift` for a missing `.last-update.json` and for a
  non-ancestor `gitHead`.
- **Static (traceability tier):** the existing frontmatter, allowed-tools conformance, word
  ceiling, and runtime-neutral checks in `bash scripts/run-tests.sh`.
- **Behavioral run (truth tier for the recorded run only):** one run in this repo, recorded as `###
  Verify` rows: status, the commit-gate page check, focus "change a hook", and the deployed
  `.claude/skills/onboarding/scripts/check_claims.py` existing after `bash
  scripts/deploy-harness.sh`.

## Success criteria

- SC-1: `check_claims.py --status` in this repo reports `behind N` with N equal to
  `git rev-list --count <gitHead>..HEAD`, where `<gitHead>` is read from `.last-update.json`.
- SC-2: `check_claims.py enforcement/commit-gate.md` exits 0 with every claim `ok`.
- SC-3: Editing one cited line, or one whole-file-evidence file, in a temp copy makes the script
  report that claim `stale` and exit 1.
- SC-4: Focus "I will change a hook" selects only the enforcement pages and their "Then also"
  pages from the routing table.
- SC-5: With `openwiki/` absent, the skill names the checked path and produces the fallback tour.
- SC-6: withdrawn by DC1 (no saved progress).
- SC-7: `bash scripts/run-tests.sh` prints `ALL GREEN`.

## Non-goals

- Generating, refreshing, or editing the wiki or `openwiki/INSTRUCTIONS.md`.
- Committing an onboarding document into the consumer repo.
- Changes to hooks, `settings.json`, deploy scripts, or the Codex adapter.
- A web or HTML view of the tour.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | The `repo-lines-v1` hash is `sha256` of the cited lines joined by `\n` with a trailing `\n` | truth: Local, 2026-10-16, all 772 `repo-lines-v1` items in `openwiki/.claims/**` recomputed and matched | SC-2, unit tests | Every claim reads `stale`; fall back to approach 3 for verification and report the format gap |
| A2 | The quickstart routing table keeps its three-column `Read first / Then also` shape across OpenWiki runs | none yet — Inference: one sample, OpenWiki 0.7.2 | accepted risk: one generator version observed | Focus mode falls back to matching section index descriptions |
| A3 | `.harness-state/` is gitignored in consumer repos | provenance: Local, 2026-10-16, `.gitignore:30` in this repo | retired by DC1 | Progress could be committed by accident; write it under `.claude/` instead |
| A4 | `deploy-harness.sh` ships `skills/<name>/scripts/` to consumers | provenance: Local, 2026-10-16, `scripts/deploy-harness.sh` syncs `skills` as a whole directory (`cp -R`) | a `### Verify` row: `.claude/skills/onboarding/scripts/check_claims.py` exists after `bash scripts/deploy-harness.sh` | Add the path to the deploy allow-list |
| A5 | The `repo-file-v1` hash is `sha256` of the raw file bytes | truth: Local, 2026-10-16, all 23 `repo-file-v1` items in `openwiki/.claims/**` recomputed and matched | unit tests | Whole-file claims read `stale`; report the format gap |
| A6 | OpenWiki emits only these two evidence formats | none yet — Inference: one generator version (0.7.2) observed | accepted risk: other prefixes report `unknown`, never `ok` | A newer format is never verified until the script learns it |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| Wiki prose outside cited claims is correct | Only claims carry evidence; prose is presented as the wiki's view |
| A claim marked `ok` is true | `ok` means the cited lines are unchanged since generation, not that the statement was right |
| The tour covers the whole codebase | It covers what the wiki or fallback sources cover |
| Page quality holds on a large application repo | The only sample is this harness repo |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Claim verification is a stdlib script recomputing the `repo-lines-v1` and `repo-file-v1` hashes; other formats report `unknown` | Deterministic, unit-testable; a moved block reads as stale | settled |
| D2 | One session per wiki page, grouped by section | Progress is tracked per page | settled |
| D3 | Progress keyed on a slug of `git config user.email`, overridable by a name argument | No prompt on the common path; ask once only when both are missing | superseded by DC1 |
| D4 | Fallback order: `CLAUDE.md`, `techstacks/`, critical patterns, `rules/`, most-changed directories, graph overview when connected | A tour exists without a wiki; no claim check applies | settled |
| D5 | Mode is chosen by argument text: empty, `status`, or focus text | No subcommand syntax to learn | settled |
| D6 | No new MCP server or dependency; the wiki is read as files | Works wherever the files exist | settled |
| D7 | No saved progress; each run starts fresh and the skill writes no file | Fully read-only; no `Write` tool; no state to gitignore; no resume across sessions | settled |
| D8 | SKILL.md names the script by its deployed path `.claude/skills/onboarding/scripts/check_claims.py`; no deploy-script change | Works in this repo after deploy and in consumers; Codex alpha path unverified | settled |

## Decision changes

- DC1 — 2026-10-16 — reopens D3 — evidence: `hooks/branch-isolation-guard.sh:74-82,166` denies a
  Write outside `specs/` on `main`, and `scripts/install-harness.sh:198-281` adds no
  `.harness-state/` ignore (research-brief.md); the user chose "No saved progress" — new
  decision: D7
- DC2 — 2026-10-16 — reopens D1 (adds where the script is named) — evidence:
  `scripts/deploy-harness.sh:420-440` rewrites only named helper paths, so a new skill-script
  path is not rewritten for consumers; deploy changes are out of scope; the user chose the
  deployed path — new decision: D8
