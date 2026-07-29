# Deep Research/Review: Phase 3 — Native Processes and Rich Diagnostics

> **Date:** 2026-07-21  
> **Status:** Research / design review, not yet implemented  
> **Prerequisite:** Phase 0 contract/discovery and Phase 2 workflow/evidence integration

## 1. Objective

Phase 3 extends the runtime substrate from Docker Compose to local processes such as `uvicorn`, `npm run dev`, `go run`, workers, or test servers; it then adds HTTP, database, resource, event, and log diagnostics.

Proposed order: native observe-only → controlled lifecycle → HTTP/database probes → events/resources → failure fingerprints → optional trace correlation.

We should not start with an observability platform or an automatic root-cause patcher.

## 2. Research conclusions

1. Native processes use an argv array, an explicit cwd/env, and `shell=False` by default.
2. Each process runs in its own process group/session so parent/child cleanup works.
3. Timeouts cover creation, readiness, command, log drain, and cleanup.
4. stdout/stderr are bounded, timestamped, redacted, and have backpressure.
5. Distinguish process running, ready, exited, signal-killed, and timeout.
6. HTTP probes default to GET/HEAD only, against loopback/allowlist; mutation requests require approval.
7. Database diagnostics are read-only and allowlisted; no arbitrary SQL.
8. Resource snapshots are point-in-time evidence, not a full filesystem/environment dump.
9. Use OpenTelemetry-compatible fields, but a full SDK/Collector is not yet required. [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)

## 3. Native process descriptor

The contract should describe `executable`, `args`, `cwd`, `env_allow`, a readiness probe, and a lifecycle policy. `args` is an array, not a shell string.

Python recommends passing an argument sequence because escaping/quoting is safer; `shell=True` requires a security review. `subprocess` supports timeout, process group, and `start_new_session`. [Python subprocess](https://docs.python.org/3/library/subprocess.html)

A `dev` script discovered from `package.json` is only a candidate — it is not automatically permission to start.

## 4. Lifecycle and cleanup

States to distinguish: `declared`, `spawned`, `running`, `ready`, `stopping`, `exited`, `failed`, `timed_out`.

The result must record exit code, signal, readiness, duration, and artifact refs. A process that has spawned but is not yet ready must not be treated as healthy.

Dev servers often spawn reloader/worker children. Policy:

1. start in an isolated session/process group;
2. send a graceful signal to the group;
3. wait for the grace period;
4. capture exit state;
5. kill the group if needed;
6. verify no child/listener remains in scope;
7. record the cleanup result.

The Python docs mention `start_new_session`/`process_group` for process control and warn about `preexec_fn` in threaded processes. [Popen process control](https://docs.python.org/3/library/subprocess.html)

Windows has different signal semantics from POSIX; without a dedicated adapter, support limits must be stated explicitly.

## 5. Timeout model

Timeouts must cover process creation, readiness wait, command execution, log drain, graceful shutdown, and forced cleanup. `subprocess.run(timeout=...)` handles the process wait, but on some platforms process creation is not interrupted immediately. [Python timeout behavior](https://docs.python.org/3/library/subprocess.html)

A timeout result must state which phase the timeout occurred in, not just return a generic exit code.

## 6. Native log capture

Capture stdout/stderr with bounded bytes, line framing, an encoding/error policy, adapter timestamp, stream name, truncation marker, and backpressure.

Do not let the process block because a pipe is full. Long-running processes need a reader loop or a bounded queue/file — do not wait for the process to finish before reading.

Normalized output may strip ANSI for the classifier; raw lines are stored only when policy allows and secrets have been handled. Records need sequence, timestamp, stream, line, truncation, and redaction count.

## 7. HTTP diagnostics

Probe levels: `tcp_open`, `http_response`, `readiness`, `smoke_scenario`.

Each probe needs a timeout, redirect policy, body limit, allowed host, expected status, and safe headers.

Default safety:

- GET/HEAD only, to loopback or an allowlist;
- POST/PUT/DELETE/webhook replay require explicit registration/approval;
- do not pull auth tokens from the environment automatically;
- the contract references a credential provider, it does not contain credential values;
- body preview is limited and redacted.

An HTTP pass does not by itself prove database/business correctness.

## 8. Database diagnostics

Database probes should be read-only and vendor-specific:

`connectivity → TCP/auth/connect`; `readiness → vendor health command`; `schema → version/metadata read-only`; `query → allowlisted bounded SELECT only`.

Do not let the AI generate arbitrary SQL. If a query is needed, the contract registers a query id, timeout, row limit, and redaction. Migration/schema mutation is outside the default diagnostic capability.

Distinguish `connection_refused`, `authentication_failed`, `database_not_ready`, `schema_version_mismatch`, `query_timeout`, `permission_denied`, and `unknown`.

## 9. Resource snapshots

Minimum metrics: CPU sample, RSS/memory, restart count, listening ports, exit code/signal, queue/request counts if the app exposes them, and disk/volume pressure if safe.

Docker Compose has `stats` to stream resource usage and `top` to view processes. [Docker Compose CLI](https://docs.docker.com/reference/cli/docker/compose/)

A snapshot is point-in-time evidence at the `before-change`, `after-start`, `after-reproduction`, and `after-fix` marks. Do not archive the entire container filesystem, environment, or database data by default.

A single high CPU sample does not by itself prove a memory leak; repeated samples/time series are needed. OpenTelemetry distinguishes metrics, traces, and logs by purpose. [OpenTelemetry metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)

## 10. Events, telemetry, and fingerprints

Compose has `events --json` to stream lifecycle events per container/service. [Compose events](https://docs.docker.com/reference/cli/docker/compose/events/)

Use OpenTelemetry-compatible fields such as `service.name`, `service.instance.id`, `deployment.environment.name`, `process.pid`, `process.command_args`, `error.type`, `http.response.status_code`, and `db.system.name`. OpenTelemetry defines traces, metrics, logs, and baggage as distinct signals; semantic conventions help correlate polyglot systems. [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)

A failure fingerprint hashes the normalized failure class, exit code/signal, exception type, top stack frames, service, probe/status, stable log template, and dependency state. Do not hash timestamps, random IDs, or raw secret-bearing logs.

Fingerprints only help recognize repeated failures and choose the next piece of evidence; they do not decide a patch. A hard stop is recommended when a repeated fingerprint exceeds the budget.

## 11. Safety model

- native processes do not self-escalate privileges;
- explicit cwd and PATH to avoid binary hijacking;
- argv array + `shell=False` by default;
- environment allowlist;
- process-group cleanup to avoid orphans;
- HTTP host/method allowlist;
- database query allowlist;
- port/process discovery does not scan outside scope;
- no exposing `/proc`, filesystem dumps, or container exec by default;
- no retrying destructive operations.

## 12. Testing strategy

Process fixtures: exit 0; non-zero exit; signal kill; orphan child; delayed readiness; readiness timeout; stdout/stderr flood; ANSI/malformed JSON; start timeout; stop timeout; port conflict; missing environment; ambiguous executable; POSIX/Windows divergence.

Probe fixtures: connection refused; HTTP 200/404/500/503; redirect; slow response; oversized body; disallowed host/method; DB auth failure; bounded SELECT timeout; schema mismatch; redaction.

Every adapter must pass the semantic suite `status → logs → healthcheck → verification → cleanup`, covering JSON shape, timeout, redaction, signal classification, truncation, and artifact refs.

## 13. Implementation boundary

Proposed modules: `runtime/adapters/native.py`, `runtime/probes/http.py`, `runtime/probes/database.py`, `runtime/probes/process.py`, `runtime/diagnostics/classify.py`, `runtime/diagnostics/fingerprint.py`, and `runtime/diagnostics/redact.py`.

The logic should be a typed library; shell scripts are only thin entrypoints.

## 14. Rollout roadmap

### Phase 3A — Native observe-only

Process discovery, status/listener, bounded stdout/stderr, readiness probes, exit/signal classification, and cleanup verification.

### Phase 3B — Controlled lifecycle

Explicit start/restart/stop, process group/signal escalation, environment/cwd policy, mutation audit, and platform-specific tests.

### Phase 3C — Rich diagnostics

HTTP/database probes, Docker/native resource snapshots, events/fingerprints, OTel-compatible fields, and optional trace correlation.

## 15. Acceptance criteria

1. Native processes run via an argv array with an explicit cwd/env.
2. Timeout and process-group cleanup work with parent/child processes.
3. Exit code, signal, readiness failure, and timeout are classified separately.
4. stdout/stderr are bounded, timestamped, truncation-aware, and redacted.
5. HTTP probes have a method/host/body/timeout policy.
6. Database probes are read-only and allowlisted.
7. Resource snapshots have a timestamp and scope.
8. Diagnostics have stable fields and fingerprint evidence refs.
9. Compose/native adapters share the same semantic contract suite.
10. No full observability backend is required to complete Phase 3.

## 16. Conclusion

Phase 3 is not "run one more command." A native runtime is process supervision, signal handling, cleanup, and safe observation. Rich diagnostics are not about collecting as much as possible; they are about choosing the right signals, bounded scope, and enough provenance for the agent to reason.

## References

- [Python subprocess](https://docs.python.org/3/library/subprocess.html)
- [Python signal](https://docs.python.org/3/library/signal.html)
- [Docker Compose events](https://docs.docker.com/reference/cli/docker/compose/events/)
- [Docker Compose CLI and stats](https://docs.docker.com/reference/cli/docker/compose/)
- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
- [OpenTelemetry metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)
