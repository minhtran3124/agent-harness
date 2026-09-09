# What we can learn from `spotify/portal-ai-plugins`

> Date: 2026-09-09 · Reviewed at Spotify commit `3c24ca3`, our repo at `e61fc51`
>
> Question: Spotify shipped a public Claude Code / Codex / Cursor plugin repo. It is roughly
> 1/60th the size of ours and solves a much narrower problem. What, concretely, is worth copying,
> and where are we already ahead?
>
> Method: four parallel agents (Spotify skills, the `shunt` plugin, multi-host packaging, our own
> architecture) plus a first-hand read of every file in the Spotify repo by the main thread. Every
> claim below is sourced to a file or a command I actually ran. Where I did not check something,
> §8 says so rather than leaving it implied.

---

## TL;DR for a reviewer in a hurry

Spotify's repo is not more sophisticated than ours. It is *smaller and better packaged*, and that
difference is the whole lesson. Five things are worth taking:

1. **Install as a plugin, not as a copy-in script.** They ship a one-line
   `claude plugin marketplace add`. We ship a `curl | bash` installer with its own conflict
   protocol. (§4.1)
2. **Write skill `description:` fields in the user's words, not ours.** Theirs say "who owns a
   service, whether a service is healthy". Ours say "lane", "wave", "receipt". The description *is*
   the routing signal, so ours only fire for people who already speak harness. (§4.2)
3. **Put routing rules inside the hook, not in CLAUDE.md.** Their file-size rule costs zero context
   tokens until the moment it fires. Our always-on preamble is ~27 KB every session; theirs is
   1.5 KB. (§4.3)
4. **Measure what the harness costs, not only whether it is correct.** They publish a token-savings
   table with a stated estimator. We have never measured what our own ceremony costs to run. (§4.4)
5. **Publish the product's known limitations.** Their README ends with three real weaknesses in
   their own design. Our README does not. (§4.5)

Separately from those five, §2 collects **five small prompt-craft patterns** that are the most
reusable thing in the repo and cost almost nothing to adopt: an anti-trigger inside the skill
description; ambiguity as a named output state rather than an error; per-row status enums declared
inside the output table; `--yes` inverted from a friction-remover into a consent marker; and
escalating rather than silently sanitising when user text violates policy. If you read only one
section, read that one.

Two things I recommend *against* copying: their fail-open hook posture (right for them, wrong for a
governance gate) and their habit of recording a known parser bug as a green PASS. (§6)

The one-line summary of the whole comparison:

> **They measure cost and don't measure judgment. We measure judgment and don't measure cost.**

---

## 1. What each repo actually is

These are not competing projects. Getting that straight first is what makes the rest of the
comparison honest.

**`spotify/portal-ai-plugins`** is a *client* for an external service. It wraps the Portal CLI
(`npx @spotify/portal-cli`) in six prompt documents — set up auth, run diagnostics, search the
service catalog, brief a service, invoke an action, submit feedback — and packages them so three
different coding agents can install them. It ships one bonus plugin, `shunt`, that routes expensive
file reads to a cheaper worker model. That is the entire repo.

**Ours** is a *governance harness* for the agent itself. It classifies a change request into a risk
lane, decides how much proof that lane owes, dispatches isolated subagents, and blocks the commit
when the declared lane does not match the staged diff. It has no external service to talk to; the
thing it operates on is the agent's own behaviour.

The size gap follows from that, and it is large:

| | Spotify | Ours |
|---|---|---|
| Files (excluding `.git`) | 36 | ~1,100 |
| Lines of code + docs | 1,744 | ~102,000 |
| Skills | 8 (6 portal + 2 shunt) | 12 |
| Hooks | 2 | 11 registered |
| Scripts | 3 | 76 |
| Commits | 6 | 868 |
| Test suite | 51 cases, **~5 s**, no credentials | 200+ shell cases + 582 pytest, **3 m 25 s** |

*(File and line counts from `find`/`wc` on both trees; commits from `git rev-list --count HEAD`.
Both suites measured by running them: theirs `bash plugins/shunt/evals/run.sh` → 51 passed, 0
failed. Ours `bash scripts/run-tests.sh` → ALL GREEN in 3:25.)*

So "Spotify is simpler" is not an insight. The useful question is narrower: **for the small surface
they do cover, did they make choices we should copy?** For several things, yes.

---

## 2. How they write a skill

Their skills are 25–92 lines. Ours are 37–74. Length is not the difference — *voice* is.

Every one of their skills has the same three-part shape: frontmatter with only `name` and
`description`; an imperative title; the exact commands in fenced bash blocks; a numbered workflow;
a short list of prohibitions. Three patterns in that shape are good and cheap to adopt.

**They forbid guessing at CLI flags.** From `skills/setup/SKILL.md:13`:

> Run `--help` before relying on a Portal CLI or host command or flag.

This targets the single most common way an agent wastes a turn: inventing a flag that does not
exist. It appears again in `skills/service/SKILL.md:12` and `skills/doctor/SKILL.md:30`. We have no
equivalent anywhere in `rules/` or `skills/`.

**They state the negative scope of a report at the point of use.** `skills/doctor/SKILL.md:78`:

> Do not report overall readiness when a required check is blocked or unverified.

And `skills/service/SKILL.md:37`:

> Treat unavailable workflows and dimensions as unavailable, not healthy.

That is our `not_observed != absent` rule from `rules/behavior.md`, restated in the vocabulary of
the actual domain — and written *inside the skill that can violate it*, rather than in a general
rules file the skill has to remember to consult.

**They route with a table, not prose.** `skills/service/SKILL.md:28-33` maps user need → exact
command:

| User need | Command |
|---|---|
| Owner, on-call, Slack, or runbook | `owner <service-name> --json` |
| Build, deployment, runtime, or incidents | `service status <entity-ref> --json` |
| Service documentation | `service docs <entity-ref> --json` |

Two lines of table replace a paragraph of "if the user asks about X, consider Y."

### Five smaller patterns that are the real craft

These are the least obvious things in the repo and the most portable. Each is one line of prose
doing structural work.

**1. An anti-trigger inside the description.** `skills/search/SKILL.md:3`:

> Use when the user asks to find services, APIs, systems, components, owners, or Portal
> documentation **and does not already know the exact entity reference.**

The trigger clause carries a *negative* condition, so the skill declines to fire when a cheaper
direct path already exists. That is routing suppression at zero orchestration cost — no dispatcher,
no priority table, just a clause. None of our 12 descriptions has one, and several of our skills
overlap in ways that would benefit (`xia2` vs `brainstorming`; `correctness-review` vs
`intent-review`).

**2. Ambiguity as a named output state, not an error.** `skills/doctor/SKILL.md:53-54`:

> When multiple instances exist and no target was provided, report the ambiguity instead of
> selecting one.

What makes this stick is that the state is then carried into the output schema at
`skills/doctor/SKILL.md:75` — `| Authentication | Ready, ambiguous, or blocked |`. A bare prose
instruction would not survive report-writing; a third value in the output enum does. This is the
same instinct as our `unconfirmed` verdict in `evals/context-boundaries/README.md`, and it is worth
generalising: **if a rule says "don't guess," the output format needs a slot for "didn't know."**

**3. Per-row status enums declared inside the output table.** `skills/doctor/SKILL.md:71-76` gives
each check a *different* vocabulary — Plugin is "Ready, warning, or blocked", Authentication is
"Ready, ambiguous, or blocked", CLI and Actions are "Ready or blocked". Six lines of table double as
the status-vocabulary spec. It kills status drift without a separate schema document.

**4. `--yes` inverted into a consent marker.** `skills/actions/SKILL.md:29`:

> Add `--yes` only when the action is marked destructive and the user authorized it.

Two conjoined conditions mean the auto-approve flag can never be used as a friction-remover. It
becomes *evidence that authorization happened* — the opposite of its normal reflex. Worth comparing
to our `BRANCH_ISOLATION_REASON` break-glass, which does the same inversion and logs it.

**5. Escalate, don't silently edit, when user text violates policy.** `skills/feedback/SKILL.md:25`:

> Do not include secrets, tokens, personal data, or internal URLs in the text. If the user's wording
> contains any, **ask them to rephrase instead of editing it silently.**

Silent sanitisation would destroy the verbatim guarantee made one line earlier at
`skills/feedback/SKILL.md:24`. Routing back to the human preserves the audit trail instead of
laundering it. We make the same verbatim promise in `templates/SUMMARY.template.md` — the `### Intent`
block says "do NOT paraphrase or summarize" because it is the oracle for intent-review — but we never
say what to do when the verbatim text is itself a problem.

### Where their skills are weaker than ours

Their safety guarantees are **prose only**. `skills/actions/SKILL.md:23-29` tells the agent to
dry-run before mutating and to "Execute only after user authorization" — but nothing enforces it.
No hook watches the `actions` path; no confirmation gate; no receipt. `skills/doctor/SKILL.md`
promises to be read-only and is read-only only because the document says so.

Ours is the opposite: `hooks/risk-corroboration.sh` re-derives the risk of the staged diff and
blocks a commit whose declared `Lane:` is too low. That is a real mechanical check, and it is the
main thing we have that they do not.

They also have no `allowed-tools` in frontmatter, and we do — `skills/feature-intake/SKILL.md:4`
restricts that skill to `Read, Write, Grep, Glob, Bash(git log *), Bash(git diff *), Bash(ls *)`.
That is least-privilege at the skill level, enforced by the runtime rather than by prose. But it is
not a general property of our repo: **only 3 of our 12 skills declare it** (`feature-intake`,
`visual-planner`, `xia2`). The other nine run unrestricted. Extending it is nearly free and belongs
on the recommendation list.

### A note on structure — weaker than it first appears, in both repos

My first read of their skills was that they share a common skeleton and ours do not. Checking that
properly, the difference is smaller and more interesting than it looked.

Neither repo reuses heading *text*. Spotify's six skills produce 14 H2 headings with **zero
repeats**. Ours produce 29 across 12 skills, with only `## References` (4×) and `## Arguments` (2×)
appearing more than once. On the literal measure, they are no more standardised than we are.

What they do have is a skeleton that is **positional, not nominal** — four things in the same place
every time, under whatever name the domain wants:

1. H1 is an imperative verb phrase ("Diagnose Spotify Portal", "Invoke Portal Actions").
2. A source-of-truth declaration around line 8 ("Use the Portal CLI as the source of truth").
3. Exactly one ordered procedure section — named `<something> workflow` in 4 of 6.
4. A terminal prohibition as the last line ("Never infer successful execution from a dry run.";
   "Do not invent services or documentation when results are sparse.").

That last one is a nice trick on its own: the strongest constraint gets the most-remembered
position in the document. Our skills have no recurring order at all, and no convention about where
a prohibition lives.

Also worth noting, their `description:` is a rigid two-clause template in all six files —
`<capability sentence>. Use when <disjunctive trigger list>.` That consistency is what makes §4.2's
recommendation cheap to execute: there is a shape to copy, not just a tone.

So the recommendation stands, but the reason is sequence, not naming: define a canonical order
(preconditions → commands → numbered workflow → prohibitions → output contract) rather than a
canonical set of headings. That is a smaller and more achievable change than "standardise the
sections," and it is the part that actually helps a reader.

---

## 3. The `shunt` plugin, which is the interesting part

`shunt` is the one piece of the repo doing something architecturally novel, and it is worth reading
in full even if we never adopt it.

**The problem it solves.** Reading a 600-line file into Claude's context costs real money. Most of
those tokens are wasted, because the question was "what does this export?" and the answer is twenty
lines. `shunt` intercepts the read and sends the file to a cheaper model instead, returning only
the answer.

**The mechanism, end to end.** This is the part worth internalising:

1. Claude calls `Read` on a file.
2. `hooks/check-file-size` fires (PreToolUse, matcher `Read`) and counts lines with `wc -l`.
3. Under 350 lines, or `offset`/`limit` set, or file missing → `{"decision": "allow"}`.
4. Over 350 lines → `{"decision": "block", "reason": …}`, and the reason is a routing instruction,
   not a refusal:

   > File is 1200 lines (threshold: 350). Use the `/bulk-reader` skill to delegate this read to
   > AiKA instead of reading it directly. If you need exact content for editing, re-read with an
   > offset/limit for just the section you need.

5. Claude reads that and invokes `/bulk-reader` — a 13-line skill whose entire body is one command.
6. `scripts/bulk-read` wraps each file in `<file path="…">` tags, ships them to a worker model via
   `portal-cli actions aika:invoke-chat`, and prints only the answer.

A second hook, `check-bash-read`, closes the obvious hole: `cat`/`head`/`tail`/`less`/`more` on a
large file would otherwise bypass the `Read` matcher entirely.

**One protocol difference worth knowing about.** Their hooks speak a different output contract than
ours. Theirs emit a top-level object and always `exit 0` — control flows entirely through stdout:

```json
{"decision": "block", "reason": "File is 1200 lines (threshold: 350). Use the /bulk-reader skill…"}
```

Ours emit the nested form and use the exit code as a second channel —
`hookSpecificOutput.permissionDecision: "deny"` (`hooks/branch-isolation-guard.sh:72`), or `exit 2`
for the git gates (`hooks/risk-corroboration.sh:207`). Both shapes work today. I have not
established which is current and which is legacy, so I am recording the difference as an
observation, not as a recommendation — but if we do move to plugin packaging (§4.1), confirming the
canonical contract is part of that work.

**Three design lines from it that generalise.** From `plugins/shunt/README.md:13`:

> Claude never assembles bash pipelines from prose. It calls a script with named arguments. The
> scripts handle everything internally.

Good rule, and we partially violate it — several of our skills contain multi-step bash the agent
has to assemble correctly.

From `hooks/check-file-size:3`:

> Self-contained: all routing logic lives here, no CLAUDE.md needed

This is the context-engineering point. The rule "delegate reads over 350 lines" costs **zero**
context tokens until it fires, because it lives in a hook that only speaks when triggered. Compare
ours: `CLAUDE.md` (16 KB) plus five always-on rule files (11 KB) is **~27 KB, roughly 7,000 tokens,
loaded into every session** whether or not any of it applies. Their equivalent always-on file,
`AGENTS.md`, is 1.5 KB.

From the README, a section titled **"What doesn't get delegated"** — listing debugging, editing,
small files, and architectural decisions. A plugin that documents when *not* to use itself is
unusual and good.

**The `aika.sh` transport is also unusually careful.** `scripts/lib/aika.sh:146-157` handles a
failure mode most people would miss: a stale pinned mode id does not error server-side, it silently
runs the turn *without* the mode — producing a confident, generic answer under the wrong
instructions. They detect it by reading back `.mode.name` from the response and treat an empty
value as a hard failure:

> A name that resolves to nothing fails the request, but a stale `mode_id` only logs a warning
> server-side and the turn runs mode-less — a generic answer under the wrong instructions. The
> output names the mode that actually ran, so treat "none" as a failure rather than passing it off.

That is the same instinct as our own "green can mean skipped" learning, applied to an LLM call.

**And the honest caveat.** `shunt`'s enforcement is shallow by design. `check-bash-read` extracts a
path with a regex over five command names; `sed -n '1,999p' file`, `awk`, `perl`, or `python -c` all
sail straight past it. Their own evals admit the gaps — `evals/bash-hook-evals.json:88` marks `grep`
as "not caught", and case 17 documents a parser bug where `head -n 5 file` is mis-parsed. That is
*fine for a cost optimisation* and would be disqualifying for a security gate. Exactly the
distinction in §6.

---

## 4. The five things worth taking

### 4.1 Install as a plugin, not as a file copy — highest value

Spotify's install is two lines the user types once:

```bash
claude plugin marketplace add spotify/portal-ai-plugins
claude plugin install portal@portal
```

Ours is `scripts/install-harness.sh`: a `curl … | bash` script that clones the repo to a temp dir,
merge-syncs a payload of nine top-level items into the target's `.claude/`, merges an entry into
`.mcp.json`, scaffolds `specs/` and `docs/solutions/`, and carries a conflict-resolution protocol
(`.harness-incoming` sidecar files) because it is hand-rolling what a package manager does.

The mechanics are already almost in reach. We have a generated Codex plugin manifest at
`adapters/codex/plugin/.codex-plugin/plugin.json` and a hook registration file at
`adapters/codex/plugin/hooks/hooks.json`. We have no `.claude-plugin/` at repo root at all —
`ls -d .claude-plugin` fails, and `git ls-files | grep marketplace` returns only test fixtures.

One real blocker: `settings.json` registers hooks by *relative* path
(`hooks/pre-bash-dispatch.sh`), which only works because we copy the tree into the project. Spotify
uses `${CLAUDE_PLUGIN_ROOT}/hooks/check-file-size`. Switching to plugin-root paths is the actual
work.

**Spike result (2026-09-09): the packaging works, but it exposes a worse problem than the one I
expected.** I built a throwaway one-hook plugin, installed it, and ran a headless session against a
test repo whose index and worktree deliberately disagreed. Three answers:

| Question | Result |
|---|---|
| Does a plugin hook get CWD = project? | ✅ `PWD` is the project directory |
| Can it read the project's git index? | ✅ `git show :file` returned the *staged* content, correctly distinct from the worktree |
| How does `${CLAUDE_PLUGIN_ROOT}` resolve? | ✅ Points at the plugin dir, **and** `CLAUDE_PROJECT_DIR` is set alongside it |

Both variables are available at once, which is exactly what our hooks need: the plugin's own libs
plus the project's git state. So the assumption held.

**But the real blocker is elsewhere, and it is dangerous.** Eight of our eleven hooks derive the
repository root *from the hook's own location*:

```bash
REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
```

(`blast-radius-check`, `branch-guard`, `commit-quality-gate`, `render-plan-on-write`,
`risk-corroboration`, `ruff-on-edit`, `scope-gate`, and `check-untracked-py` via its lib). Only
`branch-isolation-guard.sh:27` and `pre-bash-dispatch.sh:21` use `CLAUDE_PROJECT_DIR`.

Under plugin packaging `$SCRIPT_DIR` lives outside the project, and I measured two outcomes:

- **Plugin not inside any git repo** → `exit 128`, `REPO_DIR` empty. Broken, but *loudly*.
- **Plugin inside a git repo** → `exit 0`, and `git show :probe-target.txt` returned
  `DECOY-INDEX-CONTENT-from-plugin-repo` — the **plugin's** index, not the project's. The gate runs
  green while auditing the wrong repository.

The second case is not hypothetical: `claude plugin marketplace add <github-repo>` *clones* the
repo, so a marketplace-installed plugin is **always** inside a git repo. The normal installation
path is the one that fails silently. This is the "green can mean skipped" failure mode in a nastier
form — green can mean *audited the wrong repo*.

**Consequence for the plan.** The work is not "switch hook paths to `${CLAUDE_PLUGIN_ROOT}`". It is:

1. Move all 8 hooks to `CLAUDE_PROJECT_DIR` as the repo-root source, leaving `SCRIPT_DIR` only for
   locating the hook's own libraries.
2. Add a fail-closed guard: if `CLAUDE_PROJECT_DIR` is empty *and* the `SCRIPT_DIR`-derived root
   disagrees with CWD, block rather than guess. Without this, the silent-wrong-repo mode stays
   reachable forever.
3. Only then discuss the marketplace manifest.

Steps 1 and 2 are worth doing **whether or not we ever ship a plugin** — they harden an assumption
that is already fragile today. They should be split out of this item and done earlier.

**Copy the shape, not the hygiene.** Their three manifests are metadata-only — the single
structural field in each is `"skills": "./skills/"`, pointing every host at the same canonical
directory (`AGENTS.md:18`, "Keep each workflow canonical in `skills/`"). Host neutrality comes from
*writing host-neutral skills*, not from a build step that transforms them: all six SKILL.md files
carry pure two-field frontmatter with no host-specific keys. That is the part to copy.

The part not to copy is the duplication it creates. `"version": "0.1.0"` appears **seven times**
across the five manifests, hand-maintained, with nothing checking they agree. There are already two
small inconsistencies visible: `.codex-plugin/plugin.json:39-40` sets `logo` to `portal-icon-dark.svg`
and `logoDark` to `portal-icon-light.svg` — which reads inverted — and asset paths are `./assets/…`
in the Codex manifest but `assets/…` in the Cursor one. We generate our Codex adapter from a schema
(`adapters/codex/schema.json`) rather than hand-writing it, which is the better instinct; keep it and
generate the Claude manifest the same way.

There is a free win available today. Spotify's `AGENTS.md` documents `claude plugin validate
--strict .` as a validation step. I ran it on both repos:

- Spotify: `✔ Validation passed`
- Ours: `✘ Validation failed` — three warnings, all the same shape. `agents/README.md`,
  `agents/PROJECT.md`, and `agents/PROJECT.template.md` sit in `agents/` and so get parsed as agent
  definitions, but have no frontmatter.

That is a ten-minute fix (move the three files, or give them frontmatter) and then a one-line CI
step. Our CI (`.github/workflows/harness-ci.yml`) does not run it at all today.

### 4.2 Rewrite skill descriptions in the user's vocabulary

The `description:` field is the routing signal — it is what the model reads to decide whether a
skill applies. Compare:

**Theirs** (`skills/service/SKILL.md:3`):

> Use when the user asks who owns a service, whether a service is healthy, where its runbook or
> docs are, or requests a service briefing.

**Ours** (`skills/subagent-driven-development/SKILL.md:2`):

> Use to execute an approved multi-task PLAN.md: waves of isolated implementer subagents with
> per-task review, separate-session resume, and final delivery/correctness/intent gates before
> shipping.

Ours describes the *mechanism*, in our private vocabulary. Theirs describes the *user's situation*
in the user's words. Someone who says "build out the plan we agreed on" does not say "execute an
approved multi-task PLAN.md."

Three concrete moves make this actionable, all visible in their corpus:

- **Follow their two-clause template** — `<capability sentence>. Use when <disjunctive trigger
  list>.` — used verbatim in all six of their skills.
- **Phrase the trigger list as user situations**, not mechanism names.
- **Add anti-triggers where skills overlap** (§2, pattern 1). `search/SKILL.md:3` ends its trigger
  clause with "and does not already know the exact entity reference." We have at least two
  overlapping pairs that need this: `xia2` vs `brainstorming`, and `correctness-review` vs
  `intent-review`.

Two of their descriptions go further and name an *implicit* trigger — a situation rather than a
command. `skills/feedback/SKILL.md:3` fires when the user "voices an impression, complaint,
suggestion, or praise about the Portal CLI… and confirms they want it submitted." That is a skill
activating on something the user was not explicitly asking for.

This connects to a weakness in our own eval corpus. `evals/skills/prompt-refactor/activation/`
requires eight trigger cases per skill, which sounds rigorous — but reading `feature-intake.json`,
cases 1–6 are the same sentence with different prefixes bolted on ("Please do this in the
repository: classify this change request into a risk lane and confidence" / "This is
time-sensitive, but classify this change request into a risk lane and confidence"). That measures
robustness to prefixes, not activation. Real activation cases would be phrased the way a user
actually opens a session: *"can you add rate limiting to the login endpoint?"*

### 4.3 Move contextual guidance out of the always-on preamble

We already have the right idea — `rules/*.md` is two-tier, and four of nine files carry `paths:`
frontmatter so they load on demand. But the split is lopsided:

| Always-on | Contextual (`paths:`) |
|---|---|
| `architecture.md`, `behavior.md`, `guidelines.md`, `orchestration.md`, `research-depth.md` | `auto-correct-scope.md`, `plan-format.md`, `terminology.md`, `wave-parallelism.md` |

Plus `CLAUDE.md` at 16 KB, which is the single largest always-on cost and is not tiered at all.
`rules/orchestration.md` alone is 6.6 KB, and most of it — the escalation checklist, the subagent
return contract — is only relevant once a plan is actually executing.

`shunt` shows the alternative: guidance that lives in the enforcing hook and appears only when
relevant. The general form: **if a rule has a mechanical trigger, put its text in the thing that
triggers.** `hooks/scope-gate.sh:44` already does this correctly — it injects the intake-lane
guidance as `additionalContext` at the moment an implementation prompt arrives with no plan. That
text does not need to also live in `CLAUDE.md`.

One caution, from `CLAUDE.md` itself: adding `paths:` to a rule **removes** it from the always-on
set. That is a behaviour change, not a formatting change, and
`tests/scripts/rule-loading-tiers.test.sh` will catch it. Treat any such move as a real change with
a real review.

### 4.4 Measure what the harness costs, not only whether it is correct

`plugins/shunt/evals/benchmarks.json` plus the `--benchmark` path in `run.sh` produce a table like:

| Scenario | Lines | Without shunt | With shunt | Savings |
|---|---|---|---|---|
| Single large file | 4,014 | 33,684 tokens | 5,737 tokens | 82% |
| Source + test pair | 7,408 | 75,990 tokens | 4,148 tokens | 94% |

The estimator is crude — chars ÷ 4, output tokens weighted 5× — and `run.sh:290` prints that method
directly under the table. Crude and stated beats precise and hidden.

We measure nothing like this. I grepped `evals/`, `docs/`, and `scripts/` for token or cost
accounting and found none. Our evals measure catch-rate, lane-classification accuracy, and
instruction delivery — all correctness. Yet the harness's most common real-world complaint is
almost certainly *ceremony cost*: how many turns, how many tokens, how much wall-clock does the
full chain add to a normal-lane change? Nobody can answer that today, which means nobody can argue
about whether a given gate is worth its price.

The cheapest version: record turn count and elapsed time per lane in the existing `SUMMARY.md`
header, and publish a rolling table. That turns "the harness feels heavy" from a vibe into a number
we can act on — or defend.

### 4.5 Ship a "known limitations" section, and mean it

`plugins/shunt/README.md` ends by naming three real weaknesses in its own design: no enforcement for
`code-writer` (only `bulk-reader` has a hook), an `ARG_MAX` ceiling on request size because
invoke-chat input travels through argv, and an invocation timeout that large generations can exceed.
Each says what breaks and what to do about it.

We have this discipline for individual changes — the `### Not auto-verified` block in every
`SUMMARY.md`. We do not have it at the *product* level. `README.md` and `HARNESS.md` describe what
the harness enforces; neither has a section saying what it does not. A reader has to reconstruct
that from `CLAUDE.md`'s "Gate verifiability" paragraph, which is written for a contributor, not for
someone deciding whether to adopt this.

---

## 5. Where we are already ahead

Worth writing down so we do not cargo-cult a smaller repo's choices.

### 5.1 Our gates are mechanical at the commit boundary — but only there

Their `actions` skill *asks* the agent to dry-run before mutating. Our `risk-corroboration.sh`
re-derives risk from the staged diff and exits 2 when the declared lane is too low. That is the
difference between a promise and a check, and it is the reason our repo is big.

A live demonstration turned up while writing this report: my first attempt to save this file was
denied by `hooks/branch-isolation-guard.sh`, because I was on `main` and had not cut a branch. The
gate fired on the person writing the document about the gate. That is the behaviour working.

**But the claim needs a boundary drawn around it, and this is the most important correction in this
report.** What is mechanically enforced is the *commit and edit boundary* — the eleven hooks. The
*skill chain itself* is prose-linked, exactly like Spotify's. Our whole pipeline —
`feature-intake → brainstorming → xia2 → writing-plans → using-git-worktrees →
subagent-driven-development → correctness-review → intent-review → finishing-a-development-branch` —
is declared in an ASCII diagram in `skills/README.md` and a routing table in
`skills/feature-intake/SKILL.md:46-52`. Handoff happens through files (`SUMMARY.md`, `design.md`,
`research-brief.md`, `PLAN.md`, `.review-receipt.json`).

Three scripts do verify those artifacts — `verify_summary.py`, `check_plan_contract.py`, and
`check_review_receipt.py` are each invoked from a SKILL.md. But every one of them checks an
artifact's *shape and content*, not the chain's *order*. Nothing verifies that brainstorming
actually ran before planning, that research preceded the plan, or that a lane's required route was
taken rather than skipped. I checked for it:
`grep -rlniE 'design\.md|research-brief|brainstorm' hooks/*.sh` returns one hit, and it is a comment
on line 118 of `commit-quality-gate.sh`, not a check.

So chain order is enforced by the model choosing to follow prose — the same enforcement tier as
Spotify's "Execute only after user authorization." We are ahead of them on the commit boundary and
on artifact shape; we are level with them on chain order.

This is worth stating plainly because `CLAUDE.md` describes skipping a required step as "a hard gate
violation," which reads as though something checks. For the commit boundary, something does. For
the chain, the gate is the model's compliance. Two different tiers under one word.

### 5.2 Our block messages are already better than theirs

`shunt`'s block message names one alternative. Ours name several, plus the escape hatch. From
`hooks/branch-isolation-guard.sh:91`:

> You are on shared branch main. Every lane — tiny, normal and high-risk — cuts a branch BEFORE
> implementing, so editing `<file>` here is not allowed.
> Fix (tiny lane): `git checkout -b <type>/<slug>`, then re-apply the edit.
> Fix (normal / high-risk): invoke the using-git-worktrees skill for an isolated worktree + branch.
> …Override after confirming: set `BRANCH_ISOLATION_REASON=<why>` (recorded to the break-glass log).

Lane-aware, two fix paths, an audited override. This is a confirmation that our approach is right,
not a gap.

### 5.3 Our hooks fail closed on input they cannot parse

`hooks/pre-bash-dispatch.sh:47` blocks (exit 2) when the payload cannot be classified, commented
"blocking to fail safe." `hooks/branch-isolation-guard.sh:67` denies when the tool class
contradicts the matcher it was registered on.

`shunt`'s hooks fail *open* everywhere — unparseable input, missing field, unrecognised command all
return `allow`. That is the correct choice for a cost optimisation and would be a hole in a
governance gate.

### 5.4 Our test infrastructure is deeper on every axis except speed

`tests/lib.sh` gives us a real DSL: each case runs the hook inside a throwaway `mktemp` git repo
with the hook copied in, so nothing touches the working tree. It supports per-case env vars, staged
files, and an `xfail` state for known bugs.

That last one matters. Spotify's `evals/bash-hook-evals.json` case 17 encodes a real parser bug as
`expected_decision: "allow"` with the reason "Parser bug: -n and 5 are separate args". It prints
**PASS**. The bug is documented in a string nobody reads and invisible in the summary line. Our
`xfail` prints `xfail <case> — known bug: <reason>` on every run, so the bug stays visible while the
suite stays green. Ours is the better design.

Where they win is runtime: 51 cases in about five seconds with zero setup, versus our 3 m 25 s. If
someone won't run the suite locally, its depth stops mattering — a fast subset is worth adding.

### 5.5 Our behavioural evals are in a different league

`evals/README.md` and `evals/skills/prompt-refactor/README.md` describe labelled fixtures, blind
runs where the skill never sees `truth.md`, a first-run-is-the-record rule that forbids re-running
until green, and a scorer that treats a `pass → blocked` transition as *unmeasured coverage* rather
than a regression. `evals/context-boundaries/README.md` goes further and probes, per execution
context, whether an instruction actually arrived — built after a real P1 escape (#141/#143) where a
rule was referenced in a dispatch prompt but never delivered to the subagent.

Spotify has an `evals.json` with three behavioural cases and — I checked `run.sh` — **no runner that
executes it**. `run.sh` runs `hook-evals.json`, `bash-hook-evals.json`, and `transport-evals.sh`
only. Their behavioural evals are aspirational; ours are a protocol.

---

## 6. Two things not to copy

**Their fail-open hook posture.** Right for `shunt`, wrong for us. The general rule worth writing
down: *a hook's failure posture should match its purpose.* An optimisation hook that fails closed
breaks the user's workflow over a parse error. A governance gate that fails open is not a gate. We
currently apply one posture (fail-closed) uniformly — correct today, since every hook we ship is a
gate, but worth stating explicitly before we ever add an optimisation hook.

**Recording a known bug as a passing test.** Covered in §5.4. Use `xfail`.

---

## 7. Recommendations, ranked

Ordered by value ÷ cost. Each names the file that would change.

| # | Change | Files | Cost | Why now |
|---|---|---|---|---|
| **0** | **Move the 8 `git -C "$SCRIPT_DIR"` hooks to `CLAUDE_PROJECT_DIR`, + a fail-closed guard when the two roots disagree** | `hooks/*.sh` (8 files), `tests/hooks/*.test.sh` | ~half day | **Found by spike (§4.1).** Today's fragility, not a future one; a gate that resolves the wrong repo exits 0. Independent of whether we ever ship a plugin |
| 1 | Fix `claude plugin validate --strict .` and add it to CI | 3 files in `agents/`, one step in `.github/workflows/harness-ci.yml` | ~30 min | Free correctness signal we currently fail; prerequisite for #3 |
| 2 | Rewrite all 12 skill `description:` fields in user vocabulary | `skills/*/SKILL.md` | ~2 h | Directly improves activation; no mechanism change |
| 3 | Ship a root `.claude-plugin/marketplace.json` + `plugin.json`; move hook paths to `${CLAUDE_PLUGIN_ROOT}` | `settings.json`, new `.claude-plugin/`, `scripts/install-harness.sh` | ~1 day + a spike to prove index-reading gates still work | Removes the installer and its conflict protocol |
| 4 | Trim the always-on preamble: scope `orchestration.md` with `paths:`, split `CLAUDE.md` | `rules/orchestration.md`, `CLAUDE.md` | ~half day | ~7 K tokens per session today; see the caution in §4.3 |
| 5 | Add a cost dimension to evals — turns + elapsed per lane in `SUMMARY.md`, rolling table | `templates/SUMMARY.template.md`, new script | ~half day | Makes the ceremony-cost argument arguable with data |
| 6 | Add a fast subset to `run-tests.sh` (`--quick`) targeting <10 s | `scripts/run-tests.sh` | ~2 h | 3 m 25 s is a suite people run in CI and skip locally |
| 7 | Add a "Known limitations" section to `README.md` | `README.md` | ~1 h | Adoption honesty; we already do this per-change |
| 8 | Add a "run `--help` before relying on a flag" rule | `rules/behavior.md` | ~15 min | Cheap anti-hallucination guard we lack |
| 9 | Extend `allowed-tools` to the 9 skills that lack it | `skills/*/SKILL.md` | ~1 h | Least-privilege we already use in 3 of 12; no reason for the gap |
| 10 | Define a canonical section *order* for SKILL.md (not a fixed heading set) | `skills/*/SKILL.md`, `templates/` | ~half day | Our skills have no recurring sequence; theirs do, and it makes them scannable (§2) |
| 11 | Give every "don't guess" rule a matching slot in its output format | `templates/SUMMARY.template.md`, review prompts | ~2 h | §2 pattern 2 — a rule with nowhere to record "didn't know" gets silently resolved instead |
| 12 | Say what to do when verbatim user text is itself a policy problem | `templates/SUMMARY.template.md` `### Intent` block | ~30 min | §2 pattern 5 — we promise verbatim capture but never handle secrets in the request |

Items 1, 2, 7, 8, 9 and 12 are independent and can land this week. Item 3 is the big one and should get
a design pass of its own — it changes how the harness is distributed, which is a *redefine the
system* trigger under `rules/orchestration.md` and therefore an escalation, not an autonomous
change.

**One recommendation this report deliberately does not make:** "adopt `shunt`." Delegating bulk
reads to a cheaper model is a good idea, but it depends on a Portal instance with AiKA enabled,
which we do not have. The transferable part is the *pattern* — a hook that blocks an expensive
operation and names a cheaper route — not the plumbing.

---

## 8. What I did not check

Stated plainly so nobody reads more into this than it supports.

- **I did not run their `--benchmark` path.** It needs a Portal instance and auth. The 82–94 %
  savings table in `plugins/shunt/README.md` is from "a 162K-line Java monorepo" that is not in the
  repo, so the committed `benchmarks.json` fixtures cannot reproduce those exact numbers. Treat the
  percentages as their claim, not as verified.
- ~~I did not test whether a plugin-installed hook can read the project's git index.~~
  **Resolved 2026-09-09 by spike — see §4.1.** It can. But the spike found a different and more
  serious problem: 8 of 11 hooks derive the repo root from their own location, which under plugin
  packaging silently resolves to the *plugin's* repo with exit 0. Now recommendation #0.
  Still untested: whether a plugin-installed hook behaves the same on Linux, and whether
  `CLAUDE_PROJECT_DIR` is guaranteed set in every hook event (I observed it only for PreToolUse/Bash).
- **I did not evaluate the Portal CLI itself** — only the prompt documents that call it.
- **I did not install their plugin under Codex or Cursor.** Their `.codex-plugin/plugin.json`
  carries an `interface` block (brand colour, logos, default prompts) that Claude's manifest does
  not; I read the schema but did not exercise the loader.
- **Both test-suite timings are single runs on one machine** (macOS, this laptop), not benchmarks.
  They are the right order of magnitude, not precise figures.
- **I did not establish which hook output contract is canonical.** Spotify's top-level
  `{"decision": …}` and our `hookSpecificOutput.permissionDecision` both work today; I did not check
  the Claude Code docs to see whether one supersedes the other. §3 records this as an open question,
  not a finding.
- **One agent's claim did not survive checking, and it is worth recording why.** A subagent reported
  that "exactly one link in the skill chain is verified by code." Grepping the skills showed three
  verifier scripts, not one. The corrected claim in §5.1 is narrower and true: three scripts check
  artifact *shape*; nothing checks chain *order*. Flagged here because the original wording was the
  more flattering version of the finding, and it was wrong.
