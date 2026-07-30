<!--
  Escalation channel. Copy to specs/<slug>/ESCALATIONS.md.
  Default is DENY-ON-NO-RESPONSE: if `decision:` stays `pending`, the work stays BLOCKED.
  The agent appends an escalation block and stops; a human appends the decision.
-->

# require-claude-simplify-gate — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-quality-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: agent (Wave 2 continuation)
- date: 2026-07-30
- trigger: hard-gate
- question: Should the shadow-eval sandbox profile in `scripts/run_simplify_stage_eval.py` (`_sandbox_profile()`) be widened to allow filesystem writes/reads under `/tmp/claude-<uid>/`, an undocumented Claude Code internal path that the Bash tool requires to function at all — and if so, how narrowly?
- context: Task 2.1 (run the pinned shadow candidate). After fixing the relative-path bug (commit `0eb1287`) and the `~/.claude/session-env` EPERM (commit `8c51780`, via `CLAUDE_CONFIG_DIR`), a real candidate run still fails on every fixture's first Bash tool call with:
  ```
  EPERM: operation not permitted, mkdir '/private/tmp/claude-501/-private-var-folders-...-worktree'
  ```
  This is a second, distinct hardcoded scratch path (`/tmp/claude-<uid>/<dashed-absolute-cwd>/`) that the Bash tool writes to on every invocation — confirmed it does **not** honor `$TMPDIR` (already set to a sandbox-writable dir; the mkdir still targeted real `/tmp`). I independently verified (own empirical test, plus a `claude-code-guide` docs sweep) that **no documented environment variable, CLI flag, or setting redirects this path** in Claude Code 2.1.x — unlike `~/.claude`, which `CLAUDE_CONFIG_DIR` cleanly relocates. Without an exception, the Bash tool cannot run a single command inside the sandbox, so candidate collection cannot proceed at all.

  This blocks: Task 2.1's real candidate run (`evals/skills/simplify-stage/results/candidate.json`), and therefore SC-8/SC-9 and every downstream wave (3–6) that the plan gates on a passing shadow-eval quality/value verdict.

  First raw evidence from the pre-`CLAUDE_CONFIG_DIR` run is preserved (not deleted) as:
  - `evals/skills/simplify-stage/results/candidate-rejected-sandbox-session-env-eperm.json`
  - `evals/skills/simplify-stage/results/artifacts/candidate-rejected-sandbox-session-env-eperm/`
  - `evals/skills/simplify-stage/results/transcripts/candidate-rejected-sandbox-session-env-eperm/`

  No new candidate.json/artifacts have been written for this second failure mode (only reproduced via a throwaway smoke test outside the immutable-output contract, so nothing to preserve there).

- options:
  - A) **Allow the exact computed literal path** — derive `/tmp/claude-<uid>/<dashed(worktree)>` from `worktree` (string-replace `/`→`-`, matching the observed pattern) and add it as an extra allowed_root (read+write) in `_sandbox_profile()`, scoped per-run since each `worktree` is a fresh random tempdir. Narrowest possible exception, but relies on reverse-engineering an undocumented internal naming scheme that could silently change in any point release, breaking the eval invisibly (mkdir would then fail again with the same opaque EPERM, or worse, resolve to an unintended path if the scheme changes shape rather than just breaking).
  - B) **Allow the whole `/tmp/claude-<uid>/` tree** — coarser, more resilient to internal path-shape changes, but this is a per-uid directory Claude Code may use across *all* concurrent sessions on this machine (multiple real `claude` processes are running right now per `ps aux`), so it widens the sandboxed candidate's read/write reach beyond this eval run's own scratch space — a real (if hard to characterize) cross-session exposure, and a genuine loosening of the previously audited "home/.claude/Keychain unreachable" sandbox contract's spirit even though `/tmp` itself isn't literally in that list.
  - C) **Do not widen the sandbox; treat "real Claude Code candidate collection in a Seatbelt sandbox" as currently infeasible** on this OS/client-version combination, and either (i) fall back to a weaker isolation strategy (e.g. a disposable per-run macOS user account, a Linux container/VM, or dropping the sandbox requirement and relying solely on the disposable git worktree + `--dangerously-skip-permissions` scope for isolation), or (ii) hold Task 2.1 open and keep the hard-gate rollout (Waves 3–6) blocked until Anthropic ships a documented override (a feature request was already effectively identified during investigation: something analogous to `CLAUDE_CONFIG_DIR` but for this Bash-tool scratch path).
- default_if_no_response: BLOCK
- decision: B — allow the whole `/tmp/claude-<uid>/` tree (read+write) in `_sandbox_profile()`, accepting the coarser, more version-resilient exception over the narrower literal-path option
- decided_by: Minh Tran
- decided_at: 2026-07-30

<!-- copy the E0xx block for each new escalation -->
