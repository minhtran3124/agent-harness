# gh-129-durable-run-state-phase-a — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-quality-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: intent-review (fresh subagent, blind to PLAN.md, model: opus)
- date: 2026-07-24
- trigger: ambiguous-direction
- question: Does "Add machine-readable event and projection schemas" (issue #129, Phase A scope) require a formal schema-validation artifact (e.g. a JSON Schema file under `schemas/` or similar), or is the shipped combination of a documented event/RUN.json shape (module docstring in `scripts/run_state.py`) plus a runtime `REQUIRED_EVENT_KEYS` presence check sufficient?
- context: `scripts/run_state.py` and its tests are implemented, spec-reviewed, correctness-reviewed (6 findings fixed), and intent-reviewed. This is the one open finding blocking a clean intent-review pass before handoff to `finishing-a-development-branch`.
- options:
  - A) Accept the current docstring + `REQUIRED_EVENT_KEYS` runtime check as satisfying "machine-readable schema" for Phase A — the contrast in the issue is JSON (machine-readable) vs. `specs/STATE.md` prose (human-only), not "informal schema" vs. "formal schema-validation artifact." No further work; proceed to finishing-a-development-branch.
  - B) Add a formal schema artifact (e.g. `specs/gh-129-durable-run-state-phase-a/schemas/event.schema.json` + `run.schema.json`, JSON Schema draft-07 or later) and optionally wire `jsonschema`-free stdlib validation against it in `read_events`/`read_json`. This is additional scope beyond what's currently built — would need its own task/verify row before shipping.
- default_if_no_response: BLOCK
- decision: A — docstring + `REQUIRED_EVENT_KEYS` runtime check is sufficient for Phase A. The issue's contrast is JSON (machine-readable) vs. `specs/STATE.md` prose (human-only), not "informal" vs. "formal schema-validation artifact." No further work; proceed to finishing-a-development-branch.
- decided_by: Minh Tran
- decided_at: 2026-07-24
