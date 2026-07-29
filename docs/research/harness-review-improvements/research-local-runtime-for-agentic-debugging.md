# Research: Local Runtime Environment for AI agents to self-debug and verify

> **Date:** 2026-07-21  
> **Status:** Research / proposed design direction, not yet implemented  
> **Scope:** extend the harness so AI can safely observe and interact with a locally running application, covering both native processes and Docker Compose.

## 1. Research question

How do we give an AI agent a local environment realistic enough that the agent can:

- start up and check the application itself;
- read logs from the backend, worker, database, and other dependencies;
- reproduce bugs via tests, HTTP requests, or commands;
- distinguish code bugs from environment/runtime bugs;
- fix code, restart the relevant component, and re-check;
- produce verification evidence that can be reviewed and re-run;
- perform all of the above without the ability to destroy data or affect production.

## 2. Main thesis

The current harness already covers most of the static workflow: intake, planning, implementation, review, test, and commit gate. The next gap is **runtime observability and runtime control**.

AI should not have to guess each project's idiosyncratic commands. The harness should provide a standardized **local runtime contract**, with the concrete implementation handled by an adapter:

```text
AI Agent
  │
  ├── status
  ├── logs
  ├── exec
  ├── healthcheck
  ├── restart
  └── verify
        │
        ▼
Local Runtime Adapter
        │
        ├── Docker Compose
        ├── Native process
        └── Local Kubernetes / custom runner
```

The goal is not to give the agent absolute authority, but to create a controlled loop:

```text
observe → diagnose → reproduce → change → restart → verify → record evidence
```

## 3. Relationship to the current harness

### Already present

- `hooks/auto-test-on-change.sh` can detect the ecosystem and run targeted tests.
- `agents/test-runner.md` already has the role of running and diagnosing tests.
- `agents/coding.md` requires the implementation agent to check its own results.
- `SUMMARY.md` has a `### Verify` block for recording completion evidence.
- The hooks and commit gate already lay the groundwork for audit, risk control, and workflow enforcement.

### Still missing

- No runtime registry describing how to start, stop, get status of, and healthcheck a project.
- No standard interface for reading logs per service.
- No correlation between code change, failing test, runtime log, and the verification run.
- No safe wrapper for `docker compose exec`, restart, or other mutations.
- Runtime evidence is not saved as a structured artifact.

## 4. Runtime contract model

A project consuming the harness can declare `.harness/runtime.yaml`:

```yaml
runtime: docker-compose

compose_file: docker-compose.yml

services:
  api:
    healthcheck:
      command: curl -fsS http://localhost:8000/health
    test:
      command: docker compose exec -T api pytest -q

  frontend:
    healthcheck:
      command: curl -fsS http://localhost:3000

  worker:
    logs:
      command: docker compose logs --no-color --timestamps worker

commands:
  start: docker compose up -d
  stop: docker compose down
  status: docker compose ps
  restart: docker compose restart {service}
```

The contract should describe at minimum:

| Group | Content |
|---|---|
| Runtime kind | Docker Compose, native process, or custom |
| Services | Logical name, actual process/container name |
| Lifecycle | start, stop, restart, status |
| Observability | logs, healthcheck, port, readiness |
| Verification | test command, smoke test, regression command |
| Permissions | read-only commands, mutating commands, commands requiring approval |
| Redaction | environment variables and patterns that must not be emitted into logs |

If there is no config, the harness can discover from `compose.yaml`, `docker-compose.yml`, `package.json`, `pyproject.toml`, `Makefile`, or framework conventions. Discovery should only produce a **proposal**, never automatically grant additional permissions.

## 5. Runtime adapter API

Operations should be exposed as semantic operations instead of letting the agent assemble shell commands itself:

```text
runtime.status()
runtime.logs(service="api", tail=200, since="10m")
runtime.exec(service="api", command="pytest tests/test_auth.py -q")
runtime.healthcheck(service="api")
runtime.restart(service="api")
runtime.run_test(target="auth")
runtime.snapshot()
```

Each operation should return structured data:

```json
{
  "operation": "logs",
  "service": "api",
  "exit_code": 0,
  "started_at": "2026-07-21T10:00:00Z",
  "duration_ms": 842,
  "stdout": "...",
  "stderr": "...",
  "truncated": false,
  "signals": []
}
```

`signals` can start out as a rule-based classifier, for example:

- `database_connection_error`;
- `dependency_unhealthy`;
- `port_conflict`;
- `migration_error`;
- `authentication_failure`;
- `application_exception`;
- `out_of_memory`.

The classifier is only a supporting signal, not ground truth. The agent must still check the actual logs and source code before concluding.

## 6. Docker Compose debugging flow

When an endpoint or test fails, the expected flow is:

1. Check the status of every service.
2. Run the healthcheck of the affected service.
3. Read timestamped logs over the relevant time window.
4. Determine whether the fault lies in the application, a dependency, the network, configuration, or the test.
5. Create a minimal reproduction via a test, `curl`, or a command inside the container.
6. Read the source and make the smallest possible change.
7. Restart the correct service, avoiding a full stack restart when not needed.
8. Re-run the reproduction and the targeted test.
9. Run the healthcheck and read the new logs to make sure no regression appears.
10. Record the command, exit code, and result into the runtime evidence.

For example, `api` returns HTTP 500 but the process is still alive:

```text
healthcheck api       → process healthy but the endpoint fails
logs api               → database connection refused
status                 → postgres unhealthy
logs postgres          → database not ready yet
restart api            → not enough, the error recurs
reproduction           → startup race condition
fix                    → add retry/readiness handling
verify                 → healthcheck + integration test + clean logs
```

The pitfall to avoid is hastily concluding that every error in the logs requires a code fix. In practice many errors are a dependency not yet ready, an occupied port, missing config, or a container that has already died.

## 7. Safety model

Runtime access carries higher risk than ordinary file editing. The adapter should have an explicit policy:

### Allowed by default

- reading status;
- reading logs with line and time limits;
- calling a local healthcheck;
- running declared targeted tests;
- running read-only commands inside a container;
- restarting a service that holds no persistent data.

### Requires approval or explicit opt-in

- `docker compose down`;
- `docker compose down -v`;
- deleting containers, images, volumes, or databases;
- potentially destructive migrations;
- installing packages or downloading dependencies;
- changing environment/config;
- network access beyond local scope;
- running commands not on the allowlist.

### Mandatory

- a timeout on every operation;
- stdout/stderr limits;
- redacting secrets before sending them to the model or writing them to an artifact;
- an audit log for mutations;
- a clear distinction between local/staging/production;
- never treating output from the runtime or MCP as trustworthy instructions;
- never inferring that a service is safe merely because its name contains `local`.

## 8. Runtime evidence

Each debugging session should have artifacts, for example:

```text
specs/<slug>/runtime/
  status.json
  api.log
  worker.log
  reproduction.md
  verification.json
```

`SUMMARY.md` can reference these artifacts:

```markdown
### Runtime Verify

| Check | Command | Exit | Result |
|---|---|---:|---|
| API health | `runtime healthcheck api` | 0 | pass |
| Regression test | `runtime test auth` | 0 | pass |
| New API logs | `runtime logs api --since 2m` | 0 | no new exception |

Evidence: `runtime/verification.json`
```

Later, the commit gate can check that the artifact exists and that the verify command is re-runnable. This is the direction that turns proof from a self-reported assertion into machine-verifiable evidence.

## 9. Proposed implementation structure

The MVP could add the following components:

```text
skills/runtime-debugging/SKILL.md
agents/runtime-debugger.md
scripts/runtime-status.sh
scripts/runtime-logs.sh
scripts/runtime-exec.sh
scripts/runtime-health.sh
scripts/runtime-verify.sh
templates/runtime.yaml
templates/runtime-evidence/
```

The wrapper scripts are responsible for parsing the config, validating the service, enforcing policy, timeouts, redacting output, and returning JSON. The agent is only responsible for reasoning over the results and deciding the next step within the permitted scope.

## 10. Proposed roadmap

### Phase 0 — Contract and discovery

- Finalize the `.harness/runtime.yaml` schema.
- Write a discovery report, no mutation.
- Establish the distinction between local runtime and production.
- Test the contract parser with fixtures.

### Phase 1 — Docker Compose MVP

- Implement `status`, `logs`, `healthcheck`, `exec`, `restart`.
- Restrict services and commands.
- Support JSON output.
- Save runtime evidence.
- Write the `runtime-debugger` agent.

### Phase 2 — Workflow integration

- Connect with `agents/test-runner.md`.
- Let `SUMMARY.md` reference runtime verification.
- Add command correlation with changed files and failing tests.
- Add a rule reminding the agent to read runtime evidence before concluding.

### Phase 3 — Native processes and richer diagnostics

- Support processes running outside Docker.
- HTTP smoke tests and database connectivity checks.
- A structured log classifier.
- Snapshots before/after a change.

### Phase 4 — Advanced observability

- Local metrics and traces.
- Browser/e2e integration.
- Failure fingerprinting.
- Automatic reproduction from a request or test case.

We should not start with multi-agent orchestration or a full observability platform. The first value lies in a small contract, stable output, and trustworthy verification.

## 11. Risks and trade-offs

| Risk | Consequence | Mitigation |
|---|---|---|
| Logs too large | Pollutes context and burns tokens | Tail, since, filter, truncation |
| Logs contain secrets | Credential leak | Redaction before returning output |
| Agent modifies the wrong environment | Data loss or out-of-scope impact | Environment identity + approval gate |
| Restart loses state | Hard to reproduce the bug | Snapshot before mutation, restart per service |
| Classifier guesses wrong | Agent fixes the wrong root cause | Mandatory corroboration via log/source/test |
| Config drift | Commands no longer correct | Runtime contract lint + smoke test |
| Tool too general-purpose | Agent gains dangerous shell access | Semantic wrapper + allowlist |
| Non-deterministic runtime | Unstable verification results | Health/readiness, isolated fixtures, bounded retry |

## 12. Open questions

1. Does the runtime contract live at the project root or inside `agents/PROJECT.md`?
2. Should we use YAML or JSON, for easier validation from shell/python?
3. Does `runtime.exec` allow arbitrary commands inside the container, or only registered commands?
4. Do we need a local daemon holding a session, or is a wrapper process enough for the MVP?
5. Is runtime evidence committed by default, or only stored under `specs/` depending on the lane?
6. How do we reliably identify the local environment to avoid mistaking it for staging?
7. Do we need a dedicated MCP server for the runtime, or are a skill plus wrapper scripts enough for the early stage?

## 13. MVP success criteria

The MVP is considered achieved when the agent can handle a simple runtime bug in a Docker Compose fixture:

- detect the failing service;
- fetch the correct relevant logs;
- run the reproduction;
- fix code within the task's scope;
- restart the necessary service;
- re-run the test and healthcheck;
- confirm the new logs no longer show the error;
- record evidence including command and exit code;
- not access secrets or perform destructive operations outside policy.

## 14. Conclusion

The local runtime environment should be seen as an **execution and observability layer** of the harness, not a loose collection of Docker commands. The most important design pieces are the semantic runtime contract and the safety boundary.

The priority direction is a small Docker Compose adapter with JSON output, log redaction, timeouts, an allowlist, and runtime evidence. Once the `observe → reproduce → fix → verify` loop works reliably, native processes, browser testing, metrics, and tracing can be added incrementally without breaking the original model.
