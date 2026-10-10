# Nghiên cứu sâu — "AI-native SDLC playbook" của Anthropic so với harness của mình

> Ngày: 2026-10-10 · Nguồn: khóa học Claude Academy *The AI-native SDLC playbook*
> (`https://academy.claude.com/courses/ai-native-sdlc-playbook/introduction`), đã tải và đọc đầy
> đủ cả 14 bài vào ngày 2026-10-10.
>
> Bản tiếng Việt của [`2026-10-10-ai-native-sdlc-playbook-adoption.md`](2026-10-10-ai-native-sdlc-playbook-adoption.md).
> Các trích dẫn nguyên văn từ khóa học được giữ bằng tiếng Anh, kèm diễn giải tiếng Việt.
>
> Câu hỏi: playbook thực sự đề xuất gì, từng "play" được triển khai ra sao, so với workflow
> hiện tại của harness thì thế nào, và mình nên áp dụng gì — sắp theo thứ tự từ dễ đến khó?
>
> Cách làm: chỉ dùng nguồn gốc (nội dung khóa học, HTML render phía server → text). Mọi nhận định
> về harness đều dẫn đến file chứng minh nó; mọi nhận định "thiếu" đều nêu rõ đã tìm ở đâu
> (`rules/behavior.md` §1). Chỗ nào chưa kiểm tra thì ghi **unknown** (chưa rõ).

---

## Tóm tắt

- **Playbook là một ý tưởng duy nhất, áp dụng sáu lần:** mỗi giai đoạn SDLC tạo ra một *file
  Markdown có version trong Git* để giai đoạn sau dùng tiếp (`intent.md → spec.md → plan.md →
  diff → review → eval`), và mọi chính sách bắt buộc phải đúng đều được chống lưng bằng một
  kiểm soát *tất định* (hook / check trong CI), chứ không chỉ một kiểm soát mang tính khuyến nghị
  (skill / CLAUDE.md). Con người chuyển từ *làm* từng giai đoạn sang *duyệt* nó, và Giai đoạn 6
  khép vòng: một bộ giám sát tất định tự viết `intent.md` mới khi một chỉ số vượt khỏi dải kiểm
  soát (control band).
- **Harness của mình đã triển khai phần lớn nửa Build → Deploy, thường còn chặt chẽ hơn** playbook
  (các tầng bằng chứng, intent oracle không nhìn plan, cấu hình gate đọc từ git index, escalation
  "không trả lời = từ chối", kỷ luật eval trung thực, sổ review-escape).
- **Khoảng trống rõ ràng nằm ở hai đầu và ở khâu đo lường:**
  1. **Eval chạy tay, không liên tục** — play trung tâm của giai đoạn Test (chạy lại eval mỗi khi
     CLAUDE.md / skills / hooks thay đổi) là thứ mình thiếu nhất. `evals/README.md` ghi rõ
     "the LLM runs are triggered manually, not in CI" (các lượt chạy LLM được kích hoạt thủ công,
     không chạy trong CI).
  2. **Không bảo vệ vòng phản hồi** — không có gì tất định ngăn agent sửa chính cái test mà nó
     phải làm cho pass; `weakening-validation` chỉ ở chế độ warn và chỉ chạy lúc commit.
  3. **Không khép vòng trên chỉ số** — `audit-log.jsonl` báo cùng 39 findings ("needs attention")
     ở mọi lần merge từ ít nhất 2026-09-30 mà không ai xử lý: đúng kiểu "cảnh báo không ai hành
     động" mà Giai đoạn 6 được thiết kế để loại bỏ.
  4. **Không có chỉ số dẫn dắt / chỉ số trễ cho từng play** — playbook định nghĩa hai chỉ số tính
     được từ Git cho mỗi play; mình có sổ ghi (ledger) nhưng không có chỉ số được tính toán.
  5. **Ngữ cảnh luôn-nạp quá lớn** — khoảng 30 KB chỉ dẫn luôn-nạp (CLAUDE.md + 5 rule) so với
     khuyến nghị "giữ CLAUDE.md dưới một trang" của playbook.
- **Danh sách đề xuất đã xếp hạng nằm ở §6** — 6 việc dễ, 6 việc trung bình, 4 việc khó.
- **Trạng thái (2026-10-10):** artifact khởi đầu intent.md (§7, thay cho E4) đã ship ở PR #284,
  kèm một bản sửa installer ở PR #285. Những gì đã ship, khác bản phác thảo ở đâu, và đã test thế
  nào nằm ở §8.

---

## 1. Khái niệm

### 1.1 Luận điểm cốt lõi

> "Organizations have started using AI to write code at a speed unthinkable one year ago, yet the
> processes around the code haven't changed at the same pace." — Bài 1
>
> (Các tổ chức đã bắt đầu dùng AI để viết code với tốc độ không tưởng một năm trước, nhưng các
> quy trình xung quanh code thì chưa thay đổi cùng nhịp.)

Sáu giai đoạn kinh điển vẫn giữ nguyên (Plan, Design, Build, Test, Deploy, Maintain), nhưng mỗi
giai đoạn dịch chuyển:

| Giai đoạn | Truyền thống | AI-native (theo playbook) |
|---|---|---|
| Plan | Yêu cầu do hội đồng thu thập, qua workshop, ký duyệt | Claude tổng hợp vấn đề trực tiếp từ nguồn vào `intent.md` — người đọc được, máy thực thi được |
| Design | Analyst viết spec, designer đọc lại | Yêu cầu + thiết kế gộp vào một phiên làm việc với agent, bị ràng buộc bởi chính sách được mã hóa thành skill, có version trong Git |
| Build | Code/test viết tay; tài liệu viết sau | Code/test do AI sinh; tri thức tổ chức lưu thành CLAUDE.md + skills có version |
| Test | Cổng QA ở ranh giới giai đoạn | Eval liên tục đan xen trong quá trình triển khai |
| Deploy | Người review từng dòng; quản trị không nhất quán | Nhiều lớp review bằng agent; review của người dành cho code chịu quản lý/quan trọng; quản trị được thực thi *ngay khi AI hành động* qua hook |
| Maintain | Người canh production | Agent giám sát; dải kiểm soát bị vượt thì được chẩn đoán và ghi ngược thành `intent.md` mới |

Bất biến: **"Humans remain accountable for every decision that requires judgment."** (Con người
vẫn chịu trách nhiệm cho mọi quyết định cần phán đoán.)

### 1.2 Cấu trúc một play

Mỗi play trong 12 play có cùng năm phần — *Cái gì thay đổi · Bắt đầu (điều kiện tiên quyết + hạ
tầng) · Cách thực hiện · Lưu ý quản trị · Cách đo (một chỉ số dẫn dắt và một chỉ số trễ)*. Các
play tạo thành một đồ thị phụ thuộc; sáu play không có điều kiện tiên quyết và là điểm khởi đầu
được khuyến nghị: **intent.md, plan mode, CLAUDE.md, skills, vòng phản hồi, hook làm cổng phê
duyệt**.

### 1.3 Chuỗi artifact (xương sống)

```
trigger (người | ticket | cảnh báo)
  → intent.md   (Vấn đề · Kết quả đề xuất · Người dùng/hệ thống bị ảnh hưởng · Ràng buộc · Câu hỏi mở)
      product owner sửa + merge = phê duyệt
  → spec.md     (yêu cầu đánh số R1..Rn · thiết kế · bảng ràng buộc→"đáp ứng bởi" ·
                 câu hỏi mở được mang sang · Các điểm đáng lo kèm người chịu trách nhiệm)
      product owner ký duyệt; rủi ro cao hơn → tech lead
  → plan.md     (file thay đổi · thứ tự công việc trích R-id · rủi ro · bằng chứng)
      kỹ sư duyệt trong plan mode; plan được cập nhật cùng commit khi triển khai lệch khỏi nó
  → diff + output Verify (test/build/screenshot dán nguyên từ toolchain)
  → review PR (các lượt theo REVIEW.md: bug · bảo mật · tuân thủ spec.md/plan.md)
      code owner duyệt qua branch protection; agent không bao giờ tự duyệt code của mình
  → deploy qua MCP tool, phân tầng theo môi trường, prod bị chặn bởi hook + change ticket
  → giám sát: vượt dải kiểm soát → chẩn đoán → viết intent.md mới  ─┐
  → sự cố đã sửa → trở thành một eval vĩnh viễn                      │
  └────────────────────────────── vòng lặp ─────────────────────────┘
```

ID được đánh số là thứ làm cho chuỗi có thể kiểm tra được: plan trích R-id, lượt review tuân thủ
đọc `plan.md`, và bài học chỉ ra một finding "exists only because the compliance pass reads the
committed plan.md" (chỉ tồn tại vì lượt review tuân thủ đọc plan.md đã commit).

### 1.4 Các nguyên tắc lặp lại xuyên suốt các play

1. **Kiểm soát khuyến nghị vs. kiểm soát tất định.** "A skill is a control, though an advisory
   one… The skill makes violations rare and the hook makes them close to impossible." (Skill là
   một kiểm soát nhưng chỉ mang tính khuyến nghị… Skill làm vi phạm hiếm đi, còn hook làm vi phạm
   gần như không thể.) Mọi chính sách bắt buộc đều có hook *và* cùng một check trong CI, vì
   "an Edit|Write hook does not fire when a shell command rewrites the file" (hook Edit|Write
   không chạy khi một lệnh shell ghi đè file).
2. **Bảo vệ vòng phản hồi.** "An agent fixing code must not be able to weaken the check on that
   code." (Agent đang sửa code không được phép làm yếu đi chính check trên code đó.) Với bug fix:
   viết test fail trước, xác nhận nó fail đúng lý do, commit nó, rồi sửa *mà không đụng vào test*
   (được ép bằng hook chặn sửa file test).
3. **Cấu hình là code và phải có regression test.** Bộ eval chạy "on any change to CLAUDE.md,
   skills, or hooks, since that configuration steers the agent" (mỗi khi CLAUDE.md, skills hoặc
   hooks thay đổi, vì cấu hình đó điều khiển agent). Mỗi sự cố production trở thành một eval.
4. **Cổng phải tự giải thích.** Khi chặn, nó nêu lý do *và đường đi để được phê duyệt*. Hook có
   thể `allow`, `ask`, hoặc `deny`; ở chế độ không tương tác `ask` thành deny, nên pipeline phải
   có đường allow tường minh; production thì fail-closed. "The gate depends on the agent having no
   way to write to the records it reads." (Cổng chỉ đứng vững khi agent không thể ghi vào chính
   các bản ghi mà cổng đọc.)
5. **Đưa con người ra khỏi đường găng của Build.** Prompt xin phê duyệt thuộc về Deploy, không
   thuộc Build, "because an approval prompt during the build puts a person back on the critical
   path of all the sessions running in parallel" (vì prompt phê duyệt lúc build đặt con người trở
   lại đường găng của mọi phiên đang chạy song song). Hook lúc build phải nhanh và chỉ xét file
   vừa sửa; check nặng để ở commit/PR.
6. **Tách biệt trách nhiệm.** Agent viết code không thể duyệt nó; sự chú ý của con người được
   "nâng lên một tầng" — xét ý định và rủi ro.
7. **Tự chủ phân tầng theo bán kính ảnh hưởng.** Dev: tự do. Staging: hỏi / pipeline từ main.
   Prod: agent chuẩn bị, release manager cấp phép. Rollback là "the most rehearsed path in the
   pipeline" (đường đi được diễn tập nhiều nhất trong pipeline).
8. **Phát hiện tất định, chẩn đoán bằng mô hình.** Giai đoạn 6 giữ phần phát hiện "entirely
   deterministic, with no model involved" (hoàn toàn tất định, không dùng mô hình) — trung bình
   ± σ trên cửa sổ 30 ngày + luật Western Electric cho trôi dạt chậm. Các tầng: 1σ ghi log · 2σ
   chẩn đoán chỉ-đọc · 3σ đề xuất (chỉ qua PR hoặc runbook đã duyệt trước).
9. **Đo từ Git.** Gần như mọi chỉ số là hai mốc thời gian Git hoặc một phép đếm commit (vd: "đếm
   số commit `spec.md` sau commit `plan.md` đầu tiên" = mức làm lại yêu cầu).
10. **Giữ ngữ cảnh luôn-nạp nhỏ.** CLAUDE.md "under a page" (dưới một trang); "When Claude makes a
    mistake twice, the correction goes into CLAUDE.md." (Khi Claude mắc cùng một lỗi hai lần, phần
    sửa được đưa vào CLAUDE.md.)
11. **Mỗi artifact một nguồn sự thật.** Repo là nguồn sự thật, hệ thống cũ là nguồn sự thật (ghi
    ngược qua MCP), hoặc *liên kết là mức tối thiểu* (artifact trích ID bản ghi, bản ghi trích
    SHA commit).

---

## 2. Từng play: triển khai thế nào

| # | Play | Cơ chế triển khai chính | Chỉ số dẫn dắt / chỉ số trễ |
|---|---|---|---|
| 1 | **Ghi lại bằng intent.md** | Người khởi xướng brainstorm với Claude; template của tổ chức mã hóa thành skill; product owner sửa; commit vào `intent/` trong repo sản phẩm (connector commit thay cho người không dùng Git) | Thời gian từ cuộc trò chuyện đầu → intent được commit / tỉ lệ sống sót + số lần sửa intent sau commit spec đầu tiên |
| 2 | **Yêu cầu và thiết kế** | Prompt: áp dụng skills, tạo `spec.md`, "describe clearly any areas of concern, especially where you cannot satisfy contradicting policies" (mô tả rõ các điểm đáng lo, nhất là chỗ không thể thỏa các chính sách mâu thuẫn). Chạy tay → slash command → job không tương tác kích hoạt khi intent được merge, mở PR spec | Độ trễ intent→spec / số commit spec sau commit plan đầu tiên |
| 3 | **Plan mode làm mặc định** | Plan nêu file, thứ tự, test; chất vấn rủi ro & phương án bị loại; lặp "until an engineer who has never seen the conversation could implement the change from the plan alone" (đến khi một kỹ sư chưa từng thấy cuộc trò chuyện vẫn triển khai được chỉ từ plan); commit `plan.md`; giữ đồng bộ (gợi ý dùng hook). Auto mode cho việc thường ngày khi guardrail đã chín | Tỉ lệ merge ngay lượt đầu, thời gian plan→merge / số vòng làm lại, diff đã merge còn khớp plan không |
| 4 | **CLAUDE.md** | `/init`, cắt còn kiến thức ngày đầu (lệnh, quy ước, "những thứ Claude hay làm sai"), < 1 trang, code owner review | Tỉ lệ lặp lỗi / thời gian đến PR đầu tiên của người mới |
| 5 | **Skills là tri thức tổ chức** | Một chính sách đang được thực thi không đều → SKILL.md có mô tả trigger; test việc kích hoạt bằng nhiều cách diễn đạt; chủ chính sách ký duyệt thay đổi; chống lưng bằng PostToolUse hook + check PR y hệt | Thời gian từ duyệt thay đổi chính sách → skill được merge / findings trong PR trích chính sách → về 0 |
| 6 | **Phiên song song & subagent** | Mỗi task một worktree, chia task theo tính độc lập của file; 2–3 phiên, chỉ thêm "while review is keeping up" (khi review còn theo kịp); việc lặp lại thành `.claude/agents/` (verifier: "Do not fix anything; report only" — không sửa gì, chỉ báo cáo) | Số phiên đồng thời mà chất lượng review vẫn giữ / số thay đổi merge × tỉ lệ làm lại |
| 7 | **Vòng phản hồi** | Test/build một lệnh, kèm ví dụ output khỏe mạnh trong CLAUDE.md; mục tiêu định lượng; test-fail-trước cho bug; vòng hình ảnh cho UI; "chạy test trước khi báo xong, dán output"; hook chặn sửa test trong lúc fix | Tỉ lệ CI pass lượt đầu / thời gian review mỗi PR, tỉ lệ thay đổi gây lỗi |
| 8 | **Eval liên tục trong CI** | 20–50 task thật; eval JSON = commit `from` + prompt + `may_change` + các check; chạy trong worktree nháp đã xóa `evals/` và chép cấu hình của *branch* vào; bộ chấm chạy từ bản sao tạo trước lượt chạy; fail nếu có file lạc ngoài phạm vi; kích hoạt khi cấu hình đổi + hằng đêm; không bao giờ dùng `--bare` (nó bỏ qua chính cấu hình đang được test) | Xu hướng tỉ lệ pass, độ trễ sự cố→eval / regression bắt được trong CI so với ở prod |
| 9 | **AI trong vòng review PR** | `REVIEW.md`: các lượt (bug / bảo mật / tuân thủ spec+plan), định nghĩa "Important" vs "Nit", giới hạn nit (5), danh sách không báo cáo; findings tự nó không duyệt/chặn; vòng sửa `@claude`; finding lặp lần hai đưa vào CLAUDE.md; tinh chỉnh hằng tháng bằng chấm điểm findings | Thời gian đến review đầu, tỉ lệ comment được xử lý không cần người / lỗi bắt trước merge so với lỗi lọt |
| 10 | **Hook làm cổng phê duyệt** | Liệt kê các phê duyệt phải giữ; mỗi cổng một hook allow/ask/deny; hook của team trong `.claude/settings.json`, hook không thể thương lượng trong managed settings; thông báo chặn = lý do + đường phê duyệt. Managed settings bổ sung permissions allow/deny, sandbox (allowlist mạng, chặn credential), `allowManagedHooksOnly`, allowlist marketplace, phiên bản tối thiểu | Thời gian chờ mỗi cổng (OTel) / vi phạm lọt ra prod |
| 11 | **Tích hợp CI/CD** | Bắt đầu với bước phán đoán chỉ-đọc bằng `claude -p` (phân loại build fail, changelog); sau đó bước ghi đều thành PR; sandbox, token ngắn hạn có phạm vi; deploy/status/rollback là MCP server riêng cho từng môi trường; `--permission-mode dontAsk` | Số lỗi pipeline được phân loại mà không cần gọi người / DORA |
| 12 | **Khép vòng trên chỉ số** | Chọn một chỉ số ổn định; script dải σ tất định (có version, có unit test); `bands.yaml` ánh xạ tầng→tool/route; chạy headless không trạng thái; output là `intent.md` vào hàng chờ phân loại; các lần bác bỏ dùng để chỉnh dải; sự cố đã sửa → eval. Claude Tag cho sự cố đến từ chat | Độ trễ vượt dải→intent / tỉ lệ findings thành fix được merge, tỉ lệ sự cố lặp lại |

---

## 3. Đối chiếu với harness của mình

Trạng thái: ✅ mạnh · 🟡 một phần · ❌ thiếu · ➖ không áp dụng cho repo này.

| Play | Tương đương trong harness | Trạng thái | Bằng chứng / phạm vi đã tìm |
|---|---|---|---|
| intent.md | `SUMMARY.md` `### Intent` — yêu cầu **nguyên văn**, làm oracle cho `/intent-review`; sổ câu hỏi mở `QUESTIONS.template.md`; tiền tố slug `gh-NNN` làm liên kết ticket | 🟡 | `templates/SUMMARY.template.md`; `skills/feature-intake/SKILL.md:29`. Nguyên văn ≠ có cấu trúc: không có trường Vấn đề / Kết quả / Ràng buộc / Ngoài phạm vi; không có chỉ số tỉ lệ sống sót |
| spec.md | `/brainstorming` → `design.md` (chỉ khi có ngã rẽ thiết kế thật), `/xia2` → `research-brief.md`, tiêu chí thành công `SC-n` ở PLAN §3 được `verify_summary.py` ép; `ESCALATIONS.md` cho các điểm đáng lo | 🟡 | `rules/orchestration.md` (artifact policy). Không có bảng "ràng buộc → đáp ứng bởi"; các điểm đáng lo không gắn người chịu trách nhiệm trong artifact thiết kế; với repo tiêu thụ, ràng buộc chính sách dạng skill phụ thuộc `techstacks/` vốn được ship rỗng |
| Plan mode | `/writing-plans` → `PLAN.md` (Files, waves, Verify, SC-n), `/visual-planner`, `check_plan_scope` cảnh báo path ngoài plan | ✅ | `rules/plan-format.md`; bảng hook trong CLAUDE.md. Đồng bộ plan↔diff chỉ warn (`BLAST_RADIUS_STRICT=1` để chặn); không có chỉ số "diff còn khớp plan" |
| CLAUDE.md | CLAUDE.md + 5 rule luôn-nạp; `/compound` + `critical-patterns.md` + `/session-retro` cho "học từ lỗi" | 🟡 | `wc -c` của CLAUDE.md + 5 rule luôn-nạp = 30.814 byte (~7–8k token) so với "dưới một trang". Không có luật "lỗi hai lần → luôn-nạp"; tỉ lệ lặp lỗi không được đo |
| Skills | 13 skill; eval kích hoạt (should-trigger + near-miss, ≥8 mỗi chiều + holdout); nguyên tắc gate-verifiability ghép nhận định với tầng thực thi | ✅ | `evals/skills/prompt-refactor/README.md`; `skills/README.md` |
| Phiên song song & subagent | Các wave của `/subagent-driven-development`, `/using-git-worktrees`, các agent chỉ-đọc `reviewer` / `task-reviewer` / `test-runner`, file tách rời theo `wave-parallelism.md` | ✅ | `agents/`, `rules/wave-parallelism.md`. Đi trước playbook: reviewer bị ép chỉ-đọc ở mức tool |
| Vòng phản hồi | Các dòng `### Verify` (chạy lại được, có exit code), cổng chạy lại `REQUIRE_VERIFY=1`, agent `test-runner` | 🟡 | Không bảo vệ việc sửa test: `hooks/` chỉ có `branch-isolation-guard.sh`, `commit-gate.sh`, `session-knowledge.sh`; `settings.json` chỉ đăng ký PreToolUse + SessionStart; `weakening-validation` là `"mode": "warn"` trong `harness-manifest.json`. Không có quy trình test-fail-trước: grep "failing test / regression test" trong SKILL.md của `feature-intake` và `subagent-driven-development` không ra kết quả |
| Eval liên tục trong CI | `evals/` (intake-classifier, review-chain, task-review, test-runner, prompt-refactor) với chạy mù + bộ chấm tất định | ❌ (về tính *liên tục*) / ✅ (về *chất lượng* eval) | `evals/README.md`: "the LLM runs are triggered manually, not in CI". `.github/workflows/` = `harness-ci.yml`, `post-merge-maintenance.yml` — không cái nào chạy eval |
| AI trong review PR | `/correctness-review` (có chấm điểm), `/intent-review` (không nhìn plan), `/context-propagation-audit`, review receipt được ghim lúc mở PR, `docs/review-escapes.md` (review Codex bên ngoài → fixture) | 🟡 | Mạnh ở trước PR. Không có `REVIEW.md` (`ls REVIEW.md` → không tồn tại) định nghĩa mức nghiêm trọng / giới hạn nit / danh sách không báo cáo; không có vòng sửa `@claude` trong PR ở CI của mình |
| Hook làm cổng phê duyệt | `commit-gate.sh` (secrets, escalation, lane-evidence, risk corroboration, plan scope…), `branch-isolation-guard.sh`, `ESCALATIONS.md` không-trả-lời-là-từ-chối, profile minimal/standard/strict, biến môi trường break-glass | ✅ | Bảng hook trong CLAUDE.md. Thiếu: key cấp cao nhất của `settings.json` chỉ có `hooks` (không `permissions`, không `sandbox`); không dùng quyết định `ask`; thông báo deny mới kiểm tra mẫu một chỗ (`commit-gate.sh:117` có lý do + đường xử lý "Run: git add…") — các chỗ còn lại **chưa rõ** |
| CI/CD | `harness-ci` (ubuntu+macOS), `ci-strict-gate.sh` hai tầng, PR bookkeeping sau merge, `### Rollback` bắt buộc ở high-risk | 🟡 / ➖ | Không có bước phán đoán `claude -p` trong CI (grep `claude -p` ngoài specs chỉ ra test/ghi chú eval). Phân tầng deploy/MCP ➖ (không có ứng dụng được deploy) |
| Khép vòng | Sổ `trust-metrics.md` (82 dòng, mới nhất 2026-10-02), `harness-audit.sh` → `audit-log.jsonl` + band, `harness-status.sh` | 🟡 | Band là ngưỡng cố định, không dựa trên σ; ba dòng cuối đều `findings: 39` ("solutions_stale": 31, "backlog_stale": 8) và không có đường phản hồi → không gì biến một lần vượt ngưỡng thành intent |
| Nguồn sự thật | `specs/` được track trong Git; slug `gh-NNN`; tham chiếu Linear (vd `MIN-64`) trong ledger | 🟡 | Liên kết có nhưng không chính thức; không có rule nêu nguồn sự thật cho từng artifact |

### 3.1 Chỗ harness đi trước — giữ lại, đừng "đơn giản hóa" theo playbook

- **Các tầng bằng chứng** (traceability ≠ provenance ≠ truth) với dòng `Verifies:` /
  `Does not verify:` bắt buộc. Playbook không bao giờ phân biệt "dòng đó có tồn tại" với "dòng đó
  trung thực".
- **Intent oracle độc lập với plan.** Lượt review tuân thủ của playbook đối chiếu với `plan.md`;
  `/intent-review` của mình đối chiếu với *yêu cầu nguyên văn, không nhìn plan*, nên bắt được một
  plan sai mà vẫn pass review của chính nó. (Playbook dựa vào product owner cho việc này.)
- **Cấu hình gate đọc từ git index** (`gate-config-must-read-index.md`) — chính cổng release của
  playbook thừa nhận "an engineer could set `GITHUB_REF` by hand" (kỹ sư có thể tự đặt
  `GITHUB_REF`); mình đã coi cấu hình mà agent ghi được là không đáng tin.
- **Escalation không-trả-lời-là-từ-chối** — mạnh hơn "ask", và chạy được ở chế độ headless.
- **Kỷ luật eval trung thực** (lần chạy đầu là bản ghi; nhận định chỉ trong phạm vi fixture) và
  cảnh báo n nhỏ từ `2026-07-22-self-improving-harness-adoption.md` — câu "mọi eval đều pass /
  có thể ngưỡng thấp hơn" của playbook không nói gì về nhiễu khi n = 20–50.
- **Sổ review-escape** = phiên bản "mỗi sự cố thành một eval" của playbook, đã áp dụng cho các
  lỗi lọt qua review.

### 3.2 Chỗ playbook không áp dụng được

- **Người viết không phải kỹ sư, Cowork, vai trò product owner, Claude Design** — đây là meta-repo
  một người. Chỉ liên quan dưới dạng hướng dẫn mình ship cho repo tiêu thụ.
- **Managed settings qua MDM** — ở đây không có tổ chức; nhưng repo tiêu thụ nào bật
  `allowManagedHooksOnly` sẽ âm thầm vô hiệu hóa hook cấp project của mình trừ khi chuyển chúng
  vào managed settings. Đây là lỗ hổng tài liệu đáng lấp (xem M6).
- **Tự sinh spec.md khi intent được merge** — nghi thức mà mình cố ý chỉ bật theo tín hiệu
  (artifact policy trong `rules/orchestration.md`). Đừng thêm.
- **Hook xin phê duyệt người trong lúc Build** — chính playbook nói không; thiết kế của mình đã
  đồng ý (lane quyết định nghi thức, confidence quyết định có làm gián đoạn hay không).

---

## 4. Bài học, rút gọn thành những gì thay đổi cho mình

1. Mắt xích yếu nhất của mình cũng chính là thứ playbook đặt ở trung tâm: **cấu hình điều khiển
   agent (skills, rules, CLAUDE.md, agents) không có regression test khi thay đổi.** Mình test
   *hook* rất kỹ (`scripts/run-tests.sh`) nhưng *prompt* thì chỉ test tay.
2. **Một check mà agent sửa được thì không phải là check.** Mình áp dụng điều này cho cấu hình gate
   (chỉ đọc từ index) nhưng chưa áp dụng cho test trong lúc fix.
3. **Một chỉ số không có tầng phản hồi chỉ là đồ trang trí.** `audit-log.jsonl` là bằng chứng.
4. **Mỗi artifact nên mang ID để giai đoạn sau trích dẫn.** Mình có `SC-n` và Files; nhưng thiếu ở
   cấp intent (ràng buộc / câu hỏi mở không có địa chỉ để trích), nên intent oracle chỉ so được
   văn xuôi.
5. **Ngữ cảnh luôn-nạp nhỏ là một tính năng.** Mỗi byte luôn-nạp phải trả ở mọi phiên; chi tiết
   nên nằm ở rule theo path hoặc skill (cơ chế nạp rule hai tầng của mình đã hỗ trợ sẵn).

---

## 5. Câu hỏi mở

- Ngân sách: memory ghi rằng GitHub Actions đã chạm giới hạn billing ngày 2026-10-08 — eval LLM
  liên tục trên CI hosted có thể không kham nổi. Phương án thay thế khả dĩ là chạy local theo lịch
  hoặc self-hosted runner. **Cần bạn quyết định.**
- Các trường intent có cấu trúc nên do agent điền (rủi ro: diễn giải trôi dạt vào oracle) hay chỉ
  giữ khối nguyên văn làm oracle và phần cấu trúc chỉ là *góc nhìn dẫn xuất*? Ghi chú này đề xuất
  cách thứ hai.
- Hướng dẫn cho repo tiêu thụ (managed settings, REVIEW.md, sandbox) nên nằm trong `templates/` của
  repo này hay chỉ trong `docs/`.

---

## 6. Đề xuất — xếp từ dễ đến khó

Công sức: **S** ≈ vài giờ · **M** ≈ 1–3 ngày · **L** ≈ một tuần trở lên. Lane là lane dự kiến
của `feature-intake` theo các luật hard-gate hiện tại (sửa `hooks/`, `settings.json`,
`templates/`, hoặc văn bản workflow-engine sẽ nâng lane).

### Dễ (S)

| ID | Đề xuất | Nguồn trong playbook | Ở đâu | Lane |
|---|---|---|---|---|
| **E1** | **Viết chính sách review (kiểu `REVIEW.md`) cho các skill review**: thế nào là Important vs Nit, giới hạn số nit, danh sách không báo cáo (file sinh tự động, thứ CI đã ép), và nhãn bắt buộc "tuân thủ PLAN.md SC-n + SUMMARY Intent" trên mỗi finding | Play 9 | `REVIEW.md` mới hoặc một mục trong `skills/correctness-review/` | normal (workflow-engine → audit) |
| **E2** | **Rà mọi thông báo deny theo mẫu "lý do + đường phê duyệt"** và bổ sung dòng chỉ đường còn thiếu (vd "đặt `BRANCH_ISOLATION_REASON=…`", "ghi quyết định vào ESCALATIONS.md") | Play 10 | `hooks/commit-gate.sh`, `hooks/branch-isolation-guard.sh`, `hooks/lib/` | high-risk (hooks) |
| **E3** | **Thêm luật "lỗi hai lần" vào `/compound`**: một bài học tái diễn lần thứ hai được nâng lên `critical-patterns.md` (hoặc một rule theo path), và việc nâng cấp đó là output của compound | Play 4, Play 9 bước 4 | `skills/compound/SKILL.md` | normal |
| **E4** | ✅ *Được thay bằng §7, đã ship ở PR #284 (xem §8).* **Góc nhìn intent có cấu trúc bên dưới khối nguyên văn**: các trường tùy chọn `Vấn đề / Kết quả / Ràng buộc (C1..) / Ngoài phạm vi / Câu hỏi mở (Q1..)`, ghi rõ là *dẫn xuất, không phải oracle*; `/intent-review` vẫn chỉ dùng văn bản nguyên văn | Play 1 | `templates/SUMMARY.template.md`, `skills/feature-intake/SKILL.md` | high-risk (templates) |
| **E5** | **Quy trình test-fail-trước cho bug fix**: khi `Input-type` là bug fix, bảng `### Verify` phải có một dòng đỏ (test fail trước khi sửa, kèm sha commit) và một dòng xanh sau khi sửa | Play 7 | `skills/feature-intake`, `skills/subagent-driven-development`, `scripts/verify_summary.py` (trước mắt chỉ cảnh báo) | normal → high-risk nếu đổi logic verifier |
| **E6** | **Định nghĩa một chỉ số dẫn dắt + một chỉ số trễ cho mỗi giai đoạn workflow** trong `trust-metrics.md` (chỉ định nghĩa, chưa làm công cụ) — vd độ trễ intake→PLAN, tỉ lệ task-review pass lượt đầu, độ lệch plan, tỉ lệ review-escape | Mục "How to measure it" của mọi play | `docs/harness-experimental/trust-metrics.md` | tiny |

### Trung bình (M)

| ID | Đề xuất | Nguồn trong playbook | Ở đâu | Lane |
|---|---|---|---|---|
| **M1** | **Cắt ngữ cảnh luôn-nạp về gần "một trang"**: chuyển chi tiết bảng hook, ranh giới Codex alpha, và phần Gotchas dài ra khỏi CLAUDE.md sang `HARNESS.md` / rule theo path; giữ lệnh, chuỗi workflow, và "những thứ agent hay làm sai". Đo số byte trước/sau | Play 4 | `CLAUDE.md`, `rules/` (lưu ý: bỏ trạng thái luôn-nạp là thay đổi hành vi theo CLAUDE.md) | high-risk (định nghĩa lại tập luôn-nạp) |
| **M2** | **Hook bảo vệ test trong lúc fix**: PreToolUse Edit/Write chặn sửa path test khi danh sách Files của task SDD đang chạy không chứa chúng (hoặc task là bug fix đã qua commit test đỏ); biến môi trường break-glass có lý do; lặp lại check ở commit/CI vì hook Edit bỏ sót ghi đè bằng shell | Play 7, Play 10 | hook mới hoặc mở rộng `branch-isolation-guard.sh` + `ci-strict-gate.sh` | high-risk |
| **M3** | **Đồng bộ plan↔diff**: khi commit của một wave stage path ngoài PLAN Files, yêu cầu PLAN.md trong cùng commit (warn → block sau một giai đoạn đo độ chính xác, như lịch sử của `weakening-validation`) | Play 3 | `check_plan_scope` trong `commit-gate.sh` | high-risk |
| **M4** | **Script tính chỉ số**: tính các chỉ số ở E6 từ Git + SUMMARY + ledger (độ trễ từ thời gian commit, độ lệch plan = path đã merge ∖ PLAN Files, làm lại = số vòng fix được ghi vào SUMMARY vì `.harness-state/` bị gitignore); hiển thị trong `harness-status.sh` | Phần đo lường của Play 3/4/12 | `scripts/harness-status.sh`, `scripts/harness_indicators.py` mới | normal |
| **M5** | **Áp dụng cách gia cố eval runner của playbook cho các eval hiện có**: mỗi fixture ghim một commit `from` và `may_change`; chạy trong worktree nháp đã xóa `evals/`; bộ chấm được chép trước lượt chạy; check file lạc làm fail lượt chạy; không bao giờ dùng `--bare`. Bắt đầu với `intake-classifier` (rẻ nhất, đã có bộ chấm tất định) | Play 8 | `scripts/run_*_eval.py`, `evals/workflow/intake-classifier/` | normal |
| **M6** | **Profile bảo mật cho repo tiêu thụ + hướng dẫn managed settings**: `permissions.allow` cho vòng lặp trong an toàn + chặn đọc secret trong profile strict; tài liệu về `allowManagedHooksOnly` (hook của mình phải chuyển vào file managed, không thì sẽ ngừng chạy) và credential trong sandbox | Play 10 (managed settings) | các profile của `scripts/install-harness.sh`, `docs/` | high-risk (settings/install) |

### Khó (L)

| ID | Đề xuất | Nguồn trong playbook | Ở đâu | Lane |
|---|---|---|---|---|
| **H1** | **Cổng eval liên tục khi cấu hình thay đổi**: mọi diff vào `skills/`, `rules/`, `agents/`, `CLAUDE.md`, hoặc `templates/` chạy nhóm eval liên quan (`claude -p` headless) và chặn merge theo tỉ lệ pass — dùng luật biên/ý nghĩa thống kê, không phải chỉ "không thụt lùi" (phát hiện về n nhỏ từ ghi chú 2026-07-22). Chạy local hoặc trên self-hosted runner do giới hạn billing của Actions | Play 8 | workflow mới hoặc `scripts/run-config-evals.sh` chạy local + nối vào `ci-strict-gate.sh` | high-risk |
| **H2** | **Dải kiểm soát trên chính các chỉ số của harness** (findings của audit, tỉ lệ CI fail, tỉ lệ review-escape, số vòng fix của task-review): script σ + Western Electric tất định, có unit test; các tầng trong `bands.yaml` là log / chẩn đoán (chỉ-đọc) / đề xuất (chỉ qua PR) | Play 12 | bản kế nhiệm `scripts/harness-audit.sh`, `post-merge-maintenance.yml` | high-risk |
| **H3** | **Vượt dải → intent → intake**: tầng đề xuất viết bản nháp `### Intent` của SUMMARY (tác giả: agent giám sát) và chuyển vào `/feature-intake`; các lần bác bỏ dùng để chỉnh dải. Mục tiêu đầu tiên: các findings đang kẹt `solutions_stale: 31` / `backlog_stale: 8` | Play 12 | xây trên H2 + `skills/feature-intake` | high-risk (định nghĩa lại điểm vào workflow) |
| **H4** | **Vòng review bằng agent trong PR** cho repo tiêu thụ: `claude-code-action` chạy một lượt theo REVIEW.md có đọc PLAN.md + SUMMARY, vòng sửa `@claude` đến khi xanh, finding lặp lần hai tự đề xuất cho `/compound`; phê duyệt của code owner vẫn là đường merge duy nhất | Play 9, Play 11 | template cho repo tiêu thụ / ví dụ `.github/` | high-risk |

### Thứ tự đề xuất

`E6 → E2 → E1 → E3 → E5 → E4` (mỗi việc độc lập và rẻ), rồi `M5 → H1` (khoảng trống lớn nhất,
và M5 là điều kiện tiên quyết của H1), rồi `M2 → M3` (bảo vệ vòng phản hồi), rồi `M4 → H2 → H3`
(đo trước, khép vòng sau). `M1` và `M6` làm lúc nào cũng được; `H4` làm cuối, vì nhắm tới repo
tiêu thụ.

---

## 7. Quyết định (2026-10-10): `specs/<slug>/intent.md` là artifact khởi đầu workflow

E4 đưa ra hai hướng. **A** giữ lời yêu cầu trong chat làm intent duy nhất và thêm một góc nhìn có
cấu trúc dẫn xuất bên dưới. **B** dùng GitHub issue làm intent. Bạn thấy đi qua issue quá phiền,
nên chọn **một file trong repo**: ai cũng có thể viết `specs/<slug>/intent.md` theo chuẩn playbook,
chuyển cho team, và workflow bắt đầu từ chính file đó. Cách này khớp với chính lời khuyên của
playbook là "the simplest home is an intent/ folder in the product repo" (chỗ đơn giản nhất là một
thư mục intent/ trong repo sản phẩm). Ở đây thư mục đó là `specs/<slug>/`, nên intent nằm ngay cạnh
SUMMARY, PLAN và design mà nó sinh ra.

### Vì sao cách hiện tại khác playbook

| | Playbook `intent.md` | Harness `### Intent` hiện tại |
|---|---|---|
| Ai viết | Người khởi xướng + Claude, qua brainstorm | User gõ chat; intake chép lại |
| Hình thức | Template có cấu trúc | Văn xuôi nguyên văn |
| Khi nào làm rõ | Trước khi làm, ngay trong intent | Sau đó, ở design/plan, chỉ khi có tín hiệu |
| Cổng duyệt của người | Product owner, luôn luôn | Chỉ khi confidence thấp, mơ hồ, hoặc chạm hard gate |
| Vai trò chính | Đầu vào cho spec | Thước đo cho `/intent-review` lúc cuối |

Tác dụng phụ đã thấy: `### Intent` trong `specs/gh-258-sc-goalpost-guard/SUMMARY.md` chứa các câu
chat của user, đoạn trích item trong issue, **và một đoạn agent tự viết về confidence**. Tức là
thước đo "nguyên văn" đã lẫn văn của agent. Một file intent sửa được điều này vì thước đo có nguồn
do con người sở hữu.

### Luồng hoạt động

```
ai đó viết specs/<slug>/intent.md       (theo template; có thể nháp cùng Claude)
  → đặt Status: approved, commit         (được phép trên main: specs/* được miễn branch guard)
  → chuyển slug cho team
  → thành viên team chạy /feature-intake <slug>
      intake đọc intent.md, ghim theo commit SHA, phân loại lane/confidence, định tuyến
  → brainstorming / xia2 / writing-plans trích các ID C-n và Q-n từ intent
  → /intent-review chấm diff theo intent.md tại SHA đã ghim
```

### Phác thảo thiết kế (như đã chốt; bản ship khác vài chỗ — xem §8)

1. **Template** `templates/INTENT.template.md`, chép thành `specs/<slug>/intent.md`:
   phần đầu `Author:` · `Status: draft | approved` · `Approved-by:`; các mục *Vấn đề · Kết quả mong
   muốn · Người dùng và hệ thống bị ảnh hưởng · Ràng buộc (C1..) · Ngoài phạm vi · Câu hỏi mở (Q1..)
   · Thế nào là thành công*. Ví dụ trong playbook không có mục Ngoài phạm vi và Thành công; thêm vào
   vì `/intent-review` cần kiểm tra phần làm thừa và plan cần tiêu chí thành công.
2. **Duyệt là một trường, do người commit.** Intake từ chối `Status: draft` (hỏi lại hoặc
   escalate thay vì bắt đầu làm). Tác giả commit + thời gian commit là bản ghi kiểm toán, giống
   playbook.
3. **Điểm vào của intake.** `/feature-intake <slug>` (hoặc một đường dẫn) đọc
   `specs/<slug>/intent.md` thay cho chat. Khi đó `### Intent` trong `SUMMARY.md` chứa dòng nguồn
   gốc `Intent-source: specs/<slug>/intent.md @ <commit-sha>` cùng các câu chat (nếu có) nguyên
   văn; không chép lại cả file (file đã được track, SHA là đủ để ghim).
4. **Ghim, không đọc bản đang sống.** `/intent-review` đọc
   `git show <sha>:specs/<slug>/intent.md`, không đọc bản trong working copy, nên sửa intent trong
   lúc triển khai không thể "dời cột gôn". Sửa sau SHA đã ghim được báo là drift; số lần sửa như
   vậy chính là chỉ số trễ "intent bị sửa sau spec" của playbook. `intent-review` đã có
   `Bash(git log *)` và `Bash(git diff *)`; cần thêm `git show` vào `allowed-tools`.
5. **Ghi chú của agent ra khỏi thước đo.** Lập luận về confidence và các giả định mặc định chuyển
   sang mục mới `### Intake notes`; `### Intent` và `intent.md` chỉ chứa văn do người viết.
6. **ID được mang theo.** Ràng buộc `C-n` được task trong PLAN và finding của intent-review trích
   dẫn; câu hỏi mở `Q-n` thành mục `OQ-n` trong `QUESTIONS.md`, hoặc `ESCALATIONS.md` nếu chặn việc.
7. **Đường dự phòng.** Không có file intent → giữ cách hiện tại (chép nguyên văn chat). Lane tiny
   không bao giờ cần file này.
8. **Hỗ trợ soạn thảo (để sau).** Bước "brainstorm đến khi cụ thể" của playbook có thể thành một
   chế độ nháp: phỏng vấn tác giả rồi viết `intent.md` ở `Status: draft`. Bản đầu chưa cần: chỉ
   riêng template đã đủ để ai cũng viết được.

### Những gì bị đụng tới, và lane

`templates/INTENT.template.md` (mới), `templates/SUMMARY.template.md` (dòng nguồn gốc,
`### Intake notes`), `skills/feature-intake/SKILL.md` (đọc file intent, từ chối draft),
`skills/intent-review/SKILL.md` (thước đo theo SHA đã ghim, check drift, thêm `git show` vào
`allowed-tools`), có thể cả `scripts/verify_summary.py` (kiểm tra dòng `Intent-source`) và
`scripts/install-harness.sh` (ship template), cộng sơ đồ workflow trong `CLAUDE.md` /
`skills/README.md`. Đụng `templates/` + văn bản workflow-engine → lane **high-risk**, chạy đủ chuỗi.
Không phụ thuộc GitHub.

Đã kiểm tra (2026-10-10): một commit chỉ stage `specs/<slug>/intent.md`, chưa có `SUMMARY.md`, qua
được `hooks/commit-gate.sh` ở cả profile standard lẫn strict (exit 0, chạy trong worktree tạm). Mỗi
check xét `specs/<slug>/` đều bỏ qua slug khi file của riêng nó không tồn tại: escalation cần
`ESCALATIONS.md`, lane evidence cần `SUMMARY.md`, run state cần `RUN.json`/`events.jsonl`; quét
secrets và risk corroboration loại trừ `*.md` và `specs/`; plan scope bỏ qua `specs/*`. Đây là
hành vi của hook hiện tại, nên khi triển khai cần thêm một regression test để giữ nó luôn đúng.

Rủi ro: tác giả không dùng Git cần người khác (hoặc một connector) commit giúp; một `intent.md`
viết tự do, bỏ qua template sẽ làm yếu việc trích C-n/Q-n, nên intake cần cảnh báo khi thiếu mục.

---

## 8. Trạng thái triển khai (2026-10-10)

### Những gì đã ship

**PR #284** (`feat/intent-md-entry` → `sdlc`, merge thành `8ee9826`; lane high-risk, chạy đủ
chuỗi; hồ sơ spec ở `specs/intent-md-entry/`):

| Phần | File | Hành vi |
|---|---|---|
| Template | `templates/INTENT.template.md` | `Author:`, dòng `Status:` để trống kèm ghi chú chọn `approved` hoặc `draft`, và bảy mục: Problem · Proposed outcome · Affected users and systems · Constraints · Out of scope · Open questions · What success looks like |
| Intake đọc intent trước | `skills/feature-intake/SKILL.md` Step 1 | Dòng header `Status:` (phía trên `##` đầu tiên) phải đúng chữ `approved`; ghim SHA bằng `git log -1 --format=%H --diff-filter=AM -- specs/<slug>/intent.md`; dừng khi pin rỗng hoặc có sửa chưa commit; phân loại từ intent.md **cộng** chat request |
| Nguồn gốc trong SUMMARY | `templates/SUMMARY.template.md` | `### Intent` mở đầu bằng `Intent-source: specs/<slug>/intent.md @ <sha>`, sau đó là chat request nguyên văn; lập luận của agent chuyển sang mục mới `### Intake notes`, nằm ngoài oracle |
| Chạy lại intake (re-pin) | `skills/feature-intake/references/re-pin.md` | Chỉ dời dòng pin và thêm một dòng ghi chú có ngày. Dừng và hiện classification cũ/mới khi lane đổi, confidence là `low`, xuất hiện hard gate mà `Reason:`/`Flags:` chưa nêu, hoặc intent.md bị xóa. Pin không đổi → không sửa gì. Không có trạng thái `ESCALATIONS.md`: người tự sửa SUMMARY rồi chạy lại |
| Kiểm tra drift khi review | `skills/intent-review/SKILL.md` bước 1 | `git diff --exit-code <pin> -- specs/<slug>/intent.md`; khác 0 → dừng, yêu cầu re-pin |
| Loại trừ khỏi rule | `rules/terminology.md`, `skills/README.md`, `templates/structure/specs-README.md` | Hard exclusion 1 giờ bao cả `intent.md` lẫn `### Intent` |
| Regression cho commit-gate | `tests/hooks/commit-gate-evidence.test.sh` | Commit chỉ có intent.md (không SUMMARY) đi qua, cả standard lẫn strict |

**PR #285** (`fix/installer-ignore-run-lock` → `sdlc`, merge thành `b6395aa`; lane normal): lần
thử cài thật bên dưới cho thấy `specs/<slug>/events.jsonl.lock` (file khóa fcntl của
`runtime/run_state.py`) hiện là untracked ở repo consumer. `scripts/install-harness.sh` giờ thêm
`specs/**/events.jsonl.lock` vào `.gitignore` của consumer, dùng
`git check-ignore --no-index -v -n` để biết một rule trong `.gitignore` dùng chung đã phủ nó chưa.
Nhờ vậy rule hẹp cho một spec, rule phủ định path không liên quan, hay rule chỉ nằm trong
`.git/info/exclude` không làm installer bỏ qua sai. Thêm 10 case regression trong
`tests/scripts/install-gitignore.test.sh`.

### Bản ship khác phác thảo §7 ở đâu

Cố ý làm gọn, theo hướng "prompt gọn, tin model":

- **Không có trường `Approved-by:`.** `Status: approved` cộng tác giả commit là bản ghi phê duyệt.
- **Không có ID `C-n` / `Q-n`.** Các mục template là văn xuôi; plan và review không trích ID.
  Open questions không được chuyển thành mục `QUESTIONS.md`.
- **Drift là `git diff --exit-code` so với pin, không phải `git show <sha>:…`.** intent-review
  dừng khi có bất kỳ thay đổi nào sau pin thay vì đọc bản cũ, nên không cần thêm `allowed-tools`
  (vốn đã có `git diff` và `git log`).
- **`verify_summary.py` không kiểm tra dòng `Intent-source:`**, và intake không cảnh báo khi thiếu
  mục template. Cả hai vẫn là khoảng trống ở mức traceability.
- **Có thêm re-pin** (phác thảo không có), vì intent đã commit vẫn có thể đổi sau intake.
- **Không có chế độ soạn nháp** (mục 8 của phác thảo): template là con đường viết duy nhất.
- `skills/feature-intake/SKILL.md` đang ở 599/600 từ (trần progressive-disclosure), nên quy tắc
  re-pin được tách ra `references/re-pin.md`.

### Đã test thế nào

| Bằng chứng | Mức | Kết quả |
|---|---|---|
| `bash scripts/run-tests.sh`, `bash scripts/ci-strict-gate.sh sdlc` | truth | ALL GREEN / OK |
| Chuỗi review: context-propagation audit, correctness review 6 góc kèm scorer, intent review không đọc plan | provenance (receipt ghim ở `42383b9`) | 0 blocking; các advisory ghi trong SUMMARY của spec |
| Hai lần dogfood: agent context mới làm theo nội dung skill trong scratch repo | truth, mỗi case một lần | 12/12 kịch bản |
| **Cài thật**: `install-harness.sh --profile standard` vào repo trống, rồi `claude -p "/feature-intake <slug>"` (Claude Code 2.1.296) với hook bật | truth, mỗi case một lần | 5/5 cơ bản + 3/3 khó |

Các case cài thật (report đầy đủ: `specs/intent-md-entry/e2e-install-report.md`):

- **Cơ bản.** Intake lần đầu với intent auth đã approved (`high-risk`, pin khớp SHA của
  `git log`, commit qua commit-gate); re-pin cùng lane (diff SUMMARY = dòng pin + một ghi chú);
  re-pin sau khi viết lại làm đổi lane (dừng, SUMMARY giữ nguyên từng byte); `Status: draft`
  (dừng, không SUMMARY); sửa chưa commit (dừng).
- **Khó.** (H1) `Status: approved (pending security sign-off)` cùng một code block trong body chứa
  `Status: approved` → dừng. (H2) Chat nói "chỉ sửa chữ, dùng lane tiny" trong khi intent đã
  approved là auth + SendGrid → `high-risk` / `low` / `Escalate: yes`. (H3) Re-pin thêm cảnh báo
  qua SendGrid (gate `external-provider` mới, lane không đổi) → dừng, SUMMARY không đổi.

Mỗi case một lần là bằng chứng chỉ dẫn *có thể* được làm theo, không phải tỉ lệ tuân thủ.

### Khoảng trống còn lại và việc tiếp theo

- **CI chưa chạy.** Cả hai PR được merge khi job GitHub Actions không khởi động (vướng billing tài
  khoản), nên nhánh macOS chưa từng chạy trên code này; chạy lại CI trên `sdlc` khi billing ổn.
- **Merge commit có thể làm hỏng pin** (`--diff-filter=AM` bỏ qua merge; intent đổi lần cuối qua
  giải conflict sẽ ghim commit cũ hơn, và kiểm tra drift sẽ dừng). Đã ghi là residual.
- **intent-review bỏ qua intent.md đã approved nhưng chưa từng được ghim**, và intent.md không có
  heading `##` làm dòng header `Status:` bị mơ hồ.
- **Khoảng trống có sẵn của intake mà các lần thử lộ ra:** intake ghi `Escalate: yes` nhưng không
  viết `ESCALATIONS.md`; run state lúc dừng ở `queued`, lúc lên `planning`, không thống nhất.
- **Chưa thử:** kiểm tra drift của intent-review trên diff triển khai thật; Codex adapter.
- **Vẫn mở từ §6:** mọi mục trừ E4. Thứ tự đề xuất không đổi; E6 (định nghĩa chỉ số) giờ có thể
  thêm "số lần sửa intent sau khi ghim" (số lần re-pin mỗi slug), chỉ số lagging của playbook cho
  play này.

---

## Phụ lục — URL các bài học

Gốc `https://academy.claude.com/courses/ai-native-sdlc-playbook/`:
`introduction` · `capture-intent` · `requirements-and-design` · `plan-mode` · `claude-md` ·
`skills-as-institutional-knowledge` · `parallel-sessions-and-subagents` ·
`give-claude-a-feedback-loop` · `continuous-evals-in-ci` · `ai-in-the-pr-review-loop` ·
`hooks-as-approval-gates` · `ci-cd-integration-and-deployment` · `closing-the-loop-on-metrics` ·
`closing-thoughts-and-resources`
