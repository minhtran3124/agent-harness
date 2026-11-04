Verdict: out-of-date match

**Possibly stale.**
- `docs/solutions/harness/scaffold-template-instance-parity.md` (`confirmed_at` 2026-08-17, 79 days old, over the 30-day limit). It is out of date for four reasons:
  - Its frontmatter says `superseded_by: docs/adr/0010-remove-techstacks-and-project-md-rules-from-repo-files.md`, and that ADR exists.
  - Glob finds no `techstacks/` directory and no `techstacks-README.md` anywhere in the repo.
  - `plugins/harness/scripts/init-structure.sh` has zero `techstacks` mappings.
  - Its advice (edit both twins and run `diff -q`) therefore has no files to act on.
- `docs/solutions/harness/techstacks-project-owned-stack-profiles.md` (`confirmed_at` 2026-07-17, 110 days old, over the 30-day limit). It is out of date because its frontmatter says `superseded_by: docs/adr/0010-remove-techstacks-and-project-md-rules-from-repo-files.md`. Its `affects` paths `techstacks/README.md` and `scripts/init-structure.sh` are also missing. The script now lives at `plugins/harness/scripts/init-structure.sh`.

Both records say techstacks was removed. Check `docs/adr/0010-remove-techstacks-and-project-md-rules-from-repo-files.md` before you keep editing `techstacks/README.md`. Neither the file nor its template twin is in this worktree.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/scaffold-template-instance-parity.md`, `docs/solutions/harness/techstacks-project-owned-stack-profiles.md`. I also ran Glob and Grep on `**/techstacks*/**`, `**/techstacks-README.md`, `**/init-structure.sh`, `docs/adr/0010*`, and `techstacks` in `plugins/harness/scripts/init-structure.sh`.
