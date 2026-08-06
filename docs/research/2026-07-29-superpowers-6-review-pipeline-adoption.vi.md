# Đánh giá Superpowers 6.0 và hướng áp dụng cho harness hiện tại

> Ngày: 2026-07-29
> Phạm vi: bài viết của Udaykiran Estari, release Superpowers v6.0.0, tài liệu upstream và
> workflow hiện tại của repository này.

## Kết luận

Bài viết có luận điểm kiến trúc tốt nhưng phần benchmark độc lập không đáng tin cậy.
Điều nên học từ Superpowers 6.0 là xoá phần điều phối trùng lặp mà không làm yếu proof:

1. Một reviewer theo task trả về hai verdict độc lập: spec và quality.
2. Task brief, implementer report và review diff được truyền bằng đường dẫn file.
3. Reviewer có verdict `cannot_verify`; unknown không bao giờ được đổi thành pass.
4. Chỉ Critical/Important finding chặn tiến độ; Minor được ghi lại và chuyển cho final review.
5. PLAN mang Global Constraints và Interfaces đến từng isolated context.
6. Thay đổi chỉ được ship sau A/B eval chứng minh không giảm chất lượng.

## Đính chính benchmark

Bài viết nói một benchmark độc lập gồm 12 session cho thấy giảm khoảng 14% token và 9% chi
phí. Không tìm thấy nguồn xác nhận kết quả này. Nghiên cứu Norbert Laszlo mà bài viết liên kết
thực tế chạy 500 task và báo cáo:

- correctness tăng từ 45,6% lên 47,8% nhưng không có ý nghĩa thống kê;
- token trung bình tăng từ khoảng 1,56 triệu lên 2,18 triệu mỗi task;
- runtime tăng khoảng 74 giây;
- số skill invocation, action và command đều tăng.

Do đó mức tiết kiệm 50–60% phải được xem là kết quả eval nội bộ của upstream, không phải
baseline có thể áp dụng trực tiếp cho repository này.

Nguồn:

- [Bài phân tích](https://medium.com/@UdaykiranEstari/superpowers-6-0-unpacked-faster-ai-code-review-and-fewer-tokens-5ab40a6c564c)
- [Release Superpowers v6.0.0](https://github.com/obra/superpowers/releases/tag/v6.0.0)
- [Prime Radiant: Superpowers 6](https://primeradiant.com/blog/2026/superpowers-6.html)
- [Benchmark 500 task](https://norbert-laszlo.medium.com/can-a-plugin-improve-codex-benchmarking-the-superpowers-plugin-05d020066565)

## Những gì Superpowers 6.0 thay đổi

### Review pipeline

Pipeline cũ:

```text
implementer
  → spec reviewer
  → quality reviewer
  → task tiếp theo
```

Pipeline mới:

```text
implementer
  → task reviewer {
      spec_verdict,
      quality_verdict,
      findings[]
    }
  → task tiếp theo
```

Reviewer vẫn độc lập với implementer. Phần bị xoá chỉ là lần đọc lại cùng diff và metadata.

### File handoff

Upstream tạo trước:

- task brief;
- implementer report;
- review package gồm commit list, diff stat và full diff;
- progress ledger.

Controller chỉ truyền đường dẫn. Artifact lớn không nằm lại trong context đắt nhất và không bị đọc
lại ở mọi turn sau.

### Severity và unknown

- Critical/Important: sửa và review lại.
- Minor: ghi vào ledger, không chặn task.
- `Cannot verify from diff`: controller kiểm tra hoặc bổ sung context; không được xem là pass.

### PLAN

PLAN mới mang:

- Global Constraints áp dụng cho mọi task;
- Interfaces mô tả chính xác task consume và produce gì;
- task boundary đủ lớn để xứng đáng có test cycle và reviewer riêng;
- semantic preflight trước Task 1.

### Các thay đổi khác

Release còn chuyển worktree về project-local, tăng bảo mật visual brainstorming, thêm harness,
dùng thuật ngữ trung lập hơn, và tách skill eval khỏi plugin-code tests.

## So sánh với repository hiện tại

| Ý tưởng | Hiện trạng | Nhận định |
|---|---|---|
| Scale ceremony theo độ lớn/rủi ro | Có lane tiny/normal/high-risk | Đã làm tốt; tiny lane chặn fixed ceremony cost |
| Fresh implementer | Một isolated implementer cho mỗi task | Giữ nguyên |
| Một task reviewer, hai verdict | Vẫn chạy spec rồi quality reviewer | Gap lớn nhất |
| Severity gating | Reviewer có severity nhưng mọi issue đều chặn | Cần hoàn thiện |
| `cannot_verify` | Có ở downstream oracle, thiếu ở per-task spec review | Cần thống nhất |
| File handoff | Task text được paste; reviewer tự dựng diff | Chưa có |
| Global Constraints/Interfaces | Có SC và file responsibilities, chưa có schema tương ứng | Chưa đủ |
| Semantic preflight | Chủ yếu kiểm tra schema, wave và Verify | Chưa kiểm tra contradiction |
| Reviewer read-only | Không có Write/Edit/Agent nhưng Bash vẫn có thể mutate | Chưa enforce hoàn toàn |
| Final review | context audit + correctness + intent + receipt | Mạnh hơn upstream; giữ nguyên |
| Project-local worktree | Đã ưu tiên `.worktrees/` | Đã phù hợp |
| Evals tách khỏi tests | Đã có `evals/` riêng | Đã phù hợp |

Với N task sạch, pipeline hiện tại cần `N implementer + 2N task reviewer`. Sau khi hợp nhất,
pipeline còn `N implementer + N task reviewer`: giảm chính xác 50% reviewer dispatch theo task.

## Đề xuất áp dụng

### P0

1. Thay hai prompt reviewer bằng một `task-reviewer-prompt.md` có output schema cố định.
2. Tạo deterministic task-brief và review-package helper; chỉ truyền đường dẫn file.
3. Thêm `cannot_verify` và route: bổ sung context một lần, sau đó escalate.
4. Chỉ Critical/Important chặn; lưu Minor trong SUMMARY và chuyển cho final reviewer.
5. Bỏ nhánh phụ thuộc vào reviewer của external Superpowers plugin để hành vi nhất quán.

### P1

1. Thêm Global Constraints, Interfaces và Criteria mapping vào PLAN contract mới.
2. Thêm semantic plan preflight cho contradiction, incompatible interfaces và plan-mandated defect.
3. Thu hẹp tool surface của task reviewer; focused test đi qua test-runner khi cần.
4. Cho correctness và intent reviewer dùng chung diff package nhưng giữ oracle/context blindness
   riêng biệt.
5. Ghi rõ model trong mọi dispatch; không dùng model rẻ làm reviewer mặc định.
6. Giới hạn narration của controller và output của reviewer.
7. Chạy controlled A/B trên corpus có spec-only, quality-only, combined, Minor-only,
   cannot-verify, global-constraint và plan-mandated cases.

## Những gì không áp dụng

- Không dùng claim 50–60% làm acceptance target.
- Không giới hạn reasoning của controller để tiết kiệm token.
- Không đặt word budget làm mất nội dung test.
- Không gộp correctness, intent và context-propagation oracle.
- Không rewrite đa harness khi repository vẫn chủ đích phục vụ Claude Code.
- Không để review package trở thành ranh giới sự thật; reviewer vẫn được phép kiểm tra một rủi ro
  cụ thể ngoài packet và phải ghi rõ search surface.

## Quyết định

Áp dụng review compression theo task, đồng thời giữ lane routing, acceptance contract, hard hooks,
ba final oracle và review receipt. Chất lượng là hard gate; hiệu quả chỉ được đánh giá giữa các
candidate đã vượt qua quality gate.
