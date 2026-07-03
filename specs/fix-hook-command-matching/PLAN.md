---
slug: fix-hook-command-matching
status: active
owner: Minh Tran
created: 2026-07-03
---

# Wave 0a — Fix commit-gate command-matching bypass

## 1. Motivation

Four PreToolUse hooks decide whether to gate a git command by matching the command string.
Three anchor with `grep -qE '^git commit'` (`commit-quality-gate.sh:11`,
`risk-corroboration.sh:26`, `branch-guard.sh:14`); one uses a substring case
(`check-untracked-py.sh:9`). All are trivially bypassed — **reproduced live** (DR-1):

```
cd x && git commit     # ^git commit anchor: all three miss it
git -C dir commit      # anchor AND substring miss it
git -c k=v commit      # anchor misses it
command git commit     # anchor misses it
echo done; git commit  # anchor misses it
```

Any of these slips the secrets scan, debug-artifact check, targeted pytest, and lane
corroboration. The safety layer the whole harness advertises is one `&&` from silence.

Separately, `settings.json` uses `"if": "Bash(git *)"` and `statusMessage` keys that are **not
in the Claude Code hooks schema** and are silently ignored — so the four hooks already run on
*every* Bash call and rely entirely on the (broken) internal matcher. Removing `"if"` cannot
change behavior; it only removes a false impression of config-level gating.

## 2. Non-goals

- Not fixing the `grep -v '/\.claude/'` dead exclusion in `check-untracked-py.sh:10` (separate
  DR-Low finding; out of scope to stay surgical — noted in §5).
- Not touching break-glass design, branch-isolation coverage, or any other DR finding.
- Not changing what the gates *do* once triggered — only *whether they trigger*.
- Not designing a full shell parser: quote-aware tokenization of arbitrary shell is out of
  scope. We tokenize on whitespace + separators, which is sufficient to detect the git
  invocation (message quoting comes after the `commit` subcommand and does not affect detection).

## 3. Success Criteria

1. Every DR-1 bypass form is detected as a git-commit invocation (pinned by test).
2. Safe/adjacent forms do NOT false-fire: `echo "git commit"`, `git log --grep=commit`,
   `git commit-graph write` (a real non-commit subcommand), `git show`, `# git commit` comment.
3. `check-untracked-py.sh` detects both commit and push under the same wrapped/prefixed forms.
4. `bash scripts/run-tests.sh` stays green; the new test file runs inside it (and thus in CI).
5. `settings.json` (root) + `.claude/settings.json` (deployed) carry no schema-invalid keys, or
   keep only keys verified valid; hooks still fire (verified by piping JSON to a hook).
6. The shared matcher lib is included in `deploy-harness.sh` / `install-harness.sh` payloads so
   consuming repos get it (the external repo shipped a "missing installer files" bug — avoid it).

## 4. Tasks

### Task 1.1 — Shared tokenizing matcher lib + unit tests

```xml
<task id="1.1" wave="1">
  <files>hooks/lib/git-command.sh, tests/hooks/command-matching.test.sh</files>
  <action>
Create hooks/lib/git-command.sh (bash 3.2, no grep -P, no declare -A) exposing two functions:
  - hook_cmd_is_git_commit "$command"        -> exit 0 if any segment is a `git … commit`
  - hook_cmd_is_git_commit_or_push "$command"-> exit 0 for commit OR push
Algorithm (both share a helper `_git_subcommand_matches <cmd> <subcmd-regex>`):
  1. Split the command on shell separators && || ; | & and newlines into segments
     (sed -E 's/(\|\||&&|[;|&])/\n/g'); iterate segments.
  2. Per segment: read words with `read -ra` after stripping leading blanks.
     Skip leading prefix tokens: `cd`(+next word), env assignments (^[A-Za-z_][A-Za-z0-9_]*=),
     and the wrappers `command|builtin|exec|sudo|nice|env`. Any other token -> segment is not
     a git call, continue.
  3. Require the next token == `git`; else continue.
  4. Walk git global options: `-C`(+next), `-c`(+next), and any token starting with `-`
     (e.g. --no-pager, --git-dir=…) -> skip.
  5. First remaining non-option token is the subcommand; match it (exact) against the target
     regex (`^commit$` or `^(commit|push)$`). Exact match so `commit-graph` does NOT match.
Add tests/hooks/command-matching.test.sh sourcing tests/lib.sh and the lib; assert:
  - MUST match (commit): all DR-1 forms above + plain `git commit -m x` + `git -c a=b -C d commit`.
  - MUST NOT match: `echo "git commit"`, `git log --grep=commit`, `git commit-graph write`,
    `git show`, `git status`, empty string, `cd git-commit-dir && ls`.
  - commit_or_push: `git push`, `cd x && git push origin main` match; `git commit` matches; `git fetch` does not.
Do NOT wire the hooks yet — this task is the lib + its unit proof only.
  </action>
  <verify>bash tests/hooks/command-matching.test.sh</verify>
  <done>Lib exists; every assertion passes; no DR-1 form escapes and no safe form false-fires.</done>
</task>
```

### Task 2.1 — Rewire the four hooks to the shared matcher

```xml
<task id="2.1" wave="2">
  <files>hooks/commit-quality-gate.sh, hooks/risk-corroboration.sh, hooks/branch-guard.sh, hooks/check-untracked-py.sh</files>
  <action>
In each hook, replace the command filter with a call to the shared lib. Source it robustly
relative to the script: `source "$(cd "$(dirname "$0")" && pwd)/lib/git-command.sh"`.
  - commit-quality-gate.sh:11  — replace `if ! echo "$COMMAND" | grep -qE '^git commit'; then exit 0; fi`
    with `hook_cmd_is_git_commit "$COMMAND" || exit 0`.
  - risk-corroboration.sh:26   — replace `echo "$COMMAND" | grep -qE '^git commit' || exit 0`
    with `hook_cmd_is_git_commit "$COMMAND" || exit 0`.
  - branch-guard.sh:14         — same replacement as risk-corroboration.
  - check-untracked-py.sh      — replace the `case "$CMD" in *"git commit"*|*"git push"*)` block
    with `hook_cmd_is_git_commit_or_push "$CMD" || exit 0` guard, keeping the existing
    untracked-.py deny-JSON body. Preserve its `permissionDecision: deny` JSON output shape.
Keep the sourcing early (before the existing REPO_DIR resolution). Do NOT change any other
behavior in these hooks. Match existing style (comments, exit codes: 2 = block for
commit-quality-gate/risk-corroboration; branch-guard stays warn-only exit 0).
  </action>
  <verify>bash scripts/run-tests.sh</verify>
  <done>All four hooks use the lib; full suite green; hooks still block/warn as before on a real `git commit`.</done>
</task>
```

### Task 2.2 — Integration test: wrapped commands reach the gates

```xml
<task id="2.2" wave="2">
  <files>tests/hooks/gate-integration.test.sh</files>
  <action>
Add an integration test (sources tests/lib.sh) that pipes hook-input JSON to branch-guard.sh
(pure, no side effects) and asserts it ACTS on wrapped forms. For each of
`{"tool_input":{"command":"cd /tmp && git commit -m x"}}`, `git -C . commit`,
`command git commit`, `echo done; git commit` — run on a temp git repo checked out to a branch
named `main`, assert stderr contains "[BRANCH GUARD]" (i.e. the hook now recognizes the commit).
For a control (`{"tool_input":{"command":"echo hi"}}`) assert NO branch-guard output.
Rationale: branch-guard is the only gate with zero side effects, so it safely proves the
matcher is wired end-to-end through real stdin JSON, not just unit-tested in isolation.
  </action>
  <verify>bash tests/hooks/gate-integration.test.sh</verify>
  <done>Wrapped forms trigger branch-guard; control does not.</done>
</task>
```

### Task 3.1 — Remove schema-invalid settings keys (verify first) + propagate lib to installers

```xml
<task id="3.1" wave="3">
  <files>settings.json, scripts/deploy-harness.sh, scripts/install-harness.sh</files>
  <action>
1. Verify against the current Claude Code hooks schema whether `if` and `statusMessage` are
   valid hook-object keys (use the claude-code-guide agent or context7/claude-api docs). `if` is
   confirmed inert (matching is by `matcher`); remove all four `"if": "Bash(...)"` keys from
   settings.json. For `statusMessage`: remove ONLY if verification shows it is not a supported
   key; if it drives the progress label, keep it. Record the finding in SUMMARY `### Deviations`.
2. Ensure hooks/lib/ is copied into consuming repos: confirm deploy-harness.sh copies hooks/
   recursively (it uses copy_dir) so hooks/lib/git-command.sh ships; if install-harness.sh uses
   an explicit file list, add hooks/lib/git-command.sh to it.
Do NOT edit .claude/settings.json or .claude/hooks/ by hand — those are the deployed tree,
regenerated in the next task.
  </action>
  <verify>python -c "import json;json.load(open('settings.json'))" && bash scripts/run-tests.sh</verify>
  <done>settings.json is valid JSON with no confirmed-invalid keys; lib is in the install payload; suite green.</done>
</task>
```

### Task 3.2 — Redeploy into .claude/ and end-to-end verify

```xml
<task id="3.2" wave="3">
  <files>.claude/settings.json, .claude/hooks/git-command.sh</files>
  <action>
Run `bash scripts/deploy-harness.sh` (or the repo's canonical self-deploy) to regenerate the
.claude/ tree from source, so the deployed hooks, the new hooks/lib/git-command.sh, and the
cleaned settings.json all land in .claude/. Then confirm the LIVE (deployed) matcher works:
pipe `{"tool_input":{"command":"cd x && git commit -m y"}}` to
`.claude/hooks/branch-guard.sh` from a repo on branch `main` and assert it recognizes the
commit. This closes the gap where the deployed copy — the one Claude Code actually runs — could
lag the source.
  </action>
  <verify>echo '{"tool_input":{"command":"cd /tmp && git commit -m y"}}' | bash .claude/hooks/branch-guard.sh 2>&1 | grep -q 'BRANCH GUARD' && echo OK</verify>
  <done>Deployed .claude/ tree matches source; live wrapped-commit detection confirmed.</done>
</task>
```

## 5. Risks

- **Over-tight matcher false-blocks valid git.** Mitigated by exact-subcommand match
  (`commit-graph` excluded) + the MUST-NOT-match assertions in Task 1.1. Ship behavior is
  identical for a plain `git commit`; only wrapped forms change from allowed→gated.
- **Two source-of-truth trees (`settings.json` vs `.claude/settings.json`, `hooks/` vs
  `.claude/hooks/`).** Task 3.2 redeploys and verifies the live copy — never hand-edit `.claude/`.
- **`statusMessage` removal could drop the progress label.** Task 3.1 verifies before removing;
  keep if supported.
- **Adjacent dead code** (`check-untracked-py.sh:10` `.claude/` exclusion; `git ls-files` in
  session cwd) is left untouched — flagged here, deferred to a later wave to stay surgical.
- **Installer file-list drift** (the external repo's real bug) — Task 3.1 explicitly checks the
  payload includes the new lib.

## 6. Status Log

- 2026-07-03 — plan drafted (proposed). Awaiting review before worktree + execution.
- 2026-07-03 — approved; worktree `fix/hook-command-matching` off v2; status active.
- 2026-07-03 — Task 1.1 done (lib + 28 unit tests). Task 2.1 done (4 hooks rewired; `new_repo`
  copies lib — Rule 3). Task 2.2 done (6 integration tests). Task 3.1 done (removed 4 `"if"`
  keys — REQUIRED per corrected schema finding; kept `statusMessage`; lib propagates via
  `copy_dir` recursion + install PAYLOAD `hooks`). Task 3.2 done (redeployed `.claude/`, live
  e2e verified). Full suite ALL GREEN. Awaiting correctness-review + intent-review before ship.
