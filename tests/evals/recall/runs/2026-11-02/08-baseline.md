**This repo no longer has a risk gate, so the high-risk result isn't coming from anything in this branch.** The gate that keyed on `^hooks/` was `risk-corroboration.sh`. It was merged into `commit-gate.sh`, which #349 then deleted (`CHANGELOG.md:83`), along with the `Lane:` checks.

I didn't change anything or run the test suite; this comes from reading the code.

**Stale guidance:** `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md` says to declare `Lane: high-risk` with Verify and Rollback blocks, but don't follow it. It was last confirmed 2026-07-17, and nothing in this tree outside `docs/` or the changelog enforces it, apart from eval 8's fixture text. `scripts/verify_summary.py`, which it tells you to run, isn't in `scripts/` either.

**What will block a dormant hook now:** the wiring check, which is a different problem.
- **The failing test:** `tests/scripts/settings-wiring.test.sh:32` fails any `plugins/harness/hooks/*.sh` that isn't registered, with "a hook script is on disk but not wired". That's probably what you're hitting if the failure comes from `run-tests.sh`.
- **Wrong file:** hooks are registered in `plugins/harness/hooks/hooks.json`, not `settings.json`. The test at line 39 and `lint-doc-truth.sh:104` both fail if `settings.json` wires any hooks.
- **Hook table:** `lint-doc-truth.sh:98` also requires a row for the hook in the `CLAUDE.md` table. A non-✅ row is accepted as dormant.
- **Conflicting checks:** the lint allows a dormant hook, but the test doesn't.

**My recommendation:** add the script, its `hooks.json` entry and its `CLAUDE.md` row in the same PR, with the script at mode `100755`. Shipping it dormant would mean loosening the test at line 32, and only you can approve that under the "never weaken a test" rule.

**If your message is different:** if it mentions a lane or high risk, it's coming from outside this tree. Nothing in `~/.claude/settings.json` references the old gates, and `core.hooksPath` isn't set. I couldn't check `~/.claude/hooks` (permission prompt) or the `.git/hooks` directory. The other possibilities are an older installed copy of the plugin, or a consumer project that still has the legacy hooks. `/feature-intake` also still classifies risk lanes, so a high-risk result could come from there, though I didn't open that skill. The harness `intake` skill doesn't mention hooks at all.

**Problem on this branch:** eval 8 in `plugins/harness/skills/recall/evals/evals.json:167` has this exact prompt, but its action assertion expects `Lane: high-risk`, `high-risk up front` or `Rollback`. That rewards repeating the retired guidance, and even an answer rejecting it passes just by naming those terms, as this one does. It should test for flagging the record as stale instead.
