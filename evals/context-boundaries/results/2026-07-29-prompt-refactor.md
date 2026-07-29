# Context-Boundary Probe Results — skill prompt refactor candidate

**Run date:** 2026-07-29
**`claude --version`:** `2.1.220 (Claude Code)`
**HEAD sha at probe time:** `dbdd2b70afd5d76637f0a87d6014c8dff9ae4763` (`refactor/skill-prompt-surface`)
**Worktree probed:** `/tmp/harness-skills-candidate-ab`, harness deployed via `scripts/deploy-harness.sh`
**Protocol:** `evals/context-boundaries/README.md` + `probes/*.md` (this repo, same commit).
**Runner:** each probe ran in its own fresh, non-persistent `claude -p` session (`--model sonnet`,
`--effort low`). The three child-context probes were dispatched from that fresh session via the
Task tool with the probe prompt passed verbatim; the main-session probe was answered by the fresh
session itself.

## Claim discipline (scope of this result)

Each row is a claim about **one context, one Claude Code version (2.1.220), one HEAD sha** — nothing
more. `not_observed != absent`. The three isolated child contexts (implementer, reviewer, scorer)
are the **load-bearing** rows; the main-session row is not a load-bearing isolated-dispatch
boundary. This run measures the **candidate** (post-refactor) surface only; it is not an A/B — the
comparison point is the `2026-07-22-baseline.md` run at Claude Code 2.1.217, a different client
version, so differences are not attributable to the prompt refactor alone.

## Headline finding

The escape-relevant direction is clean in **all four** contexts: a path-scoped rule that is merely
*referenced* by the dispatch (`rules/wave-parallelism.md`, `paths: ["specs/**/PLAN.md"]`), never
Read, and with no matching file read, is genuinely **absent** — `NOT IN CONTEXT` everywhere. The
refactored dispatch surface did not weaken the boundary that the #141 P1 escape lives on.

Two rows differ from `2026-07-22-baseline.md`:

- **main-session is no longer contaminated.** Running the probe in a fresh `claude -p` session
  instead of the orchestrator's own working context isolated the mechanism: reading a `specs/**`
  `SUMMARY.md` (not a `PLAN.md`) delivered `auto-correct-scope.md` and did **not** deliver
  `wave-parallelism.md`. That is the first clean observation of both directions in main, and it
  closes the baseline run's recorded methodological gap.
- **implementer positive is delivered but did not echo the marker verbatim.** See the row note.

## Results

### implementer-subagent (dispatched via `Agent(general-purpose)`, fresh context)

| Field | Positive | Negative |
|---|---|---|
| Probe | auto-correct-scope heading after explicit Read in dispatch | wave-parallelism heading, referenced-not-Read, fresh context |
| Expected | delivered (`# Auto-Correction Scope`) | not-delivered (`NOT IN CONTEXT`) |
| Observed | Did **not** quote the marker. Answered that the file "begins with `---` frontmatter" and argued there is no top-level heading. The file does carry `# Auto-Correction Scope` on line 6, after `paths:` frontmatter — but frontmatter presence is **not** guessable from the filename, so the answer is positive evidence the Read actually happened. | `NOT IN CONTEXT` |
| Verdict | **delivered** (delivery proven by non-guessable file content; the probe's echo instruction was answered pedantically rather than followed — see Follow-up) | **not-delivered** (expected) |
| `claude --version` | 2.1.220 | 2.1.220 |
| HEAD sha | dbdd2b7 | dbdd2b7 |

### reviewer-agent (dispatched via `subagent_type: reviewer`, read-only, fresh context)

| Field | Positive | Negative |
|---|---|---|
| Probe | auto-correct-scope heading after explicit Read in dispatch | wave-parallelism heading, referenced-not-Read, fresh context |
| Expected | delivered (`# Auto-Correction Scope`) | not-delivered (`NOT IN CONTEXT`) |
| Observed | `# Auto-Correction Scope` | `NOT IN CONTEXT` |
| Verdict | **delivered** | **not-delivered** (expected) |
| `claude --version` | 2.1.220 | 2.1.220 |
| HEAD sha | dbdd2b7 | dbdd2b7 |

### scorer-agent (dispatched to the cheap model `haiku`, fresh context)

| Field | Positive | Negative |
|---|---|---|
| Probe | auto-correct-scope heading after explicit Read in dispatch | wave-parallelism heading, referenced-not-Read, fresh context |
| Expected | delivered (`# Auto-Correction Scope`) | not-delivered (`NOT IN CONTEXT`) |
| Observed | `# Auto-Correction Scope` — but this heading is **guessable from the filename**, so a Read cannot be proven from the output alone. | `NOT IN CONTEXT` |
| Verdict | **unconfirmed** (cheap-model caution per README; same limitation as the 2026-07-22 run — the marker is still guessable, so the follow-up below is still open) | **not-delivered** (expected) |
| Model | haiku | haiku |
| `claude --version` | 2.1.220 | 2.1.220 |
| HEAD sha | dbdd2b7 | dbdd2b7 |

### main-session (fresh `claude -p` session, uncontaminated)

| Field | Positive | Negative |
|---|---|---|
| Probe | auto-correct-scope heading present after `specs/**` read | wave-parallelism heading absent (no PLAN.md read) |
| Expected | delivered (`# Auto-Correction Scope`) | not-delivered (`NOT IN CONTEXT`) |
| Observed | `# Auto-Correction Scope` after reading `specs/gh-143-context-propagation/SUMMARY.md` | `NOT IN CONTEXT` |
| Verdict | **delivered** | **not-delivered** (expected) |
| `claude --version` | 2.1.220 | 2.1.220 |
| HEAD sha | dbdd2b7 | dbdd2b7 |

## Limitations

- Single run per context, one model per context, one client version. No variance estimate.
- The **scorer positive stays `unconfirmed`** for the same reason as the baseline run: the marker
  heading is reconstructable from the filename. This is on the positive direction only and does not
  reopen the P1 class, whose escape-relevant direction is the negative control.
- Not an A/B. The pre-refactor comparison point (`2026-07-22-baseline.md`) ran on Claude Code
  2.1.217 against a different HEAD, so a row-level difference cannot be attributed to the prompt
  refactor alone.
- The probes measure delivery of two specific path-scoped rules. A rule or dispatch not probed here
  is **unmeasured**, not confirmed delivered.

## Addendum — path-scoped delivery DOES fire in a child context that reads a matching file

Run later the same day, in a disposable sandbox worktree (`/tmp/harness-sandbox-test`, harness
deployed, `bcdb68c`). This probe answers a question the four probes above structurally could not,
because each of them only ever tested a child that read **no** matching file.

**Question.** `rules/plan-format.md` is scoped `paths: ["specs/**/PLAN.md"]`. Does it reach an
isolated `general-purpose` subagent that **reads** a `specs/**/PLAN.md` file, with no Read
instruction for the rule itself?

**Marker.** Not a heading — headings here are reconstructable from filenames, the same weakness
that keeps the scorer positive `unconfirmed` above. The marker is the **cut-off date inside the
rule's legacy-XML paragraph** (`2026-07-16`), which is not guessable from the filename or topic.

| arm | reads `specs/**/PLAN.md`? | observed | verdict |
|---|---|---|---|
| read-planmd | yes (547 lines) | quoted `2026-07-16` correctly | **delivered** |
| control-no-read | no | `NOT IN CONTEXT` | **not-delivered** (expected) |

The single variable between arms is whether a matching file was read, and the control rules out
prior knowledge and filename guessing.

**Consequence for `probes/implementer-subagent.md`.** Its wording — "no path-scoped rule auto-loads
here; a rule arrives ONLY if the dispatch prompt explicitly instructs a Read" — is **too strong**
and should be narrowed to: *a path-scoped rule does not auto-load in a child context unless that
child reads a file matching the rule's glob.* The probes above remain valid; their negative
controls read no matching file, so they measured the referenced-but-unread case specifically.

**This does not reopen or weaken #141.** That escape had the isolated worker reading no `specs/**`
file at all, so the rule genuinely never arrived. The explicit-Read fix pattern in
`implementer-prompt.md` and `correctness-review/prompts/shared.md` remains the correct and more
robust construction — delivery that depends on a consumer happening to read a path-matching file is
fragile, and silently disappears if that consumer is later handed inline text instead of a path.

## Follow-up

- The scorer positive needs a **non-guessable marker** (e.g. a nonce line inside the rule body
  rather than its heading) before an explicit-Read positive can be proven on a cheap model. Still
  open from 2026-07-22.
- The implementer probe should say "quote the first `#` heading line, ignoring YAML frontmatter" —
  this run showed the current wording is answerable pedantically without echoing the marker, which
  costs the probe its clean signal even when delivery demonstrably occurred.
