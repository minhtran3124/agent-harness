---
name: verify
description: Prove that a finished ticket works in a real run, with a pass or fail result from assertions. Use when a ticket has a `Verify:` row and its code is ready, or from `/harness:verify`.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_fill_form, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_snapshot, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_console_messages, mcp__plugin_playwright_playwright__browser_run_code_unsafe
---

# Verify

The ticket's `Verify:` row drives the run. Pass or fail comes from assertions, never a screenshot.

Use the Playwright MCP browser tools, not npm Playwright. If a tool named here is missing,
find it with `ToolSearch` by the tail of its name (for example `browser_navigate`), whatever the server prefix. If an argument is refused, fix the call from the error.

## Pick the work by ticket type

| Type | Work |
|---|---|
| BE | Run the ticket test command. Start the service. `curl` each endpoint, compare status and body. |
| FE | Run the unit tests. Then the browser steps. |
| FE+BE | Run the BE work. Compare the API contract with the FE fixture. Then the browser steps. |
| Docs or config | Run the lint and done-when commands the `Verify:` row lists. |

## Run the app

Before Start config, Login or Browser steps, read `references/run-app.md`. It holds the config, login and browser rules. Tickets that start no service and call no HTTP skip it.

## Base mode

`Mode: base` checks that the steps fail on the base commit, in a worktree without ticket code:

1. Read `verify.config.json` from the implement worktree path in the prompt. Never write or commit it.
2. Run Start config (step 5, with the `PORT` and `env` export), Login and Browser steps from `references/run-app.md` as usual. Commit nothing.
3. The steps are expected to FAIL. Report the real result, do not judge it.
4. Do not retry. The workflow decides what the result means.

## Report

Return a table: a row per command or step with PASS or FAIL, assertion text, console error count, still paths. Any FAIL makes the whole run FAIL.
Never fix code. The workflow builds the GIF from the stills.
