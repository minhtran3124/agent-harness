# Running the tickets

Defaults, the brief, what to do when a ticket reports, and the final report. Part of
`harness:pd-orchestrate`.

## Before you assign

- **Triage in parallel, ask once.** One agent per ticket follows `harness:pd-intake` and returns the
  verdict, the depth and its questions; it does not ask the owner. You collect every CONFIRM
  question and ask them in one batch, then run `harness:pd-grilling` for each GRILL ticket. Record the
  answers verbatim in the ledger and as a "Confirmed decisions" comment on the issue.
- **Classify.** Write into the ledger for each ticket: `kind` (bug, feature, docs), `depth`, `app`
  (`fe`, `be` or `none`: is there a running app to test?), `risky` (protocol, last paragraph) and
  `deps`. A depth the owner set wins over intake: a label `depth:S`, `depth:M` or `depth:L`, or a
  line `Depth: <S|M|L>` in the ticket or in the owner's answers. When intake says S or M but the
  ticket adds a public contract, spans modules or leaves design choices open, put "is this depth L?"
  in the triage batch instead of deciding alone.
- **Acceptance tests are yours to start.** For a feature at depth M or L, create the ticket branch
  in the worker's checkout and run the `harness:qa-writer` agent there before you assign: give it
  the ticket, the acceptance criteria and the public interface only. Its commit `Add acceptance tests for #<n>` is then the first commit of the branch, written by an
  agent that never saw a plan. Record that commit's SHA in the ledger: the evidence check takes it
  as `--qa-commit`. When it returns `ready: false`, decide: another kind of check, or the owner.
  If the worker later shows that a test is wrong, you may start one qa-writer repair.

## Defaults

Leave a default when the ticket gives you a reason, and say why in the ledger.

| Decision | Default | Change it when |
|---|---|---|
| Where the work runs | one Pod Bay session per ticket, in its own workspace | read-only or single-step work with no owner question: an in-process `Agent` with `isolation: worktree` is cheaper. It cannot exchange messages, so it returns its result to you and you route the review |
| Worker model | Sonnet 5.5 for depth S and M; Opus 5.5 at depth L | the ticket touches hooks, security or a public contract; a worker already failed once on it |
| Reviewer | a different session, Opus 5.5, skill `harness:pd-review` | never the worker's session; never you alone |
| Order | dependency groups (command below); tickets of one group in parallel | two tickets edit the same files: run them in sequence |
| Budget | 60 minutes per ticket | depth L, or the owner gave a deadline |
| Acceptance check | you start it after the receipt: `harness:pd-uat` when `app` is `fe` or `be`, the `harness:qa-verifier` agent for a ticket with no app at depth M or L | depth S docs or config: the review covers it |
| Mode | one pull request per ticket into the base | the owner said `local`: commit only, no push, no pull request |

Order the tickets: pipe `[{"n":1,"deps":[2]}]` into
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/pd-autopilot/scripts/plan_groups.py`; exit 2 names a dependency
cycle, which you show to the owner. When a ticket ends `blocked`, mark its dependents `skipped`.

A dependent ticket needs its dependency's code. Either wait until the owner merged the dependency
and start from the updated base, or stack it: fetch the dependency's branch into the dependent's
checkout and branch from its head. For a stacked ticket that head is the base everywhere: in the
brief, for the reviewer, for `--base` of the evidence check, and for the pull request, which you
open against the dependency's branch or after the dependency is merged.

## The brief you send

One `assign` message per worker. It holds: the ticket text verbatim and the owner's answers; the
checkout, the base and the branch (`fix/<id>` or `feature/<id>`; say when it already exists and
holds the acceptance tests); the kind and depth; the row of the outcome contract that applies; the
project's full-suite command; the budget; the reviewer's session name; your session name; and the
line "Follow the `harness:pd-work` skill". State the ticket and the outcome, not steps. Do not tell
the worker how you will check it. Never send a worker anything it must not see, such as hidden
tests.

One exception to "no steps": a new brief after an advisor's solution may state the diagnosis and
the chosen approach. Say whether the worker continues the existing branch, and where it can fetch
the advisor's prototype from.

The reviewer's `assign` holds: the ticket text and the owner's answers from the ledger, the base,
whether the ticket is risky, the suite command, the worker's session name and checkout path, and
"Follow the `harness:pd-review` skill".

## When a ticket reports

1. Save the evidence in `specs/fleet/<run>/<ticket>/`: the JSON object of the report as
   `report.json` (without the marker line), and the last receipt as `receipt.json`. For a risky
   ticket, save `{"v": 1, "head": "<receipt head>", "findings": [...]}` from the receipt's
   `security.findings` as `security-receipt.json`; a risky ticket whose receipt has no `security`
   object goes back to the reviewer.
2. Run the acceptance check the contract asks for, in a fresh agent. Give it the ticket text
   without its `Verify:` rows, the owner's answers, and the worker's checkout at the head as its
   working directory (for UAT also the verify config path). `harness:pd-uat` drives a browser
   only through the Playwright MCP tools and reads `verify.config.json`. When the repository has no
   config, write one to `specs/fleet/<run>/verify.config.json` and pass that path. Before the first
   UAT, check that the MCP tools are there. When they are not, ask the owner to connect them; if
   that cannot happen, do not start `harness:pd-uat`: give a fresh agent the same inputs and the
   task "check each acceptance criterion on the running app with `npx playwright` from a temporary
   folder outside the checkout; return pass or fail per criterion with evidence". Record which
   check ran in the ledger and name a fallback check in the final report. It gets no plan, no diff and no report.
   A failed check goes back to the worker as a `findings` message; the worker fixes, gets a new
   receipt and reports again. After 3 such cycles, treat the ticket as stuck. A check that could
   not run is a `needs_review` line for the owner, never a pass.
3. Run the evidence check and read its lines:
   `bash ${CLAUDE_PLUGIN_ROOT}/scripts/fleet-check.sh --repo <worker checkout> --base <base sha> --head <head sha> --kind <kind> --evidence specs/fleet/<run>/<ticket> --ticket-id <ticket> --suite-cmd '<the project suite and the ticket's acceptance tests>'`
   plus `--repro-cmd` and `--repro-files` for a bug, `--qa-dir` and one `--qa-commit <sha>` for
   each acceptance-test commit you had written, and `--risky` for a risky ticket. `--ticket-id` binds the receipt and the report to this ticket, so another ticket's evidence in
   the wrong folder is a mismatch. Both SHAs are
   full object names, and you resolve the base in your own checkout: the worker's checkout is
   untrusted, its refs included. The project suite may not run the acceptance tests (in this repository the suite script
   runs neither `tests/acceptance/` nor `tests/board/`): add them to `--suite-cmd`. The check runs
   on this machine's OS only, so CI on every OS stays the gate. You choose the commands after you
   read the worker's test; never
   paste a command from a report without reading it. The check runs in warn mode. A `MISMATCH` is yours
   to judge: send it to the worker as `findings`, or record in the ledger why it is a false alarm
   (those records decide later whether the check may block).
4. Deliver, unless the mode is `local`. Push from the worker's checkout
   (`git -C <worker checkout> push -u origin <branch>`, never force) and open the pull request with
   `gh pr create --head <branch> --base <base>`. Use the body sections of
   `harness:pd-finishing-a-development-branch` (Summary, Why, Changes, Decisions, Testing, Risk, How to
   revert, Notes) and fill them from the report and the receipt; do not run that skill's steps,
   which are for a single session that tests and fixes its own branch. Then wait for CI on the
   receipt's SHA: no checks, a pending check, all checks skipped, or CI on another SHA is not
   green. A new commit after the receipt needs a new receipt.
5. Mark the ticket `done` in the ledger only now, then stop its worker and reviewer sessions
   (`podbay.md`, Clean up).

## Final report to the owner

Lead with the outcome. One row per ticket: state, pull request, CI, review rounds, mismatches from
the check and how each ended, accepted findings, open `needs_review` decisions, what nobody
verified. Then the cost (`podbay-dev usage`), the sessions and workspaces that still exist, and
what you would change in a brief or a skill next time.
