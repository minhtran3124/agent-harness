---
problem_type: bug
module: hooks/repo-root-resolution
tags: hook-root-resolution, plugin-install-safety, silent-wrong-repo, claude-project-dir, fail-closed-posture, deployment-topology-assumption
severity: critical
applicable_when: Writing or reviewing any hook or script that needs "the project root" and could ever run from a location decoupled from the target repo — plugin/marketplace packaging, a vendored install, a global `~/.claude/` copy, or any distribution path other than an in-tree copy.
affects:
  - hooks/blast-radius-check.sh
  - hooks/branch-guard.sh
  - hooks/commit-quality-gate.sh
  - hooks/render-plan-on-write.sh
  - hooks/risk-corroboration.sh
  - hooks/ruff-on-edit.sh
  - hooks/scope-gate.sh
  - hooks/session-knowledge.sh
supersedes: null
confidence: high
confirmed_at: 2026-09-09
---
## Problem

Eight of twelve hook scripts derived the project's repository root from the hook's **own file
location**:

```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
```

(`blast-radius-check`, `branch-guard`, `commit-quality-gate`, `render-plan-on-write`,
`risk-corroboration`, `ruff-on-edit`, `scope-gate`; plus `session-knowledge`, which spells the
identical thing as `git -C "$HOOK_DIR"`.)

A spike on 2026-09-09 — a throwaway one-hook plugin, installed, driven by a headless session against
a test repo whose index and worktree deliberately disagreed — measured two failure modes when the
hook lives outside the project:

| Hook's own directory | Result | Exit | Consequence |
|---|---|---|---|
| Inside the project (the deployed layout) | project root | 0 | correct |
| Outside any git repo | *(empty)* | 128 | fails **loudly** |
| Inside **another** git repo | **that other repo** | **0** | gate audits the wrong repository and **reports success** |

The third row is the dangerous one, and it is the *ordinary* path: `claude plugin marketplace add`
**clones**, so a marketplace-installed plugin always sits inside a git repo. The regression test
captures what that looks like — against the pre-fix hooks, `commit-quality-gate` prints

```
[COMMIT GATE] Secrets scan... PASSED   [COMMIT GATE] Escalations... PASSED
```

while resolved to a foreign repo. Every check ran; none of them looked at the project.

## Root Cause

The logic encoded a *deployment topology* as an *identity*. `deploy-harness.sh` copies hooks into
the target project, so "the repo containing me" and "the repo I am auditing" were the same tree —
and the code asked the first question while meaning the second. The assumption stayed invisible for
the life of the repo precisely because the layout made the wrong inference return the right answer.
It only diverges once a hook's file location and the active project diverge.

Note the failure is *not* that the command errors. It succeeds, with a plausible answer, about the
wrong subject.

## Fix

```bash
REPO_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
```

The order is load-bearing, and each step earns its place:

1. **`CLAUDE_PROJECT_DIR` first** — the runtime's own answer to "which project am I running for",
   and it stays correct even when a compound shell command has changed CWD.
2. **git-from-CWD second** — must be kept, not dropped and not replaced by a bare `$PWD`:
   `tests/lib.sh` runs each hook with `cd "$repo"` and sets no `CLAUDE_PROJECT_DIR`, so removing
   this step resolves nothing under the 200+ existing contract tests.
3. **No `SCRIPT_DIR` fallback at any position.** Keeping it reachable — even last — preserves the
   exact silent-wrong-repo path the fix exists to close. A fallback that can return a *plausible
   wrong* answer is worse than one that fails.

`SCRIPT_DIR` / `HOOK_DIR` is retained in every hook, but only to locate that hook's own co-located
libraries (`hooks/lib/git-command.sh`, `hooks/lib/lane.sh`) — never as a root source.

The guard when neither step resolves preserves each hook's **documented posture** rather than
applying one project-wide default (see Prevention):

| Hook | On unresolvable root |
|---|---|
| `commit-quality-gate`, `risk-corroboration` | **exit 2**, named reason |
| `blast-radius-check` | warn, exit 0 (exit 2 under `BLAST_RADIUS_STRICT=1`) |
| `branch-guard`, `render-plan-on-write`, `ruff-on-edit`, `scope-gate` | note to stderr, exit 0 |
| `session-knowledge` | **silent** exit 0 — it runs under `exec 2>/dev/null` and is documented "never blocks / silent when empty" |

Not affected: `check-untracked-py.sh` runs CWD-relative `git ls-files` by design;
`branch-isolation-guard`, `pre-bash-dispatch` and `state-breadcrumb` already used
`CLAUDE_PROJECT_DIR`. Twelve scripts = 8 affected + 3 already correct + 1 CWD-relative.

## Regression Test

`tests/hooks/repo-root-resolution.test.sh` — 13 cases. Each hosts a hook inside a **foreign** git
repo whose staged content would trip a gate, then runs it with CWD set to a separate project and
asserts the hook acted on the project. Proven discriminating rather than vacuous: 5 of the original
11 cases **fail** when run against the pre-fix hooks (`git show HEAD:hooks/<h>.sh` into a temp
tree), and the `session-knowledge` KB-leak case fails against that hook's pre-fix version.

One case is honest about being weaker: "no resolvable project root → silent exit 0" passes both
before and after, because the old fallback also exited 0. It is a posture guard, not a
discriminator, and the spec's SUMMARY says so.

## Code Example

```bash
# WRONG — resolves to whatever repo happens to contain the hook's own file.
# Exits 0 with a plausible wrong answer when that repo is not the project.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$HOOK_DIR" rev-parse --show-toplevel 2>/dev/null)"

# RIGHT — ask the runtime, fall back to the CWD's repo, never to the script's own location.
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$REPO_ROOT" ] && { echo "[gate] cannot determine the project root — refusing to guess." >&2; exit 2; }
```

## Prevention

Two rules came out of this, the second from an explicit fork recorded in the spec's `design.md`:

- **Always:** derive a hook's repo root as `${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}`
  — ✅ `ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"`
- **Never:** derive the root a hook *audits* from the hook's own install location — ❌
  `REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"`. `SCRIPT_DIR` stays valid for
  locating the hook's own libs, never as a root source.
- **Always:** match a new guard's exit behaviour to the hook's already-documented blocking contract
  — ✅ blocking gate: `[ -z "$ROOT" ] && { echo "…" >&2; exit 2; }`
- **Never:** apply one project-wide failure posture to every hook — ❌ adding a bare `exit 2` to
  `ruff-on-edit.sh`, which `CLAUDE.md` documents as fail-visible but non-blocking. Uniform
  fail-closed would break ordinary edits over a condition that hook has no stake in; uniform
  fail-open would reproduce the silent pass this fix exists to close.

The generalisation worth carrying past hooks: **never infer the identity of the thing you are
acting on from where your own code happens to live.** Ask the runtime. If the runtime cannot say,
fail — a plausible wrong answer is the worst outcome available.

Treat every self-locating idiom as a smell whenever the artifact could be installed, symlinked,
vendored, or packaged outside the topology it was written against: `dirname "$0"`,
`${BASH_SOURCE[0]}`, `realpath "$0"`. Each is correct under exactly one install layout, and none of
them announces when that layout no longer holds.

**When adding a new hook, do both:** run it through `scripts/check-hook-root-source.sh` before
wiring it into `settings.json`, *and* add a foreign-repo-hosting case to
`tests/hooks/repo-root-resolution.test.sh`. The two are not redundant — the test technique is
spelling-independent by construction (it hosts the hook in a foreign repo and observes what the hook
acts on), where the static grep can only recognise spellings it was taught. Read
`ratchet-matches-spelling-not-property.md` before trusting the lint alone: its first version
reported clean while one of these eight hooks was still broken.

## Related

- docs/solutions/harness/ratchet-matches-spelling-not-property.md — the ratchet built to prevent
  this defect missed one instance of it; same session, and the reason is worth more than this fix
- docs/solutions/harness/gate-config-must-read-index.md — the adjacent rule for the *other* input a
  gate resolves: read policy from the git index, not the worktree
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md — why any `hooks/*` change
  carries the `high-blast` hard gate
