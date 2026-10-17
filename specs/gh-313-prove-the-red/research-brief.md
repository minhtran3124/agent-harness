# gh-313-prove-the-red — Research Brief

Written 2026-10-17. Pins: repo e0836a9; git 2.43.0; mattpocock/skills f3fc563

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Reuse existing: build on `_red_green_issue`'s row parse, the `_git` helper, and `run_at_commit.py`'s commit-resolution pattern |
| **Why this is the lightest credible path** | Every input already exists in `verify_summary.py`; the change adds one git call per matched red/green pair. |
| **Confidence** | 85% |
| **Next step** | `writing-plans`: one code task (`verify_summary.py` + tests), one prose task (rule + implementer prompt). |

Depth: **Deep** (intake lane `high-risk`). No upgrade or downgrade from evidence.

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Prompt and workflow harness (skills, rules, hooks, scripts) |
| Primary language + runtime | Python 3 (scripts), Bash (hooks) |
| Frameworks / platforms | pytest (via `/tmp/harness-tests-venv` locally); GitHub Actions `harness-ci` on ubuntu + macos |
| Relevant packages | stdlib only (`subprocess`, `re`, `pathlib`) |
| Detectable versions | git 2.43.0 (local, measured 2026-10-17 `git --version`) |
| Important constraints | Gates read the index, not the worktree (`gate-config-must-read-index`); `REQUIRE_RED_TEST` is the only switch; `hooks/` is high-blast and stays unchanged |

---

## Feature Understanding and Assumptions

- **Requested feature:** In `verify_summary.py --lane`, a bug-fix SUMMARY's red/green pair must show a non-empty diff between the red commit and the index, outside `specs/` and the red test files.
- **What success appears to mean:** A no-op "fix" exits 1 under `REQUIRE_RED_TEST=1` and prints an advisory without it; a real fix exits 0.
- **Assumptions from the request:** design D1–D9 (approved at e0836a9).
- **Assumptions still needing confirmation:** none that would change the recommendation. The `git commit -- <paths>` limit below is a risk shared with every existing index-reading gate check.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `git diff --cached --name-only <red>` in a temp repo: empty after a no-op, lists `scripts/x.py` after a staged-only edit (A2 confirmed, truth tier, 2026-10-17). |
| `Local` | Default output C-quotes non-ASCII paths (`"scripts/\303\251.py"`); `-z` prints raw paths. Parse with `-z`. |
| `Local` | Rename detection is on by default: renaming `scripts/test_x.py` to `test_y.py` lists only `scripts/test_y.py`, which is not a token, so it counts as a fix. |
| `Local` | `git diff --cached deadbee` exits 128 with "ambiguous argument"; `git rev-parse --verify --quiet deadbee^{commit}` exits 1 with no output. Resolve first, then diff with a `--` separator. |
| `Local` | Outside a repo, `git rev-parse --show-toplevel` exits 128. |
| `Local` | `scripts/run_at_commit.py:68-70` resolves the repo with `git rev-parse --show-toplevel` from the cwd and the commit with `rev-parse --verify --quiet <rev>^{commit}`. The red row runs in the cwd's repo, so D6 matches how the red row itself runs. |
| `Local` | `scripts/verify_summary.py:793` `_git(root, *args)` uses `check_output(..., stderr=DEVNULL)`: it raises `CalledProcessError` on a git error and `FileNotFoundError` when git is absent. Both must map to the cannot-check message. |
| `Local` | `_parse_verify_rows` strips surrounding backticks from the command cell (`verify_summary.py:231`), so the red regex and the token split see the bare command. |
| `Local` | `hooks/commit-gate.sh:149-157` `cd`s to `CLAUDE_PROJECT_DIR` or the git toplevel before any check, and `check_lane_evidence` runs `--lane` on a `mktemp` copy (A1 premise). |
| `Local` | `specs/gh-302-red-green-input-type/SUMMARY.md:123` is the only committed red row; `ee6da93` resolves, and its filtered diff to the index is non-empty. |
| `Upstream` | Pocock `skills/engineering/diagnosing-bugs/SKILL.md` Phase 5 step 2 (f3fc563): "If you forced the red by mutating code or a fixture, `diff` against a pristine copy to prove the mutation landed before you trust it." Changeset `diagnosing-bugs-prove-mutation.md` (#955): "an edit that silently changed nothing can't pass as a failing test". |
| `Inference` | The upstream check is an instruction to the agent; this design mechanizes the same "something changed" property in the lane gate, at provenance tier. |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** `scripts/verify_summary.py` (`_red_green_issue` ~405, `check_lane_warnings` ~468, `check_lane_evidence` ~552, `_git` 793); `scripts/test_verify_summary.py` `TestRedGreen` (~1001, fake sha `abc1234`); `scripts/run_at_commit.py`; `hooks/commit-gate.sh` `check_lane_evidence`; `rules/auto-correct-scope.md:44`; `skills/subagent-driven-development/implementer-prompt.md:63`.
- **Existing abstractions or extension points:** the `(issue, env var)` warning tuple in `check_lane_warnings`; the `_red_test_is_blocking()` split; `_RED_COMMAND_RE` with its `test` group.
- **Conventions worth preserving:** each check documents `Verifies:` / `Does not verify:` in its docstring (CLAUDE.md "Gate verifiability"); advisory lines start with `!`; error lines with `-`.
- **What can likely be reused:** the red-row loop in `_red_green_issue` (extract into `_red_pairs`); `_git`; the commit-resolution sequence from `run_at_commit.py`.
- **What appears missing locally:** a temp-git-repo fixture in `test_verify_summary.py`. `scripts/test_run_at_commit.py` builds temp repos and is the pattern to copy.

---

## Upstream Findings

- **Repositories inspected:** github.com/mattpocock/skills at f3fc563 (`.changeset/diagnosing-bugs-prove-mutation.md`, `skills/engineering/diagnosing-bugs/SKILL.md`).
- **Pattern or capability already present upstream:** "diff against a pristine copy" before trusting a red.
- **Files, modules, or areas worth modeling:** only the property; upstream has no code for it.
- **How closely the upstream pattern matches this repo:** same property, different enforcement point: upstream is prose, here it is a lane-gate check.
- **Any upstream gaps or uncertainties:** upstream checks the red side (the mutation landed); this design checks the fix side (code changed after red). Both target "an edit that changed nothing".

---

## Docs Findings

- **Official sources checked:** none beyond local behavior; the git calls were re-run on git 2.43.0 instead of read from docs.
- **Version-matched vs latest-stable status:** `--cached`, `--name-only`, `-z`, `--no-renames` and `rev-parse --verify --quiet <rev>^{commit}` are long-standing git options. macOS CI ships a different git version (not measured).
- **Built-in capabilities that already support the feature:** `git diff --cached --name-only -z <commit> --`.
- **Current recommended APIs or workflows:** resolve with `rev-parse --verify --quiet`, then diff.
- **Important caveats, deprecations, or migration notes:** path quoting (`core.quotePath`) and rename detection (`diff.renames`) change the output; `-z` and `--no-renames` make it stable across user config.

---

## Recommendation

- **Primary recommendation:** reuse existing. Extract `_red_pairs` from `_red_green_issue`; add `_red_fix_diff_issue` that runs `git rev-parse --show-toplevel`, then per pair `git rev-parse --verify --quiet <sha>^{commit}` and `git diff --cached --name-only -z --no-renames <commit> --`; drop `specs/` paths and exact test-token paths (after `::` and `./` stripping); catch `CalledProcessError` and `OSError` as cannot-check.
- **Why this is the lightest credible path:** one file, stdlib only, the same resolution sequence the red row's own helper uses.
- **Why the next-best alternative lost:** a hook-side check (design approach C) edits a high-blast file and misses manual `--lane` runs.
- **What would change this recommendation:** evidence that the gate's cwd is not the committed repo (A1 false) would force a `--repo-root` flag passed by the hook.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - `git commit -- <paths>` commits the worktree copies of the named paths, not the index. The check sees the index, so a pathspec commit can differ from what was checked. Every existing index-reading check in `commit-gate.sh` shares this limit; it is not new here.
  - With `--no-renames`, a renamed test file lists both the old and new path; only the token path is dropped, so a test rename still counts as a fix. Record in "What we do not claim" (already covered by the token-only row).
  - Existing `TestRedGreen` tests run with the cwd in this repo and the fake sha `abc1234`; without a temp repo they get the cannot-check advisory.
- **Evidence gaps:** git behavior on the macOS CI runner was not measured; the options used are long-standing.
- **Version uncertainties:** none load-bearing.
- **Follow-up questions for the user:** none.

---

## Source Pack

- **Local files read:** `scripts/verify_summary.py`, `scripts/run_at_commit.py`, `scripts/test_verify_summary.py` (red/green section), `hooks/commit-gate.sh` (lines 149–157, 238–300), `specs/gh-302-red-green-input-type/SUMMARY.md`, `docs/solutions/harness/wave-boundary-verify-evidence.md`, `docs/solutions/harness/gate-config-must-read-index.md`, `rules/auto-correct-scope.md`
- **Upstream repositories or pages checked:** https://github.com/mattpocock/skills/blob/f3fc563/.changeset/diagnosing-bugs-prove-mutation.md, https://github.com/mattpocock/skills/blob/f3fc563/skills/engineering/diagnosing-bugs/SKILL.md
- **Official docs domains or pages checked:** - none found (git behavior re-run locally on 2.43.0 instead)

---

## Evidence Boundary

> Confirmed from artifacts: git `--cached` index comparison, `-z` quoting, rename output, unknown-sha and no-repo exit codes (temp repo, git 2.43.0); hook cwd handling; gh-302 sha resolution; upstream wording at f3fc563.
> Inferred from patterns: that macOS CI git behaves the same for these options.
> Not checked: git versions other than 2.43.0; consumer repos with a `GIT_INDEX_FILE` override.
