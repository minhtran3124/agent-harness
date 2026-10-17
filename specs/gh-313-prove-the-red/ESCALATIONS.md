# gh-313-prove-the-red — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: orchestrator (correctness review, location `scripts/verify_summary.py:528-538`, score 75)
- date: 2026-10-17
- trigger: in-flight
- question: How should the fix-diff check decide which paths are the red test files, given that the exact-token rule (D1, D4) gives wrong results in both directions?
- context: The correctness review is blocked on this finding. (a) A red command that names a directory, an absolute path, a quoted path or a cwd-relative path does not exclude the edited test file, so a test-only edit after the red commit passes. (b) A red command that names the file under repair (`python3 -m doctest scripts/foo.py`, `bash hooks/x.sh < fixture`) excludes the real fix, so a real fix is reported as "no code change". Any fix reopens settled decisions D1 and D4 (a DC entry in design.md).
- options:
  - A) Test files are the paths that the red commit itself changed (`git diff-tree --no-commit-id --name-only -r --no-renames <red sha>`), outside `specs/`. Ignore the command tokens. Fixes (a) and (b). Supersedes D1 and D4. Cost: if the red commit also edits source, a fix that touches only that source is reported as "no code change"; the implementer prompt already says to commit the failing test before the fix. (recommended)
  - B) Keep the tokens, but exclude a token path only when the red commit also changed it. Fixes (b) only. (a) stays a documented limit under D4. Supersedes D1.
  - C) Keep D1 and D4. Record (a) and (b) in design "What we do not claim" and as advisories. No code change.
- default_if_no_response: BLOCK
- decision: A
- decided_by: Minh Tran
- decided_at: 2026-10-17
