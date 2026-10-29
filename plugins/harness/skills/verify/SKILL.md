---
name: verify
description: Prove that a finished ticket works in a real run, with a pass or fail result from assertions. Use when a ticket has a `Verify:` row and its code is ready, or from `/harness:verify`.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_fill_form, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_snapshot, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_console_messages, mcp__plugin_playwright_playwright__browser_run_code_unsafe
---

# Verify

Prove that the change works. The `Verify:` row of the ticket drives the run. Pass or fail comes
from assertions only. Never judge from how a screenshot looks.

Use the Claude Code Playwright plugin tools only. Do not install npm Playwright.

## Pick the work by ticket type

| Type | Work |
|---|---|
| BE | Run the ticket test command. Start the service. Call each endpoint with `curl` and compare status and body. |
| FE | Run the unit tests. Then run browser steps (see Browser steps). |
| FE+BE | Run the BE work. Compare the API contract with the FE fixture. Then run the browser steps end to end. |
| Docs or config | Run the lint and done-when commands that the `Verify:` row lists. No browser. |

## Start config

1. Read `verify.config.json` at the repo root.
2. If it does not exist, infer the start recipe from the README, `package.json`, or `Makefile`.
   Write the file with these keys: `baseUrl`, `startCommand`, `loginEnv`.
3. `loginEnv` holds the NAMES of the login variables: `VERIFY_USER` and `VERIFY_PASSWORD`.
   Never write a value into the file.
4. Commit the file on the ticket branch, so the owner reviews it in the PR diff.
5. Start `startCommand` in the background. Wait until `baseUrl` answers. Stop it at the end.

## Login

Do this once, before the captured steps, and keep it out of the evidence:

1. Open the login page. Fill the form with `browser_fill_form` from `VERIFY_USER` and `VERIFY_PASSWORD`, then submit with `browser_click`. Never pass the password through `browser_run_code_unsafe`.
2. Save `storageState` to a gitignored file.
3. Run all captured steps signed in. The login form never appears in a screenshot.

If a variable is not set, report BLOCKED. Never guess a password.

## Browser steps

For each step in the `Verify:` row:

1. `browser_navigate` to the page.
2. `browser_snapshot` to see the page.
3. `browser_run_code_unsafe` with an assertion on exact text or a selector. A true assertion
   passes. A false one throws, and the step fails.
4. `browser_take_screenshot` into `.playwright-mcp/<ticket>/`, named by step number.

After the last step, call `browser_console_messages`. Count the errors. One or more is a fail.

## Report

Return a table with one row per command or step, PASS or FAIL, and the assertion text.
Add the console error count and the path of each still. Any FAIL makes the whole run FAIL.
Do not fix the code in this skill. Do not commit evidence: Git ignores `.playwright-mcp/`.
