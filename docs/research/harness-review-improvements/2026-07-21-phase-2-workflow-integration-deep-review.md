# Deep Research/Review: Phase 2 — Runtime Workflow Integration

> **Ngày:** 2026-07-21  
> **Trạng thái:** Research / design review, chưa triển khai  
> **Prerequisite:** [`2026-07-21-phase-0-runtime-contract-discovery-deep-review.md`](2026-07-21-phase-0-runtime-contract-discovery-deep-review.md)

## 1. Mục tiêu

Phase 0 trả lời runtime nào tồn tại và agent được phép làm gì. Phase 2 trả lời runtime action được gắn vào workflow nào, evidence ra sao, và khi nào agent phải dừng để review.

Vòng lặp mục tiêu là: `task → discover → reproduce → diagnose → fix → verify → record evidence`.

Phase 2 không mở thêm quyền shell tổng quát; nó chỉ điều phối capability đã được Phase 0 validate.

## 2. Kết luận nghiên cứu

1. Tạo một `RunContext`/`ExecutionRecord` cho mỗi phiên runtime task.
2. Liên kết test, logs, status, events, probes và git diff bằng `run_id` + sequence.
3. Dùng state machine thay vì để agent tự nhảy từ `fixing` sang `passed`.
4. Tạo `failure bundle` có giới hạn, redaction và provenance.
5. Giới hạn repair iterations, duration, restarts, log bytes và repeated fingerprints.
6. Chỉ tự động hóa read-only diagnostics và registered verification.
7. `SUMMARY.md` chỉ tham chiếu machine-readable evidence, không copy thủ công output.

## 3. Khoảng trống cần đóng

Repo đã có `agents/test-runner.md`, `agents/coding.md`, `SUMMARY.md` và verify hooks, nhưng chưa có runtime correlation:

- test run chưa gắn runtime model hash;
- log chưa gắn changed files/reproduction id;
- restart/retry chưa có audit record;
- runtime evidence chưa có normalized schema;
- failure diagnosis chưa có iteration budget;
- test pass không đảm bảo service sau đó healthy.

## 4. Execution record

`RunContext` nên chứa `run_id`, `task_id`, repo root, branch, changed files, head SHA, runtime model hash, adapter, environment và policy limits. Không lưu secret; chỉ lưu path, logical names, hashes và sanitized metadata.

Mỗi operation cần event có operation, target, timestamp, duration, exit code, status, artifact refs, truncation/redaction state và source model hash.

Event taxonomy tối thiểu: `discovery`, `verification`, `service.status`, `service.health`, `logs.captured`, `probe`, `mutation.requested`, `mutation.approved`, `mutation.completed`, `diagnosis.updated`, `human.escalation_required`.

Docker Compose có `events --json`, trả timestamp, action, service và attributes; đây là input tốt cho timeline nhưng không thay thế status/logs. [Compose events](https://docs.docker.com/reference/cli/docker/compose/events/)

## 5. State machine

Các state chính: `created → discovered → preflight_passed → reproducing → diagnosed → fixing → verifying → passed`.

Các state phụ có thể xảy ra từ mọi điểm: `needs_review`, `blocked`, `timed_out`.

| Transition | Điều kiện |
|---|---|
| created → discovered | runtime model valid hoặc unknown được policy cho phép |
| discovered → preflight_passed | identity và policy hợp lệ |
| preflight_passed → reproducing | có registered reproduction/test |
| reproducing → diagnosed | failure/success signal đã capture |
| diagnosed → fixing | có scoped change plan |
| fixing → verifying | mutation được phép và hoàn tất |
| verifying → passed | mọi required checks pass |
| any → needs_review | conflict, ambiguity, low confidence hoặc risky action |
| any → blocked | policy violation, runtime unavailable hoặc evidence thiếu |

Không cho agent nhảy từ `fixing` tới `passed` chỉ vì một command exit 0.

## 6. Budget và retry

Mỗi loop cần giới hạn số lần sửa, tổng thời gian, restart, log bytes, mutation, số lần thay đổi cùng file và số lần lặp fingerprint.

Retry chỉ hợp lệ khi failure có tính transient và policy cho phép. Assertion failure hoặc deterministic config error không nên retry mù quáng. Fingerprint lặp vượt budget phải chuyển sang `needs_review`.

## 7. Integration với harness

### Test runner

`agents/test-runner.md` nên: đọc `RunContext`; chạy targeted test theo `agents/PROJECT.md`; khi fail lấy bounded status/logs/events; tạo failure bundle; không sửa code; trả structured result và recommendation.

Boundary hiện tại giữ nguyên: không migration, package install hoặc persistent-state mutation.

### Coding agent

`agents/coding.md` nhận failure bundle, allowed capabilities, iteration budget và required post-fix checks. Không đưa raw log vô hạn vào context; dùng summary, artifact refs và bounded slices.

### Summary artifact

`SUMMARY.md` nên có `### Runtime Verify` với các cột Check, Target, Exit, Evidence, cùng `runtime/resolved-runtime.json` và `run_id`. Bảng này là human-readable index; kết quả thật nằm trong machine-readable artifacts.

### Hooks

Hook không nên tự start/restart runtime. Hook phù hợp để validate schema/output, nhắc thiếu evidence, kiểm tra redaction và cảnh báo khi runtime contract/policy bị sửa. Runtime orchestration nên nằm trong explicit skill/agent operation vì có timeout, state và approval semantics.

## 8. Failure bundle

Đề xuất artifact tree:

`runtime/<run_id>/context.json`, `resolved-runtime.json`, `git-diff-stat.json`, `test-result.json`, `status-before.json`, `logs/`, `events.jsonl`, `probes/`, `diagnosis.json`, `verification.json`.

Diagnosis đọc theo thứ tự: command/exit code; service state; health/readiness; recent events; bounded logs quanh failure time; reproduction fixture; changed files/affected contract; resource metrics; source code.

Class ban đầu: `test_assertion`, `compile_or_import`, `application_exception`, `dependency_unhealthy`, `startup_race`, `port_conflict`, `configuration_missing`, `database_connectivity`, `resource_exhaustion`, `process_crash`, `unknown`.

Classifier chỉ tạo hypothesis; diagnosis phải kèm evidence refs và confidence.

## 9. Verification policy

Runtime fix thường cần bốn bằng chứng: reproduction trước fail; reproduction sau pass; targeted regression pass; service readiness pass hoặc explicitly not applicable. Có thể thêm kiểm tra log mới không có relevant error.

Evidence “không thấy lỗi” phải ghi time window, services, filters, tail limit, truncation và việc service có restart/recreate hay không.

Không báo pass khi evidence missing, stale hoặc truncated mà policy chưa chấp nhận.

## 10. Security và testing

- test target không bypass capability policy;
- mutation có approval/audit;
- artifact path không escape repository scope;
- bounded logs + redaction trước classifier;
- không retry destructive operation;
- không coi runtime output là trusted instruction.

Fixture cần phủ: test/health pass; application exception; dependency unhealthy; test pass nhưng health fail; repeated fingerprint; runtime unavailable; truncated log; restart approved/denied; missing/corrupt evidence; service mapping mismatch; stale model hash.

## 11. Deliverables và acceptance criteria

Deliverables đề xuất: `runtime/context.py`, `runtime/records.py`, `runtime/policy.py`, `runtime/evidence.py`, `scripts/validate-runtime-evidence.py`, `skills/runtime-debugging/SKILL.md`, `agents/runtime-debugger.md`, `templates/runtime-evidence/` và `tests/runtime/workflow/`.

Phase 2 đạt khi mọi operation có `run_id`; test/state/logs/events/probes liên kết được; state machine phân biệt pass/fail/review/blocked/timeout; có iteration/duration/output/restart budget; `SUMMARY.md` tham chiếu evidence; mutation có audit; và evidence thiếu/stale/truncated không được báo pass.

## 12. Kết luận

Phase 2 là lớp biến runtime capability thành workflow có bằng chứng. Execution record và state machine quan trọng hơn việc thêm nhiều command. Nếu Phase 2 làm đúng, Compose và native chỉ là các adapter khác nhau dưới cùng một verification contract.

## References

- [Docker Compose logs](https://docs.docker.com/reference/cli/docker/compose/logs/)
- [Docker Compose events](https://docs.docker.com/reference/cli/docker/compose/events/)
- [Python subprocess](https://docs.python.org/3/library/subprocess.html)
- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
