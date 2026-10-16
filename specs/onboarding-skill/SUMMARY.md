# onboarding-skill — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate (adds skills/onboarding/SKILL.md and edits skills/README.md); intake classifies workflow-as-code as high-risk even though the gate is warn-mode at commit time
Flags: external systems, multi-domain
Affects: skills/README.md (skill inventory and handoff map), skills/onboarding (new), harness-manifest.json / static skill checks if they register skills
Input-type: new spec
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/onboarding-skill/intent.md @ 5e8513c2792b8e5be9f5c29428c07897df1e0f8d

> I plan to create a skill that helps new team members onboard to an existing codebase quickly. The skill is not for the current project. It is for use when this harness is installed: a new team member uses the skill to onboard as fast as possible.

> I am thinking of using the langchain openwiki document for this project. The skill can review each topic or session. It can use knowledge from the openwiki built by langchain. We can show this to newcomers.

> check the folder openwiki/ now

> back to first my idea, the onboarding skill

### Intake notes

- Confidence high: the user approved intent.md after the design (wiki-backed sessions, verify-before-teaching, first-ticket mode, resumable progress, no-wiki fallback) was agreed in chat; one interpretation remains.
- `external systems` flag: the skill consumes LangChain OpenWiki 0.7.2 output (`openwiki/` layout observed in this repo at HEAD 996f50d). No SDK or dependency is added; the wiki is read as files.
- `multi-domain` flag: new skill plus README inventory plus whatever registration the static checks demand (to be settled by xia2).
- Branch `feat/onboarding-skill` cut from `sdlc`; the PR targets `sdlc`.

## What changed

<pending — filled at delivery>

### Rationale

<pending>

### Alternatives considered

- none yet (brainstorming pending)

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intent pin unchanged since approval | `git diff --exit-code 5e8513c2792b8e5be9f5c29428c07897df1e0f8d -- specs/onboarding-skill/intent.md` | 0 | intake-time pin check | |
| openwiki is current at intake | `test "$(python3 -c 'import json;print(json.load(open("openwiki/.last-update.json"))["gitHead"])')" = "$(git rev-parse sdlc)"` | 0 | wiki gitHead equals sdlc tip 996f50d (the design sample) | |

### Not auto-verified

- OpenWiki 0.7.2 layout (quickstart.md, per-section index.md, .claims/, .last-update.json, .page-manifest.json) was observed only in this repo — reached traceability; not re-run on a consumer project because none with a wiki is available at intake

### Rollback

- Intake only: `git switch sdlc && git branch -D feat/onboarding-skill` discards the branch (intent + SUMMARY + run-state); nothing outside `specs/onboarding-skill/` was changed
- After implementation: `git revert <sha>` per implementation commit, then delete `skills/onboarding/`

### Harness-Delta

- none
