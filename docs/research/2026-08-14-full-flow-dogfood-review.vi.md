# Dogfood full-flow: chạy toàn bộ chuỗi harness trên một feature request thật

**Ngày:** 2026-08-14
**Branch chạy:** `feature/intake-lane-check-timing` (worktree, stack trên `plan/terminology-artifact-authoring`)
**Slug:** `specs/intake-lane-check-timing`
**Người điều phối:** Claude Fable 5 (autonomous, user cấp quyền chạy tự động)

---

## 1. Mục tiêu và cách dựng bài

Yêu cầu: cài harness từ branch hiện tại, tạo một feature request, kích hoạt chạy tự động
**full flow**, rồi đánh giá kết quả.

Để bài dogfood có giá trị, feature request **không** được bịa. Tôi lấy đúng một defect có thật mà
correctness review của vòng trước (`ste-terminology-evidence`) đã phát hiện nhưng cố ý chưa sửa:

> `skills/feature-intake/SKILL.md` step 6 ra lệnh chạy `python scripts/verify_summary.py --lane <slug>`
> vô điều kiện trước khi handoff. Trên lane `normal`/`high-risk`, lệnh đó **chắc chắn** exit 1 tại
> thời điểm intake (bảng `### Verify` còn là placeholder; `high-risk` còn thiếu `### Rollback`).
> Ngoài ra `allowed-tools` không cấp bất kỳ dạng Bash nào chạy được lệnh đó.

### 1.1 Xác minh trạng thái install (không tin dòng "✓")

```
grep -c "Read.*`rules/terminology.md`" .claude/skills/{xia2,feature-intake,subagent-driven-development}/SKILL.md
→ 1, 1, 1
diff rules/terminology.md .claude/rules/terminology.md → identical
```

Cả ba delivery edge terminology đều có mặt trong bản deployed; rule khớp working tree. Kiểm bằng
**nội dung file**, không dựa vào dòng success của `deploy-harness.sh`
(theo `docs/solutions/harness/` — deploy conflict guard có thể in ✓ mà vẫn giữ file cũ).

### 1.2 Tái hiện defect *trước khi* sửa

Ngay tại bước intake, trên một record `high-risk` hoàn toàn hợp lệ:

```
python scripts/verify_summary.py --lane intake-lane-check-timing
✗ lane `high-risk`: `### Verify` has no real command row (all rows are placeholders)
exit 1
```

Đây là bằng chứng tier **truth** (chạy thật, so exit code), không phải suy luận từ đọc code.

---

## 2. Chuỗi đã chạy

```
feature-intake (high-risk, confidence high, workflow-engine gate)
  → brainstorming + spec-document review
  → xia2 (Deep, local-only, no external surface)
  → writing-plans + plan-document review
  → using-git-worktrees (worktree cách ly + deploy harness vào worktree)
  → subagent-driven-development (implementer + task-reviewer, 2 verdict)
  → context-propagation-audit
  → correctness-review (6 finder angle → dedup → scorer độc lập, threshold 75)
  → intent-review (mù với plan) ×2 vòng
  → review receipt + ship record
```

### 2.1 Commit ledger

| SHA | Nội dung | Nguồn gốc |
|---|---|---|
| `d352030` | intake record, design, research-brief, plan | intake + brainstorming + xia2 + writing-plans |
| `07474d9` | lane-scope step 6, thêm 2 grant hẹp | implementer wave 1 |
| `8fd404b` | sửa prose step 6 theo correctness review | fix-loop vòng 1 |
| `72f3919` | qualify claim layout của Check 1.6 | fix-loop vòng 2 |
| `da53bd7` | đóng gap `rules/auto-correct-scope.md` + pin `python3` | intent review vòng 1 |
| `69fe959` | mirror mô tả Check 1.6 trong README | intent review vòng 2 |
| `132b7cf` | ship record | controller |
| `9eda10d` | ghi nhận phát hiện gate-bypass | controller |

### 2.2 Trạng thái gate cuối

| Gate | Kết quả |
|---|---|
| `verify_summary.py --check intake-lane-check-timing` | exit 0 — **10/10** Verify row re-run sạch |
| `verify_summary.py --lane intake-lane-check-timing` | exit 0 (high-risk shape) |
| `check_review_receipt.py --require correctness,intent --require-audit-if dd51982` | exit 0 |
| `bash scripts/run-tests.sh` | ALL GREEN, 576 test |
| `check_plan_contract.py` | passed |

---

## 3. Đánh giá: các oracle độc lập có thực sự bắt lỗi không?

**Có — và mỗi tầng bắt một lớp lỗi mà tầng trước bỏ sót.** Đây là kết quả tích cực rõ nhất.

### 3.1 Task reviewer — bắt false green trong chính bảng chứng cứ

Verify row được viết dạng `grep -qF 'For a \`tiny\` lane...'`. `verify_summary.py` chỉ strip
backtick **ngoài cùng** rồi chạy `shell=True`; trong single-quote POSIX, backslash là ký tự
literal. Hệ quả: pattern `-F` mang backslash không tồn tại trong file.

- SC-1 sẽ MISMATCH tại ship gate (claim 0, thực tế 1).
- SC-2 "pass" **vì lý do sai** — nó chứng minh một chuỗi có backslash vắng mặt, chứ không chứng
  minh câu văn cũ đã bị xóa. Đây đúng là một false green.

Reviewer đọc tĩnh, không chạy lệnh, vẫn truy ra được cơ chế. Sau khi sửa: 10/10 row re-run sạch.

### 3.2 Correctness review — bắt việc "thay defect bằng một lời hứa sai"

Bản sửa đầu tiên (`07474d9`) viết rằng lane evidence được thực thi bởi `hooks/commit-quality-gate.sh`
Check 1.6 **và** SDD ship gate `verify_summary.py --check`. Finder chứng minh vế thứ hai **sai hoàn toàn**:

```
grep -n "check_lane_evidence" scripts/verify_summary.py
→ 415 (def), 478 (call)   # call site duy nhất, nằm trong nhánh --lane
```

`--check` chỉ chạy SC coverage + re-run Verify row. Reviewer dựng một SUMMARY `high-risk` **không có**
`### Rollback` → `--check` exit **0**, `--lane` exit **1**. Nghĩa là bản sửa đã gỡ một defect và cắm vào
đó một đảm bảo không tồn tại.

Điểm số (scorer độc lập, không thấy lý luận của finder): **85 / 75 / 75 / 75** — cả 4 đều ≥ threshold 75,
vào fix-loop. Đáng chú ý: scorer **không** được biết có bao nhiêu angle cùng báo một chỗ (agreement là
provenance, không phải evidence) — thiết kế này giữ được tính độc lập.

### 3.3 Intent review — bác bỏ một quyết định phạm vi của chính controller

Tôi đã quyết định hoãn `rules/auto-correct-scope.md` sang một slug riêng, và ghi lại quyết định đó
trong SUMMARY. Intent oracle (mù với PLAN) bác bỏ:

> `skills/feature-intake/SKILL.md:17-18` — step **1** của chính flow đang sửa ra lệnh
> "Read `rules/orchestration.md` and `rules/auto-correct-scope.md`". File bị hoãn nằm **bên trong**
> flow, không phải liền kề nó. Agent chạy step 6 đã sửa vẫn được step 1 dẫn tới câu lệnh hỏng.

Đây là giá trị cốt lõi của oracle thứ ba: nó không hỏi "có khớp plan không", nó hỏi "người viết yêu
cầu ban đầu có nhận ra đây là thứ họ xin không". Plan §2 đã liệt file đó vào non-goal — và plan đã sai.

### 3.4 Intent review vòng 2 — bắt bản ghi nói dối

Sau khi sửa, SUMMARY vẫn khẳng định các điều đã không còn đúng:

| Sai lệch | Thực tế sau `da53bd7` |
|---|---|
| "rule vẫn prescribe unconditional, unpinned `python`" | đã lane-scope + pin `python3` |
| "vẫn trỏ (Step 7)" | đã sửa thành (Step 6) |
| audit range `dd51982..72f3919` | commit mới nhất là `da53bd7` |
| Rollback thiếu `da53bd7` | revert 3 commit để lại trạng thái **lai**, mở lại defect |
| word count 596 / "+50 ≤ +50" | thực tế 598, **+52** — vượt Global Constraint |

Không tầng nào khác bắt được nhóm này. Bản ghi đi lệch khỏi cây thật ngay khi một fix commit đáp xuống.

---

## 4. Phát hiện nghiêm trọng nhất — không đến từ feature, mà từ chính lần chạy

### 4.1 Commit gate chưa bao giờ soi worktree này

`hooks/commit-quality-gate.sh:20-23` giải repo root từ thư mục của **chính script**:

```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
cd "$REPO_DIR"
```

`settings.json` đăng ký hook bằng **đường dẫn tương đối** `hooks/pre-bash-dispatch.sh`, giải về main
checkout. Xác minh trực tiếp:

```
SCRIPT_DIR=/Users/.../harness-skills/hooks
REPO_DIR  =/Users/.../harness-skills          # main checkout, KHÔNG phải worktree

git -C <main> diff --cached --name-only  → rỗng suốt phiên
git -C <worktree> show --stat 132b7cf    → 4 file đang thực sự được commit
```

**Hệ quả:** mọi commit tạo trong worktree bị chấm bằng index của main checkout — một index **trống**.
Check 1.6 (lane evidence), `risk-corroboration`, `branch-guard`, `check-untracked-py` đều **chạy**
nhưng soi nhầm repository và pass rỗng.

Bằng chứng cụ thể nhất: `d352030` commit một SUMMARY `high-risk` còn nguyên placeholder — đúng thứ mà
`verify_summary.py --lane` exit 1 — và không bị chặn.

**Vì sao đây là lỗi nghiêm trọng:** đây là "green can mean skipped" ở cấp **repository**, và nó vô hiệu
hóa gate đúng tại nơi harness **bắt buộc** cách ly. `rules/auto-correct-scope.md` quy định lane
`normal`/`high-risk` phải dùng `using-git-worktrees`. Nói cách khác: **lane càng cao thì gate càng
không chạy.** Vùng ceremony cao nhất lại là vùng mất bảo vệ.

**Hướng sửa (đề xuất, chưa thực hiện):** giải repo đích từ cwd của chính lệnh commit
(`CLAUDE_PROJECT_DIR`, hoặc cwd mà Bash tool đang dùng) thay vì từ vị trí script; thêm regression test
khẳng định một commit trong worktree được chấm bằng index của worktree.

**Chưa sửa trong lần chạy này** — `hooks/*` là bề mặt Rule-4 (high-blast), nằm ngoài scope của spec.
Đã ghi vào `specs/intake-lane-check-timing/SUMMARY.md` → `### Harness-Delta` kèm hướng sửa.

### 4.2 CWD của Bash reset âm thầm giữa phiên

Cùng lớp vấn đề, biểu hiện khác: cwd của Bash tool tự quay về main checkout giữa chừng, khiến một lệnh
`git add specs/...` stage nhầm repo. Phát hiện nhờ đường dẫn tuyệt đối in ra trong output của
`verify_summary.py` (`/harness-skills/specs/...` thay vì `/.worktrees/.../specs/...`), đã hoàn tác bằng
`git reset` và stage lại đúng chỗ.

**Bài học vận hành:** khi làm việc trong worktree, dùng `git -C <abs-path>` và đường dẫn tuyệt đối cho
mọi lệnh có tác dụng phụ. Đừng dựa vào cwd bền vững.

---

## 5. Điểm yếu và chi phí

### 5.1 Ceremony so với kích thước thay đổi

Deliverable cuối cùng là **~10 dòng prose trong 3 file**. Chi phí: 5 vòng sửa, ~1.4M token subagent,
14 lượt dispatch agent. Tỉ lệ này khó biện minh cho một prose fix — **nhưng** chính các vòng đó đã bắt
2 lời hứa sai (§3.2) và 1 gap phạm vi (§3.3). Nếu bỏ chúng, bản sửa đã ship với một đảm bảo không tồn tại.

Kết luận cân bằng: chi phí cao là thật, nhưng không phải chi phí vô ích. Vấn đề là harness **chưa có**
cơ chế giảm ceremony khi diff là prose thuần và đã có gate tier-truth phủ.

### 5.2 Subagent chết vì session limit, không có bàn giao

Một implementer subagent bị API cắt giữa fix-loop vòng 2. Flow **không có** cơ chế bàn giao cho tình
huống này — tôi phải tự tiếp quản trong main thread (chấp nhận context pollution). May là subagent đã
kịp ghi thay đổi vào working tree trước khi chết, nên không mất việc; đó là may mắn, không phải thiết kế.

### 5.3 Ngân sách từ của skill đã cạn

`skills/feature-intake/SKILL.md` hiện **598/600** từ (ceiling trong `scripts/audit_skill_prompts.py`).
Còn 2 từ. Mọi bổ sung sau này **phải cắt chỗ khác**. Đồng thời Global Constraint của plan ("≤ +50 từ")
đã bị vượt 2 từ (+52) — đã ghi nhận công khai trong `### Deviations`, không giấu.

### 5.4 Plan §2 non-goal đã sai và phải bị oracle sau bác bỏ

Việc plan tự khai một file là non-goal không có gì kiểm chứng nó. Chỉ intent review (chạy **sau khi**
implementation xong) mới bác được. Nếu chuỗi dừng ở correctness review, defect đã ship.

---

## 6. Kết luận

**Chuỗi hoạt động đúng như thiết kế.** Ba oracle độc lập bắt ba lớp lỗi khác nhau, không tầng nào thừa:

- task reviewer → chứng cứ không re-runnable (false green trong bảng Verify);
- correctness review → khẳng định sai về hành vi runtime của gate;
- intent review → quyết định phạm vi sai của chính controller, và bản ghi đi lệch khỏi cây.

**Nhưng lớp bảo vệ cơ học (hook) thì không chạy** trong cấu hình worktree mà chính harness bắt buộc.
Toàn bộ độ tin cậy của lần chạy này đến từ các oracle **model-based** và các lệnh tôi tự chạy tay,
**không** từ commit gate. Đó là kết luận quan trọng nhất của bài dogfood.

Nói gọn: harness bắt lỗi tốt bằng review, và đang **không** bắt lỗi bằng hook ở nơi nó hứa sẽ bắt.

---

## 7. Việc còn mở (cần quyết định của người dùng)

1. **Lỗ hổng gate-bypass (§4.1)** — khuyến nghị mở slug riêng. Nó lớn hơn feature vừa sửa và chạm
   `hooks/*` (Rule-4). Cần escalation trước khi động vào.
2. **Push + PR** — `feature/intake-lane-check-timing` nằm trong worktree, **chưa push**. Nó stack trên
   `plan/terminology-artifact-authoring` cũng chưa push, nên **base của PR là quyết định của bạn**,
   không có mặc định an toàn.
3. **Redeploy `.claude/` cho main checkout** — bản deployed của main vẫn là bản cũ. Cần xác nhận của
   người dùng, và phải verify **nội dung** file sau khi deploy, không tin dòng success.
4. **`/compound`** — hai learning ứng viên đã ghi trong `### Harness-Delta`: (a) SUMMARY đi lệch ngay
   khi một fix commit đáp xuống, phải re-check theo HEAD sau mỗi vòng; (b) quyết định "hoãn sang slug
   khác" trong correctness review có thể bị intent oracle bác khi file bị hoãn là bước đọc bắt buộc
   của flow đang sửa.

---

## 8. Ranh giới bằng chứng

> **Đã xác minh tier truth (chạy thật, so exit code):** defect gốc tại intake; 10 Verify row;
> `--lane`, `--check`, receipt, `run-tests.sh`, `check_plan_contract.py`; cơ chế `REPO_DIR` của hook
> (`git -C .../hooks rev-parse --show-toplevel`) và trạng thái index rỗng của main.
>
> **Đã xác minh tier traceability (đọc nguồn, không chạy):** call site duy nhất của
> `check_lane_evidence`; PAYLOAD của installer và danh sách sync của deploy-harness; hành vi
> fail-open của Check 1.6 trong consumer install.
>
> **Chưa kiểm (unknown, không phải absent):** permission matcher của Claude Code có chấp nhận dạng
> grant `Bash(python3 <path> *)` hay không — không có code nào trong repo parse `allowed-tools`;
> hành vi thực tế trong một consumer install (chưa thực hiện install thật); một lần intake lane
> `tiny` chạy sống end-to-end.
