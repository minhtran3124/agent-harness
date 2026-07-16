---
problem_type: failure
module: hooks/risk-corroboration
tags: hooks, risk-corroboration, false-positive, hard-gate, commit-hook, tests-dir, hook-friction
severity: standard
applicable_when: Watch for this when a commit is blocked by an auth/authorization hard gate but the change has nothing to do with auth — check whether an ordinary English word in a comment under `tests/` matched the scanner.
affects:
  - hooks/risk-corroboration.sh
  - tests/scripts/resync-conflict.test.sh
supersedes: null
confidence: high
confirmed_at: 2026-07-10
---
## Applicable When

A repo ships a keyword-scanning commit hook, and you are writing shell tests whose comments use ordinary English.

## Symptom

`hooks/risk-corroboration.sh` blocked a commit on the words **"session"** and **"permission"** appearing in prose comments of a shell test file. The change touched no auth code whatsoever.

## Wrong Approach

`hooks/risk-corroboration.sh:71` builds the set of added code lines with:

```bash
CODE_ADDED=$(git diff --cached -U0 -- . ':!*.md' ':!docs/' ':!specs/' ':!skills/' ':!hooks/' ':!.claude/' ...)
```

The exclusion pathspec covers prose (`*.md`, `docs/`, `specs/`) and the scanners themselves (`hooks/`) — but **not `tests/`**. Lines 86–87 then grep the result:

```bash
echo "$CODE_ADDED" | grep -qiE '(login|logout|\bsession\b|jwt|password|…)' && add_cat "auth"
echo "$CODE_ADDED" | grep -qiE '(\brole\b|permission|is_admin|…)'          && add_cat "authorization"
```

Every added line under `tests/` is treated as code, and natural-language words are treated as auth signals.

## Why It Failed

A shell test file is mostly prose comments. The scanner has no notion of comments, so `# restore the session's controlling terminal` and `# check the file's permission bits` read as auth surface. The hook then requires a `high-risk` lane declaration that the change does not warrant, and blocks the commit (exit 2).

The workaround actually applied was to **reword the comments** ("session's ctty" → "controlling terminal", "permission bits" → "file mode bits") — commit `0048a16`. That is a behavior change to satisfy a scanner, which is the wrong direction: the scanner should not be reading prose.

## Correct Approach

Do not reword prose to appease a keyword scanner. Fix the scanner's input set:

- Add `':!tests/'` to the `git diff --cached` pathspecs at `hooks/risk-corroboration.sh:71` and `:74`, **or**
- Strip comment lines (`^\s*#`) from `CODE_ADDED` before scanning, which is the more precise fix — it keeps real auth code under `tests/` visible to the gate.

Prefer the comment-stripping variant: excluding `tests/` wholesale would blind the gate to a test that genuinely adds auth surface.

This was **not fixed in-session**: `hooks/*` is a high-blast path, so touching it is a Rule-4 action under `rules/auto-correct-scope.md` requiring human judgment. It was recorded as `Harness-Delta: backlog` in `specs/resync-protected-files/SUMMARY.md`.

## Guardrail

`applied (2026-07-16):` the preferred comment-stripping variant landed — `^\+\s*#` / `^-\s*#` lines are filtered from `CODE_ADDED`/`CODE_REMOVED` before the category greps (`hooks/risk-corroboration.sh`), keeping real auth code under `tests/` visible to the gate. Landed with the required `tests/hooks/risk-corroboration.test.sh` cases: auth word in a shell comment does not trip; the same word in a live code line still does; a removed comment does not trip weakening-validation. (Review 2026-07-16 finding C4.)

## Related

- `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md` — why any `hooks/` edit, including this fix, is high-blast regardless of wiring.
- `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md` — the other recorded instance of a hook's string-scanning being coarser than the developer expects.
