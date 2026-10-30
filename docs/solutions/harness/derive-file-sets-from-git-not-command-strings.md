---
problem_type: knowledge
module: scripts/verify_summary.py
tags: git-diff-tree, command-parsing, test-file-detection, lane-gate, red-green, fix-diff, correctness-pass-catch, design-decision-reopened
severity: standard
applicable_when: A gate or script must know which files a recorded step touched (the test files of a red commit, the files of a fix), and the first idea is to parse them out of a command string that the record holds.
affects:
  - scripts/verify_summary.py
supersedes: null
confidence: high
confirmed_at: 2026-10-17
---
## Applicable When

A gate or script must know which files a recorded step touched. An example is the test files of
a red commit. The first idea is often to parse the file names out of a command string that the
record already holds.

## Pattern

Take the file set from git, not from the command text. A command string names what a person
typed, not what changed. In gh-313 the first design (D1, D4) treated each whitespace token of the
red test command as a test file. The plan-blind correctness review scored this 75, because it
failed in both directions:

- `pytest scripts/`, an absolute path, a quoted path or a path relative to a subdirectory did not
  match the edited test file. So a test-only edit after the red commit passed as a fix.
- A command that runs the file under fix (`python3 -m doctest scripts/foo.py`,
  `bash hooks/x.sh < fixture`) put the fixed file in the token set. So the check reported a real
  fix as "no code change".

The fix (E001 = A, D10) takes the red test files from the red commit itself:
`git diff-tree --root --no-commit-id --name-only -r -z --no-renames <red sha>`.

## How to Use

- Ask which commit or index state records the step, and list its paths with `git diff-tree` or
  `git diff --name-only`. Use `-z` and `--no-renames` so user config does not change the output.
- Use the command text only for what it is: the command to run.
- At design time, test the rule against real command shapes. Try a directory, an absolute path,
  a runner script, and a command that runs the code under test.
- State the cost of the git rule. In gh-313, the red commit can also edit source. Then the check
  reports a later fix to only that source as no change. A merge commit lists no paths without `-m`.

## Gotchas

- The token rule was a user-approved decision, and the per-task review passed it. Only the
  plan-blind correctness review found it. Reopening it needed a Rule 4 escalation and a `DC<n>`
  entry, and the intent had to be amended and re-pinned.

## Related

- docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md
- docs/solutions/harness/gate-config-must-read-index.md
