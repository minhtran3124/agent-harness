# Codex Deep Review: Self-Harness và hướng tự cải thiện cho `harness-skills`

> **Ngày:** 2026-07-22  
> **Nguồn chính:** [Self-Harness: Harnesses That Improve Themselves](https://arxiv.org/html/2606.09498v1)  
> **Phạm vi:** đối chiếu phương pháp, kết quả và giới hạn của paper với contracts, implementation,
> tests, evals, telemetry và research artifacts hiện có trong repository.  
> **Phương pháp:** đọc paper; trace code/docs thực tế; chạy `scripts/harness-audit.sh`,
> `scripts/harness-status.sh` và suite CI-equivalent `scripts/run-tests.sh`.

## 1. Kết luận

Repository đã có nền móng tốt cho Self-Harness: contracts rõ, deterministic tests, audit trend,
trust ledger, behavioral evals và cơ chế `/compound` biến failure thành guardrail backlog. Tuy
nhiên nó mới ở trạng thái **harness có khả năng tự quan sát một phần**, chưa phải **harness tự cải
thiện dựa trên bằng chứng**.

Khoảng trống lớn nhất là:

> Repo đang đo tính nhất quán của artifacts và một số skill riêng lẻ, nhưng chưa ghi execution
> behavior đủ chuẩn để chứng minh một thay đổi harness làm toàn workflow tốt hơn.

Paper đề xuất vòng lặp:

```text
execution traces
    → weakness mining
    → diverse, minimal candidates
    → held-in/held-out regression validation
    → accepted harness lineage
```

Paper báo cáo held-out pass rate tăng từ 40.5% lên 61.9% cho MiniMax M2.5, 23.8% lên 38.1% cho
Qwen3.5-35B-A3B và 42.9% lên 57.1% cho GLM-5. Điểm quan trọng hơn con số là mỗi model nhận các
thay đổi khác nhau: artifact recovery, retry discipline, tool-loop limits, environment persistence
và chuyển từ exploration sang implementation. Đây không phải một generic prompt dài dùng chung.

## 2. Paper thực sự đóng góp gì

### 2.1. Harness improvement là một empirical state transition

Một harness edit chỉ đáng promote khi record được:

1. behavior muốn thay đổi;
2. editable surface bị sửa;
3. evidence dẫn tới hypothesis;
4. regression result biện minh cho promotion.

Model, evaluator, tool set, budget và benchmark protocol được giữ cố định; chỉ harness thay đổi.
Thiết kế này giúp tách hiệu quả của harness edit khỏi thay đổi model hoặc môi trường.

### 2.2. Failure phải được quy về reusable mechanism

Weakness Mining không cluster đơn thuần theo outcome như `timeout` hoặc `missing artifact`. Mỗi
failure signature tách ba thành phần:

```text
terminal verifier cause
    + causal status của hành vi agent
    + reusable agent mechanism
```

Hai run cùng timeout có thể cần hai intervention khác nhau nếu một run bị kẹt ở exact-command
retry còn run kia exploration quá lâu mà không tạo artifact.

### 2.3. Proposal phải đa dạng giữa branches, tối thiểu trong từng branch

Mỗi candidate nhắm một failure mechanism và một editable surface. Proposal record phải nêu expected
behavioral effect và regression risk. Rejected proposals vẫn được lưu để lineage audit được.

### 2.4. Promotion phải non-regressive

Paper chỉ accept candidate nếu nó cải thiện ít nhất một split và không làm split còn lại giảm.
Stochastic evaluations được lặp lại và dùng aggregate pass counts. Nhiều candidate tương thích có
thể được merge thành harness kế tiếp.

## 3. Repo hiện đã có gì

| Thành phần Self-Harness | Repo hiện có | Khoảng trống |
|---|---|---|
| Verifiable outcomes | Test suite, `### Verify`, CI gates | Chưa gắn outcome với harness/model/run identity |
| Execution traces | Session transcript, SUMMARY, breadcrumbs | Không có trace schema chuẩn, causal evidence hay tool-event lineage |
| Failure mining | `/compound`, solutions, improvement backlog | Manual, per-session, không cluster failure xuyên nhiều run |
| Candidate proposals | Guardrail backlog | Không có candidate ID, parent harness, hypothesis, isolated branch hay rejected archive |
| Regression validation | Hai behavioral eval suites | Manual, nhỏ, không có diagnostic/promotion/final split |
| Promotion | PR và human review | Chưa có machine-readable promotion rule cho behavioral candidates |
| Model-specific harness | Chưa có | Một harness chung; eval record không pin đầy đủ model/runtime profile |
| Harness lineage | Git history, trust ledger | Không biểu diễn lineage theo candidate và evidence |
| Safety boundary | Hard gates, strict CI, branch isolation | Chưa khai báo rõ editable surfaces và immutable trusted core |

### 3.1. Nền tảng tốt cần giữ

- `HARNESS.md` tách risk và ambiguity thành hai trục độc lập.
- Completion claim cần proof có thể chạy lại, không chỉ prose.
- `skills/compound/SKILL.md` đã có ratchet từ failure track sang
  `docs/harness-experimental/improvement-backlog.md`.
- `evals/README.md` quy định labeled fixtures, blind runs, first-run record và claim discipline.
- `scripts/bookkeeping.sh` cùng post-merge workflow đã biến trust ledger thành event-sourced record.
- `scripts/harness-audit.sh` đã có JSON output và trend log.
- `docs/research/harness-review-improvements/2026-07-20-production-agent-harness-review.md` đã phác thảo đúng tiền đề
  `RUN.json`, `events.jsonl`, bounded recovery và run observability.

### 3.2. Behavioral coverage còn hẹp

Repo có 14 skill directories nhưng behavioral eval hiện mới đo:

- `/feature-intake`;
- `/correctness-review`;
- `/intent-review`.

`evals/skills/review-chain` có năm planted-defect fixtures. `evals/workflow/intake-classifier` có
bảy classification fixtures. Đây là nền tốt nhưng chưa đủ để claim full-workflow improvement.
Các LLM runs vẫn manual; CI chỉ chạy deterministic scorers và contract tests.

### 3.3. Audit hiện đo repository drift, không đo agent behavior

`scripts/harness-audit.sh` đo SUMMARY thiếu Verify, stale plan, stale solution, stale backlog,
manifest degradation và dirty contract surfaces. Nó chưa trả lời:

- run nào lặp tool error;
- model nào thường thiếu required artifact;
- recovery success rate;
- số human corrections;
- token/tool-call/wall-time regression;
- harness version nào thực sự tăng task success.

Vì vậy `findings=0, band=healthy` chỉ có nghĩa governance artifacts đang sạch theo sáu check hiện
tại, không có nghĩa harness behavior đã được chứng minh tối ưu.

## 4. Những thứ repo nên học và áp dụng

### 4.1. Chuẩn hóa behavioral trace trước khi xây optimizer

Mỗi run cần một record tối thiểu:

```json
{
  "run_id": "...",
  "task_id": "...",
  "harness_sha": "...",
  "model_id": "...",
  "model_config_hash": "...",
  "evaluator_version": "...",
  "budget": {},
  "outcome": "pass|fail|blocked",
  "tool_events": [],
  "verification_events": [],
  "artifacts": [],
  "failure_signature": null
}
```

Nên mở rộng trực tiếp proposal `specs/<slug>/RUN.json` và `specs/<slug>/events.jsonl` trong research
hiện có, không tạo observability schema song song. V1 chưa cần OpenTelemetry Collector hay raw
transcript storage.

Trace phải bounded, redact secrets và lưu artifact references thay vì commit toàn bộ hội thoại.

### 4.2. Dùng failure signature ba tầng

Schema gợi ý:

```yaml
verifier_cause: required_artifact_missing
causal_status: agent_deleted_artifact_after_tool_error
agent_mechanism: artifact_recovery_failure
support: 3
representative_run_ids:
  - run-123
  - run-207
evidence_refs:
  - runtime/run-123/events.jsonl
```

Failure fingerprint dùng để deduplicate; failure signature dùng để quyết định loại harness
intervention. Không auto-patch chỉ vì fingerprint match.

### 4.3. Biến `/compound` thành consumer của evidence

`/compound` phù hợp cho knowledge crystallization nhưng không nên là nguồn evidence duy nhất. Thêm
một tầng deterministic trước nó:

1. ingest failed run records;
2. group exact failure signatures;
3. chỉ tạo weakness khi support ≥2 hoặc failure safety-critical;
4. tạo evidence bundle gồm failed và representative passing behaviors;
5. giao bundle cho `/compound` hoặc proposer model để sinh candidate.

Không tự động chạy toàn `/compound` sau mọi task.

### 4.4. Khai báo editable surfaces và trusted core

Mở rộng `harness-manifest.json`:

```json
{
  "editable_surfaces": {
    "prompt_guidance": {"risk": "normal"},
    "skill_workflow": {"risk": "high"},
    "retry_policy": {"risk": "high"},
    "tool_middleware": {"risk": "high"}
  },
  "immutable_surfaces": [
    "evaluation_truth",
    "promotion_rules",
    "permissions",
    "secret_scanning",
    "branch_isolation",
    "hard_gate_vocabulary"
  ]
}
```

Agent có thể đề xuất PR cho editable surfaces nhưng không được sửa evaluator, answer keys hoặc
promotion rule trong cùng candidate. Policy, permissions, hooks và recovery boundaries vẫn cần
human review. Self-improvement không đồng nghĩa self-authorization.

### 4.5. Mỗi proposal phải nhỏ và có lineage

Candidate record:

```yaml
candidate_id:
parent_harness_sha:
model_profile:
target_failure_signature:
evidence_run_ids:
edited_surface:
expected_behavior_change:
regression_risks:
diff_path:
evaluation_runs:
decision: proposed|accepted|rejected
```

Mỗi candidate chỉ nên sửa một mechanism hoặc một surface. Các candidate chạy ở worktree riêng.
Rejected candidates phải được lưu để proposer không lặp lại cùng hypothesis bằng wording khác.

Nếu nhiều candidate pass độc lập, phải test lại bản merge tổng hợp. `A pass` và `B pass` không chứng
minh `A+B pass`.

### 4.6. Xây eval pyramid

Ba tầng đề xuất:

1. **Component eval:** từng skill, router, reviewer và middleware.
2. **Workflow eval:** request → intake → plan → implement → review → verify.
3. **Real-run shadow eval:** failures/corrections thực tế đã redact và đóng băng.

Ưu tiên fixture cho các behavior paper chứng minh có giá trị:

- required artifact được tạo sớm và còn tồn tại lúc kết thúc;
- không retry exact command vô hạn;
- tool error chuyển sang artifact-focused recovery;
- exploration có budget và chuyển sang implementation;
- environment changes được verify qua shell session mới;
- agent không final khi verifier hoặc sanity check còn fail.

### 4.7. Dùng ba split thay vì chỉ held-in/held-out

Một giới hạn của paper là split gọi là held-out vẫn được dùng lặp lại để quyết định promotion. Vì
vậy nó thực chất là validation set, không còn là final untouched test.

Repo nên dùng:

- `diagnostic`: trace được đưa cho weakness miner và proposer;
- `promotion`: chỉ trả aggregate outcomes cho gate;
- `final-shadow`: không được query trong candidate search, chỉ chạy lúc release/milestone.

Nếu thử nhiều candidate trên cùng promotion set, cần rotation hoặc sequential-testing budget để
giảm adaptive overfitting.

### 4.8. Promotion gate phải đa mục tiêu

Candidate chỉ được accept khi:

- deterministic suite không regression;
- behavioral target cải thiện;
- safety fixtures giữ 100%;
- artifact completeness không giảm;
- false positives và human escalations không vượt threshold;
- token/tool-call/wall-time nằm trong budget;
- không thêm permission hoặc làm yếu validation;
- combined candidate đã được test lại;
- có rollback rõ và diff nhỏ.

Với stochastic eval, dùng paired repeats và confidence intervals hoặc bootstrap. Hai attempts như
paper chỉ nên xem là tín hiệu ban đầu, chưa đủ mạnh cho high-risk policy changes.

### 4.9. Thêm model/runtime overlays, không fork toàn repo

Giữ kiến trúc:

```text
core harness contracts
    + model/runtime profile overlays
    + project-specific rules
```

Không cần tạo nhiều bản skill tree. Pin model/runtime identity trong eval và chỉ condition một số
guidance/middleware theo profile khi có evidence. Chưa nên xây portability layer lớn nếu chưa có
model hoặc consumer thứ hai thực sự sử dụng repo.

### 4.10. Biến human correction thành training signal

Trust ledger nên bổ sung typed interventions:

```text
correction | override | rework | approval | false_alarm
```

Record cần nêu source, run ID, candidate ID, corrected behavior và commit/PR. Đây là nguồn weakness
mining thực tế giá trị hơn chỉ nhìn test failure.

## 5. Finding live phát hiện trong review

`scripts/harness-status.sh` đang đọc sai cột trust ledger.

Schema thật:

```text
Date | Slug | Lane | Affects | Confidence | Flags | Escalated | Outcome | Notes
```

Nhưng script lấy:

```text
column 5 → lane
column 7 → confidence
column 9 → hook
```

Do `awk -F'|'` có empty field trước dấu `|` đầu tiên, mapping đúng phải tính cả offset đó. Output
hiện đưa `Affects` vào `lane`, `Flags` vào `conf` và `Outcome` vào `hook`.

Test `tests/scripts/harness-status.test.sh` chỉ assert data row được render và script không abort;
nó không assert semantic mapping của từng field. Đây là ví dụ trực tiếp rằng có telemetry chưa đủ:
reader/evaluator của telemetry cũng cần regression test về semantic correctness.

## 6. Critique paper cần giữ khi áp dụng

### 6.1. Held-out không phải final untouched test

Outcome của held-out split được dùng trong mỗi promotion decision. Candidate search vì vậy có thể
overfit thích nghi vào split này dù raw traces không lộ cho proposer.

### 6.2. Primary metric quá hẹp

Pass rate không đo cost, latency, tool calls, safety regressions, human intervention hoặc độ phức
tạp tăng thêm của harness.

### 6.3. Hai repeats còn yếu

Với 64 tasks và agent behavior stochastic, hai attempts không cung cấp statistical confidence mạnh
cho high-risk changes.

### 6.4. Candidate merge có interaction risk

Các edit pass riêng lẻ vẫn có thể xung đột khi merge. Final combined harness phải được đánh giá như
một candidate mới.

### 6.5. Benchmark và evaluator là trust bottleneck

Paper thừa nhận accepted edits có thể benchmark-specific và phụ thuộc chất lượng verifier/trace.
Higher-stakes changes cần acceptance gate mạnh hơn pass-rate non-regression.

### 6.6. Chưa chứng minh cross-model transfer

Paper chứng minh model-specific adaptation, nhưng không đánh giá đầy đủ việc harness tối ưu cho model
A chạy trên model B. Repo không nên gọi một overlay là universal nếu chưa có cross-profile matrix.

## 7. Roadmap khuyến nghị

### P0 — Sửa semantic observability

- Fix mapping trong `scripts/harness-status.sh`.
- Thêm contract test pin đúng `Lane`, `Confidence`, `Outcome` từ schema thực.
- Không parse cột bằng magic index nếu có thể đọc header thành map.

### P1 — Run evidence contract

- Triển khai tối thiểu `RUN.json`, `events.jsonl`.
- Pin model, harness SHA, evaluator, budget và environment identity.
- Bounded retention và redaction.

### P2 — Eval registry

- Khai báo component/workflow evals.
- Diagnostic/promotion/final-shadow splits.
- Metrics, safety invariants và resource budgets.

### P3 — Weakness miner

- Deterministic failure signatures.
- Support/actionability threshold.
- Evidence bundle chứa failed và passing exemplars.

### P4 — Candidate runner

- Worktree riêng cho mỗi candidate.
- Bounded diff và declared surface.
- Lineage cùng rejected-candidate archive.

### P5 — Promotion gate

- Multi-objective acceptance.
- Paired repeated runs.
- Combined-candidate re-evaluation.
- Human-reviewed PR, không auto-merge.

### P6 — Model overlays

- Chỉ triển khai sau khi có dữ liệu cho ít nhất hai model/runtime profiles.
- Tách universal core khỏi evidence-backed overlays.

## 8. Không nên làm lúc này

- Không auto-merge self-generated harness changes.
- Không commit raw transcripts.
- Không cho proposer sửa evaluator hoặc promotion rule của chính candidate.
- Không dựng dashboard, OpenTelemetry backend hoặc persistent Collector trước trace schema.
- Không tăng độ dài system prompt hàng loạt mà không có failure mechanism cụ thể.
- Không dùng pass rate làm metric duy nhất.
- Không port Rust/SQLite/database substrate chỉ để bắt chước một self-evolving platform.
- Không tự động chạy ceremony đầy đủ cho tiny tasks; giữ nguyên nguyên tắc ceremony scales with risk.

## 9. Verification snapshot

Tại thời điểm review:

- `bash scripts/harness-audit.sh --json` trả `findings: 0`, `band: healthy`;
- `bash scripts/run-tests.sh` kết thúc `ALL GREEN` cho các contract suites đã chạy;
- Python unit tests và một số pytest-dependent cases bị skip vì môi trường không có pytest;
- behavioral evals vẫn là manual-run, không nằm trong CI-equivalent suite;
- worktree đã có các thay đổi/untracked research artifacts từ trước review; review này không sửa hoặc
  xóa các artifacts đó.

## 10. References

- Zhang et al., [Self-Harness: Harnesses That Improve Themselves](https://arxiv.org/html/2606.09498v1), 2026.
- `HARNESS.md`
- `harness-manifest.json`
- `skills/compound/SKILL.md`
- `evals/README.md`
- `evals/skills/review-chain/README.md`
- `evals/workflow/intake-classifier/README.md`
- `scripts/harness-audit.sh`
- `scripts/harness-status.sh`
- `scripts/bookkeeping.sh`
- `docs/harness-experimental/trust-metrics.md`
- `docs/harness-experimental/improvement-backlog.md`
- `docs/research/harness-review-improvements/2026-07-20-production-agent-harness-review.md`
- `docs/research/harness-review-improvements/2026-07-21-phase-2-workflow-integration-deep-review.md`
- `docs/research/harness-review-improvements/2026-07-21-phase-3-native-diagnostics-deep-review.md`
- `docs/research/harness-review-improvements/2026-07-21-phase-4-advanced-observability-deep-review.md`
