# Deep Research/Review: Phase 0 — Runtime Contract and Discovery

> **Date:** 2026-07-21  
> **Status:** Research / design review, not yet implemented  
> **Parent:** [`docs/research/harness-review-improvements/research-local-runtime-for-agentic-debugging.md`](research-local-runtime-for-agentic-debugging.md)

## 1. Executive summary

Phase 0 should not be seen as "adding a YAML file to hold a few commands". It is about defining a **safety contract between the project, the harness, the runtime adapter, and the AI agent**.

Recommendations after review:

1. Separate the three data layers: declared contract, discovery report, and resolved runtime model.
2. Discovery only produces candidates and warnings; it does not grant itself mutation permission.
3. Use the logical service name as the stable layer; mapping down to a Docker Compose service is an implementation detail.
4. Do not let the contract contain arbitrary shell commands in Phase 0. The contract references semantic operations and registered test targets.
5. Resolve Docker Compose using the Compose CLI itself (`docker compose config --format json`); do not rewrite a Compose parser. That command renders the canonical model, merges files, and resolves interpolation. [Compose config reference](https://docs.docker.com/reference/cli/docker/compose/config/)
6. `.harness/runtime.yaml` is good for UX, but the parser strategy must be settled before writing code. If you want to stay stdlib-only like `harness-manifest.json`, JSON is the simpler choice.
7. Phase 0 is only complete when discovery is deterministic, with provenance, conflict handling, secret-safe output, and fixture tests.

## 2. Questions Phase 0 must answer

| Question | Required result |
|---|---|
| Which runtime is in use? | `docker-compose`, `native`, `unknown` |
| Where is the source of truth? | specific path and hash |
| What is the project identity? | root, project name, environment label |
| Which services exist? | logical name, runtime name, profile, state |
| Which services may the agent observe? | explicit capability |
| Which services may be mutated? | allowlist and approval policy |
| How do we know a service is ready? | healthcheck/readiness or `unknown` |
| Which test/smoke checks can run? | registered target and provenance |
| What is still unknown? | warnings, conflicts, unsupported features |

Successful discovery does not mean the runtime is safe to control; it only means the harness understands enough context to decide the next step.

## 3. Boundaries and terminology

### Declared contract

A file committed by the project owner, e.g. `.harness/runtime.yaml`. It declares runtime kind, Compose files/profile/project name, logical services, healthchecks, verification targets, policy, and redaction rules. The contract can be outdated, so it must be cross-checked against the actual runtime.

### Discovery

A read-only process that finds evidence from the filesystem and runtime CLI: Compose files, manifests, process listeners, Compose project/service list, health metadata, and test runner declarations. Discovery output is not an instruction and is not automatically a permission.

### Resolved runtime model

The canonical model combining the contract, discovered evidence, and runtime state. Only a validated model may be handed to the runtime adapter.

```text
declared contract + discovery + runtime observation
              │
              ▼
validation + precedence + conflict handling
              │
              ▼
resolved model → read-only capabilities / gated mutations
```

### Logical service and runtime service

`api` is a logical service. It may map to the Compose service `backend`, the native process `uvicorn`, or a Make target. The agent uses the logical name; the adapter holds the runtime-specific mapping.

### Configuration and runtime state

Configuration says how the runtime should be controlled. State says what the runtime currently looks like. Never write runtime state back into the contract.

## 4. Docker Compose constraints

### Multiple files and the project model

Compose has `compose.yaml`, `compose.yml`, override files, `-f`, `COMPOSE_FILE`, profiles, `include`, and `extends`. Multiple files are merged in order; paths in the merged model are resolved relative to the base file. [Application model](https://docs.docker.com/compose/intro/compose-application-model/), [merge files](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)

Discovery must record:

```text
selected compose files
selection source
project directory
env-file selection
active profiles
project name
resolved model hash
```

It is not safe enough to just find `compose.yaml` and then parse the services list.

### Interpolation and environment

Compose supports `${VAR}`, default/required expressions, and `$$`; interpolation happens before merge, per file. Unresolved variables can produce warnings and become empty strings. [Interpolation](https://docs.docker.com/reference/compose-file/interpolation/)

`.env`, the shell environment, `--env-file`, `environment`, `env_file`, and the CLI all have different precedence. [Environment precedence](https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/)

Consequences:

- the model on disk is not necessarily the model the runtime sees;
- raw `docker compose config` may contain secrets;
- discovery must use the canonical Compose model but redact before returning it to the model or storing an artifact.

### Project name and isolation

The project name affects container/resource names and isolation. Precedence covers `-p`, `COMPOSE_PROJECT_NAME`, the top-level `name`, the directory containing the Compose file, and the current directory. [Project name](https://docs.docker.com/compose/how-tos/project-name/)

Worktrees/branches can collide if the directory basename is used. Phase 0 must report the project name and warn if the identity is unstable; do not change the name without an explicit policy.

### Profiles and the active graph

A service with a profile may not be active. A service targeted directly can activate a profile; a dependency between incompatible profiles can make the model invalid. [Profiles](https://docs.docker.com/reference/compose-file/profiles/)

The report must distinguish:

```text
declared service: debug-ui
profile: debug
active now: false
available with profile=debug: true
capability: observe=false until explicitly selected
```

### Healthcheck and readiness

A Compose healthcheck is the command that determines container health; `depends_on: condition: service_healthy` can wait for a dependency to be healthy. But container health is not necessarily business readiness. [Compose services](https://docs.docker.com/reference/compose-file/services/), [Compose specification](https://compose-spec.github.io/compose-spec/spec.html)

The contract should distinguish:

```text
container_health → Docker health status
service_ready    → service-level readiness
application_smoke → HTTP/CLI business check
```

If only container health exists, the output must record `readiness_level: container` and must not call it application healthy.

### Canonical resolution

`docker compose config --format json` is the source of the resolved model: it merges files, resolves variables, and expands short notation. The adapter should not reimplement Compose merge/interpolation with regexes or a bespoke parser.

## 5. Contract design review

### Option A — Arbitrary command

```yaml
services:
  api:
    logs:
      command: docker compose logs api
    test:
      command: docker compose exec api pytest
```

Flexible, but it turns config into a shell execution surface; hard to allowlist, easy to inject into, hard to port to a native runtime. **Not recommended for v1.**

### Option B — Semantic targets

```yaml
services:
  api:
    runtime_name: api
    observe: true
    health:
      probes:
        - id: http-health
          type: http
          url: http://127.0.0.1:8000/health
          expected_status: 200
    verification:
      - id: auth-tests
        runner: pytest
        selector: tests/auth/
```

The adapter picks a safe command for status/logs/health/verify. Portable, validatable, and easy to grant capabilities for; the tradeoff is that edge cases need extensions. **Recommended for v1.**

### Option C — Semantic core + gated custom operations

Allow custom operations only when there is a stable id, `read_only`, timeout/output limits, an argv array instead of a shell string, approval for mutations, and fixture tests. **Suitable after the MVP, not as the default.**

## 6. YAML or JSON?

### YAML

Easy to read, fits DevOps config, supports comments; but it needs a parser dependency and requires controlling duplicate keys, aliases, anchors, and implicit typing.

### JSON

Stdlib parser, less ambiguous semantics, fits the current tooling and `harness-manifest.json`; but it is verbose and has no native comments.

JSON Schema 2020-12 is the current meta-schema, but JSON Schema does not parse YAML by itself; these are two different concerns. [JSON Schema specification](https://json-schema.org/specification)

### Recommendation

Settle the parser strategy before implementing. If you do not want to add a dependency to the harness, use JSON. If you keep `.harness/runtime.yaml`, you must document the parser, its version, duplicate-key behavior, and the test contract.

## 7. Proposed contract v1

```yaml
version: 1
runtime:
  kind: docker-compose
  compose:
    files: [compose.yaml, compose.override.yaml]
    project_directory: .
    project_name: null
    profiles: []

services:
  api:
    runtime_name: api
    role: application
    observe: true
    mutate: false
    health:
      container: true
      probes:
        - id: http-health
          type: http
          url: http://127.0.0.1:8000/health
          expected_status: 200
          timeout: 5s
    verification:
      - id: unit
        runner: pytest
        selector: tests/api/
        read_only: true

policies:
  default_capability: observe
  allow_restart: [api]
  approval_required: [exec, start, stop, database-mutation]
  limits:
    log_lines: 500
    output_bytes: 200000
    command_timeout: 60s

redaction:
  env_names: ['*TOKEN*', '*PASSWORD*', '*SECRET*', '*PRIVATE_KEY*']
```

Schema rules:

- `version` is required and only known versions are accepted;
- runtime kind is an enum; `unknown` is only a discovery state, not an adapter;
- paths are relative to the root/project directory; reject escapes such as `../../prod`;
- service names and runtime names must not contain shell metacharacters;
- HTTP probes are local scope only in the MVP;
- a selector must not become a raw shell string;
- `mutate: true` does not bypass approval;
- limits have upper bounds;
- unknown keys must be rejected or live under an explicit `extensions`, never silently ignored.

## 8. Precedence and conflict handling

Proposed order from authoritative to heuristic:

1. Explicit invocation flags.
2. Committed runtime contract.
3. Canonical Compose model.
4. Runtime observation.
5. Repository conventions.
6. Filename/script heuristics.

Rules:

- the contract confirms the intended mapping, not that a service is currently healthy;
- the runtime model confirms that a service exists, it does not grant mutation permission;
- heuristics only produce candidates;
- a conflict between an explicit contract and the runtime is `error` or `needs_review`, never a silent override;
- a missing signal is `unknown`, not `false`.

Examples:

```text
contract: api -> backend
compose services: [api, db]
result: error — declared runtime_name backend not found
```

```text
contract: api.observe = true
runtime: api container absent
result: capability observe=true, state=absent
```

## 9. Discovery algorithm

### Step 0 — Root

- take an explicit root;
- canonicalize the path and symlinks;
- reject `/`, home, or broad unsafe targets;
- confirm a `.git`/project marker;
- do not scan parents outside scope unless enabled.

### Step 1 — Contract

- look for `.harness/runtime.yaml` or `.harness/runtime.json`;
- if both exist and there is no precedence rule, fail;
- parse, schema-validate, and record source/hash/parser version.

### Step 2 — Candidates

Deterministic order: explicit contract → `compose.yaml` → `compose.yml` → `docker-compose.yml` → `docker-compose.yaml` → known native manifests/scripts → unknown. Do not scan every YAML file, since Kubernetes/CI fixtures could be mistaken for Compose.

### Step 3 — Resolve Compose

- take the file list from the contract or explicit invocation;
- resolve project directory/profile/env policy;
- run `docker compose ... config --format json`;
- capture exit code, stderr warnings, Compose version, and model hash;
- do not store expanded secret values;
- separate declared, active, and profile services.

### Step 4 — Observe state

- `docker compose ps --all --format json` when available;
- a fallback parser only when needed, and it must warn;
- collect health/status/restart count;
- do not run `logs --follow` during discovery;
- logs only tail a bounded sample when the caller requests it.

### Step 5 — Map services

- explicit mapping beats heuristics;
- an exact name match is high confidence but still records provenance;
- role guesses (`api`, `web`, `db`, `worker`) are only candidates;
- ambiguous mapping is `needs_review`;
- an inactive profile is not running/usable.

### Step 6 — Emit

```text
discovery-report.json  # evidence, warnings, candidates, provenance
resolved-runtime.json  # validated model and gated capabilities
```

Resolved output must not contain raw environment, tokens, secrets, or a full unredacted config.

## 10. Confidence and provenance

Every fact needs a source, method, confidence, and timestamp:

```json
{
  "value": "api",
  "source": ".harness/runtime.yaml:services.api.runtime_name",
  "method": "explicit",
  "confidence": 1.0,
  "observed_at": "2026-07-21T10:00:00Z"
}
```

Confidence only helps orchestration, it does not grant permission by itself:

| Signal | Confidence | Use |
|---|---:|---|
| explicit contract | 1.0 | use after schema/policy validation |
| exact runtime match | 0.9 | read-only; mutation still needs policy |
| role heuristic | 0.6 | suggestion / needs review |
| filename/script guess | <0.6 | not executable |

"Not observable" must be `unknown`; the absence of a result does not prove "does not exist".

## 11. Capability model

Do not map `observe: true` to a general-purpose shell. Capabilities should be granular:

```text
service.api.logs
service.api.status
service.api.healthcheck
service.api.exec.readonly
service.api.restart
project.start
project.stop
project.database_mutation
```

Each capability has a subject, operation, read-only/mutating flag, source, approval, timeout/output limit, and audit requirement. The default should be observe-only; `down -v` and volume/database destruction are hard-blocked in the MVP.

## 12. Environment and secret handling

Do not send raw `docker compose config`, do not run `docker compose exec env` by default, and do not put `.env` contents into the report. Emit only variable names/presence markers when needed, mask values, and support project redaction patterns. Docker likewise recommends caution with sensitive data in the environment and suggests considering Secrets. [Environment best practices](https://docs.docker.com/compose/how-tos/environment-variables/best-practices/)

Redaction must be tested against all of:

- `TOKEN`, `PASSWORD`, `SECRET`, `PRIVATE_KEY`;
- URLs containing credentials;
- JSON log fields;
- multiline private keys;
- ANSI/control characters;
- secrets split across multiple lines.

## 13. Native process discovery

The native adapter is a later phase; Phase 0 only reports candidates from `package.json`, `pyproject.toml`, `Makefile`, `Procfile`, README, and listening ports.

A script named `dev` is not automatically a safe start command:

```text
candidate: npm run dev
source: package.json:scripts.dev
confidence: 0.8
executable: false
reason: no explicit runtime contract permission
```

A native runtime also involves process groups, child processes, signal forwarding, port collisions, PID reuse, cwd, environment, TTY, and cleanup. That is why processes are not auto-started in Phase 0.

## 14. Failure modes

| Failure | Required behavior |
|---|---|
| No contract found | `unknown`, no mutation |
| Both YAML and JSON present | fail validation |
| Compose invalid | stop before capability issuance |
| Missing required env | preserve warning/error |
| Service mapping mismatch | hard validation error |
| Multiple Compose candidates | `needs_review` |
| Profile inactive | `inactive`, no readiness claim |
| Healthcheck missing | `readiness=unknown` |
| Project-name collision risk | warning or explicit name required |
| Secret in output | redact + audit |
| Unsupported Compose feature | fail closed for mutation |
| Docker unavailable | config discovery may pass; state unknown |

## 15. Testing strategy

### Schema tests

Test a minimal valid contract, every runtime kind, unknown version/key, path traversal, invalid service name, invalid URL scope, invalid limits, and mutation missing approval.

### Discovery fixtures

| Fixture | Expected result |
|---|---|
| only `compose.yaml` | one deterministic candidate |
| base + override | correct selected files and provenance |
| profiles | inactive services are not healthy |
| explicit mapping mismatch | validation error |
| exact mapping | high-confidence mapping |
| ambiguous api/backend | needs review |
| missing `.env` variable | warning/error preserved |
| secret-like values | redacted output |
| invalid Compose | no executable model |
| Docker unavailable | runtime state unknown |
| native-only repo | candidate report, no auto-start |

### Golden output

Snapshot the normalized model; do not snapshot container IDs, timestamps, log order, or other volatile fields. Separate the deterministic model, volatile observation, and invocation metadata.

### Drift tests

CI should check that every schema version has a parser, every verification runner has an adapter, every service mapping exists in the canonical model, docs/schema do not drift, and fixture secrets do not leak into the output.

## 16. Discovery observability

The report must explain why a given model was chosen:

```json
{
  "schema_version": 1,
  "runtime_kind": "docker-compose",
  "sources": [
    {"path": ".harness/runtime.yaml", "kind": "declared", "sha256": "..."},
    {"path": "compose.yaml", "kind": "compose-input", "sha256": "..."}
  ],
  "decisions": [
    {"field": "services.api.runtime_name", "value": "api", "source": "explicit", "confidence": 1.0}
  ],
  "warnings": [],
  "capabilities": [],
  "redactions": {"count": 3}
}
```

The agent must know the model's source, age, confidence, and warnings; it must not receive an opaque model.

## 17. Decisions to settle before coding

1. **File format:** JSON if zero dependencies is the priority; YAML if the parser policy is documented clearly.
2. **Raw commands:** not in core v1; semantic targets first.
3. **Authority:** explicit contract > canonical model > runtime state > convention > heuristic.
4. **Compose parsing:** delegate to `docker compose config --format json`.
5. **Scope:** Compose discovery/model first; native only reports candidates.
6. **Capability:** observe-only by default; mutation explicit + audited; `down -v` hard-blocked.
7. **Evidence:** `specs/<slug>/runtime/` when attached to a task; no secrets; generated output does not replace the contract.

## 18. Proposed deliverables

```text
.harness/runtime.schema.json       # or an equivalent schema
scripts/runtime-discover.py        # read-only discovery
scripts/runtime-validate.py        # schema + semantic validation
scripts/runtime-normalize.py       # canonical model
templates/runtime-contract.yaml
tests/runtime/fixtures/
```

Parsing/hashing/JSON logic should live in Python; the Bash wrapper only holds the invocation and exit-code contract.

## 19. Acceptance criteria

Phase 0 is done when:

1. There is a versioned schema and a clearly documented parser strategy.
2. Discovery runs read-only on a fixture repo.
3. The Compose model comes from `docker compose config --format json`.
4. Selected files, project directory, profile, and project name all have provenance.
5. A contract mismatch produces a clear error and does not auto-fix the config.
6. Mapping distinguishes logical name, runtime name, and active state.
7. A missing healthcheck yields `readiness=unknown`.
8. The report contains no raw secret values.
9. Heuristic discovery grants no mutation capability.
10. There are fixtures for override, profile, interpolation failure, missing runtime, ambiguity, and redaction.
11. The normalized model is deterministic.
12. The agent knows when to `proceed`, `needs_review`, or `blocked`.

## 20. Review conclusion

Phase 0 should optimize for being **explainable, deterministic, and fail-closed at the capability boundary**, not for covering every kind of project.

```text
The AI knows which runtimes exist,
knows what has been confirmed,
knows what is only a guess,
knows which services are active,
and is blocked before any mutation that was not granted.
```

If these boundaries are settled first, later phases can add logs, exec, restart, and automated verification without turning the harness into a shell-access layer that is hard to control.

## 21. References

- [Docker Compose file reference](https://docs.docker.com/reference/compose-file/)
- [Compose application model](https://docs.docker.com/compose/intro/compose-application-model/)
- [Docker Compose config CLI](https://docs.docker.com/reference/cli/docker/compose/config/)
- [Merge Compose files](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)
- [Compose interpolation](https://docs.docker.com/reference/compose-file/interpolation/)
- [Compose services and healthcheck](https://docs.docker.com/reference/compose-file/services/)
- [Compose profiles](https://docs.docker.com/reference/compose-file/profiles/)
- [Compose project name](https://docs.docker.com/compose/how-tos/project-name/)
- [Compose environment precedence](https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/)
- [Compose environment best practices](https://docs.docker.com/compose/how-tos/environment-variables/best-practices/)
- [JSON Schema specification](https://json-schema.org/specification)
