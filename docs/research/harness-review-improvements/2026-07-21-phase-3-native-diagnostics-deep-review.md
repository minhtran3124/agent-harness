# Deep Research/Review: Phase 3 — Native Processes và Rich Diagnostics

> **Ngày:** 2026-07-21  
> **Trạng thái:** Research / design review, chưa triển khai  
> **Prerequisite:** Phase 0 contract/discovery và Phase 2 workflow/evidence integration

## 1. Mục tiêu

Phase 3 mở rộng runtime substrate từ Docker Compose sang process local như `uvicorn`, `npm run dev`, `go run`, worker hoặc test server; sau đó bổ sung HTTP, database, resource, event và log diagnostics.

Thứ tự đề xuất: native observe-only → controlled lifecycle → HTTP/database probes → events/resources → failure fingerprints → optional trace correlation.

Không nên bắt đầu bằng một observability platform hoặc automatic root-cause patcher.

## 2. Kết luận nghiên cứu

1. Native process dùng argv array, explicit cwd/env và `shell=False` mặc định.
2. Mỗi process chạy trong process group/session riêng để cleanup parent/child.
3. Timeout bao phủ creation, readiness, command, log drain và cleanup.
4. stdout/stderr bounded, timestamped, redacted và có backpressure.
5. Phân biệt process running, ready, exited, signal-killed và timeout.
6. HTTP probe mặc định chỉ GET/HEAD tới loopback/allowlist; mutation request cần approval.
7. Database diagnostics chỉ read-only và allowlisted; không arbitrary SQL.
8. Resource snapshot là point-in-time evidence, không full filesystem/environment dump.
9. Dùng OpenTelemetry-compatible fields nhưng chưa cần full SDK/Collector. [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)

## 3. Native process descriptor

Contract nên mô tả `executable`, `args`, `cwd`, `env_allow`, readiness probe và lifecycle policy. `args` là array, không phải shell string.

Python khuyến nghị truyền argument sequence vì escaping/quoting an toàn hơn; `shell=True` cần security review. `subprocess` hỗ trợ timeout, process group và `start_new_session`. [Python subprocess](https://docs.python.org/3/library/subprocess.html)

Một script `dev` discover từ `package.json` chỉ là candidate, không tự động là start permission.

## 4. Lifecycle và cleanup

Các state cần phân biệt: `declared`, `spawned`, `running`, `ready`, `stopping`, `exited`, `failed`, `timed_out`.

Result phải ghi exit code, signal, readiness, duration và artifact refs. Process spawned nhưng chưa ready không được coi là healthy.

Dev server thường spawn reloader/worker child. Policy:

1. start trong isolated session/process group;
2. gửi graceful signal tới group;
3. chờ grace period;
4. capture exit state;
5. kill group nếu cần;
6. verify không còn child/listener trong scope;
7. ghi cleanup result.

Python docs nêu `start_new_session`/`process_group` cho process control và cảnh báo `preexec_fn` trong threaded process. [Popen process control](https://docs.python.org/3/library/subprocess.html)

Windows có signal semantics khác POSIX; nếu chưa có adapter riêng, phải giới hạn support rõ ràng.

## 5. Timeout model

Timeout cần bao phủ process creation, readiness wait, command execution, log drain, graceful shutdown và forced cleanup. `subprocess.run(timeout=...)` xử lý thời gian chờ process nhưng process creation trên một số platform không bị interrupt ngay. [Python timeout behavior](https://docs.python.org/3/library/subprocess.html)

Kết quả timeout phải chỉ rõ timeout xảy ra ở phase nào, không chỉ trả một exit code chung.

## 6. Native log capture

Capture stdout/stderr với bounded bytes, line framing, encoding/error policy, adapter timestamp, stream name, truncation marker và backpressure.

Không để process block vì pipe đầy. Process lâu dài cần reader loop hoặc bounded queue/file, không chờ process kết thúc mới đọc.

Normalized output có thể bỏ ANSI để classifier; raw line chỉ lưu khi policy cho phép và đã xử lý secret. Record cần sequence, timestamp, stream, line, truncation và redaction count.

## 7. HTTP diagnostics

Các mức probe: `tcp_open`, `http_response`, `readiness`, `smoke_scenario`.

Mỗi probe cần timeout, redirect policy, body limit, allowed host, expected status và safe headers.

Default safety:

- chỉ GET/HEAD tới loopback hoặc allowlist;
- POST/PUT/DELETE/webhook replay cần explicit registration/approval;
- không lấy auth token từ environment tự động;
- contract tham chiếu credential provider, không chứa credential value;
- body preview bị giới hạn và redacted.

HTTP pass không tự chứng minh database/business correctness.

## 8. Database diagnostics

Database probe nên read-only và vendor-specific:

`connectivity → TCP/auth/connect`; `readiness → vendor health command`; `schema → version/metadata read-only`; `query → allowlisted bounded SELECT only`.

Không cho AI tự sinh SQL arbitrary. Nếu cần query, contract đăng ký query id, timeout, row limit và redaction. Migration/schema mutation nằm ngoài default diagnostic capability.

Phân biệt `connection_refused`, `authentication_failed`, `database_not_ready`, `schema_version_mismatch`, `query_timeout`, `permission_denied` và `unknown`.

## 9. Resource snapshots

Minimum metrics: CPU sample, RSS/memory, restart count, listening ports, exit code/signal, queue/request counts nếu app expose và disk/volume pressure nếu safe.

Docker Compose có `stats` để stream resource usage và `top` để xem process. [Docker Compose CLI](https://docs.docker.com/reference/cli/docker/compose/)

Snapshot là point-in-time evidence tại các mốc `before-change`, `after-start`, `after-reproduction`, `after-fix`. Không archive toàn bộ container filesystem, environment hoặc database data mặc định.

Một CPU sample cao không tự chứng minh memory leak; cần repeated samples/time series. OpenTelemetry phân biệt metrics, traces và logs theo mục đích. [OpenTelemetry metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)

## 10. Events, telemetry và fingerprints

Compose có `events --json` để stream lifecycle events theo container/service. [Compose events](https://docs.docker.com/reference/cli/docker/compose/events/)

Nên dùng fields tương thích OpenTelemetry như `service.name`, `service.instance.id`, `deployment.environment.name`, `process.pid`, `process.command_args`, `error.type`, `http.response.status_code` và `db.system.name`. OpenTelemetry định nghĩa traces, metrics, logs và baggage là các signal khác nhau; semantic conventions giúp correlate polyglot systems. [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)

Failure fingerprint hash normalized failure class, exit code/signal, exception type, top stack frames, service, probe/status, stable log template và dependency state. Không hash timestamp, random ID hoặc raw secret-bearing log.

Fingerprint chỉ giúp nhận biết failure lặp và chọn evidence tiếp theo; không tự quyết định patch. Khuyến nghị hard-stop khi fingerprint lặp vượt budget.

## 11. Safety model

- native process không tự nâng quyền;
- explicit cwd và PATH để tránh binary hijacking;
- argv array + `shell=False` mặc định;
- environment allowlist;
- process-group cleanup để tránh orphan;
- HTTP host/method allowlist;
- database query allowlist;
- port/process discovery không scan ngoài scope;
- không expose `/proc`, filesystem dump hoặc container exec mặc định;
- không retry destructive operation.

## 12. Testing strategy

Process fixtures: exit 0; exit non-zero; signal kill; orphan child; delayed readiness; readiness timeout; stdout/stderr flood; ANSI/malformed JSON; start timeout; stop timeout; port conflict; missing environment; ambiguous executable; POSIX/Windows divergence.

Probe fixtures: connection refused; HTTP 200/404/500/503; redirect; slow response; oversized body; disallowed host/method; DB auth failure; bounded SELECT timeout; schema mismatch; redaction.

Mỗi adapter phải pass semantic suite `status → logs → healthcheck → verification → cleanup`, với JSON shape, timeout, redaction, signal classification, truncation và artifact refs.

## 13. Implementation boundary

Đề xuất các module `runtime/adapters/native.py`, `runtime/probes/http.py`, `runtime/probes/database.py`, `runtime/probes/process.py`, `runtime/diagnostics/classify.py`, `runtime/diagnostics/fingerprint.py` và `runtime/diagnostics/redact.py`.

Logic nên là typed library; shell scripts chỉ là thin entrypoints.

## 14. Rollout roadmap

### Phase 3A — Native observe-only

Process discovery, status/listener, bounded stdout/stderr, readiness probes, exit/signal classification và cleanup verification.

### Phase 3B — Controlled lifecycle

Explicit start/restart/stop, process group/signal escalation, environment/cwd policy, mutation audit và platform-specific tests.

### Phase 3C — Rich diagnostics

HTTP/database probes, Docker/native resource snapshots, events/fingerprints, OTel-compatible fields và optional trace correlation.

## 15. Acceptance criteria

1. Native process chạy bằng argv array và explicit cwd/env.
2. Timeout và process-group cleanup hoạt động với parent/child process.
3. Exit code, signal, readiness failure và timeout phân loại riêng.
4. stdout/stderr bounded, timestamped, truncation-aware và redacted.
5. HTTP probe có method/host/body/timeout policy.
6. Database probe read-only và allowlisted.
7. Resource snapshot có timestamp và scope.
8. Diagnostics có stable fields và fingerprint evidence refs.
9. Compose/native adapters dùng chung semantic contract suite.
10. Không cần full observability backend để hoàn thành Phase 3.

## 16. Kết luận

Phase 3 không phải “chạy thêm một command”. Native runtime là process supervision, signal handling, cleanup và safe observation. Rich diagnostics không phải thu thập càng nhiều càng tốt; đó là chọn đúng signal, bounded scope và provenance đủ để agent lập luận.

## References

- [Python subprocess](https://docs.python.org/3/library/subprocess.html)
- [Python signal](https://docs.python.org/3/library/signal.html)
- [Docker Compose events](https://docs.docker.com/reference/cli/docker/compose/events/)
- [Docker Compose CLI and stats](https://docs.docker.com/reference/cli/docker/compose/)
- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
- [OpenTelemetry metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)
