# Run board at launch

Step 8, just before the Workflow call: unless the profile sets `"board": false`, run
`node ${CLAUDE_SKILL_DIR}/scripts/open_board.js --idle-exit 30` from this session's working directory and
give the owner the URL it prints. The board reads the runs of the project whose folder started
this session, so do not pass a ticket worktree or the plugin folder as `--project`.

- It reuses a board that already runs for this project on port 4317. When another project's board holds
  the port, it starts one on a free port.
- The board it starts stops by itself 30 minutes after the run ends (`--idle-exit 30`).
- It opens the page in a browser on macOS, Windows and Linux with a desktop. It opens nothing in CI or
  when `HARNESS_BOARD_NO_OPEN=1`; then it prints the URL for the owner to open.
- It always exits 0. A board problem prints one line and never stops the launch: go on with the Workflow
  call.
- `"board": false` in the profile skips this step.

The board itself: `${CLAUDE_PLUGIN_ROOT}/board/README.md`.
