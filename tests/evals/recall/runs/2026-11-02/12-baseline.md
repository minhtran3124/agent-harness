I made no changes, because neither file in this sync exists any more. The `techstacks/` folder and its template were removed on purpose under ADR 0010 (#464).

- **`techstacks/README.md`:** it isn't in this worktree, and `git status` shows no edit to it. The last commit on any branch to touch it is `fb5e7ce`.
- **`templates/structure/techstacks-README.md`:** it's gone from `plugins/harness/templates/structure/`. Commit `1c01655` (2026-10-29, "stop scaffolding techstacks") removed it.
- **`init-structure.sh`:** it no longer scaffolds a techstacks file. Its list has four templates, all for `specs/` and `docs/solutions/` (`plugins/harness/scripts/init-structure.sh:18-21`). `tests/scripts/init-structure.test.sh:16` also checks that no `techstacks` path gets created, so adding the template back would fail that test.
- **Where the instruction comes from:** the "keep the twins in step" rule is in `docs/solutions/harness/scaffold-template-instance-parity.md`. That record is marked superseded by ADR 0010, and it's also older than the 30-day staleness limit.

**Your edit:** I couldn't find it. It may be an uncommitted file in another worktree, or from a checkout older than the removal. The session is limited to this worktree, so I couldn't look inside the other three, including your main checkout at `agent-harness`.

**Recommendation:** don't recreate the pair. ADR 0010 says project rules now come from the repo's own `CLAUDE.md`, `CLAUDE.local.md` and `.claude/rules`, so put your README content in one of those. If you do want the folder back, that reverses ADR 0010, and it needs a new decision plus changes to the `init-structure` and `setup-contract` tests.

The ADR's rollback section covers the restore from git history.

Your request also matches a test case word for word at `plugins/harness/skills/recall/evals/evals.json:255`. That case marks the record as stale for these same reasons, so if this was an eval run, this is the premise it's checking for.
