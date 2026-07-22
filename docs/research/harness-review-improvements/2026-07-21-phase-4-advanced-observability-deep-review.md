# Deep Research/Review: Phase 4 — Advanced Observability

> **Ngày:** 2026-07-21  
> **Trạng thái:** Research / design review, chưa triển khai  
> **Prerequisites:** Phase 0 contract/discovery, Phase 2 workflow integration và Phase 3 native diagnostics

## 1. Scope

Phase 4 là lớp nâng cao sau khi runtime contract, bounded workflow, native lifecycle và basic probes đã ổn định.

Phạm vi gồm traces/context propagation, metrics, profiles, browser/e2e traces, cross-signal correlation, advanced failure fingerprints và automatic reproduction. Đây không phải là việc xây production observability platform đầy đủ trong harness.

## 2. Executive summary

1. Bắt đầu từ correlation/evidence model, không bắt đầu từ Collector/backend.
2. Dùng OpenTelemetry-compatible resource, trace, span, log và metric fields.
3. Traces chỉ có giá trị khi context propagation được duy trì qua process/network boundaries. [Context propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
4. Metrics phải có cardinality và retention budget; không group mặc định theo raw URL, user ID hoặc request ID.
5. Profiles hiện là signal Alpha; chỉ bật theo opt-in cho performance/resource investigation. [OpenTelemetry profiles](https://opentelemetry.io/docs/concepts/signals/profiles/)
6. Browser tracing dùng failure-only hoặc first-retry; không trace mọi test mặc định. [Playwright Trace Viewer](https://playwright.dev/docs/trace-viewer)
7. Automatic reproduction phải bounded, redacted, replayable và approval-aware.
8. Collector là optional infrastructure; Phase 4A không cần persistent backend.

## 3. Câu hỏi Phase 4 giải quyết

| Câu hỏi | Signal phù hợp |
|---|---|
| Request đi qua service nào? | trace/span |
| Chậm ở dependency nào? | trace + metrics |
| Function nào tiêu thụ CPU/memory? | profile |
| Browser test fail tại action nào? | browser trace |
| Failure có giống lỗi cũ không? | fingerprint + correlated evidence |
| Có replay được không? | sanitized reproduction artifact |

OpenTelemetry phân biệt traces, metrics, logs, baggage và profiles theo vai trò; profiles hiện vẫn Alpha. [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)

## 4. Unified observability record

Phase 4 phải mở rộng `RunContext`/`ExecutionRecord` của Phase 2, không tạo schema song song.

Mỗi artifact cần chung run ID, task/spec ID, runtime model hash, service/resource identity, test/reproduction ID, time window, git SHA, sampling policy và redaction status.

Artifact tree đề xuất:

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

Generated artifacts phải bounded, có content hash và không chứa raw secrets.

## 5. Traces và context propagation

Trace nối một request qua frontend, API, worker và database. Context propagation truyền trace/span context qua process/network boundaries; W3C Trace Context là propagator phổ biến trong OpenTelemetry. [Context propagation](https://opentelemetry.io/docs/concepts/context-propagation/)

Contract nên có trace ID, span ID, parent span, resource identity, operation, timing, status/error, bounded attributes, links tới log/probe/test step và propagation source.

Nếu app chưa instrument, trả `trace_unavailable`; không dựng distributed trace giả chỉ từ timestamp logs. Có thể tạo synthetic root span cho controlled reproduction nhưng phải đánh dấu `synthetic=true`.

Trace context từ external input phải sanitize hoặc ignore. Baggage không nên chứa credential, PII hay secrets vì nó đi qua service boundaries. [OpenTelemetry security guidance](https://opentelemetry.io/docs/concepts/context-propagation/)

## 6. Metrics và cardinality

Use cases gồm request rate/error/latency, queue depth, retry count, database pool, CPU/memory, test duration và readiness transitions.

Default policy:

- allowlist metric names/attributes;
- giới hạn distinct values mỗi attribute;
- normalize route template thay vì raw path;
- bucket hoặc drop high-cardinality values;
- ghi metric overflow/drop count;
- giới hạn sample window và storage size.

OpenTelemetry cảnh báo cardinality cao làm tăng memory cost và có thể tạo overflow behavior. [OpenTelemetry metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)

Metric biểu diễn aggregate/trend; nó không chứng minh request cụ thể gây latency. Causal path cần trace hoặc reproduction.

## 7. Profiles

Profiles cho biết code paths tiêu thụ resource và có thể link sample với trace/span/resource context. Profiles specification hiện Alpha. [Profiles specification](https://opentelemetry.io/docs/specs/otel/profiles/)

Use cases: CPU hotspot, heap/allocation investigation, slow endpoint correlated với span và regression giữa hai commit.

Policy:

- opt-in theo task/lane;
- failure/performance investigation trước, continuous profile sau;
- duration và sampling rate bounded;
- không profile process ngoài scope;
- artifact có build/runtime identity;
- redaction code paths, command args và labels nếu cần.

Không dùng profile như default test evidence vì tooling và semantics còn evolving.

## 8. Browser/e2e observability

Playwright Trace Viewer có timeline, DOM snapshots, screenshots, network requests, console và source context. Playwright khuyến nghị `on-first-retry` hoặc `retain-on-failure` thay vì trace mọi test vì chi phí cao. [Trace Viewer](https://playwright.dev/docs/trace-viewer), [best practices](https://playwright.dev/docs/best-practices)

Browser artifact phải gắn test ID, browser/project, run ID, base URL, trace hash, screenshot/video policy, network policy và redaction status.

Trace có thể chứa DOM, cookies, headers, request bodies, tokens, screenshots và PII. Default nên là local-only, không upload tự động, redact auth/cookies, allowlist base URL, không record credential/payment flows nếu chưa opt-in và retention ngắn.

## 9. Automatic reproduction

Reproduction sources: failing test, sanitized HTTP request, browser action sequence, trace attributes, structured event chain hoặc user scenario.

Mỗi reproduction cần source artifact, preconditions, steps, expected failure, side-effect classification, timeout, environment assumptions, cleanup, redaction status và replay budget.

Không tự replay POST/PUT/DELETE, payment, email, webhook hoặc database mutation. Read-only GET, deterministic fixture, isolated transaction, mocked provider và disposable browser scenario có thể được replay theo policy.

Replay cần idempotency key hoặc approval nếu không tránh được side effect.

## 10. Correlation model

Graph correlation nên nối:

```text
task → run → git change → test → browser action → trace/span
                         → log → metric → profile → reproduction
```

Không correlate chỉ bằng timestamp nếu đã có identity. Timestamp chỉ là fallback và phải có confidence thấp.

`correlations.json` ghi source, target, method, confidence và time window cho mỗi edge.

## 11. Collector/backend options

OpenTelemetry Collector có receivers, processors, exporters, connectors và extensions. [Collector components](https://opentelemetry.io/docs/collector/components/)

- **No Collector:** agent đọc local artifacts; đơn giản và local-only.
- **Ephemeral Collector:** chạy trong fixture/task, export local rồi cleanup; gần production protocol hơn nhưng thêm failure surface.
- **Persistent backend:** UX investigation tốt nhưng stateful, tốn tài nguyên và dễ vượt scope harness.

Khuyến nghị: Phase 4A không Collector; Phase 4B thử ephemeral Collector; chưa standardize persistent backend. Collector pipeline cần memory bound, queue/retry policy và drop diagnostics vì misconfiguration/exporter failure có thể làm mất data. [Collector troubleshooting](https://opentelemetry.io/docs/collector/troubleshooting/)

## 12. Advanced fingerprinting và diagnosis

Fingerprint v2 có thể kết hợp error type, stable stack frames, route template, dependency span path, log template, metric anomaly window, profile top frames, browser action và runtime state.

Không chứa raw request body, token, PII, random IDs hoặc full secret-bearing stack.

Mỗi fingerprint có evidence refs, confidence và `ambiguous` state khi signals conflict. AI có thể dùng graph để chọn bước quan sát tiếp theo, nhưng không tự patch chỉ vì classifier/metric anomaly.

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

Đề xuất `runtime/observability/correlation.py`, `sampling.py`, `metrics_policy.py`, `trace_policy.py`, `profile_policy.py`, `replay.py`, `fingerprint_v2.py` và `retention.py`.

Adapter-specific integrations nằm dưới `adapters/` hoặc optional plugin. Core harness không require mọi telemetry backend.

## 15. Rollout roadmap

### Phase 4A — Correlation và artifacts

Unify run/test/resource identities; lưu signal references; bounded sampling/retention; fingerprint schema; không persistent backend.

### Phase 4B — Browser và replay

Failure-only browser traces; artifact redaction; safe read-only replay; disposable environment fixtures.

### Phase 4C — Profiles và ephemeral Collector

Opt-in CPU/heap profiles; trace/profile links; ephemeral Collector fixture; queue/memory/drop diagnostics.

### Phase 4D — Investigation UX

Evidence graph, timeline, root-cause hypotheses with confidence, human review surface và optional persistent local backend.

## 16. Open decisions

1. OpenTelemetry SDK/Collector là core hay optional?
2. Browser trace artifacts commit hay local/ignored?
3. Profile support bắt đầu với Python, Go hay generic external profiler?
4. Retention/size limits khác nhau theo lane ra sao?
5. Có cho synthetic trace root cho reproduction không?
6. Replay chạy trong process/container nào?
7. Có cần evidence viewer hay JSON/CLI đủ cho v1?
8. Khi fingerprint conflict, escalation threshold là gì?

Khuyến nghị: no persistent backend, failure-only browser tracing, opt-in profiles, read-only replay và hard approval cho side effects.

## 17. Acceptance criteria

1. Traces/logs/metrics/profiles/browser artifacts có chung run/resource/test identity.
2. Context propagation và missing instrumentation được phân biệt.
3. Metrics có cardinality, size và retention limits.
4. Profiles opt-in và có signal status/limitations.
5. Browser traces failure-only/first-retry mặc định và có redaction policy.
6. Replay artifact có preconditions, side-effect classification, timeout và cleanup.
7. Unsafe replay bị reject hoặc yêu cầu approval.
8. Fingerprint v2 có evidence refs, confidence và ambiguous state.
9. Optional Collector không thành hard dependency của core.
10. Artifacts bounded, hashed, redacted và có retention policy.
11. Fixtures phủ trace, metric, profile, browser, replay và collector failure.
12. Harness tests pass trên macOS và Ubuntu; unsupported platform behavior được khai báo.

## 18. Kết luận

Phase 4 nên là **correlation and investigation layer**, không phải một hệ thống monitoring khác. Giá trị lớn nhất là nối test step → request → trace → log → metric/profile → reproduction trong cùng run context.

Thứ tự an toàn là artifact correlation trước, browser/replay sau, profiles/Collector tiếp theo, rồi mới cân nhắc persistent local backend.

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
