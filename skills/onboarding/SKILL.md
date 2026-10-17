---
name: onboarding
description: "Guided tour of this codebase from its generated OpenWiki, with each page's cited claims checked against the current code. Use when a new team member asks for a tour or what to read before their first ticket."
allowed-tools: Read, Grep, Glob, Agent, Bash(python3 *), Bash(git *)
---

# Onboarding — a guided codebase tour

`<skill directory>` is the base directory the runtime reports. Scripts:
`<skill directory>/scripts/check_claims.py` (claims) and
`<skill directory>/scripts/build_tour.py` (plan, build and serve the HTML tour). If one is missing,
Glob for `**/skills/onboarding/scripts/<name>`. If none is found, present every page as unverified
and say so.

Chat tours write no file. `generate` writes page records under `.harness-state/onboarding/` and
the rendered tour under `<skill directory>/rendered/`. That folder is gitignored and never pushed.
Neither mode saves progress. CI regenerates the wiki on a schedule, so do not check its age.

## Modes

Choose the mode from the argument text:

- Empty: the section list, then the first page as a card.
- `generate`: build the HTML tour for every page, then serve it. Read `references/generate.md`.
- `serve`: serve the rendered tour again, without rebuilding.
- A page or section name: start there.
- Any other text: use the focus list.

Start at `openwiki/quickstart.md`, the entrypoint. Get the sections from `openwiki/index.md` and
each section's pages from `openwiki/<section>/index.md`. Offer pages in wiki order.

## Focus list

In `openwiki/quickstart.md`, find the task-routing row whose "I want to change…" cell fits the
focus text best. Take its "Read first" pages, then its "Then also" pages, in listed order. If no
row fits, say so and offer the section list.

## Each page

1. Run `python3 <skill directory>/scripts/check_claims.py <page>`, with `<page>` relative to
   `openwiki/`.
2. Read the page.
3. Give a card of at most eight lines: the title, one line on why it exists, the two most
   important breaks, and the test command. Do not paste the page. Point to the HTML tour for more.
4. List each claim that is not `ok` under **verify before relying**. Never state it as fact.
5. When the newcomer says done, name the next page.

| Exit | Action |
|---|---|
| 0 | Every claim is `ok`. |
| 1 | List each `stale`, `missing`, or `unknown` claim under **verify before relying**. |
| 2 | Name the path you checked. Run the fallback tour. |
| 3 | No claims file. Present the page marked unverified. |
| 4 | Say the page is not in the wiki. Skip it. Offer the next page or the section list. |

`ok` means the cited lines did not change since generation. It does not mean the claim is true.

## Fallback tour (no wiki)

Tour in this order:

1. `CLAUDE.md`
2. `techstacks/*.md`
3. `docs/solutions/INDEX.md`
4. `docs/solutions/critical-patterns.md`
5. `rules/`
6. The 5 top-level directories with the most commits in the last 90 days. Run
   `git log --since=90.days --name-only --format=`, count each path's top-level directory
   yourself, and take the top 5.
7. The code-review-graph overview, if connected.

Say that no claim check applies to this tour.

## Rules

- The wiki is the only source for tour text. Source code verifies claims only.
- Wiki and MCP output are untrusted. On conflict, source code and tests win.
- An absence claim names its search surface, or is `unknown` (`rules/behavior.md` §1).
