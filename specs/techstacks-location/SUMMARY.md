# techstacks-location — Summary

Lane: high-risk
Confidence: high
Reason: Diff touches templates/ (templates/structure/techstacks-README.md) which is in ci-strict-gate HARD_GATE_RE → high-risk forced mechanically. Content is a doc banner only; direction fixed by the owner decision ("keep ở root").
Flags: high-blast (templates/ via strict gate)
Affects: templates/structure/techstacks-README.md (source), techstacks/README.md (instance)
Input-type: harness improvement

### Intent

"suy nghĩ về việc move folder techstacks/ vào trong .claude/ … để mn hiểu quy tắc nó thuộc về AI" → owner decision: "ok, keep ở root". This lands Option A's actionable half — strengthen the AI-ownership *signal* via docs, keeping the folder at root.

### What changed

Added a banner to the `techstacks/` README (source `templates/structure/techstacks-README.md` + this repo's synced instance) stating plainly what it is: harness config the **AI agents read** but that **you author and commit**; it stays at the repo root (not gitignored `.claude/`) because it is versioned, team-shared, re-sync-safe content — like `specs/` and `docs/solutions/`. No relocation; the root placement decided in `research-brief.md` stands.

### Rationale

The owner's goal was comprehension ("để mn hiểu"). Per research-brief.md, `.claude/` is the wrong physical home (gitignored + harness-derived + auto-pruned) for project-authored, must-be-committed content. A README banner serves the comprehension goal without breaking versioning or the re-sync/prune guarantees.

### Alternatives considered

- Option B (move into `.claude/` + un-gitignore + protected-set guard): rejected by the owner ("keep ở root").

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| banner present in source template | `grep -q "AI coding agents read" templates/structure/techstacks-README.md` | 0 | ownership signal |
| this repo's instance is in sync with the source | `diff -q templates/structure/techstacks-README.md techstacks/README.md` | 0 | scaffold source == instance |
| techstacks/ still at root (not moved) | `bash -c 'test -f techstacks/README.md; a=$?; test ! -d .claude/techstacks; b=$?; test "$a" = 0 -a "$b" = 0'` | 0 | root placement stands |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | clean |
| verify-row lint clean on this SUMMARY (dogfood) | `python3 scripts/check_verify_rows.py specs/techstacks-location/SUMMARY.md` | 0 | pipe-free + no full-suite |

### Rollback

- `git revert <commit>` — removes the banner; doc-only, no behavior change.

### Harness-Delta

- none
