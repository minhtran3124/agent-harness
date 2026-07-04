---
slug: entropy-trend
status: shipped
owner: Minh Tran
created: 2026-07-04
---

# Wave 4 — Entropy has a trend (feat/entropy-trend)

## 1. Motivation

`scripts/harness-audit.sh` is a point-in-time advisory check with 3 promise-vs-evidence gaps
covered (SUMMARY missing `### Verify`, active PLAN gone stale, `docs/solutions` stale) and zero
test coverage of its own. `docs/harness-v03-plan-overview.md` §2/§3 (Wave 4) calls for growing it
to 6 checks and emitting one JSON line per post-merge run to `docs/harness-experimental/audit-log.jsonl`
so the number becomes a trend instead of a single sample — closing v0.3 success criterion #5
("harness-audit cho một con số + trend ≥3 tuần data JSONL", §4). Depends on Wave 1 (event-sourced
post-merge bookkeeping, merged PR #34/#36/#37) and Wave 3 (`harness-manifest.json` +
`check_manifest.py`, merged PR #35) — both already shipped.

## 2. Non-goals

- No blocking behavior change: `harness-audit.sh` stays advisory (exit 0) by default; `--strict`
  keeps exiting 1 on any finding, unchanged for the 3 existing checks.
- No weighted/cap-100 score — raw finding count + the existing 3-band summary (`healthy` /
  `minor drift` / `needs attention`) is the whole scoring model (§3 Wave 4 non-goal: "không
  blocking, không cap-100 màu mè").
- No new GitHub Actions workflow and no job that runs on every push — the only write-back-to-repo
  mechanism in this repo is the existing post-merge bookkeeping PR flow (Wave 1); reuse it instead
  of requesting new permissions.
- No actual Inactive/Degraded/Full ladder for the manifest (that was Wave 3 scope-on-paper that
  shipped as a binary consistent/drift checker) — "manifest Degraded" here means
  `check_manifest.py` exits non-zero, nothing fancier.

## 3. Success Criteria

1. `bash scripts/harness-audit.sh` reports 6 distinct check categories (not just 3); each new
   check has at least one fixture case that fires and one that doesn't, pinned in
   `tests/scripts/harness-audit.test.sh`.
2. `bash scripts/harness-audit.sh --json --root <dir>` prints exactly one line, parseable by
   `python3 -c 'import json,sys; json.loads(sys.stdin.read())'`, with a `checks` object carrying
   all 6 per-category counts.
3. No added line in `scripts/harness-audit.sh`, `scripts/bookkeeping.sh`, or
   `scripts/harness-status.sh` contains the literal substring `audit_log` (case-insensitive,
   underscore form) — confirmed by `grep -ri audit_log <files>` returning nothing. (The file on
   disk is named `audit-log.jsonl`, hyphenated; see `specs/entropy-trend/SUMMARY.md` Reason.)
4. `scripts/bookkeeping.sh` appends one well-formed JSONL line (with a `pr` field) to
   `docs/harness-experimental/audit-log.jsonl` per merged PR, and a second run for the same PR
   does not double-append (inherits the script's existing idempotency guard).
5. `.github/workflows/post-merge-maintenance.yml` actually commits the new file (the bookkeeping
   PR's `git add` list includes it — otherwise it stays untracked forever).
6. `scripts/harness-status.sh` prints the last 5 `audit-log.jsonl` rows as a compact trend line,
   and still exits 0 when the file does not exist yet (pre-first-merge state).
7. `bash scripts/run-tests.sh` stays green (auto-discovers the new `tests/scripts/harness-audit.test.sh`
   via its existing glob; no edit to `run-tests.sh` needed for that).

## 4. Tasks

### Task 1.1 — harness-audit.sh: 6 checks + `--root` + `--json`

```xml
<task id="1.1" wave="1">
  <files>scripts/harness-audit.sh, tests/scripts/harness-audit.test.sh</files>
  <action>
Add a `--root DIR` flag (default: current behavior — `cd "$(dirname "$0")/.."`), following the
same convention as `scripts/bookkeeping.sh`/`scripts/check_manifest.py`, so tests can point the
script at a throwaway fixture tree. Parse it alongside the existing `--strict` and new `--json`
flags (all three are independent booleans/values; `--json` suppresses the human-readable output
and the "=== Harness Audit ===" banner — prints nothing else to stdout).

Change `HARNESS_AUDIT_STALE_DAYS` default from `14` to `30` (env var override unchanged) — this
is check 2 (active PLAN gone stale), per the plan overview's "plan active >30d im lặng" wording.

Track a per-category counter alongside the existing shared `FINDINGS` counter (bump both at each
`note` call): `VERIFY_MISSING`, `PLAN_STALE`, `VERIFY_NEVER_RERUN`, `BACKLOG_STALE`,
`MANIFEST_DEGRADED` (0 or 1, not a count), `SOLUTIONS_STALE`.

Add 3 new checks after the existing 3 (renumber the file's inline comments 1-6):

- **Check 4 — verify-never-rerun.** For every `specs/*/SUMMARY.md` with a `### Verify` section,
  extract each data row's Command cell (3rd `|`-delimited field; strip backticks/whitespace).
  Skip placeholder cells (`<command>`, `-`, `—`, `–`, empty — same placeholder set as
  `scripts/verify_summary.py`'s `_PLACEHOLDER_COMMANDS`). For each real command, pull any
  whitespace-separated token containing a `/` (a path-looking fragment, e.g. `scripts/foo.sh` out
  of `bash scripts/foo.sh -x`). If none of a row's path-fragments appear as a substring anywhere
  in `scripts/run-tests.sh` or any `.github/workflows/*.yml`, flag once per offending SUMMARY file
  (not once per row): `note "verify command never re-run outside intake: $s -> <command>"`.
- **Check 5 — backlog-stale.** Parse `docs/harness-experimental/improvement-backlog.md`'s table
  (skip the header + separator rows). Its columns are
  `| Date | From failure (slug) | Proposed guardrail | Target path | Status |`. For each row whose
  last (`Status`) cell trims to exactly `open`, compute `days_since(Date)`; if it exceeds
  `HARNESS_AUDIT_BACKLOG_DAYS` (env var, default `14`), flag
  `note "backlog entry open ${age}d > ${BACKLOG_DAYS}d: <slug-cell> (opened $date)"`. Skip the
  whole check silently if the file doesn't exist.
- **Check 6 — manifest-degraded.** Only run when both `harness-manifest.json` and
  `scripts/check_manifest.py` exist under `$ROOT` (skip silently otherwise — keeps fixture repos
  that don't carry a manifest from false-flagging). Run
  `python3 scripts/check_manifest.py --root "$ROOT" >/dev/null 2>&1`; non-zero exit ->
  `MANIFEST_DEGRADED=1` and `note "harness-manifest.json degraded (check_manifest.py reported drift)"`.
  Skip silently if `python3` is unavailable (mirrors `run-tests.sh`'s own skip pattern).

`--json` output: build via `python3 -c` (stdlib `json.dumps`, fed the counts as argv — do not
hand-roll JSON string concatenation in bash, to guarantee correct escaping), one line, shape:
`{"date":"YYYY-MM-DD","findings":N,"band":"healthy|minor drift|needs attention","checks":{"verify_missing":n,"plan_stale":n,"verify_never_rerun":n,"backlog_stale":n,"manifest_degraded":0|1,"solutions_stale":n}}`.
`date` is `$(date +%F)` computed in bash and passed in as an argv string (this script may run
under `Date.now()`-restricted contexts elsewhere in the repo's tooling, but this is a plain shell
script executed directly — no such restriction applies here). The existing human-readable path
and `--strict` exit-1-on-any-finding behavior are unchanged for the 3 pre-existing checks; the 3
new checks also count toward `--strict`'s pass/fail.

Do not introduce the literal substring `audit_log` (case-insensitive) anywhere in the script —
this script never needs to name the JSONL file itself (that happens in `scripts/bookkeeping.sh`,
Task 2.1), so this constraint should be trivially satisfiable here.

Test file (new): follow `tests/scripts/bookkeeping.test.sh`'s shape — `source
"$(dirname "$0")/../lib.sh"`, build fixture trees with `mktemp -d` + `_CLEANUP_DIRS`, use
`t`/`pass`/`fail`/`finish`. Cases:
  1. Empty fixture (no specs/, no backlog, no manifest) -> `--json` reports `findings: 0`,
     `band: "healthy"`.
  2. `specs/x/SUMMARY.md` with no `### Verify` heading -> `verify_missing` >= 1.
  3. `specs/x/PLAN.md` with `status: active` and a date >30 days old -> `plan_stale` >= 1; a date
     10 days old -> `plan_stale` == 0.
  4. `specs/x/SUMMARY.md` with a `### Verify` row whose command references a path not present in
     a fixture `scripts/run-tests.sh`/`.github/workflows/*.yml` -> `verify_never_rerun` >= 1; a
     row whose path IS present in the fixture `run-tests.sh` -> 0.
  5. `docs/harness-experimental/improvement-backlog.md` with an `open` row dated >14 days ago ->
     `backlog_stale` >= 1; a `done` row or a recent `open` row -> 0.
  6. Fixture with `harness-manifest.json` + a stub `scripts/check_manifest.py` that `exit 1`s ->
     `manifest_degraded == 1`; a stub that `exit 0`s -> `manifest_degraded == 0`; fixture with
     neither file -> `manifest_degraded == 0` (check skipped, not flagged).
  7. `--json` output is exactly one line and round-trips through
     `python3 -c 'import json,sys; json.loads(sys.stdin.read())'`.
  8. `--strict` still exits 1 when any finding is present, 0 when none (regression guard for the
     pre-existing behavior).
  </action>
  <verify>bash tests/scripts/harness-audit.test.sh && bash -n scripts/harness-audit.sh && ! grep -riq audit_log scripts/harness-audit.sh</verify>
  <done>All 8 test cases pass; script has zero literal `audit_log` occurrences; `--strict` regression case passes.</done>
</task>
```

### Task 2.1 — bookkeeping.sh: emit one JSONL line per merged PR

```xml
<task id="2.1" wave="2">
  <files>scripts/bookkeeping.sh, tests/scripts/bookkeeping.test.sh</files>
  <action>
After the existing step 5 (ledger row append), add a step 6: run
`bash scripts/harness-audit.sh --root "$ROOT" --json` (relative `scripts/harness-audit.sh` works
because the script already `cd`s into `$ROOT` near the top), capture its single-line stdout, pipe
it through `python3 -c` to inject a `"pr"` field (`int($PR)`) and re-serialize with `json.dumps`,
then append the resulting line to `docs/harness-experimental/audit-log.jsonl` (create the file if
missing; `docs/harness-experimental/` already exists in every fixture that has a ledger).

Name the path variable something that does NOT contain the literal substring `audit_log` — e.g.
`TREND_LOG="docs/harness-experimental/audit-log.jsonl"` (hyphenated path value, non-colliding
variable name; see `specs/entropy-trend/SUMMARY.md` Reason for why this matters mechanically).

This step runs after the script's existing idempotency guard (the `grep -qF "shipped (PR #${PR}, "`
early-exit at the top of the file) — no additional idempotency logic is needed; a re-run for an
already-recorded PR exits before reaching step 6 at all. Verify this holds with a test.

Update the final `echo "bookkeeping: recorded PR #${PR} ..."` message to also mention the trend
line was appended (cosmetic, one clause — do not restructure the message).

Test additions to `tests/scripts/bookkeeping.test.sh` (same `make_fixture` helper, same
`--root "$d"` pattern as every existing case in the file):
  - New case: after a normal `bash "$SCRIPT" --pr 42 ...` run, `tail -1
    "$d/docs/harness-experimental/audit-log.jsonl"` is valid JSON (round-trips through
    `python3 -c 'import json,sys; json.loads(sys.stdin.read())'`) and its `pr` field equals `42`.
  - Extend the existing idempotency case ("second run for the same PR does not double-append or
    double-bump"): also assert `wc -l < audit-log.jsonl` is `1` after both runs, not `2`.
  </action>
  <verify>bash tests/scripts/bookkeeping.test.sh && bash -n scripts/bookkeeping.sh && ! grep -riq audit_log scripts/bookkeeping.sh</verify>
  <done>New + extended test cases pass; no literal `audit_log` substring in the script.</done>
</task>
```

### Task 2.2 — post-merge-maintenance.yml: commit the new file

```xml
<task id="2.2" wave="2">
  <files>.github/workflows/post-merge-maintenance.yml</files>
  <action>
In the "Open the bookkeeping PR" step, extend the existing
`git add VERSION CHANGELOG.md docs/harness-experimental/trust-metrics.md` line to also list
`docs/harness-experimental/audit-log.jsonl` — otherwise `bookkeeping.sh`'s new file (Task 2.1)
stays untracked forever and success criterion 5 is not met. No other change to this workflow file.
  </action>
  <verify>grep -qF 'git add VERSION CHANGELOG.md docs/harness-experimental/trust-metrics.md docs/harness-experimental/audit-log.jsonl' .github/workflows/post-merge-maintenance.yml</verify>
  <done>The git add line in the workflow includes the new JSONL path.</done>
</task>
```

### Task 2.3 — harness-status.sh: surface the trend

```xml
<task id="2.3" wave="2">
  <files>scripts/harness-status.sh</files>
  <action>
Add a new `=== Audit Trend (last 5 runs) ===` section after the existing "Last 5 Trust-Metrics
Rows" section and before the "Drift Audit (advisory)" section, mirroring the existing sections'
style (plain bash + a small `python3 -` heredoc for JSON parsing, same as the "Wired Hooks"
section above it). Define a path variable for the log (again, avoid the literal `audit_log`
substring — e.g. `AUDIT_TREND_LOG="$REPO_ROOT/docs/harness-experimental/audit-log.jsonl"` is fine,
it doesn't contain `audit_log` as a contiguous substring). If the file doesn't exist, print
`  [not found: $AUDIT_TREND_LOG]` (same pattern as the existing `TRUST_METRICS` not-found case).
Otherwise `tail -5` the file and, per line, parse with `python3 -c` and print
`date  findings=N  band=<band>` (one line per row, same terse style as the trust-metrics rows).
The script must still exit 0 when the file is absent (pre-first-merge repo state) — this already
falls out of following the existing `TRUST_METRICS` if/else pattern exactly.
  </action>
  <verify>bash scripts/harness-status.sh >/dev/null && bash -n scripts/harness-status.sh && ! grep -riq audit_log scripts/harness-status.sh</verify>
  <done>Script runs clean end-to-end against the real repo (no audit-log.jsonl yet) and exits 0; no literal `audit_log` substring.</done>
</task>
```

## 5. Risks

- **`verify-never-rerun` false positives on legitimate one-off commands** (e.g. a manual
  `curl`/browser-check row that was never meant to be wired into CI). Accepted: this check is
  advisory-only (exit 0 by default), and the finding text names the exact SUMMARY + command so a
  human can judge it in seconds; it is not meant to force every Verify row into `run-tests.sh`.
- **`manifest-degraded` skip-if-absent could mask real drift in a repo that deletes its manifest
  outright.** Accepted for this repo: `harness-manifest.json` is itself checked by
  `scripts/check_manifest.py` in CI (`scripts/run-tests.sh`), so an outright-deleted manifest
  already fails the suite through a different, more direct path.
- **Bash table-parsing for `improvement-backlog.md` and `### Verify` cells is inherently brittle**
  (pipe-delimited markdown, not a real parser). Accepted: mirrors the existing 3 checks' approach
  (`grep`/`awk` over specs' Markdown) rather than introducing a new parsing dependency — consistent
  with the file's own stated philosophy ("advisory drift detector", not a strict format validator).
- **`audit_log` naming avoidance is a manual/reviewed convention, not machine-enforced** beyond the
  `<verify>` grep in each task. If a future edit reintroduces the substring, `risk-corroboration.sh`
  will mechanically block that commit at `normal` lane — an acceptable backstop even though it's
  reactive rather than preventive.

## 6. Status Log

- 2026-07-04 — plan drafted (Wave 4 of v0.3, `docs/harness-v03-plan-overview.md`); pending worktree.
- 2026-07-04 — worktree `.worktrees/feat/entropy-trend` created off `v2`; baseline green (147 tests, 1 skipped).
- 2026-07-04 — Wave 1 / Task 1.1 done. Commits `d4c03d7` (implementation) + `1eddcbd` (review fix:
  `set -u` unbound-array crash in check 4 when no `run-tests.sh`/workflows exist in root, found by
  code-quality review, fixed + regression-tested). Spec review ✅, code-quality review ✅ after fix.
- 2026-07-04 — Wave 2 / Tasks 2.1, 2.2, 2.3 done (dispatched in parallel, zero file overlap
  confirmed). Commits `842bc4d` (2.2), `abbf25f` (2.3), `e3d2146` (2.1), `5b506ec` (review fix:
  2.3's Audit Trend section crashed the whole script under `set -e` on a malformed JSONL line —
  `harness-status.sh` is meant to degrade gracefully; fixed with a `try/except` skip). Spec review
  ✅ (all 3), code-quality review ✅ after the 2.3 fix. Full suite green (147 passed, 1 skipped)
  after every commit.
- 2026-07-04 — Final adversarial correctness review (whole diff, opus model, 2 rounds). Round 1
  found 2 candidates: a `KeyError` gap in `harness-status.sh`'s trend guard (scored 100, fixed in
  `5590288`) and a `dirname "$0"`/`--root` edge case in `bookkeeping.sh` (scored 50, below the
  80 threshold, recorded as advisory in SUMMARY.md, not fixed). Round 2 (post-fix) found nothing
  new — ✅ clean. Residual work gate satisfied.
- 2026-07-04 — Final intent review (blind to PLAN.md, oracle = SUMMARY ### Intent + source
  `docs/harness-v03-plan-overview.md`). Found 1 drift (JSONL emission cadence: "every CI run"
  shipped as "every merge") — confirmed correct by the user directly; documented in
  SUMMARY.md ### Intent Findings. `/compound` ran: 2 new `docs/solutions/scripts/` entries +
  critical-patterns promotion + INDEX rebuild (7 entries). Full suite green (147 passed, 1
  skipped, incl. new 16-case harness-audit.test.sh). Shipped via `feat/entropy-trend` (PR #42).
