# Watch a run live on the board

You run `/harness:autopilot` and want to see what the run does right now. The run board shows it in a
browser. It needs no install and no build.

## Steps

1. Open a second terminal in your project folder.
2. Start the board:

   ```
   node plugins/harness/board/board.js
   ```

3. Open `http://127.0.0.1:4317` in your browser.
4. Start the board before or during `/harness:autopilot`. Both work. The board shows the newest run of
   the project, and it switches to a newer run by itself.

## What you see

Each agent of the run appears when it starts and when it returns. You see its stage, its model and its
effort, and a short summary of what it returned.

## Options

- `--project <path>` watches a project other than the current folder.
- `--run <run id>` watches one named run.
- `--port <n>` uses a different port than 4317.
- `--no-follow` stays on the first run and does not switch to a newer one.

## One limit

The `log()` lines and the PR link appear only after the run ends. Claude Code writes them in one summary
file at the end, so the board cannot show them while the run is still going.
