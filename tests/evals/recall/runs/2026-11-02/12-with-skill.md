Verdict: existing decision: ADR 0010 removed `techstacks/` and its template twin, so there is no pair left to keep in step.

**Possibly stale.**
- `docs/solutions/harness/scaffold-template-instance-parity.md` (`confirmed_at` 2026-08-17, 77 days old):
  - ADR 0010 supersedes it.
  - `techstacks/README.md` and `templates/structure/techstacks-README.md` are missing.
  - `scripts/init-structure.sh` is missing; the script is now at `plugins/harness/scripts/init-structure.sh`.
  - The script's four rows have no techstacks mapping, so the record's premise fails. Do not apply its `diff -q` parity step here.
- `docs/solutions/harness/techstacks-project-owned-stack-profiles.md` (`confirmed_at` 2026-07-17, 108 days old):
  - ADR 0010 supersedes this decision record, so it is listed here and not under Already decided.
  - `techstacks/README.md` and the script's old `scripts/` path are missing. I did not check its three `rules/*.md` paths.

**Note for this task.** No `techstacks/README.md` exists in this worktree, so your edited file is not here. ADR 0010 has `status: needs-review`. To reverse it, it says to restore `techstacks-README.md`, `PROJECT.template.md` and the setup steps from git history. Project rules now come from `CLAUDE.md`, `CLAUDE.local.md` and `.claude/rules`.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/scaffold-template-instance-parity.md`, `docs/solutions/harness/techstacks-project-owned-stack-profiles.md`, `docs/adr/0010-remove-techstacks-and-project-md-rules-from-repo-files.md`, `plugins/harness/scripts/init-structure.sh`. Glob checks: `techstacks/**`, `templates/structure/**`, `**/*techstacks*`, `**/*init-structure*`. Grep checks: `techstacks` across the repo outside `docs/solutions/`, and `#?464` in `docs/adr/`. The `techstacks` Grep also printed two lines from `plugins/harness/skills/recall/evals/evals.json`, which look like this eval's answer key. I did not open that file, and the findings above come from the checks listed here.
