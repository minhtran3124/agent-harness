Verdict: no match

Both records on this pair are superseded and their premise is false in this repo, so I list them only under Possibly stale.

**Possibly stale.**
- `docs/solutions/harness/scaffold-template-instance-parity.md` (confirmed_at 2026-08-17, 77 days old). It is marked superseded by ADR 0010. Its `affects` paths `techstacks/README.md` and `templates/structure/techstacks-README.md` do not exist. `plugins/harness/templates/structure/` has no `techstacks-README.md`, and `plugins/harness/scripts/init-structure.sh` has no `techstacks` mapping. Its parity pattern does not apply to this pair. Note that `git ls-files` shows only the `plugins/harness/templates/structure/` templates `docs-solutions-INDEX.md`, `docs-solutions-README.md`, `docs-solutions-critical-patterns.md` and `specs-README.md`. These are other twins and I did not check whether the pattern applies to them.
- `docs/solutions/harness/techstacks-project-owned-stack-profiles.md` (confirmed_at 2026-07-17, 108 days old). It is marked superseded by ADR 0010. `techstacks/` was removed, and `rules/architecture.md` and `rules/guidelines.md` are not at the repo root.

**Search surface:** docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/scaffold-template-instance-parity.md, docs/solutions/harness/techstacks-project-owned-stack-profiles.md, plus `ls` of `techstacks/` and `templates/structure/`, `git ls-files` filtered for techstacks, init-structure and templates/structure, and grep of plugins/harness/scripts/init-structure.sh for "techstacks". I did not open ADR 0010 (docs/adr/0010-remove-techstacks-and-project-md-rules-from-repo-files.md).
