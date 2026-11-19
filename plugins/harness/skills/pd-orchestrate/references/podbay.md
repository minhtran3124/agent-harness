# Pod Bay for the orchestrator

Pod Bay runs Claude sessions in tmux, each in a checkout of a workspace `src` or `src-NN`. The CLI
on this machine may be `podbay` or `podbay-dev`. Before you rely on a subcommand or a flag, run it
with `--help`: the CLI changes between versions.

| Need | Command |
|---|---|
| Sessions and their state (idle, asks, attach target, links) | `podbay-dev ls` |
| Checkouts and workspaces | `podbay-dev checkouts` |
| A new workspace of clean clones | `podbay-dev ws-new <project>` (prints the new `src-NN`) |
| A session in a checkout | `podbay-dev start <project> <repo> --ws <src-NN> --trust` |
| Say what a session is for (shows in `ls`) | `podbay-dev describe <uuid> '<text>'` |
| Last prompt, reply and screen of a session | `podbay-dev detail '<session name>' --lines 30` |
| Tokens used by the sessions of this machine | `podbay-dev usage` |
| Stop a session (its conversation is kept) | `podbay-dev stop '<session name>'` |
| Delete a workspace | `podbay-dev ws-rm <project> <src-NN>`: only when the owner says so |

## Start a session for a role

1. Pick a workspace with no running session, or make one. One ticket per workspace; a reviewer or
   an advisor gets its own workspace too, so no session shares a working tree with another.
2. Start the session. Its name is in the output (`title`), and `attach` gives its tmux target.
3. Set the model: type `/model <model id>` into the session
   (`tmux send-keys -t '<tmux target>:' '/model <model id>' Enter`), then read the status line with
   `podbay-dev detail` and confirm the model name. A session keeps its default model otherwise.
4. Keep every session of a run in the same permission mode as yours. A session in another mode
   holds your messages until its user approves them. Workers, reviewers and advisors run tests and
   other project commands: in a mode that prompts for each one, they stop at every prompt, so tell
   the owner before the run when your mode is not auto.
5. Send the brief with `SendMessage` to the session's name (`ListAgents` lists the live names) and
   `notify_when_idle: true`. Record the session in the ledger.

## Wait

- One idle notice arrives for each `notify_when_idle` send. Do other work until then; if there is
  none, yield. Never loop on `ls` or `detail`.
- Look at a session with `detail` only when it is silent past its budget, or an idle notice came
  with no message from it.
- What you may see, and what it means:

| Screen | Meaning | Do |
|---|---|---|
| a permission prompt | the session waits for a human | tell the owner which session and which command; do not answer the prompt for them |
| an `AskUserQuestion` dialog | the session asks the owner | tell the owner; it is their answer |
| "held for approval" on your send | permission modes differ | restart the session in your mode, or ask the owner |
| an idle prompt, no report | the agent stopped early | send one message that asks for the report or the blocker |
| a usage-limit line | the account is out of quota | stop assigning; tell the owner when it resets |

## Clean up

Stop a ticket's worker and reviewer only when the ticket is `done`, `blocked` or `skipped`: a
failed acceptance check reopens it. `podbay-dev start ... --resume latest` brings a stopped
session back with its conversation. Leave workspaces in place and list
them in your final report; the owner decides when they go. `ws-rm` refuses a workspace with work
that is not pushed.
