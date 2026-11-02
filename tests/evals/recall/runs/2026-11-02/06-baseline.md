**No skill in this worktree is over the 600-word limit, so I didn't change anything.** The one on this branch, `plugins/harness/skills/recall/SKILL.md`, has 379 words, which leaves 221 words for new sentences. It doesn't need trimming, and I found no test that pins its word count (I searched `scripts/run-tests.sh`, `tests/scripts/` and `.github/workflows/`).

I counted every tracked `SKILL.md` with `wc -w`, which matches how the audit counts words:

| Skill | Words | Status |
|---|---|---|
| `asd-ste100` | 2659 | Over the limit, but exempt: it has an `UPSTREAM.md`, so `scripts/audit_skill_prompts.py:77` treats it as vendored |
| `autopilot` | 599 | Under, but only just: `tests/scripts/autopilot-launch.test.sh:19` requires under 600, so one more word fails |
| `grilling` | 598 | Under |
| `diagnosing-bugs` | 598 | Under |
| `tickets` | 597 | Under |
| `release-notes`, `intake`, `decision-record` | 595 each | Under |

Every other skill has 584 words or fewer.

**What I couldn't check:**
- **Audit script:** running it needed approval, so these counts are from `wc -w`, not its own output.
- **Other checkouts:** checking the main checkout and the `plan-556` and `adr` worktrees for uncommitted changes also needed approval. If your over-limit draft is in one of those, I haven't seen it.

**If you meant a different file:** send me its path and the sentences you want to add. It's probably one of the near-limit skills, or a draft in another checkout. I'd follow `docs/solutions/harness/deletion-test-for-word-ceiling.md`:
1. Delete only whole sentences the model would do anyway.
2. Move blocks that only some branches reach into `references/`.
3. Keep any sentence with a condition word (`if`, `only`, `never`, etc.) intact, or move it whole.
4. Check the result with `scripts/check_scope_qualifiers.py`.
