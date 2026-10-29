---
name: verify
description: Prove that a finished ticket works in a real run, with a pass or fail result from assertions. Use when a ticket has a `Verify:` row and its code is ready, or from `/harness:verify`.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, ToolSearch, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_fill_form, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_snapshot, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_console_messages, mcp__plugin_playwright_playwright__browser_run_code_unsafe
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

## Start config

Only tickets whose `Verify:` row starts a service or calls HTTP use the config.
Others skip Start config and Login; never read, create or commit `verify.config.json`.

1. Read `verify.config.json` at the repo root, or at the path the `Verify:` row names.
2. If it does not exist, infer the start recipe from the README, `package.json`, or `Makefile`.
   Write the file with `baseUrl`, `startCommand`, `loginEnv`. Never write or use a
   config with an empty `baseUrl` or `startCommand`: if it cannot be inferred, report
   BLOCKED and write no file.
3. `loginEnv` holds the NAMES `VERIFY_USER` and `VERIFY_PASSWORD`. Never a value.
4. Commit the file on the ticket branch.
5. With a `${PORT}` placeholder in `baseUrl`, export a free `PORT` and substitute it; export each `env` entry. Start `startCommand` in the background, wait until `baseUrl` answers, stop it after.

See `references/config.md` for `env`, `${PORT}` and throwaway credentials.

## Login

Once, before captured steps:

1. Open the login page. Fill the form with `browser_fill_form` from `VERIFY_USER` and `VERIFY_PASSWORD`, then `browser_click` submit. Never pass the password through `browser_run_code_unsafe`.
2. Save `storageState` to `.playwright-mcp/storage-state.json` (gitignored), nowhere else.
3. Run captured steps signed in.

If a variable is unset, report BLOCKED unless config.md allows throwaway credentials. Never guess a password.

## Browser steps

For each step in the `Verify:` row:

1. `browser_navigate` to the page.
2. `browser_snapshot` it.
3. `browser_run_code_unsafe` with an assertion on exact text or a selector. A false assertion
   throws and the step fails.
4. `browser_take_screenshot` into `.playwright-mcp/<ticket>/`, named by step number. In a worktree
   the tool refuses the path; use `page.screenshot({ path })` in `browser_run_code_unsafe`.

After the last step, call `browser_console_messages`. Count the errors. One or more is a fail.

## Base mode

`Mode: base` checks that the steps fail on the base commit, in a worktree without ticket code:

1. Read `verify.config.json` from the implement worktree path in the prompt. Never write or commit it.
2. Run Start config (step 5, with the `${PORT}` and `env` export), Login and Browser steps as usual. Commit nothing.
3. The steps are expected to FAIL. Report the real result, do not judge it.
4. Do not retry. The workflow decides what the result means.

## Report

Return a table: a row per command or step with PASS or FAIL, assertion text, console error count, still paths. Any FAIL makes the whole run FAIL.
Never fix code. The workflow builds the GIF from the stills.
