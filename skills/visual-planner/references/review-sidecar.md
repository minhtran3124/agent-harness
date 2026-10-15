# Plan-review sidecar

Use JSON with `base` provenance and `files`. Each file has `path`, `status`, `dependents`,
`dependent_names`, `tests`, `risk`, and `note`. Include `flows` when known. Evidence may come from
Grep/Read or an optional code-graph tool. The evidence informs the sidecar but does not replace
inspection: unknown coverage remains unknown.
