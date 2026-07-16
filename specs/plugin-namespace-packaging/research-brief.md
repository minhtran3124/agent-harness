# plugin-namespace-packaging — Research Brief

Date: 2026-06-11 · Sources: official Claude Code docs (code.claude.com/docs), repo scan

## Question

Package this repo as a Claude Code plugin named `harness` so all skills are invoked as
`/harness:<skill>` — what exists, what's the lightest credible path?

## Confirmed facts (docs, v2.1.154+)

1. **Manifest**: `.claude-plugin/plugin.json` at repo root. Required: `name` (kebab-case —
   becomes the namespace). Optional: `version`, `description`, `author`, `homepage`,
   `repository`, `license`, `keywords`. Omitting `version` → git commit SHA used.
2. **Skill discovery**: `skills/<dir>/SKILL.md` at plugin root is auto-discovered — **our
   existing layout already matches**. Invocation name = `<plugin-name>:<skill-dir-name>`;
   the `name:` frontmatter field is ignored for plugins. No per-skill rename needed.
3. **GitHub install**: requires `.claude-plugin/marketplace.json` in the repo. User flow:
   `/plugin marketplace add minhtran3124/harness-skills` →
   `/plugin install harness@<marketplace-name>`.
4. **Hooks**: plugin hooks (`hooks/hooks.json`) and project `settings.json` hooks fire
   independently — no conflict. Per E001=A we ship **no plugin hooks**; the repo's
   `hooks/hooks.json` must NOT exist at plugin root or it would be auto-loaded — verify
   `hooks/` contains only `.sh` files (it does today).
5. **Path limitation**: plugin skills cannot reference outside the plugin dir (`../` fails
   after install caching). Skills referencing `templates/…`, `rules/…` resolve against the
   **user's project** at runtime, so the installer must still deliver
   rules/templates/hooks/settings.json into target projects (consistent with E002=A).

## Repo deltas required

| Area | Delta |
|---|---|
| `.claude-plugin/plugin.json` | new — `name: harness` + metadata |
| `.claude-plugin/marketplace.json` | new — single-plugin marketplace, `source: github` |
| `CLAUDE.md`, `skills/README.md`, `HARNESS.md`, `README.md` | `/skill` → `/harness:skill` cross-references; install instructions |
| `scripts/install-harness.sh` | PAYLOAD drops `skills` + `agents`(?); add plugin-install guidance; keep rules/templates/hooks/settings/MCP wiring |
| `scripts/deploy-harness.sh` | stop deriving `.claude/skills/` from `skills/` (plugin now serves skills) — or keep for repo-local dogfooding only |
| `hooks/scope-gate.sh`, `risk-corroboration.sh` | check for bare skill-name matching; update regex if they grep `/skill-name` |
| Skill cross-refs inside `skills/*/SKILL.md` | skills that name other skills (`/xia2`, `/compound`, …) should use namespaced form |

## Open risks

- **Dogfooding**: this repo itself loads skills via `.claude/skills/` (deploy-harness).
  After plugin-only, repo dev sessions need the plugin installed locally
  (`/plugin marketplace add ./` works for local testing) or keep deploy-harness as a
  dev-only path — decide in plan (lean: keep deploy-harness for repo-local dev, mark dev-only).
- **Existing installed projects** break on bare names after migration — needs a migration
  note in README/installer output, not code.

## Recommendation (lightest credible path)

Manifest + marketplace + doc sweep + installer trim, in that order; hooks stay untouched
except grep-verify for bare-name matching. No skill directory renames, no hooks.json.
