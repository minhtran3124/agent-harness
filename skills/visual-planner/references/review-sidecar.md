# Plan-review sidecar

Use JSON with `base` provenance and `files`; each file has `path`, `status`, `dependents`,
`dependent_names`, `tests`, `risk`, and `note`. Include `flows` when known. Evidence may come from
Grep/Read or an optional code-graph tool; it informs the sidecar but does not replace inspection:
unknown coverage remains unknown.
