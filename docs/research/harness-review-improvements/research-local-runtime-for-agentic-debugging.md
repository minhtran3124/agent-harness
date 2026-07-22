# Nghiên cứu: Local Runtime Environment cho AI Agent tự debug và verify

> **Ngày:** 2026-07-21  
> **Trạng thái:** Research / đề xuất hướng thiết kế, chưa triển khai  
> **Phạm vi:** mở rộng harness để AI có thể quan sát và tương tác an toàn với ứng dụng đang chạy local, bao gồm native process và Docker Compose.

## 1. Câu hỏi nghiên cứu

Làm thế nào để cung cấp cho AI agent một môi trường local đủ thật để agent có thể:

- tự khởi động và kiểm tra ứng dụng;
- đọc log của backend, worker, database và các dependency;
- tái hiện lỗi bằng test, HTTP request hoặc command;
- phân biệt lỗi code với lỗi môi trường/runtime;
- sửa code, restart thành phần liên quan và kiểm tra lại;
- tạo ra bằng chứng verify có thể xem lại và chạy lại;
- thực hiện các thao tác trên mà không có quyền phá huỷ dữ liệu hoặc làm ảnh hưởng production.

## 2. Luận điểm chính

Harness hiện tại đã bao phủ phần lớn workflow tĩnh: intake, planning, implementation, review, test và commit gate. Khoảng trống tiếp theo là **runtime observability và runtime control**.

AI không nên phải tự đoán các command đặc thù của từng project. Harness nên cung cấp một **local runtime contract** chuẩn hóa, còn phần triển khai cụ thể được xử lý bởi adapter:

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

Mục tiêu không phải là cho agent quyền tuyệt đối, mà là tạo một vòng lặp có kiểm soát:

```text
observe → diagnose → reproduce → change → restart → verify → record evidence
```

## 3. Liên hệ với harness hiện tại

### Đã có

- `hooks/auto-test-on-change.sh` có khả năng phát hiện ecosystem và chạy targeted test.
- `agents/test-runner.md` đã có vai trò chạy và chẩn đoán test.
- `agents/coding.md` yêu cầu implementation agent tự kiểm tra kết quả.
- `SUMMARY.md` có khuôn `### Verify` để ghi bằng chứng hoàn thành.
- Các hook và commit gate đã tạo nền tảng cho audit, risk control và workflow enforcement.

### Còn thiếu

- Không có runtime registry mô tả cách start, stop, status và healthcheck project.
- Không có interface chuẩn cho đọc log theo service.
- Không có correlation giữa code change, failing test, runtime log và lần verify.
- Không có wrapper an toàn cho `docker compose exec`, restart hoặc các mutation khác.
- Bằng chứng runtime chưa được lưu thành artifact có cấu trúc.

## 4. Mô hình runtime contract

Một project tiêu thụ harness có thể khai báo `.harness/runtime.yaml`:

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

Contract nên mô tả tối thiểu:

| Nhóm | Nội dung |
|---|---|
| Runtime kind | Docker Compose, native process hoặc custom |
| Services | Tên logical, tên process/container thực tế |
| Lifecycle | start, stop, restart, status |
| Observability | logs, healthcheck, port, readiness |
| Verification | test command, smoke test, regression command |
| Permissions | command read-only, command mutation, command cần approval |
| Redaction | environment variable và pattern không được xuất vào log |

Nếu không có config, harness có thể discovery từ `compose.yaml`, `docker-compose.yml`, `package.json`, `pyproject.toml`, `Makefile` hoặc framework conventions. Discovery chỉ nên tạo **đề xuất**, không tự động cấp thêm quyền.

## 5. Runtime adapter API

Các thao tác nên được expose dưới dạng semantic operation thay vì để agent tự ghép shell command:

```text
runtime.status()
runtime.logs(service="api", tail=200, since="10m")
runtime.exec(service="api", command="pytest tests/test_auth.py -q")
runtime.healthcheck(service="api")
runtime.restart(service="api")
runtime.run_test(target="auth")
runtime.snapshot()
```

Mỗi operation nên trả về dữ liệu có cấu trúc:

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

`signals` có thể bắt đầu bằng rule-based classifier, ví dụ:

- `database_connection_error`;
- `dependency_unhealthy`;
- `port_conflict`;
- `migration_error`;
- `authentication_failure`;
- `application_exception`;
- `out_of_memory`.

Classifier chỉ là tín hiệu hỗ trợ, không phải ground truth. Agent vẫn phải kiểm tra log và source code thực tế trước khi kết luận.

## 6. Docker Compose debugging flow

Khi một endpoint hoặc test bị lỗi, flow dự kiến là:

1. Kiểm tra trạng thái toàn bộ service.
2. Chạy healthcheck của service bị ảnh hưởng.
3. Đọc log có timestamp trong khoảng thời gian liên quan.
4. Xác định lỗi thuộc application, dependency, network, configuration hay test.
5. Tạo reproduction tối thiểu bằng test, `curl` hoặc command trong container.
6. Đọc source và thực hiện thay đổi nhỏ nhất có thể.
7. Restart đúng service, tránh restart toàn bộ stack nếu không cần.
8. Chạy lại reproduction và targeted test.
9. Chạy healthcheck và đọc log mới để đảm bảo không xuất hiện regression.
10. Ghi lại command, exit code và kết quả vào runtime evidence.

Ví dụ, `api` trả HTTP 500 nhưng process vẫn sống:

```text
healthcheck api       → process healthy nhưng endpoint lỗi
logs api               → database connection refused
status                 → postgres unhealthy
logs postgres          → database chưa ready
restart api            → không đủ, lỗi tái diễn
reproduction           → startup race condition
fix                    → thêm retry/readiness handling
verify                 → healthcheck + integration test + log sạch
```

Điểm cần tránh là kết luận vội rằng mọi lỗi trong log đều cần sửa code. Nhiều lỗi thực tế là dependency chưa ready, port bị chiếm, config thiếu hoặc container đã chết.

## 7. Safety model

Runtime access có rủi ro cao hơn file editing thông thường. Adapter nên có policy rõ ràng:

### Cho phép mặc định

- đọc status;
- đọc logs với giới hạn dòng và thời gian;
- gọi healthcheck local;
- chạy targeted test đã khai báo;
- chạy command read-only trong container;
- restart service không chứa dữ liệu persistent.

### Cần approval hoặc explicit opt-in

- `docker compose down`;
- `docker compose down -v`;
- xóa container, image, volume hoặc database;
- migration có khả năng destructive;
- cài package hoặc tải dependency;
- thay đổi environment/config;
- truy cập network ngoài local scope;
- chạy command không nằm trong allowlist.

### Bắt buộc

- timeout cho mọi operation;
- giới hạn stdout/stderr;
- redact secrets trước khi gửi cho model hoặc ghi artifact;
- audit log cho mutation;
- phân biệt rõ local/staging/production;
- không coi output từ runtime hoặc MCP là instruction đáng tin cậy;
- không tự suy luận rằng service an toàn chỉ vì tên của nó chứa `local`.

## 8. Runtime evidence

Mỗi phiên debug nên có artifact, ví dụ:

```text
specs/<slug>/runtime/
  status.json
  api.log
  worker.log
  reproduction.md
  verification.json
```

`SUMMARY.md` có thể tham chiếu artifact này:

```markdown
### Runtime Verify

| Check | Command | Exit | Result |
|---|---|---:|---|
| API health | `runtime healthcheck api` | 0 | pass |
| Regression test | `runtime test auth` | 0 | pass |
| New API logs | `runtime logs api --since 2m` | 0 | no new exception |

Evidence: `runtime/verification.json`
```

Về sau, commit gate có thể kiểm tra artifact tồn tại và command verify có thể chạy lại được. Đây là hướng chuyển proof từ self-reported assertion thành machine-verifiable evidence.

## 9. Đề xuất cấu trúc triển khai

MVP có thể thêm các thành phần sau:

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

Wrapper script chịu trách nhiệm parse config, validate service, enforce policy, timeout, redact output và trả JSON. Agent chỉ chịu trách nhiệm lập luận trên kết quả và quyết định bước tiếp theo trong phạm vi được phép.

## 10. Lộ trình đề xuất

### Phase 0 — Contract và discovery

- Chốt schema `.harness/runtime.yaml`.
- Viết discovery report, không mutation.
- Xác định distinction giữa local runtime và production.
- Test contract parser bằng fixture.

### Phase 1 — Docker Compose MVP

- Implement `status`, `logs`, `healthcheck`, `exec`, `restart`.
- Giới hạn service và command.
- Hỗ trợ output JSON.
- Lưu runtime evidence.
- Viết `runtime-debugger` agent.

### Phase 2 — Workflow integration

- Kết nối với `agents/test-runner.md`.
- Cho phép `SUMMARY.md` tham chiếu runtime verification.
- Thêm command correlation với changed files và failing tests.
- Thêm rule nhắc agent đọc runtime evidence trước khi kết luận.

### Phase 3 — Native processes và richer diagnostics

- Hỗ trợ process chạy ngoài Docker.
- HTTP smoke tests và database connectivity checks.
- Log classifier có cấu trúc.
- Snapshot trước/sau thay đổi.

### Phase 4 — Advanced observability

- Metrics và traces local.
- Browser/e2e integration.
- Failure fingerprinting.
- Reproduction tự động từ request hoặc test case.

Không nên bắt đầu bằng multi-agent orchestration hoặc một observability platform đầy đủ. Giá trị đầu tiên nằm ở contract nhỏ, output ổn định và verification đáng tin cậy.

## 11. Rủi ro và trade-off

| Rủi ro | Hệ quả | Biện pháp |
|---|---|---|
| Log quá lớn | Làm nhiễu context và tốn token | Tail, since, filter, truncation |
| Log chứa secret | Rò rỉ credential | Redaction trước khi trả output |
| Agent sửa nhầm môi trường | Mất dữ liệu hoặc tác động ngoài scope | Environment identity + approval gate |
| Restart làm mất state | Khó tái hiện lỗi | Snapshot trước mutation, restart theo service |
| Classifier đoán sai | Agent sửa sai nguyên nhân | Bắt buộc corroborate bằng log/source/test |
| Config drift | Command không còn đúng | Runtime contract lint + smoke test |
| Tool quá tổng quát | Agent có quyền shell nguy hiểm | Semantic wrapper + allowlist |
| Runtime không deterministic | Kết quả verify không ổn định | Health/readiness, isolated fixture, retry có giới hạn |

## 12. Các câu hỏi còn mở

1. Runtime contract đặt ở project root hay trong `agents/PROJECT.md`?
2. Có nên dùng YAML hay JSON để dễ validate bằng shell/python?
3. `runtime.exec` cho phép arbitrary command trong container hay chỉ command đã đăng ký?
4. Có cần một local daemon giữ session, hay wrapper process là đủ cho MVP?
5. Runtime evidence có commit mặc định hay chỉ lưu trong `specs/` tùy lane?
6. Làm thế nào nhận diện chắc chắn local environment để tránh nhầm staging?
7. Có cần MCP server riêng cho runtime, hay skill + wrapper script đủ cho giai đoạn đầu?

## 13. Tiêu chí thành công của MVP

MVP được xem là đạt khi agent có thể xử lý một bug runtime đơn giản trong fixture Docker Compose:

- phát hiện service lỗi;
- lấy đúng log có liên quan;
- chạy reproduction;
- sửa code trong phạm vi task;
- restart service cần thiết;
- chạy lại test và healthcheck;
- xác nhận log mới không còn lỗi;
- ghi lại evidence có command và exit code;
- không truy cập secret hoặc thực hiện destructive operation ngoài policy.

## 14. Kết luận

Local runtime environment nên được xem là một **execution and observability layer** của harness, không phải một tập lệnh Docker rời rạc. Thiết kế quan trọng nhất là semantic runtime contract và safety boundary.

Hướng ưu tiên là Docker Compose adapter nhỏ, có output JSON, log redaction, timeout, allowlist và runtime evidence. Khi vòng lặp `observe → reproduce → fix → verify` hoạt động đáng tin cậy, native process, browser testing, metrics và tracing có thể được thêm dần mà không làm vỡ mô hình ban đầu.
