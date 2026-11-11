# Run board at launch

`${CLAUDE_SKILL_DIR}/scripts/board-start.sh` starts the run board (`plugins/harness/board/board.js`) for the directory where
Claude Code was started, and opens it in a browser when a desktop is there. Details: `plugins/harness/board/README.md`.

- Run it with no `cd`, and with no arguments except `--stop`. It exits 0 and prints one line, always.
- A line that starts with `board: http://` or `board: already running at` holds the URL: give it to the owner.
- Any other line (`skipped`, `could not start`, `no display`) means the board is not shown: say so in one line and launch anyway.
- The board keeps running after the run. In the final report say how to stop it:
  `bash ${CLAUDE_SKILL_DIR}/scripts/board-start.sh --stop`.
- The board shows runs of the project in the current directory. If it shows no run while one is live, the project path
  differs from the one Claude Code writes under: tell the owner to start the board by hand with `--project <path>`.
