# gh-213-safeguard-parity-test — Summary

Lane: normal
Confidence: high
Reason: Additive test/CI work (new `tests/scripts/safeguard-parity.test.sh` + `run-tests.sh` registration); no manifest hard gate fires — the test reads `skills/`, `agents/`, `rules/` but does not modify them. Multi-file with a new CI-blocking gate, so not tiny.
Flags: cross-platform (CI runs ubuntu+macos)
Affects: tests/scripts/* only — run-tests.sh already globs tests/scripts/*.test.sh, no registration edit
Input-type: spec slice

> Slice 1 of 3 of GitHub issue #213 (initiative). The issue itself mandates one PR per item,
> each through normal intake, item 1 first. Items 2 and 3 get their own intake when started.
> Research is already done: `specs/brichan-mechanism-port/research-brief.md` (Standard depth,
> pinned at Brichan `b63b29d`) — xia2 must not be re-run; the port design there is the input
> to planning. Do not rename `specs/brichan-mechanism-port/`.

### Intent

From <https://github.com/minhtran3124/agent-harness/issues/213> (verbatim, item 1 + execution note):

> ## 1. Verbatim safeguard-parity test (~0.5 day)
>
> Port of Brichan's `tests/contract/test_skill_parity_contract.py`: assert that load-bearing safeguard sentences appear verbatim (whitespace-normalized) in **every** context that duplicates them, plus negative assertions banning previously-rejected overbroad wording, plus proximity checks (a dangerous action string must sit next to its precondition).
>
> First markers for us:
> - `not_observed != absent` across `rules/behavior.md`, `agents/reviewer.md`, `correctness-scorer-prompt.md`
> - the `spec_verdict`/`quality_verdict` pair across its five duplication sites
> - template↔instance **heading** parity driven by the `rows` table in `scripts/init-structure.sh`
>
> Replaces part of context-propagation-audit's manual work with a permanent CI check. Note: byte parity `rules/` ↔ `.claude/rules/` is deliberately wrong (deploy rewrites paths; `.claude/` untracked) — marker parity post-deploy is the right shape.
>
> ## Suggested execution
>
> One PR per item, each through normal intake. Item 1 first (cheapest, highest leverage).

## What changed

Added `tests/scripts/safeguard-parity.test.sh` (414 lines, the only implementation file): a CI contract suite asserting whitespace-normalized safeguard-marker parity across duplicated prose contexts (6 marker rows), negative markers banning reviewer-write phrasings, an action↔audit-record proximity window, and template↔instance heading parity driven live from the `rows` table in `scripts/init-structure.sh` (5 pairs checked, INDEX visibly exempt). Every check family carries a fail-closed diagnostic and a mutation self-check (4 total). Auto-discovered by `run-tests.sh`'s L3 glob — no registration edit. 21 passed + 1 skip in ~2s.

### Rationale

Ports Brichan's safeguard-parity mechanism as a permanent CI check replacing part of context-propagation-audit's manual work; checker functions are root-parameterized so mutation self-checks prove the suite is load-bearing, and every cannot-run path prints a distinct fail/skip (green never means skipped).

### Alternatives considered

- Byte parity `rules/` ↔ `.claude/rules/` — rejected by the issue itself (deploy rewrites paths; `.claude/` untracked).
- A separate marker config file — rejected; the marker table lives in the test, the rows mapping is parsed live from init-structure.sh (single source).

### Deviations

- Rule 1 — `assert_absent` fail-closed `(unreadable)` on norm_file failure (was fail-open, contradicted Global Constraints). `tests/scripts/safeguard-parity.test.sh`. Commit `6b94443`.
- Rule 1 — NUL-safe `find -print0` loop + `(no-md-files)` report in `assert_absent` (unquoted word-splitting risk). Commit `6b94443`.
- Rule 1 — window-0 out-of-window proximity assertion (window arithmetic previously unexercised on the reject path). Commit `6b94443`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| suite | `bash tests/scripts/safeguard-parity.test.sh` | 0 | 21 passed, 1 skipped, 0 FAIL — run at HEAD 2c726ba | SC-1 |
| mutation-case count | `grep -c "mutation check:" tests/scripts/safeguard-parity.test.sh` | 0 | prints 4 | SC-2 |
| glob placement | `ls tests/scripts/safeguard-parity.test.sh` | 0 | on the run-tests.sh L3 glob path | SC-3 |
| visible INDEX exemption | `bash -c "out=\$(mktemp); bash tests/scripts/safeguard-parity.test.sh > \$out 2>&1; grep -q docs-solutions-INDEX \$out"` | 0 | skip line names the pair + reason | SC-4 |

### Not auto-verified

- The negative-marker set bans plausible invariant-contradicting phrasings, not historically-rejected wording — reached traceability; no rejection history exists to derive from.
- Post-deploy marker parity (deployed `.claude/` tree after path rewriting) is not asserted — source-tree parity only; deferred pending human direction.
- The "five duplication sites" mapping for the verdict pair (2 literal + 3 prose) — reached traceability against today's grep; the site list is curated in the test, not derived.

### Review roll-up (Minor findings, for final review chain)

- 1.1 Minor (quality): mutation-case `case` glob `*rules/behavior.md*` would also match the `(missing-file)` spelling; optional tightening to exact `[ "$mut" = "rules/behavior.md" ]`. Non-blocking — negative control covers the practical window.
- 1.1 Minor (quality): report-1.1.md header line-count stale (116 → 134 after fix commit 455561b); update at ship.

- 1.2 Minor (plan-mandated): proximity window arithmetic — RESOLVED in task 1.3 (window-0 assertion, commit 6b94443).
- 1.2 Minor (quality): `assert_absent` fail-open on unreadable file — RESOLVED in task 1.3 (commit 6b94443).
- 1.2 Minor (quality): unquoted `find` word-splitting — RESOLVED in task 1.3 (commit 6b94443).
- 1.2 Minor (quality): banned phrases are plain-English substrings; future benign prose could false-positive. No change now; tighten via compound on first real false positive.

- 1.3 Minor (quality): partial-parse truncation of rows table could under-check — RESOLVED post-review (row-count floor >= 6, commit fdebf75).

### Correctness-review advisories (scored < 75, durably recorded — tests/scripts/safeguard-parity.test.sh)

- 50 — `assert_absent` loop ignores `find`'s exit status; an untraversable subdir is silently unscanned (:149-159).
- 50 — banned-phrase match is case-sensitive and intra-phrase-emphasis-blind (:153-155).
- 50 — negative-marker scan surface includes `skills/*/tests/` fixture corpora that deploy strips; a fixture quoting a banned phrase would false-fail (:168).
- 50 — `parse_rows` truncates at the first non-pipe line; the >=6 floor can't see truncation of later-added rows (:289/:343).
- 50 — assert_marker mutation case uses a glob where siblings use exact equality (:126).
- 50 — proximity uses nearest-pair distance; a second far-away anchor occurrence is undetectable (:198-200).
- 50 — window-0 proximity case exercises the reject branch but not the gap==window boundary; `-le`→`-lt` mutant survives (:262-279).
- 50 — fixture guards run after the mkdir/cp they protect; failed `mktemp -d` writes to `/rules` etc. on a root-writable FS (:102 and 4 siblings).
- 50 — heading mutation self-check copies the live hook-mutated specs/STATE.md instead of a synthetic fixture (:350-365).
- 50 — `rel="${f#$root/}"` expands `$root` unquoted as a pattern; glob metachars in the checkout path break the strip (:151).
- 25 — `assert_marker` with zero relpaths returns a vacuous pass; unreachable from current call sites (:35-49).

- re-review (low, latent) — extract_headings evaluates the HTML-comment opener before the fence guard; an unterminated `<!--` inside a fenced block silently drops all later headings. Not reachable by any current template. Fix: check fence state first.
- re-review nit — `(no-md-files)` return discards accumulated `(missing-dir)` names in its diagnostic (still fails closed).
- re-review nit — per-line heading normalizer collapses but doesn't trim; a trailing space on a legal markdown heading would false-miss. Not triggered by any current pair.

### Intent Findings

- gap→resolved-by-mapping — "five duplication sites" for the verdict pair: covered as 2 literal-token sites (`spec_verdict`/`quality_verdict` in SDD SKILL.md + task-reviewer-prompt.md) + 3 prose sites (`quality verdicts` in agents/task-reviewer.md + skills/README.md; `two verdicts` in rules/auto-correct-scope.md + skills/README.md) = 5. The `scripts/*.py` consumers the reviewer proposed are code, already guarded by `scripts/check_task_review_contract.py`, not prose duplication sites.
- drift (advisory) — the negative-marker set is invariant-derived (reviewer structural read-only), not recovered from previously-rejected wording; this repo has no such rejection history yet. The set grows only via `compound` when a real rejection is recorded.
- drift (advisory) — the shipped proximity pair is action↔audit-record (`BRANCH_ISOLATION_REASON` ↔ `break-glass-log.md`, currently adjacent lines), not action↔precondition; the harness supports precondition pairs and the first real one should be added via `compound`.
- gap (deferred, ambiguous) — "marker parity post-deploy is the right shape": shipped as source-tree marker parity (reading a); a deploy-to-scratch + re-assert step (reading b) is NOT implemented. Deferred pending human direction — see final report / PR description.
- drift (advisory, equivalent) — markers are tokens/fragments rather than full sentences; consistent with the intent's own token-shaped first marker (`not_observed != absent`); machinery supports sentences when wanted.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
