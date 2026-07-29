# Plan-review sidecar

Use JSON with `base` provenance and `files`; each file has `path`, `status`, `dependents`,
`dependent_names`, `tests`, `risk`, and `note`. Include `flows` when known. The graph informs the
sidecar but does not replace inspection: unknown graph coverage remains unknown.
