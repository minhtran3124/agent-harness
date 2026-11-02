The harness already has both things you're asking about, and the decision was **pilot first, and a warn-only ratchet that never blocks a build**. The linter is in `plugins/harness/skills/asd-ste100/`, vendored with its skill. I read your request as extending these checks or vendoring another skill, and the rules below cover both. I changed nothing.

## Ratchet
- **Warn-only:** `scripts/check_ste_baseline.py` compares each file's hard count with `scripts/ste-baseline.json`. `run-tests.sh` calls it, and the default run always exits 0.
- **No blocking gate:** a blocking lint in CI or a hook was rejected, because the linter is a style tool. Only `--strict` exits 1, on a WARN or a skipped run, and only plan checks use it.
- **`synonym-rotation` is excluded:** the one-word rule showed no measured effect (H3, 40/40 vs 36/36 assertions correct). The rule is that a rule with a measured null must not block.
- **Only one rule has a measured effect:** machine-decidable acceptance criteria (1/8 vs 8/8, p=0.0014). `must` vs `should` was inconclusive, so a truly mandatory step belongs in a gate, not in a modal verb.

## Pilot
- **Approach:** pilot then gate was chosen over rewriting everything untested or running a full A/B first.
- **Run:** three high-traffic files were measured with comprehension probes and real `feature-intake` runs (80 trials, $2.91).
- **Pass bar:** each method had to stay within 2 correct answers of the original, with no probe falling from 10/10 to 7/10 or lower. All three passed.
- **Rollout condition:** any bulk rewrite plan must ask for a per-file meaning-equivalence review. The pilot caught two dropped conditions only because its brief asked for that, while tests passed and lint counts fell.

## Vendoring a third-party skill
- **Vendor into the skill directory:** don't commit an `npx skills` install or vendor just the linter. The record's reason is that `deploy-harness.sh` syncs only `skills/`, so consumers didn't get the install; that path has since moved under `plugins/harness/`.
- **Add `UPSTREAM.md`:** record the commit, the sha256 prefixes and every delta. Updates are manual re-vendors.
- **Word ceiling:** that file also exempts the skill from the 600-word ceiling. Any skill can claim this by adding the marker, and the review scored that as advisory.

## Where the records no longer match the tree
- **`review_package.py` is gone:** a repo-wide search doesn't find it, so the per-file review check in Decision 3 and "keep the two `DISABLED_RULES` constants equal" look obsolete. Only `check_ste_baseline.py` still has the constant.
- **Old paths:** the records use `skills/...`, but the code now lives in `plugins/harness/skills/...`. The re-vendor steps in `UPSTREAM.md` still say `skills/asd-ste100/`.
- **Counts differ by route:** a manual `ste-lint.py` run still includes `synonym-rotation`, so it shows higher counts than the ratchet.
- **Scope qualifier check was never built:** `check_scope_qualifiers.py` was proposed but doesn't exist, and I found no sign the task-reviewer instruction was added (I didn't check that prompt directly).

## Before you add a check
- **Fenced prompt text is invisible to the lint:** this is a critical pattern. Fenced dispatch prompts report `0 → 0`, and the proposed fix is not in `check_ste_baseline.py`. Treat a clean count as no evidence for that text.
- **Prove a new ratchet can fail:** run it against the pre-fix tree and require it to fail. Also derive its match from the defect, not from the same list as the fix.

Before making a new rule blocking, measure it first. Add it to the warn-only ratchet if the measurement is null or missing.

I didn't read `specs/ste100-harness-prose/DECISION.md`, which is gitignored scratch. The sources I used are `docs/solutions/harness/ste100-adoption-decisions.md`, its related solution entries, and `docs/research/ste-terminology-evidence/DECISION.md`.
