# plugin-namespace-packaging — Summary

Lane: high-risk
Confidence: high (E001=A, E002=A resolved 2026-06-11; implementation verified)
Reason: Hard gate — touches settings.json hook registration and installer scripts (high-blast files); flags 6, 8, 9 also fired.
Flags: public contracts, existing behavior, weak proof
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

## What changed

Packaged the repo as a Claude Code plugin named `harness` so all skills invoke as
`harness:<dir-name>`:

- **Manifests** — added `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`
  (`source: "./"`). Dropped the `license` field (no LICENSE file in repo). No `hooks/hooks.json`
  per E001=A.
- **Doc/string sweep** — rewrote every harness-owned slash-command usage from `/<skill>` to
  `/harness:<skill>` across root docs (CLAUDE.md, README.md, HARNESS.md), `skills/README.md` +
  all `skills/*/SKILL.md`, hook message strings (scope-gate, risk-corroboration,
  commit-quality-gate) + the scope-gate test, governance docs (rules/, agents/README.md,
  docs/solutions/README.md), and — via the Task 3.1 residue sweep — bundled templates, skill
  READMEs, compound subagent prompts, and other shipped scaffolding. External skills
  (`/systematic-debugging`, `/code-review`, compound-engineering, …) left bare.
- **Installer** (E002=A, plugin-only for skills/agents) — `deploy-harness.sh` copy loop reduced
  to `hooks rules templates`, added a per-entry migration step removing previously-deployed
  harness-owned `skills/`+`agents/` entries (foreign entries preserved). `install-harness.sh`
  PAYLOAD dropped `skills`/`agents`, keeps the `skills/` source-sanity check, and now prints
  the two `/plugin` install commands. README install section rewritten to plugin-first +
  governance-layer curl + a "Migrating from flat skills" note.
- **Dogfood — NOT run (reverted).** The repo-local `deploy-harness.sh` was executed once but it
  mutated the user's live `.claude/` without confirmation; reverted on request — `.claude/` was
  restored to its `main`-source state (14 skill dirs + agents + governance). The local
  deploy + `/plugin install` dogfood is now a **human-confirmed manual step only** (see below).
  Functional correctness of the installer change is still proven by the Task 2.4 verify, which
  deploys into a throwaway `--target` tmp dir (never the live `.claude/`).

### Rationale

User confirmed plugin-namespace approach (option A) with namespace `harness:` to prevent
skill-name collisions with other installed plugins/frameworks (e.g. bare `compound` vs
`compound-engineering:ce-compound`). Plugin manifest namespaces all skills automatically
without renaming each skill directory.

### Alternatives considered

- Per-skill name prefix (`hs-`) without plugin packaging — rejected by user (works but
  requires renaming every skill + every cross-reference; not idiomatic).
- Both plugin + prefix (compound-engineering style) — deferred; can be added later for the
  most generic skill names if collisions persist.

### Deviations

- **Scope (Task 3.1 step 2)** — the repo-wide residue sweep found bare harness-skill slash-refs
  in ~21 files beyond the success-criteria list (bootstrap-xia2 templates, skill READMEs,
  compound subagent prompts, `templates/SUMMARY.template.md`, `agents/PROJECT*.md`,
  `docs/solutions/INDEX.md` + `critical-patterns.md`, `view_plan.py` comment, a hook-test
  label). Per Task 3.1's explicit "fix if it is a slash-command usage" mandate, all were
  namespaced. Several (bootstrap-xia2 templates) were also required to pass Task 3.1's own
  verify. `view_plan.py:145` confirmed a display-only comment, not matching logic.
- `correctness-reviewer-prompt.md:56` — a `/xia2` usage was initially masked by the
  `/SKILL.md:` line filter (the line also held a `skills/xia2/SKILL.md` path); caught by the
  unfiltered grep and fixed.
- **Rule 3 (blocking) — `tests/scripts/install-harness.test.sh`** (not in any task's `<files>`;
  blast-radius hook flagged it). Task 2.4's plugin-only PAYLOAD change made the test's stale
  assertion `[ -d "$tgt/.claude/skills" ]` fail. Updated it to the new contract (require
  `.claude/{hooks,rules,settings.json}`, assert no `.claude/{skills,agents}`) — same pattern as
  Task 2.3's scope-gate test update. Full suite then `ALL GREEN`. PLAN gap: Task 2.4 should
  have included this companion test in its `<files>`.
- **Rule 2 (correctness-review hardening) — added `tests/scripts/deploy-harness.test.sh`**
  (new; blast-radius hook flagged it — intentional). `migrate_plugin_shipped` (the only
  destructive code in the change — per-entry `rm -rf` of skills/agents) had zero test coverage.
  Added a regression test that pre-populates a target `.claude/` with a harness-owned + a
  foreign skill/agent, deploys, and asserts owned entries are pruned, foreign entries
  preserved, and governance deployed. Green. Closes correctness-review Finding 2.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| 1.1 manifests | `jq -e '.name=="harness"' plugin.json && jq -e '.plugins[0].name=="harness" and .plugins[0].source=="./"' marketplace.json && test ! -f hooks/hooks.json` | 0 | both manifests valid; no plugin hooks file |
| 2.1 root docs | `! grep -nE '<14-skill regex>' CLAUDE.md README.md HARNESS.md` | 0 | grep exit 1 (no bare refs) |
| 2.2 skills sweep | `! grep -rnE '<14-skill regex>' skills/README.md skills/*/SKILL.md` | 0 | grep exit 1 |
| 2.3 hooks | `bash -n {scope-gate,risk-corroboration,commit-quality-gate}.sh && bash tests/hooks/scope-gate.test.sh && ! grep -nE '…:/…' <hooks+test>` | 0 | scope-gate test 5/5; syntax ok; no bare refs |
| 2.4 installer | `bash -n install-harness.sh deploy-harness.sh && deploy --target $T && test -d $T/.claude/{hooks,rules} && test -f settings.json && test ! -d $T/.claude/{skills,agents}` | 0 | fresh-target deploy: governance only, no skills/agents |
| 2.5 governance docs | `! grep -rnE '<14-skill regex>' rules/ agents/README.md docs/solutions/README.md` | 0 | grep exit 1 |
| 3.1 exact verify | `jq -e .name plugin.json && ! grep -rnE '<6-skill regex>' … \| grep -vE 'skills/[a-z-]+/\|docs/research'` | 0 | clean |
| 3.1 full residue | `grep -rnE '<14-skill regex>' --include=*.{md,sh,py,json} … \| grep -vE 'research\|backup\|/SKILL.md:'` | 1 | no genuine residue (exit 1 = clean) |
| 3.1 dogfood | (skipped — would mutate live `.claude/`; needs human confirmation) | — | functional proof comes from the 2.4 `--target` tmp deploy instead |
| migration regression | `bash tests/scripts/deploy-harness.test.sh` | 0 | owned skills/agents pruned, foreign preserved, governance deployed |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN (incl. new deploy-harness test + python 85 passed/1 skipped) |

### Rollback

- Code/docs/manifests: `git revert <sha>` per commit, or `git checkout main -- <path>` — all
  changes are plain-file reversible. `.claude-plugin/` is a new dir; `rm -rf .claude-plugin` removes it.
- Installer behavior: `git revert` the scripts commit.
- Local `.claude/` (gitignored derived copy): restore flat skills by checking out `main` and
  running the pre-change `deploy-harness.sh`, i.e. `git stash && git checkout main -- scripts/deploy-harness.sh && bash scripts/deploy-harness.sh` — repopulates `.claude/skills` from `skills/`.

### Manual follow-up (human-confirmed only — DO NOT auto-run)

`.claude/` is the user's live environment — do not mutate it without explicit confirmation
(see memory `never-mutate-dot-claude`). When the user chooses to migrate this repo locally:

1. `bash scripts/deploy-harness.sh` (repo-local) — re-syncs `.claude/` to the new
   governance-only layout and removes the flat skill/agent copies. **Only with confirmation.**
2. `/plugin marketplace add ./`  →  `/plugin install harness@harness-skills`, then confirm a
   skill resolves as `/harness:compound` (flat `/compound` would be gone locally).
3. Restart Claude Code in this repo so the new `.claude/` loads.

### Advisory Findings

From `/correctness-review` (FIND → SCORE → threshold 80; high-risk lane). One independent
adversarial finder + first-person pass converged: **no P0/P1**, primary install path correct.
Cleared: `rm -rf` safety (`$OUT` always absolute, guarded globs), no orphaned `$SK`/`$AG`
(`set -e` only), valid manifests, `view_plan.py` reformat semantically identical, hook/test
assertions tight. Findings below the 80 threshold (recorded, not blocking):

- **[~45 · P2] Stale skills survive a `--keep-sources` + local-only re-sync.** `migrate_plugin_shipped`
  prunes by enumerating the deploy ROOT's `skills/*/`. On the normal installer path ROOT = the
  full fetched clone (has `skills/`), so stale `.claude/skills` IS pruned at install time
  (line 190, before `.harness-source/` is written). Only if a user later re-syncs *exclusively*
  from `.harness-source/` (which no longer stages `skills/`, per E002=A) would the per-entry
  prune find nothing to enumerate — but by then the install-time deploy already removed the
  stale entries, so the reachable harm is near-nil. Matches the documented "manual re-sync"
  risk in PLAN §5. No fix; the kept-sources path is governance-only by design. Mitigated in
  practice by the new `deploy-harness.test.sh` proving the primary prune path works.

### Harness-Delta

- **backlog** — the residue-sweep verify uses a line-scoped `/SKILL.md:` exclusion that can
  mask a genuine slash-command usage when the same line also contains a `…/SKILL.md` path.
  A token-scoped filter (or always pairing it with an unfiltered grep) would be more robust.
  Candidate `/compound` learning.
