# intent-md-entry — Research Brief

Written 2026-10-10. Pins: repo 49a1c93 + uncommitted; git 2.43.0

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing — extend `feature-intake`, `intent-review`, and the SUMMARY template with prose; add one template file and one hook test |
| **Why this is the lightest credible path** | Every capability the design needs already exists: the skills already hold `git log`/`git diff`, `templates/` already ships to consumers, and `commit-gate.sh` already lets an intent-only commit through |
| **Confidence** | 85% |
| **Next step** | `/writing-plans` for `specs/intent-md-entry`, folding in the five plan-relevant findings under Local Findings |

Research depth: **Deep** (intake lane `high-risk`). No upgrade needed; no signal raised it further.

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Harness meta-repo: Markdown skills, bash hooks, Python scripts |
| Primary language + runtime | Bash, Python 3 (scripts/tests), Markdown (skills) |
| Frameworks / platforms | Claude Code skills/hooks; Codex advisory adapter (`adapters/codex`) |
| Relevant packages | none — no dependency manifest is touched |
| Detectable versions | git 2.43.0 (local) |
| Important constraints | `CLAUDE.md`: workflow-engine changes need a context-propagation audit; `rules/terminology.md` hard exclusion on `### Intent`; user note 2026-10-10: keep instructions lean |

---

## Feature Understanding and Assumptions

- **Requested feature:** anyone writes `specs/<slug>/intent.md` to the playbook standard, hands it
  to the team, and the workflow starts from it, with no GitHub issue and no SUMMARY needed to create
  it (SUMMARY `### Intent`, verbatim).
- **What success appears to mean:** design SC-1…SC-7 (`specs/intent-md-entry/design.md`).
- **Assumptions from the request:** approved design D1–D6 (intent file, `Status` field, SHA pin,
  stop on drift, `### Intake notes`, no new machinery).
- **Assumptions still needing confirmation:** none that change the recommendation.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `skills/feature-intake/SKILL.md:4` and `skills/intent-review/SKILL.md:4` already allow `Bash(git log *)` and `Bash(git diff *)` |
| `Local` | Only three places read `### Intent`: `skills/intent-review/SKILL.md:14`, `skills/intent-review/intent-reviewer-prompt.md:43`, `templates/SUMMARY.template.md:27`; plus the hard exclusion in `rules/terminology.md:26,78` and docs in `templates/structure/specs-README.md:30-31`, `skills/README.md:165` (grep for `### Intent` across skills, agents, scripts, hooks, rules, templates, runtime, adapters) |
| `Local` | `skills/subagent-driven-development/references/review-chain.md` delegates to the `intent-review` skill and says "do not copy it here" — the oracle logic has one owner |
| `Local` | `scripts/verify_summary.py` has no reference to `Intent` (grep `-i intent`), so a new `### Intake notes` section and an `Intent-source:` line do not touch its parser |
| `Local` | `scripts/install-harness.sh:34` payload includes `templates`; `scripts/deploy-harness.sh:591` syncs `templates` into `.claude/templates/` (present on disk) |
| `Local` | `hooks/commit-gate.sh` specs checks skip a slug when their own file is absent (escalations, lane evidence, run state); scratch-worktree run on 2026-10-10 exited 0 under standard and strict |
| `Local` | Evidence-type hook tests live in `tests/hooks/commit-gate-evidence.test.sh` (header: "escalation / lane-evidence / run-state"), not `commit-gate.test.sh` |
| `Local` | `scripts/lint-skill-bash.sh` (run by `run-tests.sh:39`) fails a skill whose bash fence uses an unassigned `$var`; blocks with `<placeholder>` are treated as illustrative |
| `Local` | `.claude/` is gitignored (`.gitignore:26`) and is where Claude Code loads skills; edits under `skills/` reach a session only after `bash scripts/deploy-harness.sh` |
| `Local` | `evals/skills/prompt-refactor/behavior/feature-intake.json` and `intent-review.json` exist; the prompt-refactor corpus is not run by `run-tests.sh` or CI (grep `skill_eval\|prompt-refactor` in both: no hit); `score_skill_eval.py --validate-corpus` exits 0 |
| `Docs` | `git diff --help` (2.43.0): `--exit-code` makes the exit status 1 on differences; `git log --help`: `--diff-filter=` selects Added (A) / Modified (M) / Deleted (D) … |
| `Upstream` | Claude Academy *AI-native SDLC playbook*, lesson "Capture as intent.md" (read 2026-10-10): intent.md template = Problem / Proposed outcome / Affected users and systems / Constraints / Open questions; product owner review then commit; "simplest home is an intent/ folder in the product repo" |
| `Upstream` | GitHub spec-kit (secondary sources, see Source Pack): specs at `specs/<NNN>-<feature>/`, templates filled by the agent, approval is a human review gate rather than a status field |
| `Inference` | The pin/drift command pair behaves as the design states — measured 2026-10-10 scratch-repo probe (untracked → empty pin; clean → 0; uncommitted edit → 1; deleted → 1; deleted-and-recreated untracked → 1; unknown SHA → 128); re-proven by design SC-5 |

---

## Local Findings

- **Relevant files:** `skills/feature-intake/SKILL.md` (74 lines), `skills/intent-review/SKILL.md`
  (44 lines), `skills/intent-review/intent-reviewer-prompt.md`, `templates/SUMMARY.template.md`,
  `rules/terminology.md`, `templates/structure/specs-README.md`, `skills/README.md`,
  `skills/feature-intake/tests/*.md`, `tests/hooks/commit-gate-evidence.test.sh`.
- **Extension points:** feature-intake procedure step 5 ("Write `SUMMARY.md` … including the user
  intent verbatim") is where the intent-file branch goes; intent-review "Establish a blind oracle"
  step 1 is where the drift check goes.
- **Conventions worth preserving:** intake test cases are Markdown tables run manually
  (`skills/feature-intake/tests/README.md`); hook tests use `new_repo` / `stage` / `run_hook` /
  `assert_rc_contains` from `tests/lib.sh`.
- **What can be reused:** both skills' existing git permissions; the template shipping path; the
  existing escalation rule for chat/intent conflicts.
- **Plan-relevant findings (not in the design text):**
  1. Put the intent-only hook test in `tests/hooks/commit-gate-evidence.test.sh` (the design names
     `commit-gate.test.sh`; the evidence file is where specs-scoped checks are tested).
  2. Write the git commands in the skills as inline code or with `<pin>`-style placeholders, not as
     bash fences with `$var`, or `lint-skill-bash.sh` fails.
  3. The dogfood run (SC-3–SC-5) must run `bash scripts/deploy-harness.sh` first, or the session
     still loads the old `.claude/skills` copies.
  4. In a consumer repo the template is at `.claude/templates/INTENT.template.md`; the skills keep
     the repo's existing convention of naming `templates/…` (the deployed feature-intake still reads
     `templates/SUMMARY.template.md`). The author-facing line in `specs-README.md` should name both.
  5. Optional, not required by any gate: add an intent-file case to
     `evals/skills/prompt-refactor/behavior/feature-intake.json`. Recommend skipping (YAGNI; the
     corpus is not wired to CI).
- **What is missing locally:** nothing the design depends on.

---

## Upstream Findings

- **Repositories inspected:** the playbook course (primary); GitHub spec-kit via secondary write-ups.
- **Pattern already present upstream:** a human-authored or human-corrected intent/spec file in the
  repo, reviewed before the next stage reads it.
- **Worth modeling:** the playbook's five intent sections (we add Out of scope and success, per
  design); spec-kit's `specs/<id>-<name>/` layout matches ours.
- **How closely it matches:** close on the artifact; neither upstream pins the intent to a commit
  or checks it at review — that part is ours.
- **Gaps:** spec-kit details come from secondary blogs, not the repo; not load-bearing for this design.

---

## Docs Findings

- **Official sources checked:** local `git diff --help`, `git log --help` (git 2.43.0).
- **Version-matched vs latest:** version-matched to the local git; `--exit-code` and
  `--diff-filter` are long-standing options.
- **Built-in capabilities:** `git log --diff-filter=AM` and `git diff --exit-code <commit> -- <path>`
  cover pinning and drift without any script.
- **Caveats:** none found for this use.

The change has no dependency or external-system surface; git is the only tool it relies on.

---

## Recommendation

- **Primary recommendation:** reuse existing — prose changes to two skills and two templates, one
  new template, one hook test, intake test cases, doc lines.
- **Why lightest:** no permission, script, gate, or installer change is needed (Evidence Ledger rows 1, 5, 6).
- **Why the next-best alternative lost:** a helper in `verify_summary.py` (design approach 1) would
  make the approval check deterministic but adds code the user asked to avoid; the git commands
  already give a deterministic signal the model reads.
- **What would change this:** dogfood showing the model skipping the drift check or misreading
  `Status`; then promote the check into `verify_summary.py`.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** prose compliance (design "What we do not claim"); `lint-skill-bash.sh` on new
  fences (finding 2); stale `.claude/` copy during dogfood (finding 3).
- **Context propagation:** the intent oracle reaches the reviewer only through the intent-review
  controller pasting it into `intent-reviewer-prompt.md`; that prompt's INTENT line must name the
  intent.md source, or the controller may paste only the `Intent-source:` line. The
  `context-propagation-audit` stage must check this delivery.
- **Evidence gaps:** spec-kit read only through secondary sources; Codex runtime not exercised.
- **Version uncertainties:** none load-bearing.
- **Follow-up questions for the user:** none.

---

## Source Pack

- **Local files read:** `skills/feature-intake/SKILL.md`, `skills/feature-intake/tests/README.md`,
  `skills/feature-intake/tests/confidence-escalation-cases.md`, `skills/intent-review/SKILL.md`,
  `skills/intent-review/intent-reviewer-prompt.md`, `skills/subagent-driven-development/references/review-chain.md`,
  `templates/SUMMARY.template.md`, `templates/ESCALATIONS.template.md`, `templates/QUESTIONS.template.md`,
  `templates/structure/specs-README.md`, `rules/terminology.md`, `hooks/commit-gate.sh`,
  `hooks/lib/lane.sh`, `hooks/branch-isolation-guard.sh`, `tests/hooks/commit-gate.test.sh`,
  `tests/hooks/commit-gate-evidence.test.sh`, `scripts/run-tests.sh`, `scripts/lint-skill-bash.sh`,
  `scripts/check_slim_surface.py`, `scripts/check_runtime_neutral_sources.py`,
  `scripts/install-harness.sh`, `scripts/deploy-harness.sh`, `scripts/verify_summary.py` (grep),
  `evals/skills/prompt-refactor/behavior/feature-intake.json`, `docs/solutions/INDEX.md`.
- **Upstream repositories or pages checked:**
  `https://academy.claude.com/courses/ai-native-sdlc-playbook/capture-intent`,
  `https://intuitionlabs.ai/articles/spec-driven-development-spec-kit`,
  `https://www.augmentcode.com/guides/github-spec-kit-practical-guide-sdd-workflow`,
  `https://matsen.fredhutch.org/general/2026/02/10/spec-kit-walkthrough.html`
- **Official docs domains or pages checked:** local `git diff --help` and `git log --help`
  (git 2.43.0); no network docs needed.

---

## Evidence Boundary

> Confirmed from artifacts: skill permissions; every `### Intent` consumer (grep surface named above);
> template shipping; commit-gate behavior on an intent-only commit (run); git pin/drift behavior (run);
> lint-skill-bash and deploy behavior (read).
> Inferred from patterns: adding `### Intake notes` does not affect `verify_summary.py` (no `Intent`
> reference found); spec-kit approval practice (secondary sources).
> Not checked: Codex runtime behavior; whether `check_frontmatter_contract.py` constrains SKILL.md
> body length (frontmatter is unchanged, so not expected to matter).
