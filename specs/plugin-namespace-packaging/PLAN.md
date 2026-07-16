---
slug: plugin-namespace-packaging
status: shipped
owner: Minh Tran
created: 2026-06-11
---

# Harness Plugin Packaging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use subagent-driven-development (or executing-plans) to implement this plan task-by-task.

**Goal:** Package this repo as a Claude Code plugin named `harness` so every skill is invoked as `/harness:<skill>`, eliminating name collisions with other installed skill libraries.

**Architecture:** Add a `.claude-plugin/` manifest pair (plugin.json + marketplace.json) — the existing `skills/<name>/SKILL.md` layout is already plugin-conformant, so skills need no renames (invocation name = plugin name + skill *directory* name; frontmatter `name:` is ignored for plugins). Per ESCALATIONS E001=A hooks stay registered via `settings.json` (no plugin `hooks/hooks.json`); per E002=A the installer goes plugin-only for skills/agents and keeps delivering hooks/rules/templates/settings.json into target projects.

**Tech Stack:** Claude Code plugin manifest (docs: code.claude.com/docs/en/plugins-reference), bash installer scripts, jq, grep.

**Inputs:** `specs/plugin-namespace-packaging/research-brief.md`, `specs/plugin-namespace-packaging/ESCALATIONS.md` (E001=A, E002=A — decided 2026-06-11).

---

## 1. Motivation

All skills currently load flat (`/compound`, `/brainstorming`, `/writing-plans`…). Generic names collide with other plugins/frameworks (e.g. `compound` vs `compound-engineering:ce-compound`). Plugin packaging namespaces every skill automatically without renaming any of them.

## 2. Non-goals

- No per-skill `hs-` prefix renames (rejected alternative — see SUMMARY.md).
- No plugin `hooks/hooks.json` (E001=A — hooks remain project-level via settings.json).
- No dual install path (E002=A — installer stops copying skills/agents).
- No changes to skill *behavior*, gates, or frontmatter `name:` fields.
- No marketplace publication beyond this repo's own `.claude-plugin/marketplace.json`.

## 3. Success Criteria

1. `/plugin marketplace add minhtran3124/harness-skills` + `/plugin install harness@harness-skills` installs all 14 skills as `harness:<dir-name>`.
2. `bash scripts/deploy-harness.sh --target <dir>` produces `.claude/` with hooks/rules/templates/settings.json and **no** skills/ or agents/.
3. No bare `/skill-name` slash-command reference to a harness-owned skill survives in CLAUDE.md, README.md, HARNESS.md, skills/README.md, skills/*/SKILL.md, rules/*.md, agents/README.md, docs/solutions/README.md, or hook message strings (external skills like `/systematic-debugging` stay bare). `rules/` ships into target projects, so its refs are user-facing too.
4. Both manifest JSONs validate with `jq`.

## 4. Tasks

### Task 1.1 — Plugin + marketplace manifests

```xml
<task id="1.1" wave="1">
  <files>.claude-plugin/plugin.json, .claude-plugin/marketplace.json</files>
  <action>
Create .claude-plugin/plugin.json:

{
  "name": "harness",
  "version": "0.1.0",
  "description": "Skill framework + risk/trust harness for Claude Code — workflows from brainstorm to ship",
  "author": { "name": "Minh Tran" },
  "repository": "https://github.com/minhtran3124/harness-skills",
  "license": "MIT",
  "keywords": ["skills", "workflow", "governance", "risk", "harness"]
}

Create .claude-plugin/marketplace.json (same-repo source uses relative "./"):

{
  "name": "harness-skills",
  "description": "Marketplace for the harness plugin — workflow skills + risk/trust governance",
  "plugins": [
    {
      "name": "harness",
      "source": "./",
      "description": "14 workflow skills (intake → brainstorm → plan → build → review → ship), namespaced as harness:&lt;skill&gt;"
    }
  ]
}

Rationale: skills/ at repo root is auto-discovered by the plugin loader; agents/ likewise.
No component-path overrides needed. Do NOT create hooks/hooks.json (E001=A).
Check LICENSE file exists; if the repo has no license file, drop the "license" field rather
than inventing one.
  </action>
  <verify>jq -e '.name=="harness"' .claude-plugin/plugin.json &amp;&amp; jq -e '.plugins[0].name=="harness" and (.plugins[0].source=="./")' .claude-plugin/marketplace.json &amp;&amp; test ! -f hooks/hooks.json</verify>
  <done>Both manifests exist, validate, name the plugin "harness"; no plugin hooks file</done>
</task>
```

### Task 2.1 — Root docs sweep (CLAUDE.md, README.md, HARNESS.md)

```xml
<task id="2.1" wave="2">
  <files>CLAUDE.md, README.md, HARNESS.md</files>
  <action>
Rewrite every slash-command reference to a harness-owned skill from /&lt;skill&gt; to
/harness:&lt;skill&gt;. Harness-owned skill names (14): feature-intake, brainstorming, xia2,
bootstrap-xia2, writing-plans, visual-planner, using-git-worktrees,
subagent-driven-development, executing-plans, correctness-review, review-diff, compound,
create-pr, finishing-a-development-branch.

ONLY rewrite slash-command usages (preceded by start-of-line, space, backtick, or "(" );
do NOT touch file paths like skills/feature-intake/SKILL.md or specs/… paths.
Do NOT namespace external skills: /systematic-debugging, /test-driven-development,
/requesting-code-review, /session-tracker, /skill-creator, /code-review, /compound-engineering:* .

In README.md, replace the curl-installer-first instructions with a two-part install:
  1. Skills (plugin):  /plugin marketplace add minhtran3124/harness-skills
                       /plugin install harness@harness-skills
  2. Project harness (hooks/rules/templates/settings): the existing curl install-harness.sh
     one-liner (unchanged URL), now described as "installs the governance layer only".
Add a short "Migrating from flat skills" note: previously-installed projects keep working
until re-synced; after re-sync, bare /skill names are gone — use /harness:&lt;skill&gt;.

CAUTION (verify-regex pitfall): never write the literal slash form "/compound-engineering…"
in new prose — the verify grep's \b makes it match /compound. Refer to that plugin without
a leading slash ("the compound-engineering plugin").

In CLAUDE.md "Skill Workflow" section and HARNESS.md flow descriptions, update the chain
arrows (feature-intake → … → finishing-a-development-branch) to namespaced form.
  </action>
  <verify>! grep -nE '(^|[^[:alnum:]_/.-])/(feature-intake|brainstorming|xia2|bootstrap-xia2|writing-plans|visual-planner|using-git-worktrees|subagent-driven-development|executing-plans|correctness-review|review-diff|compound|create-pr|finishing-a-development-branch)\b' CLAUDE.md README.md HARNESS.md</verify>
  <done>Zero bare slash-refs to harness skills in the three root docs; install section shows plugin flow first</done>
</task>
```

### Task 2.2 — skills/README.md + SKILL.md cross-reference sweep

```xml
<task id="2.2" wave="2">
  <files>skills/README.md, skills/brainstorming/SKILL.md, skills/bootstrap-xia2/SKILL.md, skills/correctness-review/SKILL.md, skills/compound/SKILL.md, skills/subagent-driven-development/SKILL.md, skills/feature-intake/SKILL.md, skills/visual-planner/SKILL.md, skills/writing-plans/SKILL.md, skills/xia2/SKILL.md</files>
  <action>
Same rewrite rule as task 2.1 (slash-command usages only; same 14-name list; same external
exclusions), applied to skills/README.md (~60 refs: workflow diagrams, tables, handoff map)
and the 8 SKILL.md files that cross-reference sibling skills.

Notes:
- skills/README.md "External Skills" table stays bare (those are not ours).
- Handoff-map ASCII diagram entries (e.g. "/brainstorming ──► /xia2 → /writing-plans")
  become /harness:brainstorming ──► /harness:xia2 → /harness:writing-plans — keep column
  alignment readable; reflow the diagram if needed.
- Do NOT edit frontmatter name: fields — the plugin loader ignores them and project-skill
  fallback (if someone still copies skills flat) keeps working.
- Trigger lines inside SKILL.md prose ("Trigger: /compound") become Trigger: /harness:compound.
  </action>
  <verify>! grep -rnE '(^|[^[:alnum:]_/.-])/(feature-intake|brainstorming|xia2|bootstrap-xia2|writing-plans|visual-planner|using-git-worktrees|subagent-driven-development|executing-plans|correctness-review|review-diff|compound|create-pr|finishing-a-development-branch)\b' skills/README.md skills/*/SKILL.md</verify>
  <done>Zero bare slash-refs to harness skills under skills/; external-skill refs untouched</done>
</task>
```

### Task 2.3 — Hook advisory-message strings

```xml
<task id="2.3" wave="2">
  <files>hooks/scope-gate.sh, hooks/risk-corroboration.sh, hooks/commit-quality-gate.sh, tests/hooks/scope-gate.test.sh</files>
  <action>
Hooks reference skills only inside user-facing message strings (verified — no matching
logic uses skill names). Update:
- hooks/scope-gate.sh line ~19: "Run /feature-intake" → "Run /harness:feature-intake"
- hooks/risk-corroboration.sh: ALL /feature-intake occurrences (lines ~132, ~140, ~145) → "/harness:feature-intake"
- hooks/commit-quality-gate.sh line ~156: "running /compound" → "running /harness:compound"
- tests/hooks/scope-gate.test.sh line ~11: the assertion expects "Run /feature-intake" —
  update the expected string to "Run /harness:feature-intake" so the test still passes.
No other edits — surgical string changes only.
  </action>
  <verify>bash -n hooks/scope-gate.sh &amp;&amp; bash -n hooks/risk-corroboration.sh &amp;&amp; bash -n hooks/commit-quality-gate.sh &amp;&amp; bash tests/hooks/scope-gate.test.sh &amp;&amp; ! grep -nE '(^|[^[:alnum:]_/.:-])/(feature-intake|compound)\b' hooks/scope-gate.sh hooks/risk-corroboration.sh hooks/commit-quality-gate.sh tests/hooks/scope-gate.test.sh</verify>
  <done>Hook messages point at namespaced skills; scripts still parse; scope-gate test green</done>
</task>
```

### Task 2.4 — Installer + deploy scripts go plugin-only for skills/agents

```xml
<task id="2.4" wave="2">
  <files>scripts/install-harness.sh, scripts/deploy-harness.sh</files>
  <action>
deploy-harness.sh:
1. Change the copy loop `for d in skills agents hooks rules templates` to
   `for d in hooks rules templates` (skills + agents now ship via the plugin).
2. Add a migration step after the loop: remove previously-deployed harness-owned entries —
   for each dir in ROOT/skills/*/ remove "$OUT/skills/&lt;basename&gt;", for each file in
   ROOT/agents/* remove "$OUT/agents/&lt;basename&gt;" (per-entry, mirroring copy_dir's
   merge-sync rationale: foreign user-installed entries in .claude/skills stay untouched).
   Keep strip_archive (now folded into / after this step). Label the step
   "Removing plugin-shipped skills/agents (now via /plugin install harness)".
3. Update the summary block: drop the skills/agents counts (or print "via plugin"),
   keep hooks/rules counts.
4. Update the header comment: skills/agents are plugin-shipped; this script deploys the
   governance layer (hooks/rules/templates/settings.json) and is also the repo-local
   dev path.

install-harness.sh:
1. PAYLOAD=(hooks rules templates settings.json scripts/deploy-harness.sh) — drop skills, agents.
2. Keep the `[ -d "$SRC/skills" ]` source-sanity check (repo still contains skills/).
3. After the deploy step, print next-step instructions:
     Skills are installed separately as a plugin:
       /plugin marketplace add minhtran3124/harness-skills
       /plugin install harness@harness-skills
4. Update the install description strings ("Install the claude-skills harness…") to mention
   "governance layer (hooks/rules/templates); skills via plugin".
  </action>
  <verify>bash -n scripts/install-harness.sh &amp;&amp; bash -n scripts/deploy-harness.sh &amp;&amp; T=$(mktemp -d) &amp;&amp; bash scripts/deploy-harness.sh --target "$T" >/dev/null 2>&amp;1 &amp;&amp; test -d "$T/.claude/hooks" &amp;&amp; test -d "$T/.claude/rules" &amp;&amp; test -f "$T/.claude/settings.json" &amp;&amp; test ! -d "$T/.claude/skills" &amp;&amp; test ! -d "$T/.claude/agents" &amp;&amp; rm -rf "$T"</verify>
  <done>Fresh-target deploy yields hooks/rules/templates/settings only; both scripts parse; installer prints plugin instructions</done>
</task>
```

### Task 2.5 — Governance docs sweep (rules/, agents/, docs/solutions/)

```xml
<task id="2.5" wave="2">
  <files>rules/orchestration.md, rules/auto-correct-scope.md, agents/README.md, docs/solutions/README.md</files>
  <action>
Same rewrite rule as task 2.1 (slash-command usages only; same 14-name list; same external
exclusions; same /compound-engineering literal caution), applied to the remaining files with
confirmed bare refs: rules/orchestration.md (~line 34), rules/auto-correct-scope.md (~line 11),
agents/README.md (~lines 51–52), docs/solutions/README.md (~line 6). Sweep each whole file,
not just the cited lines. rules/ ships into target projects via the installer, so these are
user-facing references, not internal notes.
  </action>
  <verify>! grep -rnE '(^|[^[:alnum:]_/.-])/(feature-intake|brainstorming|xia2|bootstrap-xia2|writing-plans|visual-planner|using-git-worktrees|subagent-driven-development|executing-plans|correctness-review|review-diff|compound|create-pr|finishing-a-development-branch)\b' rules/ agents/README.md docs/solutions/README.md</verify>
  <done>Zero bare slash-refs to harness skills in rules/, agents/README.md, docs/solutions/README.md</done>
</task>
```

### Task 3.1 — Final verification sweep + local dogfood check

```xml
<task id="3.1" wave="3">
  <files>(read-only verification; specs/plugin-namespace-packaging/SUMMARY.md)</files>
  <action>
1. Re-run the verify commands of tasks 1.1–2.5 (all must pass together).
2. Repo-wide residue check for bare harness-skill slash-refs outside excluded areas
   (specs/ is local-only, docs/research-* are historical notes — exclude them):
   grep -rnE '(^|[^[:alnum:]_/.:-])/(feature-intake|brainstorming|xia2|bootstrap-xia2|writing-plans|visual-planner|using-git-worktrees|subagent-driven-development|executing-plans|correctness-review|review-diff|compound|create-pr|finishing-a-development-branch)\b' \
     --include='*.md' --include='*.sh' --exclude-dir=specs --exclude-dir=.git --exclude-dir='.harness-backup-*' --exclude-dir=node_modules . \
   — triage every hit: fix if it is a slash-command usage, leave if path/historical.
3. Dogfood note: this repo's own .claude/skills still carries flat copies until
   deploy-harness is re-run locally. Run `bash scripts/deploy-harness.sh` (repo-local) and
   confirm .claude/skills harness-owned dirs are removed; then the user installs the plugin
   locally (/plugin marketplace add ./ → /plugin install harness@harness-skills) — record
   this as a manual follow-up in SUMMARY.md (interactive /plugin commands cannot run from a hook).
4. Fill SUMMARY.md ### Verify table with every command actually run + exit codes, and
   ### Rollback (git revert per commit; .claude/ restorable via deploy-harness from a
   pre-change checkout).
  </action>
  <verify>jq -e .name .claude-plugin/plugin.json >/dev/null &amp;&amp; ! grep -rnE '(^|[^[:alnum:]_/.:-])/(feature-intake|brainstorming|writing-plans|subagent-driven-development|correctness-review|finishing-a-development-branch)\b' --include='*.md' --include='*.sh' --exclude-dir=specs --exclude-dir=.git --exclude-dir='.harness-backup-*' --exclude-dir=node_modules . | grep -vE 'skills/[a-z-]+/|docs/research'</verify>
  <done>All task verifies green; residue grep clean (paths/historical only); SUMMARY.md Verify + Rollback filled</done>
</task>
```

## 5. Risks

| Risk | Mitigation |
|---|---|
| Existing installed projects keep bare-name skills until re-synced; after re-sync skills vanish unless plugin installed | README migration note (task 2.1) + installer prints plugin instructions (task 2.4) |
| This repo's own dogfooding breaks between deploy re-run and local plugin install | Task 3.1 sequences it; flat copies in .claude/skills keep working until the re-run |
| Marketplace `source: "./"` semantics differ across Claude Code versions | Verified against current docs (research-brief §3); smoke-test via local `marketplace add ./` is a manual follow-up |
| Doc sweep regex over/under-matching (paths vs slash-commands) | Verify greps require non-word char before `/`, excluding `skills/<name>/` paths; task 3.1 triages every residual hit by hand |
| `agents/` dropped from installer — consuming projects relying on project-level agents | Agents are plugin-shipped (auto-discovered `agents/` at plugin root); same delivery, new mechanism |

## 6. Status Log

- 2026-06-11 — plan written (intake: high-risk lane, E001=A / E002=A decided by Minh Tran).
- 2026-06-11 — executed on branch `feature/plugin-namespace-packaging` (executing-plans). Wave 1
  (1.1) → Wave 2 (2.1–2.5, 5 parallel subagents, disjoint files) → Wave 3 (3.1). All task
  verifies green; `scripts/run-tests.sh` ALL GREEN. Deviation: Task 2.4 also required updating
  `tests/scripts/install-harness.test.sh` (stale `.claude/skills` assertion → plugin-only
  contract) — should be added to Task 2.4 `<files>`. Manual follow-ups recorded in SUMMARY.md.
- 2026-06-11 — shipped via `feature/plugin-namespace-packaging` (PR #13). `/correctness-review`
  passed (no P0/P1; 1 advisory). `scripts/run-tests.sh` ALL GREEN.
