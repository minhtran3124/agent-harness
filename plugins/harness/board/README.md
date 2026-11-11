# Agent Flow Board

A live view of one `ship.js` (autopilot) run: which agent runs now, with which model and effort, what each
step returned, and where the run waits for you. One Node file, no dependencies, no build.

![The board on a finished real run](../../../docs/images/board/board-completed-light.png)

More shots of real runs (dark theme, a killed run) are in `docs/images/board/`.

```
node plugins/harness/board/board.js                    # newest run of the project in the current directory
node plugins/harness/board/board.js --project ~/code/app
node plugins/harness/board/board.js --run wf_596bd115-74c
```

Then open `http://127.0.0.1:4317`. Start the board before or during `/harness:autopilot`; it switches to a
newer run of the same project by itself (`--no-follow` keeps the first one). It works for any project
that runs `ship.js`, because it only needs the project path.

## Embed it in another page

- `?embed=1` hides the board's own header and footer note and makes the background transparent, so a host
  page (such as a local dashboard) can show the board in an `<iframe>`. `?theme=light|dark` follows the host's theme.
- In embed mode the page posts `{type: 'afb-height', height}` to its parent when its height changes, so the
  host can size the iframe without an inner scroll bar. It sends nothing else.
- The page loads `flow.json` and `events` with relative URLs. A reverse proxy can serve the board under a
  path such as `/board/<project>/` (note the final `/`); the board itself still binds `127.0.0.1` only.

## Where the data comes from

Claude Code writes these files for every Workflow run. The board reads them and nothing else:

| File | What the board takes |
|---|---|
| `~/.claude/projects/<project>/<session>/subagents/workflows/<run id>/journal.jsonl` | one `started` and one `result` line per agent: label, phase, status, the agent's short summary, check rows |
| `.../<run id>/agent-<id>.jsonl` | first and last timestamp, `message.model`, `effort` |
| `~/.claude/projects/<project>/<session>/workflows/<run id>.json` | written once at the end: run status, final PR, the `log()` lines |

`<project>` is the project path with every character outside `A-Z a-z 0-9` replaced by `-`.

The server polls these files every 500 ms and pushes new events to the page with Server-Sent Events.
`flow.json` maps the stage part of each agent label (`#321 QA check fix r2 · title` → `QA check fix`) to a
box. A stage that matches no box still shows in the event log. Edit `flow.json` to change the diagram.

## Privacy

The server binds `127.0.0.1` only. It sends labels, phases, statuses, models, efforts, times, check row
counts and the agent's own summary (cut to 200 characters). It never sends prompts, tool calls or file
contents from the transcripts.

## Limits

- Verifies: each agent of the run appears when it starts and when it returns, within about one poll interval.
- Does not verify: `log()` lines and `phase()` calls, because Claude Code writes them only in the summary
  at the end of the run; runs of local mode, which skip the UAT phase.
- The file layout belongs to Claude Code and is not a public contract. If it changes, the board shows
  "No ship.js run found" or no model; `tests/board/board.test.js` pins the format the board expects.
- A check box shows its first result. When a fix round then passes, the Re-check box turns green and the
  summary's Check phase says Passed; the first check stays red, on purpose, so the failure stays visible.
- A box shows the latest agent of its stage; the caption counts all agents of the box (`2 agents`; the UAT / QA check box also holds `fetch owner request`).
- After the run ends, a box that never ran says `Not run`, and a check stopped by the end of the run makes the Check phase `Stopped`.
- The setup agent (`check plugin and tools`) has no box; it shows only in the event log.
- A killed run has no PR link on the board: Claude Code writes `result: null` in its summary, so the PR
  number is not in any file the board reads.

Tests: `bash tests/scripts/board.test.sh`.
