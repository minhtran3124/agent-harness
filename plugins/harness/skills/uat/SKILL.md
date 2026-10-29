---
name: uat
description: Check the running app against the owner's request, blind to the plan, the diff and the Verify row. Use after a ticket is built, or from `/harness:uat N`, for FE, BE and FE+BE tickets.
allowed-tools: Read, Grep, Glob, Bash, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_fill_form, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_snapshot, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_console_messages, mcp__plugin_playwright_playwright__browser_run_code_unsafe
---

# UAT

Acceptance test of the running app. The owner's words are the only source. Pass or fail comes from assertions, never a screenshot.

Use the Playwright MCP browser tools, not npm Playwright. If a tool named here is missing, find it with `ToolSearch` by the tail of its name.

## Step 0: prerequisite

Run `test -f "${CLAUDE_PLUGIN_ROOT}/skills/verify/references/run-app.md"`. The agent's cwd is the ticket worktree, so never use a path relative to this skill's folder. If the file is missing, stop and report BLOCKED. Never write it inline.

## Input

A ticket number. Read only:

- the issue body, and
- the `Confirmed decisions` comment.

When the prompt already supplies the request text, use it and never run `gh issue view`. Only a standalone `/harness:uat N` fetches the issue. Standalone blindness is best effort: the agent sees the whole issue, so ignore any `Verify:` text yourself. Ship mode strips it in code.

Do not read `git log`, diffs, `docs/adr/`, `specs/` or any plan.

## Scenarios

1. Number the acceptance bullets AC1..ACn.
2. Write 3 to 8 scenarios: each AC at least once, then up to 3 more.
3. Every row names exactly one of: an AC id, `negative`, `extra`, `not-browser-checkable`.
4. An AC no browser can check (a doc, a log, a config) gets a `not-browser-checkable` row. It does not count toward pass or fail.

## Run the app

Read `${CLAUDE_PLUGIN_ROOT}/skills/verify/references/run-app.md` by path and follow its Start config, Login and Browser steps. Copy none of them here.

Overrides of that file:

- Never infer a config, never write one, never commit one. Use only an existing file.
- Config path: the prompt's config path if given, else a `Config:` line in Confirmed decisions, else `verify.config.json` at the repo root.
- No config found: report BLOCKED. Write no file.
- Missing credentials: report BLOCKED. Use throwaway credentials only where `config.md` allows.
- App will not start: report BLOCKED with the start error. This is not an AC failure.

Stay with the config's own port. Stop the app when done.

## Report

Return a table: scenario, covers, PASS or FAIL, assertion text, still path. Then the browser console error count. Report it; console errors alone do not fail the run (only a FAIL on an AC does).

Return `passed_ac` true only when every AC row that a browser can check passed. A failed negative or extra row goes into `non_ac_failures`; it never sets `passed_ac` false.

Never fix code. Never change the app, the tests or the config.
