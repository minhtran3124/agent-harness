# intent-md-entry — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: feature-intake (orchestrator)
- date: 2026-10-10
- trigger: system-redefinition
- question: Which scope edges are in this change — an authoring helper that drafts intent.md with the author, and shipping the intent template to consumer repos?
- context: high-risk lane with medium confidence; brainstorming cannot start until scope is fixed.
- options:
  - A) Template + intake/intent-review support only, in this repo and shipped to consumers; no authoring helper yet
  - B) A plus an authoring helper (Claude interviews the author, writes intent.md as draft)
  - C) This repo only; no consumer shipping, no authoring helper
- default_if_no_response: BLOCK
- decision: A — template + feature-intake/intent-review support, shipped to consumer repos; no authoring helper in this change
- decided_by: Minh Tran (user, via AskUserQuestion in session)
- decided_at: 2026-10-10
