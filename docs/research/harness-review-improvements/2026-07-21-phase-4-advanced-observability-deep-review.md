# Deep Research/Review: Phase 4 — Advanced Observability

> **Date:** 2026-07-21  
> **Status:** Research / design review, not yet implemented  
> **Prerequisites:** Phase 0 contract/discovery, Phase 2 workflow integration, and Phase 3 native diagnostics

## 1. Scope

Phase 4 is the advanced layer that comes after the runtime contract, bounded workflow, native lifecycle, and basic probes have stabilized.

Its scope covers traces/context propagation, metrics, profiles, browser/e2e traces, cross-signal correlation, advanced failure fingerprints, and automatic reproduction. This is not about building a full production observability platform inside the harness.

## 2. Executive summary

1. Start from the correlation/evidence model, not from the Collector/backend.
2. Use OpenTelemetry-compatible resource, trace, span, log, and metric fields.
3. Traces are only valuable when context propagation is preserved across process/network boundaries. [Context propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
4. Metrics must have a cardinality and retention budget; do not group by raw URL, user ID, or request ID by default.
5. Profiles are currently an Alpha signal; enable them opt-in only for performance/resource investigation. [OpenTelemetry profiles](https://opentelemetry.io/docs/concepts/signals/profiles/)
6. Browser tracing should use failure-only or first-retry; do not trace every test by default. [Playwright Trace Viewer](https://playwright.dev/docs/trace-viewer)
7. Automatic reproduction must be bounded, redacted, replayable, and approval-aware.
8. The Collector is optional infrastructure; Phase 4A needs no persistent backend.

## 3. Questions Phase 4 answers

| Question | Matching signal |
|---|---|
| Which services does the request pass through? | trace/span |
| Which dependency is slow? | trace + metrics |
| Which function consumes CPU/memory? | profile |
| At which action did the browser test fail? | browser trace |
| Does this failure resemble a previous one? | fingerprint + correlated evidence |
| Can it be replayed? | sanitized reproduction artifact |

OpenTelemetry distinguishes traces, metrics, logs, baggage, and profiles by role; profiles are still Alpha. [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)

## 4. Unified observability record

Phase 4 must extend Phase 2's `RunContext`/`ExecutionRecord`, not create a parallel schema.

Every artifact needs a shared run ID, task/spec ID, runtime model hash, service/resource identity, test/reproduction ID, time window, git SHA, sampling policy, and redaction status.

Proposed artifact tree:

```text
runtime/<run-id>/observability/
  resource.json
  traces/
  metrics/
  profiles/
  browser/
  correlations.json
  reproduction/
```

Generated artifacts must be bounded, carry a content hash, and contain no raw secrets.

## 5. Traces and context propagation

A trace links one request across the frontend, API, worker, and database. Context propagation carries trace/span context across process/network boundaries; W3C Trace Context is the common propagator in OpenTelemetry. [Context propagation](https://opentelemetry.io/docs/concepts/context-propagation/)

The contract should carry trace ID, span ID, parent span, resource identity, operation, timing, status/error, bounded attributes, links to log/probe/test step, and propagation source.

If the app is not instrumented, return `trace_unavailable`; do not fabricate a distributed trace from timestamp logs alone. A synthetic root span may be created for controlled reproduction, but it must be marked `synthetic=true`.

Trace context from external input must be sanitized or ignored. Baggage should not contain credentials, PII, or secrets, because it crosses service boundaries. [OpenTelemetry security guidance](https://opentelemetry.io/docs/concepts/context-propagation/)

## 6. Metrics and cardinality

Use cases include request rate/error/latency, queue depth, retry count, database pool, CPU/memory, test duration, and readiness transitions.

Default policy:

- allowlist metric names/attributes;
- limit distinct values per attribute;
- normalize to a route template instead of a raw path;
- bucket or drop high-cardinality values;
- record metric overflow/drop counts;
- limit sample window and storage size.

OpenTelemetry warns that high cardinality raises memory cost and can trigger overflow behavior. [OpenTelemetry metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)

A metric represents an aggregate/trend; it does not prove that a specific request caused latency. The causal path requires a trace or a reproduction.

## 7. Profiles

Profiles show which code paths consume resources and can link samples to trace/span/resource context. The profiles specification is currently Alpha. [Profiles specification](https://opentelemetry.io/docs/specs/otel/profiles/)

Use cases: CPU hotspots, heap/allocation investigation, a slow endpoint correlated with a span, and regressions between two commits.

Policy:

- opt-in per task/lane;
- failure/performance investigation first, continuous profiling later;
- bounded duration and sampling rate;
- do not profile processes outside scope;
- artifacts carry build/runtime identity;
- redact code paths, command args, and labels when needed.

Do not use profiles as default test evidence, since tooling and semantics are still evolving.

## 8. Browser/e2e observability

The Playwright Trace Viewer provides a timeline, DOM snapshots, screenshots, network requests, console output, and source context. Playwright recommends `on-first-retry` or `retain-on-failure` rather than tracing every test, because the cost is high. [Trace Viewer](https://playwright.dev/docs/trace-viewer), [best practices](https://playwright.dev/docs/best-practices)

A browser artifact must carry the test ID, browser/project, run ID, base URL, trace hash, screenshot/video policy, network policy, and redaction status.

A trace can contain DOM, cookies, headers, request bodies, tokens, screenshots, and PII. The default should be local-only, no automatic upload, redacted auth/cookies, an allowlisted base URL, no recording of credential/payment flows unless opted in, and short retention.

## 9. Automatic reproduction

Reproduction sources: a failing test, a sanitized HTTP request, a browser action sequence, trace attributes, a structured event chain, or a user scenario.

Each reproduction needs a source artifact, preconditions, steps, expected failure, side-effect classification, timeout, environment assumptions, cleanup, redaction status, and a replay budget.

Do not auto-replay POST/PUT/DELETE, payments, email, webhooks, or database mutations. Read-only GETs, deterministic fixtures, isolated transactions, mocked providers, and disposable browser scenarios may be replayed under policy.

Replay requires an idempotency key or approval when side effects are unavoidable.

## 10. Correlation model

Graph correlation should link:

```text
task → run → git change → test → browser action → trace/span
                         → log → metric → profile → reproduction
```

Do not correlate by timestamp alone when an identity is already available. Timestamps are only a fallback and must carry low confidence.

`correlations.json` records source, target, method, confidence, and time window for each edge.

## 11. Collector/backend options

The OpenTelemetry Collector has receivers, processors, exporters, connectors, and extensions. [Collector components](https://opentelemetry.io/docs/collector/components/)

- **No Collector:** the agent reads local artifacts; simple and local-only.
- **Ephemeral Collector:** runs inside a fixture/task, exports locally, then cleans up; closer to the production protocol but adds failure surface.
- **Persistent backend:** best investigation UX but stateful, resource-hungry, and easily beyond harness scope.

Recommendation: no Collector in Phase 4A; try an ephemeral Collector in Phase 4B; do not standardize a persistent backend yet. A Collector pipeline needs memory bounds, a queue/retry policy, and drop diagnostics, because misconfiguration/exporter failure can lose data. [Collector troubleshooting](https://opentelemetry.io/docs/collector/troubleshooting/)

## 12. Advanced fingerprinting and diagnosis

Fingerprint v2 can combine error type, stable stack frames, route template, dependency span path, log template, metric anomaly window, profile top frames, browser action, and runtime state.

It must not contain raw request bodies, tokens, PII, random IDs, or a full secret-bearing stack.

Each fingerprint has evidence refs, confidence, and an `ambiguous` state when signals conflict. The AI may use the graph to choose the next observation step, but must not patch on its own merely because of a classifier/metric anomaly.

## 13. Testing strategy

### Trace

No instrumentation; single-service; propagated multi-service; missing/broken context; untrusted trace header; trace/log mismatch; sampled-out trace.

### Metrics

Bounded cardinality; high-cardinality bucketing; missing samples; clock skew; counter reset; overflow visibility.

### Profiles

Opt-in; timeout; missing profiler; build mismatch; redaction; trace/profile link.

### Browser

Pass without trace; first-retry trace; failure-retained trace; secret header/cookie redaction; oversized trace; disallowed base URL; disposable replay.

### Replay

Safe GET; rejected mutation; idempotency required; cleanup failure; stale artifact/model hash.

## 14. Implementation boundary

Proposed: `runtime/observability/correlation.py`, `sampling.py`, `metrics_policy.py`, `trace_policy.py`, `profile_policy.py`, `replay.py`, `fingerprint_v2.py`, and `retention.py`.

Adapter-specific integrations live under `adapters/` or an optional plugin. The core harness must not require every telemetry backend.

## 15. Rollout roadmap

### Phase 4A — Correlation and artifacts

Unify run/test/resource identities; store signal references; bounded sampling/retention; fingerprint schema; no persistent backend.

### Phase 4B — Browser and replay

Failure-only browser traces; artifact redaction; safe read-only replay; disposable environment fixtures.

### Phase 4C — Profiles and ephemeral Collector

Opt-in CPU/heap profiles; trace/profile links; ephemeral Collector fixture; queue/memory/drop diagnostics.

### Phase 4D — Investigation UX

Evidence graph, timeline, root-cause hypotheses with confidence, human review surface, and an optional persistent local backend.

## 16. Open decisions

1. Is the OpenTelemetry SDK/Collector core or optional?
2. Are browser trace artifacts committed or local/ignored?
3. Should profile support start with Python, Go, or a generic external profiler?
4. How should retention/size limits differ by lane?
5. Do we allow a synthetic trace root for reproduction?
6. In which process/container does replay run?
7. Do we need an evidence viewer, or is JSON/CLI enough for v1?
8. When fingerprints conflict, what is the escalation threshold?

Recommendation: no persistent backend, failure-only browser tracing, opt-in profiles, read-only replay, and hard approval for side effects.

## 17. Acceptance criteria

1. Trace/log/metric/profile/browser artifacts share a common run/resource/test identity.
2. Context propagation and missing instrumentation are distinguished.
3. Metrics have cardinality, size, and retention limits.
4. Profiles are opt-in and carry signal status/limitations.
5. Browser traces are failure-only/first-retry by default and have a redaction policy.
6. Replay artifacts have preconditions, side-effect classification, timeout, and cleanup.
7. Unsafe replay is rejected or requires approval.
8. Fingerprint v2 has evidence refs, confidence, and an ambiguous state.
9. An optional Collector does not become a hard dependency of the core.
10. Artifacts are bounded, hashed, redacted, and have a retention policy.
11. Fixtures cover trace, metric, profile, browser, replay, and collector failure.
12. Harness tests pass on macOS and Ubuntu; unsupported platform behavior is declared.

## 18. Conclusion

Phase 4 should be a **correlation and investigation layer**, not yet another monitoring system. Its greatest value is linking test step → request → trace → log → metric/profile → reproduction within the same run context.

The safe order is artifact correlation first, browser/replay next, profiles/Collector after that, and only then consider a persistent local backend.

## References

- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)
- [OpenTelemetry context propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
- [OpenTelemetry metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)
- [OpenTelemetry profiles](https://opentelemetry.io/docs/concepts/signals/profiles/)
- [OpenTelemetry profiles specification](https://opentelemetry.io/docs/specs/otel/profiles/)
- [OpenTelemetry Collector components](https://opentelemetry.io/docs/collector/components/)
- [OpenTelemetry Collector troubleshooting](https://opentelemetry.io/docs/collector/troubleshooting/)
- [Playwright Trace Viewer](https://playwright.dev/docs/trace-viewer)
- [Playwright best practices](https://playwright.dev/docs/best-practices)
