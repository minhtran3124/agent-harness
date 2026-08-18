# Research-depth policy

This is the canonical policy for xia2 research depth. Intake owns risk classification; when an
intake record exists, map `high-risk` to **Deep**, `normal` to **Standard**, and permit **Quick**
only for a `tiny` lane that satisfies every Quick condition below. Research may move up on evidence
but never down. In the absence of intake, use the portable classifier.

## Portable classifier

Choose **Deep** if any condition applies: migration/schema or data-loss work; a high-blast file;
a new external integration or runtime dependency; a shared runtime configuration contract; or an
auth/session/transaction-scope change.

Choose **Quick** only if no Deep signal applies, at most one file changes, no new public callable
is added in a shared module, there is no new dependency or public API contract, and no entry point
is involved. Otherwise choose **Standard**. If a signal is uncertain, choose Standard.

Signals can be explicit or implicit. Common portable evidence includes dependency manifests,
`migrations/`/`alembic/`, DDL SQL, API schemas/routes, auth-related identifiers, CI/config/hooks,
and shared configuration read by many modules. Urgency and prompt brevity never lower depth.

## Coverage

External sources are required by **surface**, not by depth alone. A change has an *external
surface* when it adds or upgrades a dependency, integrates an external system, or relies on a
version-specific API. Depth sets how broadly to look; surface sets whether to look outside.

- Quick: local artifact and reuse search.
- Standard: Quick coverage plus upstream patterns, and version-matched official documentation
  when the change has an external surface.
- Deep: broad local mapping and explicit risk analysis, and — when an external surface exists —
  multiple upstream sources and changelogs.

When no external surface exists, record it in `research-brief.md` under Source Pack as
`- none (local-only; no external surface)`. Silence is not the same as "none": an empty Source
Pack cannot be distinguished from research that was skipped, which is how a Deep declaration
comes to mean nothing.

Document the selected depth and any later upgrade in `research-brief.md`.
