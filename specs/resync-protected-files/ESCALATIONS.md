<!--
  Escalation channel. Copy to specs/<slug>/ESCALATIONS.md.
  Default is DENY-ON-NO-RESPONSE: if `decision:` stays `pending`, the work stays BLOCKED.
  The agent appends an escalation block and stops; a human appends the decision.
-->

# resync-protected-files — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.

---

## E001

- raised_by: agent (Task 1.5)
- date: 2026-07-09
- trigger: system-redefinition
- question: Should `scripts/bookkeeping.sh`'s minor-vs-patch regex be widened to cover `scripts/` (specifically `deploy-harness.sh` / `install-harness.sh`), or should this PR ship as a patch bump with a follow-up filed?
- context: `CHANGELOG.md` (lines 4-6) documents the bump rule in prose: "**patch** for fixes/docs, **minor** for a new skill/hook or a changed skill/hook contract, **major** for a breaking change to the workflow or a machine-read schema." `scripts/bookkeeping.sh` line 76 implements this as `grep -qE '^(hooks/|settings\.json|skills/)'` — it does not match `scripts/`. This PR (`feat/resync-protected-files`) changes `scripts/deploy-harness.sh` and `scripts/install-harness.sh` — the deploy/install engine every consuming project runs — adding new flags (`--overwrite-conflicts`, restructured `--dry-run` wiring) and new conflict behavior (protected-file keep/overwrite/backup policy, `.harness-incoming` sidecars). That is a changed *tool* contract in the same sense the CHANGELOG rule already treats a changed skill/hook contract as minor-worthy, but the regex has no `scripts/` branch, so the post-merge automation (`.github/workflows/post-merge-maintenance.yml` → `scripts/bookkeeping.sh`) will classify this merge as a **patch** bump, not minor. Confirmed against the current `VERSION` file (`0.8.1`): under today's regex this PR bumps to **0.8.2** (patch); if `scripts/` (or just `scripts/deploy-harness.sh`/`scripts/install-harness.sh`) were added to the minor-match branch, the same merge would bump to **0.9.0** (minor) instead. Widening the regex is itself a change to the versioning contract — a documented ESCALATE-worthy "redefine the system" action per `rules/orchestration.md` — and is out of scope for this PR per its own task list (Task 1.4 explicitly forbids touching `VERSION`/`CHANGELOG.md` in-PR; this task, 1.5, forbids touching `bookkeeping.sh`). `tests/scripts/bookkeeping.test.sh` exists and currently pins the `hooks/`/`skills/` minor-match cases (e.g. lines 35, 59-61) — widening the regex would need a companion test update there, not just a one-line script edit.
- options:
  - A) Accept the patch bump (0.8.1 → 0.8.2) for this PR as-is; file a follow-up issue/PR to widen `scripts/bookkeeping.sh`'s minor-match regex (own lane, own tests/scripts/bookkeeping.test.sh update, own CHANGELOG/VERSION semantics review) so future deploy/install-engine contract changes are correctly classified as minor.
  - B) Widen the regex now (e.g. add `scripts/deploy-harness.sh` or `scripts/install-harness.sh`, or a broader `scripts/` prefix) so this merge bumps to 0.9.0 (minor) instead. Requires: editing `scripts/bookkeeping.sh` line 76, updating `tests/scripts/bookkeeping.test.sh` to cover the new prefix, and its own risk lane/review — this is a versioning-contract change, not a docs or resync-guard change, so it does not belong inside this PR's diff without a separate decision.
- default_if_no_response: BLOCK (take option A by default — do not widen the regex, do not touch `bookkeeping.sh`/`VERSION`/`CHANGELOG.md` in this PR)
- decision: A — accept the patch bump for that PR (long since shipped as such); widening `scripts/bookkeeping.sh`'s minor-match regex to cover the deploy/install engine is a separate follow-up with its own tests and lane, tracked under issue #67 follow-ups.
- decided_by: Minh Tran (recorded by agent per explicit instruction, 2026-07-16 session)
- decided_at: 2026-07-16

<!-- copy the E0xx block for each new escalation -->
