# Design — Restore signal to the commit gate (review items 1→3)

> Slug: `simplify-gate-surface` · Date: 2026-07-23 · Lane: high-risk
> Scope: items 1→3 of the gate review. Items 4→7 (delete the `app/` half of
> `commit-quality-gate.sh`, merge the commit-path hooks, drop the
> `weakening-validation` detector, delete dormant leftovers) are **out of scope** here
> and stay on the backlog.

## 1. Problem

The gate surface does not distinguish risky commits from ordinary ones.

| Measurement | Value | How it was measured |
|---|---|---|
| Recent commits (last 40) tripping a hard gate | **34/40 = 85%** — all `workflow-engine` | replay of the hook's path regex over `git show --name-only` per sha |
| Specs declaring `Lane: high-risk` | **41/63 = 65%** | `grep -h '^Lane:' specs/*/SUMMARY.md` |
| `weakening-validation` firings in those 40 commits | **1**, on `48c1728 refactor(evidence): consolidate lane validation` — a refactor, not a weakening (precision 0) | replay of the removed-line regex |

`workflow-engine` matches `skills/*/SKILL.md`, `agents/*.md`, `rules/*.md`. In a harness
repo those paths *are* the product, so the gate fires on almost every commit. The
consequence is not extra safety — it is that `Lane: high-risk` becomes the only lane that
can ever be committed, which discards the classification `/feature-intake` just computed.
A gate that says "yes" to 85% of inputs carries ~0 bits.

Two secondary defects compound it:

**(a) The escape hatch does not work as documented.** `hooks/risk-corroboration.sh:44-45`
says a category can be loosened "WITHOUT editing this file" by listing it in
`RISK_WARN_CATEGORIES`, but never says *where* the variable must live. Reproduced against
the real hook in a throwaway repo:

```
A) command string carries the prefix, hook env clean  → BLOCKED (exit 2)
B) var present in the hook's own process env          → warn,   exit 0
```

PreToolUse hooks are spawned by Claude Code with the **session** environment, and they run
*before* the command. An inline `VAR=x git commit` prefix sets the variable only for the
`git` process, so the hook never sees it. Any agent reading that comment will hand the user
a workaround that cannot work.

**(b) The consistency checker prevents its own cleanup.** `scripts/check_manifest.py:82-104`
regex-parses the hook source:

```python
hook_added = set(re.findall(r'add_cat\s+"([^"]+)"', rc))
hook_modes = set(re.findall(r"^\s*([a-z][a-z/-]*)\)\s*echo\s+\"(?:block|warn)\"", rc, re.M))
```

So `harness-manifest.json` is *declared* the single source of truth while actually being
validated **against** the hook — the dependency points the wrong way. The 2026-07-16
over-engineering review proposed deleting `category_mode()` (18 lines of `case` where every
branch returns `"block"` — a constant in a function costume); `phase-2-deep-review-2026-07-16.md:17`
overruled it because deletion fails CI on 8 slugs. The checker is what makes the change
expensive.

## 2. Approach — make gate *mode* data, not code

`harness-manifest.json` already carries a `mode` field per detectable gate; today it is
decorative, mirrored by hand into the hook's `case` statement and then read back out by regex.
Make it load-bearing:

```
BEFORE   manifest.mode  ──(hand-mirrored)──►  hook case stmt  ──(regex)──►  check_manifest
                                                    ▲
                                             the real authority

AFTER    manifest.mode  ──(jq at hook runtime)──►  hook decision
              ▲
       the real authority        check_manifest verifies only add_cat ↔ manifest slugs
```

Concretely:

- `category_mode()` keeps its signature and its `RISK_WARN_CATEGORIES` override, but its body
  becomes a manifest lookup (one `jq` call for all slugs, resolved once before the partition
  loop). `jq` is already a hard dependency of this hook — it parses the stdin JSON.
  Known asymmetry, accepted: the env override only *loosens* (block → warn); there is no
  per-session knob to re-tighten a warn-mode gate — re-tightening is a one-line manifest edit,
  which is the durable path anyway.
- `check_manifest.py` drops the `hook_modes` regex and its two problem branches. It keeps the
  `add_cat` ↔ `manifest.detectable` bidirectional check, which is a genuine inventory
  invariant (a detector with no manifest entry, or vice versa, is real drift).
- Loosening a gate becomes: edit one JSON field. Reversible, reviewable, greppable, and it
  travels with the repo instead of living in someone's shell.

### Fallback semantics (deliberate)

| Situation | Resolved mode | Why |
|---|---|---|
| Manifest present, slug has `mode` | that mode | the point of the change |
| Manifest present, slug absent or `mode` missing | `block` | unknown gate ⇒ conservative |
| Manifest unreadable / invalid JSON | `block` | fail-safe: a broken manifest must not silently un-block a gate |
| No `jq` | moot — unreachable | if `jq` is absent the hook already exits 0 at stdin parsing (line 27+36) and never reaches mode resolution; today's no-`jq` behavior is *allow*, not block. The mode lookup can assume `jq` exists. |
| **Consumer repo** (harness deployed to `.claude/`, no manifest at repo root) | `block` | see below |

The manifest is **not** deployed — `deploy-harness.sh:383` syncs only
`skills agents hooks rules templates`. The hook resolves its repo root via
`git rev-parse --show-toplevel`, so in a consumer repo the manifest is simply absent and every
gate blocks, exactly as it does today. That is the right default: the 85% firing rate is a
*meta-repo* artifact (consumers read `skills/*/SKILL.md`, they don't author it), so consumers
should keep the strict behavior. This is a documented property, not an accident.

## 3. The `env` question — why review item 2 changes shape

The review said: add an `env` block to `settings.json` and set
`RISK_WARN_CATEGORIES="weakening-validation"` there. Reading `deploy-harness.sh:335-351`
before implementing shows that would be half-broken:

```jq
$cur                       # consumer's settings as the BASE
| .hooks = ( … merge … )   # only .hooks is replaced
```

The merge takes the **consumer's** file as the base and replaces only `.hooks`. A new
top-level `env` key in our `settings.json` therefore reaches a consumer on **first install**
(where `$derived` is written wholesale, line 363) and is **silently dropped on every
re-sync**. Shipping a knob with install-vs-resync-dependent behavior is worse than not
shipping it.

So item 2 is delivered as three separate, honest pieces:

1. **The durable, shared loosening lives in the manifest** (§2) — no env var needed, which is
   what actually fixes the incident from the screenshot.
2. **The correct session-scoped override is `.claude/settings.local.json` → `env`** (gitignored,
   machine-local, genuinely inherited by hooks). This spec **documents** it in the hook comment
   and block message; it does not write that file. `.claude/` is deployed state and mutating it
   requires explicit human confirmation, so it is called out in the plan's Risks rather than
   automated.
3. **The misleading comment is corrected** so no future agent regenerates the impossible
   `VAR=x git commit` advice.

## 4. Which gates get loosened, and why exactly those two

| Gate | New mode | Evidence |
|---|---|---|
| `workflow-engine` | `warn` | 34/40 commits (85%). Path-only detection in a repo where those paths are the product. The *lane* signal it was meant to protect is better served by `/feature-intake` + the CI strict gate, which still block. |
| `weakening-validation` | `warn` | 1 firing in 40 commits, and it was a refactor. The detector greps removed lines for `assert `/`validator`/`required=True`/`\braise ` — routine in Python tooling. This is the exact category that blocked the session in the reported incident. |

The other seven detectable gates (`auth`, `authorization`, `data-loss/migration`,
`audit/security`, `external-provider`, `public-contract`, `high-blast`) stay `block`. They are
low-frequency here and high-consequence; the hook's own comment already warns "never
auth/external-provider first."

**Mode changes enforcement, not classification.** `/feature-intake` keeps treating both
categories as hard-gate flags that force `Lane: high-risk` in `SUMMARY.md`; only the commit
hook stops *blocking* on them. This is deliberate: it fixes the pain (a blocked commit with
no working override) without redefining what intake means, and it keeps the intake eval
fixture `LC-11` (`weakening-validation → high-risk`,
`skills/feature-intake/tests/lane-classification-cases.md:19`) valid and green. Bringing the
65% high-risk rate down is a *classification* change to `feature-intake`, and it is a
separate spec.

`warn` is not "off": the category is still detected and still printed to stderr
(`[RISK CORROBORATION] note: warn-mode categories present: …`), so the signal stays in the
session log and can be re-tightened by reverting one field.

## 4b. Activation — the live gate is the deployed copy

In this repo the hook that actually fires on `git commit` is
`.claude/hooks/risk-corroboration.sh` (registered in `.claude/settings.json:41`), a deployed
copy of the source in `hooks/`. Editing the source and merging changes **nothing at runtime**
until `scripts/deploy-harness.sh` re-syncs `.claude/` — and mutating `.claude/` requires
explicit human confirmation, so it is never automated by this spec. Task 3.1 therefore ends
with an explicit activation ask; the incident this spec fixes reproduces until that deploy
runs. (The deployed hook resolves the repo root via `git rev-parse --show-toplevel`, so after
deploy it finds `harness-manifest.json` at the root of this repo as designed.)

## 5. What still blocks after this change

Loosening two categories does not leave the surface ungoverned:

- `hooks/branch-isolation-guard.sh` — still hard-denies implementation edits on a shared branch.
- `commit-quality-gate.sh` — secrets scan, pending-escalation gate, lane-evidence gate all unchanged.
- `scripts/ci-strict-gate.sh` — still requires a changed `Lane: high-risk` SUMMARY with a
  machine-verified `### Verify` row whenever a PR touches `hooks/`, `settings.json`,
  `render_plan.py`, or `templates/`. **This PR will trip it and must satisfy it.**
- The seven remaining `block` gates.

## 6. Non-goals

- Touching `verify_summary.py`, `ci-strict-gate.sh`, or the review-receipt engine. They are
  earned evidence machinery with real tests, they run in CI rather than on the commit path, and
  they are not the source of the friction.
- Deleting the `app/`-scoped half of `commit-quality-gate.sh` (item 4).
- Merging `check-untracked-py.sh` / `branch-guard.sh` into the commit gate (item 5).
- Removing the `weakening-validation` **detector** (item 6) — only its mode changes here.
- Deleting the dormant leftovers: `break-glass-log.md`, `BLAST_RADIUS_STRICT`,
  `RISK_CORROBORATION_STRICT`, `auto-test-on-change.sh` (item 7).

## 7. Expected effect

- Commits tripping a **blocking** gate: 85% → ~15% (the 6/40 that also hit `high-blast`,
  which stays `block` by design).
- `check_manifest.py`: −~15 lines, and the last regex that reads shell source disappears.
- Cost of loosening a future gate: 4-file coordinated edit + CI fix → one JSON field.
- One class of impossible advice (`VAR=x git commit`) removed from the harness's own docs.
