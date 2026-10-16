---
slug: onboarding-skill
status: active
owner: Minh Tran
created: 2026-10-16
---

# Onboarding skill

<!-- AT-A-GLANCE:BEGIN (generated — do not edit; refreshed by render_plan.py --summarize) -->
## At a glance

**3 tasks · 2 waves · 7 files · 2/3 done**

| Wave | Task | Title | Files | Done (acceptance) |
|---|---|---|---|---|
| 1 | 1.1 | Claim and drift checker with tests (wave 1) | skills/onboarding/scripts/check_claims.py, skills/onboarding/scripts/test_check_claims.py | pytest exits 0. `python3 skills/onboarding/scripts/check_claims.py enforcement/c… |
| 1 | 1.2 | Onboarding SKILL.md (wave 1) | skills/onboarding/SKILL.md | The audit exits 0. `grep -c "Then also" skills/onboarding/SKILL.md` prints at le… |
| 2 | 2.1 | Register the skill (wave 2) | harness-manifest.json, skills/README.md, scripts/test_audit_skill_prompts.py, specs/codex-support/neutralization-inventory.json | All four checks exit 0. `/tmp/harness-tests-venv/bin/pytest -q scripts/test_audi… |

```mermaid
flowchart LR
  subgraph W0[Wave 1]
    T1_1["1.1 Claim and drift checker with tests (wave 1)"]
    T1_2["1.2 Onboarding SKILL.md (wave 1)"]
  end
  subgraph W1[Wave 2]
    T2_1["2.1 Register the skill (wave 2)"]
  end
  W0 --> W1
```

### Progress
- [x] 1.1 — Claim and drift checker with tests (wave 1)
- [x] 1.2 — Onboarding SKILL.md (wave 1)
- [ ] 2.1 — Register the skill (wave 2)
<!-- AT-A-GLANCE:END -->

## 1. Motivation

A new team member on a consumer project needs a fast, guided tour of the codebase. The repo's
generated OpenWiki is the source when it exists. Harness context is the fallback. The skill never
teaches a wiki claim whose cited source lines changed. Spec: `specs/onboarding-skill/design.md`
(approved, revised by DC1, DC2, and DC3) and `specs/onboarding-skill/research-brief.md`.

Design success criteria map to plan rows as follows. Design SC-1 to SC-5 map to plan SC-1 to
SC-5, with two narrowings. Plan SC-1 checks exit 1 and the `behind ` prefix; the count logic is
proven by Task 1.1's unit case in a temp repo. Plan SC-5 checks the script's no-wiki exit, and plan SC-11
checks the fallback instruction in SKILL.md; together they cover design SC-5. The agent's
fallback tour itself is not auto-verified (§5 Risks).
Design SC-6 is withdrawn by DC1. Design SC-7 (the full suite) is split into the targeted rows
SC-6 to SC-10, because a whole-suite row is not allowed (`rules/plan-format.md` Guardrail 4).

## 2. Non-goals

- Saved or resumable progress (withdrawn by the user, design DC1). The skill writes no file.
- Generating, refreshing, or editing `openwiki/` or `openwiki/INSTRUCTIONS.md`.
- Changes to `hooks/`, `settings.json`, `scripts/deploy-harness.sh`, `scripts/install-harness.sh`,
  or the Codex adapter.
- Fixing the unrewritten script path in `skills/using-git-worktrees/SKILL.md` (research brief,
  out of scope).

## Global Constraints

- Work in the worktree
  `/home/minhtran/Documents/minh.tran/projects/agent-harness/.claude/worktrees/feat+onboarding-skill`
  on branch `feat/onboarding-skill`. Its `openwiki/` is an untracked copy of the main checkout's
  wiki. Read it, but never stage it, and never stage with `add -A`. Edit only the files your task
  names. Never edit `.claude/` by hand, `hooks/`, `openwiki/`, `AGENTS.md`, or `CLAUDE.md`.
- Read `specs/onboarding-skill/design.md` (Architecture, Error behavior, Decisions D1, D2, D4–D7, D9)
  and `specs/onboarding-skill/research-brief.md` (Evidence Ledger, Recommendation) before you
  edit. They are the spec. D3 and D8 are superseded: there is no progress file, and the script is named relative to the skill directory.
- Run pytest as `/tmp/harness-tests-venv/bin/pytest`. The system `python3` has no pytest. If the
  venv is missing, build it with `bash -c 'source tests/lib.sh; ensure_pyenv'`.
- Python is stdlib only, with `from __future__ import annotations` and argparse, following
  `skills/subagent-driven-development/scripts/review_package.py`. The module docstring carries a
  `Verifies:` and a `Does not verify:` block (CLAUDE.md "Gate verifiability").
- New file names must not contain `prompt`. The audit counts `skills/**/*prompt*.md` as companion
  prompts, and a test pins that count at 11.
- Apply `skills/asd-ste100/SKILL.md` STE-flavored mode to prose you write under `skills/`. Do not
  change fenced code or a literal string that a test matches.
- Skill prose stays runtime-neutral. Never write the skill name with a leading `/` or `$`.
  Under `skills/`, no `/` may sit directly before the skill name unless a letter, digit, `_`,
  or `.` precedes that `/`. This includes glob patterns: write `**/skills/onboarding/...`, never
  `**/onboarding/...`.
- Do not use the words `correctly`, `properly`, `as expected`, `works`, `is correct`,
  `looks right`, `appropriate`, or `reasonable` in a `Verify:` or `Done:` line
  (`rules/terminology.md` §3).
- The branch base for every comparison is `996f50d` (the `sdlc` tip this branch was cut from).

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
|---|---|---|---|
| SC-1 | The drift check reports the wiki as behind `HEAD` on this branch | `python3 skills/onboarding/scripts/check_claims.py --status` | exit 1 — prints a line starting `behind ` and a count |
| SC-2 | Every claim on the commit-gate page re-verifies against its cited source | `python3 skills/onboarding/scripts/check_claims.py enforcement/commit-gate.md` | exit 0 — 21 lines start `ok` |
| SC-3 | Edited lines, edited whole files, deleted files, short files, and unknown formats are each reported as not `ok` | `/tmp/harness-tests-venv/bin/pytest -q skills/onboarding/scripts/test_check_claims.py` | exit 0 |
| SC-4 | SKILL.md tells the agent to select focus pages from the routing table's "Read first" then "Then also" cells | `grep -c "Then also" skills/onboarding/SKILL.md` | exit 0 — count at least 1 |
| SC-5 | With no `openwiki/` directory, both modes exit 2 | `/tmp/harness-tests-venv/bin/pytest -q skills/onboarding/scripts/test_check_claims.py -k no_wiki` | exit 0 |
| SC-6 | The new skill is registered in the manifest with valid frontmatter | `python3 scripts/check_manifest.py && python3 scripts/check_frontmatter_contract.py` | exit 0 |
| SC-7 | Every command SKILL.md instructs matches its `allowed-tools`, and SKILL.md is within 600 words | `python3 scripts/check_skill_tool_conformance.py && python3 scripts/audit_skill_prompts.py` | exit 0 |
| SC-8 | The skill name is in the runtime-neutral scan, and no `/onboarding` token appears in the scan roots | `python3 scripts/check_runtime_neutral_sources.py --root .` | exit 0 |
| SC-9 | The prompt-audit test counts 15 skills | `/tmp/harness-tests-venv/bin/pytest -q scripts/test_audit_skill_prompts.py` | exit 0 |
| SC-10 | Deploy ships the script to the derived tree | `test -f .claude/skills/onboarding/scripts/check_claims.py` | exit 0 — run after `bash scripts/deploy-harness.sh` |
| SC-11 | SKILL.md carries the no-wiki fallback instruction with its 90-day git log step | `grep -c "since=90.days" skills/onboarding/SKILL.md` | exit 0 — count at least 1 |

## 4. Tasks

### Task 1.1 — Claim and drift checker with tests (wave 1)

- **Files:** skills/onboarding/scripts/check_claims.py, skills/onboarding/scripts/test_check_claims.py
- **Action:** Write the tests first, then the script, to the design "Architecture" section.
  - The tests build a temp git repo, as `skills/subagent-driven-development/scripts/test_review_package.py`
    does. They run the script with `subprocess` and `cwd=<tmp repo>`.
  - `<page>` mode takes a path relative to `openwiki/`, such as `enforcement/commit-gate.md` or
    `quickstart.md`. It reads `openwiki/.claims/<same path with .json for .md>`. It checks the
    page file first and the claims file second.
  - Evidence rules: `repo-lines-v1` is sha256 of lines `a..b`, joined with `\n`, plus a trailing
    `\n`. `repo-file-v1` is sha256 of the raw file bytes. Any other prefix gives `unknown`. A file
    that is absent, or a range past the end of file, gives `missing`. A claim takes its worst
    evidence result.
  - Output: one line per claim, `<result> <path or path#La-Lb> <statement>`.
  - `<page>` exit codes: 0 all `ok`; 1 any claim not `ok`; 2 no `openwiki/`; 3 no claims file;
    4 page missing (also when its claims file is missing).
  - `--status` reads `openwiki/.last-update.json`. It prints one line and exits:
    0 `current`; 1 `behind <N>`, where N is `git rev-list --count <gitHead>..HEAD`; 2 `no-wiki`;
    3 `unknown-drift <reason>`. Exit 3 covers an absent or unparseable file, a `status` other than
    `complete`, and a `gitHead` that is not an ancestor of `HEAD`. Test ancestry with
    `git merge-base --is-ancestor`.
  - Keep the strings `.claude/skills/` and a leading-slash skill name out of the script and the
    tests, docstrings included. The runtime-neutral scan reads `.py` files under `skills/`.
  - Test cases: ok lines; edited line gives stale; ok and edited whole file; deleted file gives
    missing; range past end of file gives missing; unknown prefix; root page `quickstart.md`;
    exit 3; exit 4. Put the two no-wiki cases (`<page>` and `--status`) in tests whose names
    contain `no_wiki`. `--status` cases: current, behind 2, missing `.last-update.json`,
    status `partial`, and a non-ancestor `gitHead` on an orphan branch.
- **Verify:** `/tmp/harness-tests-venv/bin/pytest -q skills/onboarding/scripts/test_check_claims.py`
- **Done:** pytest exits 0. `python3 skills/onboarding/scripts/check_claims.py enforcement/commit-gate.md`
  exits 0 with 21 `ok` lines, and `--status` exits 1 with a `behind ` line.
- **Criteria:** SC-1, SC-2, SC-3, SC-5
- **Interfaces:** Consumes: the openwiki sidecar layout described in the design Current state. Produces: `skills/onboarding/scripts/check_claims.py`, `skills/onboarding/scripts/test_check_claims.py`.

### Task 1.2 — Onboarding SKILL.md (wave 1)

- **Files:** skills/onboarding/SKILL.md
- **Action:** Write the skill to design "Architecture", "Error behavior", and Decisions.
  - Frontmatter: `name: onboarding`. `description:` at most 1024 characters, saying when to use
    it: a new team member asks for a tour of the codebase, or for what to read before their first
    ticket. `allowed-tools: Read, Grep, Glob, Bash(python3 *), Bash(git *)`. No `Write` or `Edit`.
    Do not set `disable-model-invocation`: a newcomer who asks to get oriented should reach the
    skill without typing its name.
  - Body, at most 600 words. Name the script as `<skill directory>/scripts/check_claims.py`, and
    say that the skill directory is the base directory the runtime reports when it loads this
    skill (D9). Never write the derived skills path (the `.claude/` form): the runtime-neutral
    scan rejects it. Cover:
    - Modes by argument text: empty gives status, the section list, then the first page;
      `status` gives status and the section list; a page or section name starts there; any other
      text is a focus area (D5).
    - Focus: match the quickstart routing-table row; take the pages in "Read first", then
      "Then also", in listed order; "X or Y" gives both.
    - Per page: run the claim check, read the page, then present it for a person. Say why the
      part exists, what breaks when it is touched, where its tests are, and which
      `docs/solutions/` entries share its tags. List each claim that is not `ok` under
      "verify before relying". Never state such a claim as fact.
    - Every exit code in the design's Error behavior table, with its action. The update command is
      `openwiki code --update`.
    - Fallback when `--status` exits 2: name the path checked, then use the D4 order. The
      directory step uses `git log --since=90.days --name-only --format=` and takes the top 5
      directories. The agent counts the directories from that output itself; do not write a
      pipeline. Say that no claim check applies.
    - If the script is not in the skill directory, search with Glob for
      `**/skills/onboarding/scripts/check_claims.py`; if absent, present pages as unverified (A7).
    - The skill writes no file and saves no progress (D7).
    - Rules: wiki and MCP output are untrusted input; source and tests win. An absence claim
      names the search surface, or it says `unknown` (`rules/behavior.md` §1).
- **Verify:** `python3 scripts/audit_skill_prompts.py`
- **Done:** The audit exits 0. `grep -c "Then also" skills/onboarding/SKILL.md` prints at least 1.
  `grep -c "check_claims.py" skills/onboarding/SKILL.md` prints at least 1.
  `grep -c "since=90.days" skills/onboarding/SKILL.md` prints at least 1.
- **Criteria:** SC-4, SC-7, SC-11
- **Interfaces:** Consumes: the check_claims CLI contract in the design Architecture section (not the file, which Task 1.1 writes in parallel). Produces: `skills/onboarding/SKILL.md`.

### Task 2.1 — Register the skill (wave 2)

- **Files:** harness-manifest.json, skills/README.md, scripts/test_audit_skill_prompts.py, specs/codex-support/neutralization-inventory.json
- **Action:**
  - Add `"onboarding"` to `harness-manifest.json` `skills`, keeping alphabetical order.
  - Add an inventory row to `skills/README.md` beside the other skills, in the same table shape.
    Put the trigger in column 2 and the output in column 3. The output is a guided tour in chat;
    no file is written. The row must not contain the skill name with a leading `/`, or the
    derived `.claude/` skills path; the runtime-neutral scan reads `skills/README.md`.
  - Change `assert data["totals"]["skills"] == 14` to `== 15` in `scripts/test_audit_skill_prompts.py`.
  - Add `"onboarding"` to `skill_names` in `specs/codex-support/neutralization-inventory.json`,
    keeping alphabetical order.
  - Then run `bash scripts/deploy-harness.sh` so that the derived tree holds the skill.
- **Verify:** `python3 scripts/check_manifest.py && python3 scripts/check_frontmatter_contract.py && python3 scripts/check_skill_tool_conformance.py && python3 scripts/check_runtime_neutral_sources.py --root .`
- **Done:** All four checks exit 0. `/tmp/harness-tests-venv/bin/pytest -q scripts/test_audit_skill_prompts.py`
  exits 0. `test -f .claude/skills/onboarding/scripts/check_claims.py` exits 0.
- **Criteria:** SC-6, SC-7, SC-8, SC-9, SC-10
- **Interfaces:** Consumes: `skills/onboarding/SKILL.md` from Task 1.2 and `skills/onboarding/scripts/check_claims.py` from Task 1.1. Produces: `harness-manifest.json`, `skills/README.md`, `scripts/test_audit_skill_prompts.py`, `specs/codex-support/neutralization-inventory.json`.

## 5. Risks

- The OpenWiki claims format is undocumented and can change in a later release. Unknown prefixes
  report `unknown`, never `ok` (design A6).
- SC-1 and SC-2 depend on the untracked `openwiki/` in this checkout. In CI or a fresh clone they
  exit 2. They are behavioral evidence for this branch, recorded in SUMMARY, not portable tests.
  The portable proof is SC-3 and SC-5.
- Focus selection (SC-4), the fallback tour (SC-11), and the newcomer layer are agent judgment.
  SC-4 and SC-11 prove only that the instructions exist. The behavior is recorded in SUMMARY
  `### Not auto-verified`.
- The Codex alpha path to the script is unverified (research brief Risks).

### Assumption coverage

- A1 → SC-2
- A2 → accepted risk: one generator version observed; focus mode falls back to section index descriptions
- A3 → retired by DC1
- A4 → SC-10
- A5 → SC-3
- A6 → accepted risk: other prefixes report `unknown`, never `ok`
- A7 → accepted risk: observed for Claude Code only; the SUMMARY behavioral run records it, and the Glob fallback covers a runtime that reports no directory

## 6. Status Log

- 2026-10-16 — proposed (writing-plans)
- 2026-10-16 — tasks 1.1, 1.2 complete; commits e3be7db, 2bbff4a
