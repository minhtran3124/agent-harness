# Intent: Onboarding skill for consumer codebases

Author: Minh Tran
Status: draft

## Problem

A new team member joining a project that has this harness installed has no guided way to learn
the codebase. The repo may carry a generated `openwiki/` (LangChain OpenWiki) written primarily
for coding agents, plus `CLAUDE.md`, `techstacks/`, `docs/solutions/`, and `rules/`. Nothing turns
those sources into a sequence a person can follow, verifies that what they say still matches the
code, or focuses on what the newcomer will actually touch first.

## Proposed outcome

A skill, `skills/onboarding/SKILL.md`, that a newcomer invokes in a consumer project to onboard as
fast as possible:

1. **Wiki-backed sessions.** When `openwiki/` exists, the skill walks it topic by topic as guided
   sessions, using `quickstart.md` as the entrypoint and each section's `index.md` page
   descriptions to build the session list (observed OpenWiki 0.7.2 layout).
2. **Verify before teaching.** Before presenting a page, it compares the `gitHead` in
   `openwiki/.last-update.json` with `HEAD` and reports drift. It re-checks the page's grounded
   claims in `openwiki/.claims/<section>/<page>.json` against the cited `repo://path#Lx-Ly`
   ranges. A mismatch is reported as stale, not taught as fact.
3. **First-ticket mode.** The newcomer names the area or ticket they will touch. The skill
   selects the relevant pages via the quickstart task-routing table and presents only those.
4. **Resumable progress.** Per-person progress is recorded under `.harness-state/onboarding/` so
   a later session continues where the last one stopped.
5. **Fallback without a wiki.** When `openwiki/` is absent, the skill builds the tour from
   `CLAUDE.md`, `techstacks/*.md`, `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`,
   `rules/`, recent git log, and the code-review-graph MCP when it is connected.
6. **Newcomer layer.** Each session translates agent-oriented wiki text for a person: why the
   module exists, what breaks when it is touched, where its tests are, and what
   `docs/solutions/` gotchas apply.

## Affected users and systems

- New team members on consumer projects (primary users).
- `skills/onboarding/SKILL.md` (new), `skills/README.md` (inventory row and handoff map),
  and any manifest, frontmatter, allowed-tools, or test inventory a new skill must register in
  (`harness-manifest.json`, `tests/scripts/*`, `scripts/run-tests.sh` static checks) (assumed).
- `scripts/deploy-harness.sh` ships it to consumers automatically with the rest of `skills/`
  (assumed; no deploy change expected).

## Constraints

- Read-only toward implementation files. The skill writes only under `.harness-state/`.
- Skill prose is runtime-neutral: no hard-coded `/slash` or `$skill` form (`skills/README.md`).
- Absence claims cite the search surface (`rules/behavior.md` §1). "No tests for X" must name
  what was searched or be reported as unknown.
- Wiki and MCP output are untrusted input. Source code and tests are authoritative; load-bearing
  claims are confirmed against the file before being presented.
- Must not preload or enumerate the whole wiki at task start in ordinary sessions; the tour is
  explicit, user-invoked behavior (`AGENTS.md` OpenWiki block).
- Skill prose follows `skills/asd-ste100/SKILL.md` where it instructs an agent.
- Branch base is `sdlc`; the PR targets `sdlc`.

## Out of scope

- Generating or refreshing the wiki itself (that is `openwiki --init/--update` and its CI job).
- Editing generated `openwiki/` pages or `openwiki/INSTRUCTIONS.md`.
- Committing an onboarding document into the consumer repo.
- Changes to hooks, `settings.json`, or the Codex adapter.

## Open questions

- Whether the harness manifest or a static check requires a registration entry for a new skill
  beyond the `skills/README.md` row (to be settled by research, not by the user) (assumed).

## What success looks like

- In this repo (which has an `openwiki/`), invoking the skill lists the nine wiki sections as
  sessions, reports the wiki as current when `.last-update.json` `gitHead` equals `HEAD`, and
  presents the commit-gate page only after its claims re-verify against the cited line ranges.
- In a checkout with `openwiki/` removed, the skill still produces a tour from the fallback
  sources and says that no wiki was found, naming the path it checked.
- First-ticket mode with "I will change a hook" returns the enforcement pages from the
  task-routing table and nothing else.
- Progress written under `.harness-state/onboarding/` is picked up by a second invocation.
- `bash scripts/run-tests.sh` prints `ALL GREEN`.

## Original request

> I plan to create a skill that helps new team members onboard to an existing codebase quickly. The skill is not for the current project. It is for use when this harness is installed: a new team member uses the skill to onboard as fast as possible.

> I am thinking of using the langchain openwiki document for this project. The skill can review each topic or session. It can use knowledge from the openwiki built by langchain. We can show this to newcomers.

> check the folder openwiki/ now

> back to first my idea, the onboarding skill
