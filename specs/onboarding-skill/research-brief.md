# onboarding-skill — Research Brief

Written 2026-10-16. Pins: repo 7a39185; OpenWiki 0.7.2 (output observed in `openwiki/`, generated at 996f50d)

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | build from scratch, reusing harness conventions (no upstream verifier exists) |
| **Why this is the lightest credible path** | OpenWiki ships no claim-verify command, and every registration point a new skill needs is already mechanical and listed below |
| **Confidence** | 85% |
| **Next step** | User decides the two design changes in "Risks"; then `writing-plans` |

Depth: **Deep** (intake lane `high-risk`). No upgrade or waiver. The re-run classifier adds no
signal: the change adds no dependency, schema, or entry point, and the external surface is the
read-only OpenWiki file format.

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Claude Code skill framework and workflow harness (meta-repo) |
| Primary language + runtime | Markdown skills; Bash hooks; Python 3 stdlib scripts |
| Frameworks / platforms | Claude Code (established); Codex advisory alpha (not GA) |
| Relevant packages | none added; OpenWiki 0.7.2 is an external CLI whose output is read as files |
| Detectable versions | OpenWiki 0.7.2 (`.github/workflows/openwiki-update.yml` installs `openwiki@0.7.2`) |
| Important constraints | 600-word SKILL.md ceiling (budget); runtime-neutral skill prose; branch-isolation guard on Write/Edit; `.claude/` is derived |

---

## Feature Understanding and Assumptions

- **Requested feature:** a skill that onboards a new team member to a consumer codebase fast,
  using OpenWiki when present (`specs/onboarding-skill/intent.md` @ 5e8513c, design @ 7a39185).
- **What success appears to mean:** design SC-1 to SC-7.
- **Assumptions from the request:** a newcomer runs the skill in a consumer repo where the harness
  is installed, often on the default branch.
- **Assumptions still needing confirmation:** the two design changes under "Risks".

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/check_manifest.py:93-99` fails when a `skills/<name>/SKILL.md` exists but is missing from `harness-manifest.json` `skills`, and the reverse. |
| `Local` | `scripts/check_frontmatter_contract.py` requires non-empty `name:` and `description:`, with `name:` equal to the register key, for every skill in the manifest. |
| `Local` | `scripts/audit_skill_prompts.py:21-22`: description at most 1024 characters (budget), SKILL.md at most 600 words (budget). |
| `Local` | `scripts/test_audit_skill_prompts.py:145` asserts `totals.skills == 14` (measured 2026-10-16). Adding a skill makes it 15. This test must change. |
| `Local` | `scripts/check_skill_tool_conformance.py` requires every shell command in SKILL.md and `references/*.md` to match an `allowed-tools` `Bash(...)` pattern, also after stripping `.claude/`. |
| `Local` | `scripts/check_ste_baseline.py` is warn-only. A file missing from `scripts/ste-baseline.json` has baseline 0. |
| `Local` | `scripts/generate_skill_eval_corpus.py` covers 13 of 14 skills (`test_generate_skill_eval_corpus.py:17`, measured 2026-10-16). An entry is optional. |
| `Local` | `scripts/check_runtime_neutral_sources.py` flags `/<name>` only for names in `specs/codex-support/neutralization-inventory.json` `skill_names`. That list does not hold `session-retro` or `asd-ste100`. Adding `onboarding` makes the runtime-neutral constraint mechanically checked. No `/onboarding` token exists in the scan roots today (grep, 2026-10-16). |
| `Local` | `scripts/render_codex_adapter.py:164-177,252` copies every manifest skill into the Codex plugin. No per-skill adapter edit is needed. |
| `Local` | `scripts/deploy-harness.sh` copies `skills/` whole (`cp -R`), so `skills/onboarding/scripts/` ships. Its `rewrite_derived_paths` rewrites only named helper paths: `scripts/<CONSUMER_SCRIPTS>`, `harness-manifest.json`, `render_plan.py`, and `skills/asd-ste100/scripts/ste-lint.py` (lines 420-440). A new `skills/onboarding/scripts/check_claims.py` mention is **not** rewritten. `tests/scripts/consumer-subset.test.sh:96-103` is the test that pins the asd-ste100 rewrite. |
| `Local` | The deployed `.claude/skills/using-git-worktrees/SKILL.md:4,10` still names `skills/using-git-worktrees/scripts/detect-isolation.sh`. That path does not resolve from a consumer root. This is a latent bug in another skill and out of scope here. |
| `Local` | `scripts/lint-doc-truth.sh:12,32` scans only `CLAUDE.md`, `README.md`, `HARNESS.md`, `skills/README.md`, `agents/*.md`, and `rules/*.md`. It maps `.claude/...` to the root source. It does not scan `skills/*/SKILL.md`. |
| `Local` | `hooks/branch-isolation-guard.sh:11-15,74-82,166`: on a shared branch (default `main master`), a Write or Edit is allowed only when every path is under `specs/`. A Write to `.harness-state/onboarding/<key>.json` on `main` is **denied**. The guard is registered on Write and Edit only. Bash is not judged by it. |
| `Local` | `scripts/install-harness.sh:198-281` appends `.claude/` and `specs/**/events.jsonl.lock` to a consumer's `.gitignore`. It does **not** add `.harness-state/`. This repo ignores it at `.gitignore:30`, but consumers do not get that line. Design A3 is false for consumers. |
| `Local` | Existing `.harness-state/` writers: `runtime/runtime_mode.py:217` creates its directory with `mkdir(parents=True, exist_ok=True)`. `subagent-driven-development` writes `.harness-state/sdd/` from a task branch, so the guard never blocks it. |
| `Local` | Script conventions (`skills/subagent-driven-development/scripts/review_package.py`, `test_review_package.py`): shebang, a one-line docstring, `from __future__ import annotations`, argparse, stdlib only, sibling paths resolved from `Path(__file__)`. Tests load the module with `importlib`, build a temp repo with `git -C <tmp> init/add/commit`, and pass `-c user.name=t -c user.email=t@t`. |
| `Local` | Evidence formats in `openwiki/.claims/**`: 772 `repo-lines-v1` and 23 `repo-file-v1` items (measured 2026-10-16, Python sweep). Every hash was recomputed and matched. |
| `Docs` | OpenWiki code mode: "Each Claim points to exact repository evidence such as `repo://src/server.ts#L40-L82`" with "the evidence version OpenWiki observed". The hash method and sidecar schema are **not documented**. |
| `Docs` | The CLI reference lists `openwiki code --init`, `openwiki code --update`, and `openwiki code --update --print`. Plain `openwiki --update` also runs code mode. It lists no claim-verify command. |
| `Docs` | `.last-update.json` is "metadata for the last successful documentation check (including no-op updates)". Its fields are not documented. |
| `Upstream` | `langchain-ai/openwiki` README: Grounded Claims "track material facts back to versioned source evidence and surface them when the evidence changes". Search found no public description of `repo-lines-v1`. |
| `Inference` | The claims format is an undocumented internal format. It can change in any OpenWiki release. The local recomputation is the only proof of the hash rule. |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** `harness-manifest.json`; `skills/README.md`
  inventory table; `scripts/check_manifest.py`; `scripts/check_frontmatter_contract.py`;
  `scripts/audit_skill_prompts.py` and its test; `scripts/check_skill_tool_conformance.py`;
  `scripts/check_runtime_neutral_sources.py` with its inventory; `scripts/deploy-harness.sh`;
  `tests/scripts/consumer-subset.test.sh`; `hooks/branch-isolation-guard.sh`;
  `scripts/install-harness.sh`.
- **Existing abstractions or extension points:** the manifest `skills` list drives the frontmatter
  check, the manifest check, and the Codex adapter. Skill-local `scripts/` with a co-located
  `test_*.py` is auto-collected by `scripts/run-tests.sh:191`.
- **Conventions worth preserving:** stdlib-only Python; a `Verifies:` / `Does not verify:` block
  in a script docstring (CLAUDE.md "Gate verifiability"); temp-repo tests; `allowed-tools` naming
  exact command patterns.
- **What can likely be reused:** the `review_package.py` and `test_review_package.py` skeleton;
  the `mkdir(parents=True, exist_ok=True)` pattern from `runtime_mode.py`.
- **What appears missing locally:** any onboarding skill (searched `skills/`, `skills/README.md`);
  any `.harness-state/` gitignore for consumers (searched `scripts/install-harness.sh`,
  `scripts/deploy-harness.sh`, `templates/structure/`).

Required registration for the new skill:

| Item | Required by | Required? |
|---|---|---|
| `harness-manifest.json` `skills` entry | `check_manifest.py`, frontmatter check, Codex adapter | yes |
| `skills/README.md` inventory row | design; `lint-doc-truth.sh` checks its paths | yes |
| `test_audit_skill_prompts.py` count 14 to 15 | the test fails otherwise | yes |
| frontmatter `name`, `description`, `allowed-tools` | frontmatter and conformance checks | yes |
| `neutralization-inventory.json` `skill_names` entry | makes runtime-neutral prose checked | recommended |
| `ste-baseline.json` entry | warn-only; missing means 0 | no |
| eval corpus entry | coverage is already 13 of 14 | no |

---

## Upstream Findings

- **Repositories inspected:** `github.com/langchain-ai/openwiki` (README via search); the
  `wijzer` Claude Code plugin listing (format-compatible with OpenWiki; not inspected in depth).
- **Pattern or capability already present upstream:** OpenWiki reconciles stale claims inside
  `openwiki code --update`. It runs a model and needs an API key. It offers no offline check
  that a newcomer could run.
- **Files, modules, or areas worth modeling:** none. The sidecar layout is the only interface.
- **How closely the upstream pattern matches this repo:** close in data, not in tooling.
- **Any upstream gaps or uncertainties:** the hash format is undocumented (see Docs).

---

## Docs Findings

- **Official sources checked:** OpenWiki quickstart, code mode, and CLI reference on
  docs.langchain.com.
- **Version-matched vs latest-stable status:** the docs are unversioned. They are read as current
  on 2026-10-16. The local wiki is 0.7.2.
- **Built-in capabilities that already support the feature:** `openwiki visualize` gives a human
  browser view. It does no claim checks and no guided order. The `openwiki_search` and
  `openwiki_read` retrieval tools named in `AGENTS.md` come from `openwiki integrations install`.
  They are optional.
- **Current recommended APIs or workflows:** `openwiki code --update` (or `openwiki --update`) to
  refresh. The design's suggested command is correct.
- **Important caveats, deprecations, or migration notes:** "Running `--init` again replaces the
  existing generated repository wiki and Claims." Progress keys can point at pages that a re-init
  removes. Design exit 4 covers that case.

---

## Recommendation

- **Primary recommendation:** build the skill and its script as designed, with two changes:
  1. **Progress is written by the script, through Bash.** A `check_claims.py --mark <page>
     done|skipped [--person <name>]` mode writes `.harness-state/onboarding/<key>.json`. On first
     write it also creates `.harness-state/onboarding/.gitignore` containing `*`. Reason: the
     branch-isolation guard denies the Write tool on `main`, where a newcomer usually is. Also,
     consumers do not gitignore `.harness-state/`. `allowed-tools` then drops `Write`.
  2. **SKILL.md names the script by its deployed path,** `.claude/skills/onboarding/scripts/
     check_claims.py`. It also says that the script lives in this skill's own directory.
     Reason: deploy does not rewrite new skill-script paths. The out-of-scope list forbids deploy
     changes. The doc-truth lint does not scan SKILL.md, and the tool-conformance check strips
     `.claude/` before matching.
- **Why this is the lightest credible path:** neither change touches hooks, deploy, or the
  installer. Both stay inside the new skill.
- **Why the next-best alternative lost:**
  - Adding `.harness-state/` to the installer's gitignore append changes `install-harness.sh`.
    That is a deploy script, which the intent's Out of scope excludes.
  - A specs-style exemption in the guard edits a hook, a high-blast file.
  - A rewrite pattern in `deploy-harness.sh` follows the asd-ste100 precedent, but it is also out
    of scope.
- **What would change this recommendation:** if you allow deploy-script changes, the rewrite
  pattern plus a `consumer-subset.test.sh` row is the more consistent path for change 2.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - The claims format is undocumented. A new OpenWiki release can change it. Design A6 turns that
    into `unknown` results, never false `ok` results.
  - The Codex alpha copies the skill into a plugin directory where `.claude/` does not exist. The
    script path there is not verified. Codex is advisory and not GA.
- **Evidence gaps:** content quality on a large application repo (design "What we do not
  claim"); the `.last-update.json` fields are observed only, not documented.
- **Version uncertainties:** one generator version (0.7.2) is observed.
- **Follow-up questions for the user:** design changes 1 and 2 above alter approved design text
  (Architecture, Worked trace step 5, A3, A4, and allowed-tools). Under `rules/auto-correct-scope.md`
  Rule 4, they need your approval and a `DC1` entry before planning.

---

## Source Pack

- **Local files read:** `harness-manifest.json`; `scripts/check_manifest.py`;
  `scripts/check_frontmatter_contract.py`; `scripts/audit_skill_prompts.py`;
  `scripts/test_audit_skill_prompts.py`; `scripts/check_skill_tool_conformance.py`;
  `scripts/check_ste_baseline.py`; `scripts/ste-baseline.json`;
  `scripts/generate_skill_eval_corpus.py`; `scripts/test_generate_skill_eval_corpus.py`;
  `scripts/check_runtime_neutral_sources.py`; `specs/codex-support/neutralization-inventory.json`;
  `scripts/render_codex_adapter.py`; `adapters/runtime-entry-bindings.json`;
  `scripts/deploy-harness.sh`; `scripts/install-harness.sh`; `scripts/lint-doc-truth.sh`;
  `scripts/run-tests.sh`; `tests/scripts/consumer-subset.test.sh`;
  `hooks/branch-isolation-guard.sh`; `runtime/runtime_mode.py`;
  `skills/subagent-driven-development/SKILL.md` and `scripts/review_package.py` with its test;
  `skills/using-git-worktrees/SKILL.md`; `skills/asd-ste100/SKILL.md`;
  `.github/workflows/openwiki-update.yml`; `openwiki/.claims/**`; `.gitignore`.
- **Upstream repositories or pages checked:** https://github.com/langchain-ai/openwiki (via
  search result); https://awesome.ecosyste.ms/projects/github.com%2Fgpxl%2Fwijzer
- **Official docs domains or pages checked:** https://docs.langchain.com/oss/openwiki/quickstart.md;
  https://docs.langchain.com/oss/openwiki/code-mode.md;
  https://docs.langchain.com/oss/openwiki/cli-reference

---

## Evidence Boundary

> Confirmed from artifacts: the registration table; the guard denies Write on `main` outside
> `specs/`; the installer adds no `.harness-state/` ignore; deploy ships but does not rewrite new
> skill-script paths; both hash rules (795 of 795 items); `openwiki code --update` is valid.
> Inferred from patterns: the claims format is unstable across releases; newcomers usually start
> on the default branch.
> Not checked: Codex alpha path resolution for skill scripts; OpenWiki output on a repo other than
> this one; whether `openwiki_search` tools are installed in any consumer.
