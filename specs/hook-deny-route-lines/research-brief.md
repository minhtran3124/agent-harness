# hook-deny-route-lines — Research Brief

Written 2026-10-14. Pins: repo 94682f9; Claude Code hooks docs (code.claude.com, read 2026-10-14); Codex hooks docs (learn.chatgpt.com, read 2026-10-14)

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing — inline route lines in the existing echo/jq blocks, asserted with the existing `tests/lib.sh` helpers |
| **Why this is the lightest credible path** | Every gap already has a message block and (except G5) a test that asserts its reason; the change is one line per block plus one assertion per test |
| **Confidence** | 85% |
| **Next step** | `writing-plans` (Q1 answered yes 2026-10-14 → design DC1) |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Harness meta-repo (skills, rules, hooks, scripts) |
| Primary language + runtime | Bash (hooks; bash 3.2 compatible per `commit-gate.sh` header), Python 3 (normalizer, scripts) |
| Frameworks / platforms | Claude Code PreToolUse hooks; Codex advisory alpha (0.147.0) |
| Relevant packages | `jq` (deny JSON), `python3` (normalizer) |
| Detectable versions | no manifest pins for bash/jq; Codex CLI 0.147.0 per CLAUDE.md |
| Important constraints | high-blast `hooks/*` (manifest); `scripts/ci-strict-gate.sh` blocks a `hooks/` diff without a high-risk SUMMARY whose Verify rows re-run clean; run `bash scripts/run-tests.sh` before pushing (memory: Actions billing limit) |

---

## Feature Understanding and Assumptions

- **Requested feature:** every blocking hook path prints reason + route (E2, play 10); approved
  design `specs/hook-deny-route-lines/design.md` (approach A, 11 gaps, 21 tested paths).
- **What success appears to mean:** each of the 21 blocking paths has a test asserting its route
  text; `bash scripts/run-tests.sh` green; no exit code / decision change.
- **Assumptions from the request:** message text only; no new override variable.
- **Assumptions still needing confirmation:** Q1 below — whether a "complete" message whose route
  is known to mislead counts as complete.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | 21 blocking paths (measured 2026-10-14 `grep -n -E "exit 2\|permissionDecision\|deny" hooks/*.sh hooks/lib/*`): 18 `exit 2` in `commit-gate.sh` + 3 JSON denies; `hooks/lib/` has none (only a comment at `lane.sh:42`) |
| `Local` | Existing reason assertions: G1 `commit-gate.test.sh:80`; G2 `:109,:115`; G3 `:121`; G4 `:350` **and** `commit-gate-risk.test.sh:478`; G6 `:59,:183,:216,:222`; G7 `:189`; G8 `:241`; G9 `:320` (inside an `ensure_pyenv` guard); G10 `:406–411`; G11 `branch-isolation-guard.test.sh:92,99,104,109,242,247,252,257` |
| `Local` | Test helpers: `tests/lib.sh` — `new_repo`, `stage`, `run_hook` (sets `OUT` = stdout+stderr, `RC`), `run_hook_args`, `assert_rc_contains`, `skip`; no existing `chmod 000` use in `tests/hooks/` |
| `Local` | `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md`: the untracked-`.py` deny scans the whole command string, so following its route "Run: git add <files>" as `git add x.py && git commit` in **one** Bash call is denied again; CLAUDE.md Gotchas documents the two-call workaround, the deny message does not |
| `Local` | `scripts/install-harness.sh` "resolve source": without `--source` it clones `$BRANCH` (default `main`) from `REPO_URL` (default `…/harness-skills`); README.md:84 one-liner uses `…/agent-harness` |
| `Docs` | Claude Code hooks (code.claude.com/docs/en/hooks, 2026-10-14): "The message that comes with the block is your hook's stderr. If your hook also printed JSON that makes a blocking decision, Claude Code uses that decision's reason instead." Claude receives it as the tool error, prefixed `PreToolUse:Bash hook error: [<cmd>]:`. A JSON deny: "Claude Code reads the JSON decision, blocks the tool call, and shows Claude the reason." No length cap stated for the deny reason |
| `Docs` | Codex hooks (learn.chatgpt.com/docs/hooks, 2026-10-14): exit 2 with "the blocking reason" on stderr and a JSON `permissionDecisionReason` are documented, but the page does not state that the model receives either for PreToolUse; no version given ("release behavior reference") |
| `Upstream` | Playbook play 10 (via `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §1.4 item 4): "A block states the reason *and the route to approval*" |
| `Inference` | Multi-line stderr reaches Claude whole on exit 2 (the docs' first-line truncation applies to non-blocking exits); the 10 complete messages already rely on this |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** `hooks/commit-gate.sh`, `hooks/branch-isolation-guard.sh`; `tests/hooks/commit-gate.test.sh`, `commit-gate-evidence.test.sh`, `commit-gate-risk.test.sh`, `branch-isolation-guard.test.sh`, `repo-root-resolution.test.sh`; `tests/lib.sh`; `scripts/run-tests.sh`.
- **Existing abstractions or extension points:** none needed — each block is `echo … >&2; exit 2` or a `jq -cn` deny object; a route is one more `echo` / one more string segment.
- **Conventions worth preserving:** `[COMMIT GATE] <check>... FAILED` then two-space-indented `BLOCKED:` / follow-up lines; JSON reasons use `\n` between lines (`branch-isolation-guard.sh:176`).
- **What can likely be reused:** every existing reason test — add an `assert_rc_contains` for the route on the same `OUT` (no new fixture except G5).
- **What appears missing locally:** a G5 test (no message today); route assertions on all 21 paths; the untracked-`.py` route does not warn about the combined-call trap (see Q1).

---

## Upstream Findings

- **Repositories inspected:** the Claude Code hooks reference example (`no-rm.sh`, reason only: "Blocked: rm commands are not allowed").
- **Pattern or capability already present upstream:** "reason + route" exists as a principle (playbook play 10), not as a reusable library or message format.
- **Files, modules, or areas worth modeling:** none beyond our own `branch-isolation-guard.sh:176` (already the most complete reason + Fix + Override shape in the repo).
- **How closely the upstream pattern matches this repo:** principle only; the format is ours to choose (design D2: no uniform marker on existing messages).
- **Any upstream gaps or uncertainties:** Codex model-visibility of PreToolUse block text is undocumented.

---

## Docs Findings

- **Official sources checked:** code.claude.com/docs/en/hooks (first 100k chars of 270k; PreToolUse decision-control section beyond that not read); learn.chatgpt.com/docs/hooks.
- **Version-matched vs latest-stable status:** both are current-release pages read 2026-10-14; neither is pinned to Codex 0.147.0 or a Claude Code version.
- **Built-in capabilities that already support the feature:** exit-2 stderr and JSON `permissionDecisionReason` are the documented block-message channels on both runtimes — exactly the channels the hooks already use.
- **Current recommended APIs or workflows:** no change needed to channel or exit code.
- **Important caveats, deprecations, or migration notes:** when a hook prints both a JSON decision and stderr, Claude uses the JSON reason — not relevant here (no path does both).

---

## Recommendation

- **Primary recommendation:** reuse existing — design approach A as approved; add the G5 message and test; add route assertions next to existing reason assertions; G4's route assertion goes in `commit-gate.test.sh:350` (one is enough; `commit-gate-risk.test.sh:478` asserts the same block).
- **Why this is the lightest credible path:** one echo + one assertion per path, zero new helpers, matches existing style.
- **Why the next-best alternative lost:** a shared `hook_deny` helper (approach B) cannot serve G2/G3 (they fire when a lib is missing) and would rewrite the 10 complete messages.
- **What would change this recommendation:** if Codex is shown not to surface stderr to the model, routes would still help humans, but the Codex-agent benefit would be nil — the text change stays the same, so the recommendation would not flip.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - G5 test uses `chmod 000`; macOS and ubuntu CI runners are non-root, but the test must `skip` as root and restore permissions before cleanup (design A4).
  - G9's assertion only runs where `ensure_pyenv` succeeds; elsewhere it is a `skip`, so its route coverage is environment-dependent (design notes it).
  - Changing message text can break assertions elsewhere that match the old text exactly — mitigated: the change appends lines, it does not edit existing ones (except G5, which has none).
  - `ci-strict-gate.sh` will require this slug's SUMMARY to be high-risk with Verify rows that re-run clean.
- **Evidence gaps:** Codex PreToolUse model-visibility (Docs silent); Claude docs PreToolUse section past 100k chars not read.
- **Version uncertainties:** neither docs page is version-pinned.
- **Follow-up questions for the user:**
  - **Q1.** The untracked-`.py` deny (one of the 10 "complete" messages) says "Run: git add <files>", but doing that in the same Bash call as `git commit` is denied again (`pretooluse-hook-denies-combined-git-add-commit.md`). Should its route gain "in a separate Bash call, then commit"? That edits a message the design (D2) and intent say stay as they are, so a yes is a design change (DC1) and widens the intent's "messages that already have both stay" by one message.

---

## Source Pack

- **Local files read:** `hooks/commit-gate.sh`, `hooks/branch-isolation-guard.sh`, `hooks/lib/*` (grep), `tests/lib.sh`, `tests/hooks/*.test.sh` (grep), `scripts/install-harness.sh`, `README.md:84`, `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md`, `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md`, `specs/codex-support-phase-1/SUMMARY.md`, `specs/codex-support-phase-4/SUMMARY.md` (grep), `specs/hook-deny-route-lines/{intent,design}.md`
- **Upstream repositories or pages checked:** Claude Code hooks reference example (`no-rm.sh`) on code.claude.com; playbook play 10 via the local research note
- **Official docs domains or pages checked:** https://code.claude.com/docs/en/hooks; https://learn.chatgpt.com/docs/hooks (redirected from developers.openai.com/codex/hooks)

---

## Evidence Boundary

> Confirmed from artifacts: the 21-path inventory and 10/11 split; every existing reason assertion location; the installer's `--source` behaviour; the combined `git add && git commit` trap; Claude Code delivers exit-2 stderr and JSON deny reasons to Claude.
> Inferred from patterns: multi-line exit-2 stderr reaches Claude untruncated; `chmod 000` blocks `cd` for non-root CI runners.
> Not checked: whether Codex 0.147.0 shows PreToolUse block text to the model; the remainder of the Claude hooks page past 100k chars; behaviour in a real Codex session.
