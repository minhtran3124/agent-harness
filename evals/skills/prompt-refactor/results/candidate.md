# Candidate live-evaluation status

Run date: 2026-07-28  
Environment: `cld-edgeful` (`CLAUDE_CONFIG_DIR=~/.claude-edgeful`), `claude-sonnet-5`, Claude
Code `2.1.220`, reasoning `low`, one clean no-tools session per observation.

## Current evidence

The historical baseline (`924af147e9721c0e09fb5d3f25a71e4465ea9b10`) and candidate have
matching passing golden-path observations for these eight skill families:

- `using-git-worktrees`
- `feature-intake`
- `finishing-a-development-branch`
- `intent-review`
- `subagent-driven-development`
- `visual-planner`
- `writing-plans`
- `xia2`

Eight early dispatches had response-collection or environment failures. Their original blocked
records are preserved in `invalid-collections.json`; they are not model observations and were
replaced only after `capture_skill_eval.py` saved a raw response for a valid clean dispatch.

This is partial evidence only. It does **not** satisfy Task 7.1's required activation, all-behavior,
review-chain, context-boundary, and end-to-end coverage, and it must not be used to claim quality
non-regression. The current candidate behavior collection covers all case IDs and passes the
explicit behavior gate (`python3 scripts/score_skill_eval.py --suite behavior --candidate`).
Baseline comparison, activation, review-chain, context-boundary, and end-to-end coverage remain
outstanding. The historical Edgeful baseline batch is currently blocked by the local profile being
logged out (`cld-edgeful auth status` reports `loggedIn: false`); no unauthenticated output is
treated as model evidence.
