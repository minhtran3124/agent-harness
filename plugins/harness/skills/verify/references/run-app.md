# Run the app: Start config, Login, Browser steps

Read this before Start config, Login or Browser steps. Skip it for tickets that start no service and call no HTTP.

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
5. With a `${PORT}` placeholder in `baseUrl`, export a free `PORT` and substitute it; export each `env` entry; resolve `$VERIFY_*`. Start `startCommand` in the background, wait for `baseUrl`, stop it after.

See `config.md` for `env`, `${PORT}` and throwaway credentials.

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
