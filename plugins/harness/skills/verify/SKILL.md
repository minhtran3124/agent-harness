---
name: verify
description: Prove that a finished ticket works in a real run, with a pass or fail result from assertions. Use when a ticket has a `Verify:` row and its code is ready, or from `/harness:verify`.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_fill_form, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_snapshot, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_console_messages, mcp__plugin_playwright_playwright__browser_run_code_unsafe
---

# Verify

The ticket's `Verify:` row drives the run. Pass or fail comes from assertions only,
never from a screenshot.

Use the Playwright MCP browser tools, not npm Playwright. If a tool named here does not exist,
find it with `ToolSearch` by the tail of its name (`browser_navigate`, `browser_snapshot`,
`browser_fill_form`, `browser_click`, `browser_take_screenshot`, `browser_console_messages`,
`browser_run_code_unsafe`), whatever the server prefix. If an argument is refused, read the error
and fix the call.

## Pick the work by ticket type

| Type | Work |
|---|---|
| BE | Run the ticket test command. Start the service. `curl` each endpoint and compare status and body. |
| FE | Run the unit tests. Then run browser steps (see Browser steps). |
| FE+BE | Run the BE work. Compare the API contract with the FE fixture. Then run the browser steps. |
| Docs or config | Run the lint and done-when commands the `Verify:` row lists. No browser. |

## Start config

Only tickets whose `Verify:` row starts a service or calls HTTP (`curl` or a URL) use the config.
Others skip Start config and Login: never read, create or commit `verify.config.json`.

1. Read `verify.config.json` at the repo root, or at the path the `Verify:` row names.
2. If it does not exist, infer the start recipe from the README, `package.json`, or `Makefile`.
   Write the file with these keys: `baseUrl`, `startCommand`, `loginEnv`. Never write or use a
   config with an empty `baseUrl` or `startCommand`: if the recipe cannot be inferred, report
   BLOCKED with the reason and write no file.
3. `loginEnv` holds the NAMES `VERIFY_USER` and `VERIFY_PASSWORD`. Never write a value.
4. Commit the file on the ticket branch.
5. Start `startCommand` in the background, wait until `baseUrl` answers, stop it at the end.

## Login

Do this once, before the captured steps, out of the evidence:

1. Open the login page. Fill the form with `browser_fill_form` from `VERIFY_USER` and `VERIFY_PASSWORD`, then submit with `browser_click`. Never pass the password through `browser_run_code_unsafe`.
2. Save `storageState` to `.playwright-mcp/storage-state.json` (gitignored), nowhere else.
3. Run all captured steps signed in.

If a variable is not set, report BLOCKED. Never guess a password.

## Browser steps

For each step in the `Verify:` row:

1. `browser_navigate` to the page.
2. `browser_snapshot` to see the page.
3. `browser_run_code_unsafe` with an assertion on exact text or a selector. A false assertion
   throws and the step fails.
4. `browser_take_screenshot` into `.playwright-mcp/<ticket>/`, named by step number. In a worktree
   the tool refuses the path: use `page.screenshot({ path })` in `browser_run_code_unsafe`.

After the last step, call `browser_console_messages`. Count the errors. One or more is a fail.

## Base mode

`Mode: base` (from the prompt) checks that the steps fail on the base commit, in a worktree with
no ticket code:

1. Read `verify.config.json` from the implement worktree path in the prompt. Never write or commit it.
2. Run Start config (step 5), Login and Browser steps as usual.
3. The steps are expected to FAIL. Report the real result and do not judge it.
4. Commit nothing.

## Report

Return a table: one row per command or step, PASS or FAIL, and the assertion text.
Add the console error count and the path of each still. Any FAIL makes the whole run FAIL.
Do not fix code.
