**The strict gate you describe no longer exists in this repo, so nothing here can be splitting your row or timing it out.** I didn't change anything, because there's no `SUMMARY.md` to fix: this worktree has no `specs/` directory, and a search for `**/SUMMARY.md` found nothing.

## What was removed
- **Gate scripts:** `44e9c2f` and `d5b7ba0` (both #349, and both in this branch's history) deleted `ci-strict-gate.sh`, `verify_summary.py` and `check_verify_rows.py`.
- **`SUMMARY` template:** it went too, according to `CHANGELOG.md:85`.
- **Old guidance:** `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md` describes this exact symptom, but it's stale. It was last confirmed 2026-08-17, and two of the files it lists under `affects` are gone.

## Which fix you need
I can't tell where you're seeing this, so it depends on your setup:

- **On current code:** you may be following old docs, or the failure comes from something else. Verification now uses a single `Verify:` line in the ticket, not a `### Verify` table, so a `|` in the command can't split any columns.
    - A whole-suite row is fine, because `plugins/harness/skills/intake/SKILL.md:61` rates `Verify: bash scripts/run-tests.sh` as READY.
    - `ship.js` has no 60s limit, and `harness-ci.yml` sets no `timeout-minutes`.
    - If something is still timing out, send me the failing output. One thing to check is the Bash tool's 120-second default, which applies when an agent runs the suite without a longer timeout. I didn't time the suite, so that's only a guess.
- **On an older checkout (for example `legacy-v2.37.0`, or a copied `.claude/` from before #349):** the old rules still apply, so fix both problems in the row:
    - **Remove pipes:** the parser splits rows on `|`, so use `grep -e a -e b` instead of `grep -E "a|b"`. Replace `cmd | wc -l` with a redirect to a temp file, and `||` chains with captured `$?` values.
    - **Keep it under 60s:** the gate re-runs each command with a 60s limit. Remove `bash scripts/run-tests.sh` from the table, mention it in a prose note saying the CI `tests` job covers it, and use one fast, specific check in the table instead.

## Problems this exposed
Two things are wrong in the repo, and I left both alone:

- **Stale record:** the record is still marked `severity: critical`, and both `critical-patterns.md` and `INDEX.md` still list it, so people can keep acting on rules that no longer exist.
- **Recall eval gap on this branch:** your message is word for word eval 3 in `plugins/harness/skills/recall/evals/evals.json`. That record meets the stale definition in `recall/SKILL.md`, but eval 3 has no `stale_premise` assertion, unlike evals 11 and 12. A recall answer that lists the record under **Do first** or **Avoid**, telling you to follow the retired rules, would still pass. `/harness:recall` has to print `pipe-free` or `60s` to pass that eval, so it needs the same `stale_premise` assertion.
