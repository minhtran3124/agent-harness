# Hỗ trợ Codex — Thiết kế tổng thể

> Bản tiếng Anh (bản gốc, được các skill đọc): [`design.md`](./design.md)

**Trạng thái:** chỉ thiết kế. Không triển khai, không chốt bố cục file, không có code.
**Mục tiêu:** người dùng chạy **OpenAI Codex CLI** nhận được đúng bộ harness — cùng lane, cùng
artifact, cùng các gate — như người dùng chạy Claude Code, từ **một nguồn duy nhất**.

---

## 1. Phát hiện khiến việc này khả thi

Harness được xây dựng dựa trên mô hình mở rộng của Claude Code. Trong năm 2026, Codex CLI đã hội
tụ về đúng mô hình đó. Cả ba bề mặt mà harness phụ thuộc giờ đều tồn tại trên cả hai runtime:

| Harness phụ thuộc vào | Claude Code | Codex CLI | Kết luận |
|---|---|---|---|
| Prompt program | `skills/<n>/SKILL.md`, frontmatter YAML `name`/`description` | Skills — **cùng tên file, cùng hai trường frontmatter bắt buộc**, model tự chọn *hoặc* gọi tường minh | gần như đồng nhất |
| Cơ chế cưỡng chế | hooks: stdin JSON → exit 2 / `permissionDecision:"deny"` / `hookSpecificOutput.additionalContext`, regex `matcher`, `type:"command"` | hooks: **cùng contract, trùng từng trường** | gần như đồng nhất |
| Context cô lập | `agents/*.md` + Task tool + whitelist tool | `.codex/agents/*.toml` + spawn tool + **`sandbox_mode`** | cùng ngữ nghĩa, khác cách mã hoá |

Vì vậy câu hỏi không còn là *"harness có chạy được trên Codex không"* mà là *"đường nối nhỏ nhất
nào giữ được một nguồn sự thật phục vụ hai runtime."*

**Hệ quả chi phối toàn bộ phần dưới:** khối lượng công việc là ~70% *trung tính hoá phần lõi hiện
có* và ~30% *viết adapter cho Codex*. Nửa trung tính hoá cải thiện luôn cả phía Claude — nó gỡ bỏ
những phụ thuộc ngầm vào một runtime duy nhất mà harness hiện chưa có oracle nào kiểm chứng.

---

## 2. Kiến trúc — một nguồn, hai adapter

Hiện tại repo đã tách **nguồn** (gốc repo) khỏi **bản cài dẫn xuất** (`.claude/`, bị gitignore, do
`deploy-harness.sh` dựng). Thiết kế giữ nguyên hình dạng đó và thêm một target thứ hai. Nó **không**
thêm bản sao thứ hai của nguồn.

```
        NGUỒN TRUNG TÍNH RUNTIME                ADAPTER              BẢN CÀI DẪN XUẤT
  ┌──────────────────────────────────┐
  │ skills/    agents/    rules/     │──┬──► claude adapter  ──►  .claude/
  │ hooks/     templates/ runtime/   │  │                          (settings.json, skills/, …)
  │ scripts/   harness-manifest.json │  │
  └──────────────────────────────────┘  └──► codex adapter   ──►  .agents/skills/  +  .codex/
                                                                   (hooks.json, agents/*.toml,
                                                                    AGENTS.md)
```

Ba nguyên tắc chi phối đường nối này:

1. **Nguồn không bao giờ nhắc tên runtime.** Không đường dẫn `.claude/`, không cú pháp gọi
   `/skill-name`, không tên tool chỉ có ở Claude — trong bất kỳ file nào thuộc `skills/`,
   `agents/`, `rules/`.
2. **Adapter chỉ làm việc cơ học.** Adapter mã hoá lại và đặt lại vị trí; nó không được mang
   policy. Adapter nào cần *quyết định* điều gì tức là phần lõi trung tính đã bị rò rỉ.
3. **Sai khác phải được khai báo, không để tự phát hiện.** Điều adapter không làm được phải ghi
   vào một sổ đối chiếu kiểm tra được bằng máy (§5), không để người dùng gặp phải lúc chạy.

### 2.1 Bốn tầng, xét theo mức độ khả chuyển

| Tầng | Ví dụ | Khả chuyển | Việc cần làm |
|---|---|---|---|
| **Lõi logic** | `runtime/run_state.py`, `scripts/*.py`, schema `specs/`, templates, manifest | 100% — Python và file thuần, không dính runtime | không |
| **Cưỡng chế** | `hooks/*.sh` | ~85% — cùng contract, khác từ vựng và hình dạng payload | shim chuẩn hoá input (§3) |
| **Bề mặt chỉ dẫn** | `skills/`, `agents/`, `rules/` | ~70% — cùng khái niệm, khác cách phân phối và mã hoá | trung tính hoá (§4) |
| **Điểm vào** | `CLAUDE.md`, `settings.json`, script cài đặt | ~0% — bản chất là đặc thù runtime | adapter sinh ra |

Việc lõi logic khả chuyển 100% là dữ kiện chịu lực: lane, quy tắc bằng chứng, FSM run-state,
plan contract, lint verify-row và review receipt **vốn đã** trung tính với runtime. Hỗ trợ Codex
không đụng đến phần tư duy thật sự của harness — chỉ đụng cách nó được phân phối và cưỡng chế.

---

## 3. Cưỡng chế — đường nối ở tầng hook

### 3.1 Cái gì chuyển sang miễn phí

Tên sự kiện (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`,
`SessionEnd`), cấu hình dạng `matcher` + `type:"command"`, chặn bằng exit 2, quyết định `deny`, và
tiêm `additionalContext` — giống nhau trên cả hai runtime. Chín script hook **không cần viết lại**.

### 3.2 Cái gì gãy — và gãy theo kiểu nào

Ba khác biệt đáng kể, và hai trong số đó **fail open** — kiểu nguy hiểm:

| Khác biệt | Tác động lên harness |
|---|---|
| **Từ vựng tool.** `tool_name` chính tắc của Codex cho mọi thao tác sửa file là `apply_patch` (`Write`/`Edit` chỉ là alias cho matcher); shell là `shell`/`unified_exec`. | Matcher phần lớn sống sót nhờ alias — cần xác nhận thực nghiệm. |
| **Hình dạng payload.** `apply_patch` mang **một envelope patch**, không phải `{file_path}`. Bốn hook (`branch-isolation-guard`, `blast-radius-check`, `ruff-on-edit`, `render-plan-on-write`) đọc `.tool_input.file_path` với fallback `// empty`. | **Fail open âm thầm.** Chúng exit 0 và không cưỡng chế gì cả. Với `branch-isolation-guard`, nghĩa là edit code trên nhánh chung không còn bị chặn — không lỗi, không cảnh báo. |
| **Độ phủ sự kiện.** Việc phát sự kiện hook của Codex là opt-in theo từng tool handler và còn lỗ hổng độ phủ đang mở ở upstream. | Một gate có thể được *cấu hình* mà vẫn không bao giờ chạy. |

### 3.3 Hướng xử lý: một đường nối chuẩn hoá duy nhất

Các hook ngừng tự parse stdin thô. Một shim dùng chung (được mọi hook source, đặt cạnh
`hooks/lib/` sẵn có) đọc stdin một lần, nhận diện runtime, và xuất ra một khung nhìn chuẩn hoá:
tool đang gọi, **tập** file bị đụng, câu lệnh shell, nội dung prompt.

Vì sao chọn hình dạng này:

- Nó là **một đường nối kiểm thử được**, không phải chín. Mẫu contract-test hiện có ở
  `tests/hooks/*.test.sh` mở rộng sang đây trực tiếp.
- Một envelope patch tự nhiên sinh ra *nhiều* file, nên contract trung tính phải là **tập** file.
  Điều đó đúng hơn hẳn `file_path` đơn lẻ hiện tại — `blast-radius-check` và
  `branch-isolation-guard` vốn đã mang ngữ nghĩa tập hợp.
- Nó biến fail-open thành **quyết định policy tường minh cho từng hook**. Hook nào không xác định
  được input của mình phải chọn: cảnh báo lớn, hoặc từ chối. Im lặng không còn là lựa chọn.

### 3.4 Hai ràng buộc cứng từ phía Codex

- **`SessionEnd` có timeout ~1s (tối đa 3s)**, so với ~600s ở các sự kiện khác.
  `state-breadcrumb.sh` chạy git rồi append file. Phải đo; nếu không vừa thì chuyển sang `Stop`.
  Đây là ràng buộc hành vi thật sự, không phải ghi chú tinh chỉnh.
- **Hook đang ở dạng experimental, cần feature flag (`[features] hooks = true`), tắt trên Windows,
  và hook cấp project yêu cầu thư mục `.codex/` được đánh dấu trusted.** Do đó một bản cài Codex
  có thể triển khai đầy đủ mà **không có cưỡng chế nào**. Xem §6.

---

## 4. Bề mặt chỉ dẫn — trung tính hoá phần lõi

Bốn điểm dính cụ thể, mỗi điểm có một hướng xử lý. Cả bốn đều là *đơn giản hoá* nguồn hiện tại,
không phải thêm thắt.

### 4.1 Tự động nạp rule theo path — rủi ro lớn nhất

Claude Code tự tiêm `rules/plan-format.md`, `wave-parallelism.md` và `auto-correct-scope.md` qua
frontmatter `paths:` khi một file `specs/**` khớp được đọc. **Codex không có cơ chế tương đương.**
Rule liên quan an toàn nhất của harness — `auto-correct-scope.md`, nơi chứa tiêu chí STOP của
Rule 4 — đến được các context reviewer/implementer cô lập một phần là nhờ kênh này.

Đây cũng đang là một khiếm khuyết tiềm ẩn *ngay hôm nay*: PR #141 đã ship một rule được tham chiếu
nhưng chưa từng được đọc trong một context subagent cô lập — chính vì vậy mới có
`/context-propagation-audit`.

**Hướng xử lý:** hạ `paths:` từ *cơ chế* xuống *chất xúc tác*.

- Bước `Read` tường minh trong skill tiêu thụ trở thành **bảo đảm phân phối duy nhất**. Một số
  skill đã làm vậy (`writing-plans`, `correctness-review`, `intent-review`,
  `subagent-driven-development`, `implementer-prompt.md`) — thiết kế biến điều đó thành phổ quát
  và audit biến nó thành chứng minh được.
- `/context-propagation-audit` trở thành oracle: với mỗi rule, mọi context tiêu thụ đều có một
  Read. Skill này đã tồn tại và đã chạy trên các diff workflow-engine.
- **Bác bỏ:** nhúng nội dung rule vào `AGENTS.md`. Đó chính là tái tạo khiếm khuyết
  `stale-inline-policy` mà repo này từng dính.

**Đây là hạng mục dễ khiến hỗ trợ Codex sai một cách âm thầm nhất, và nó được sửa luôn ở phía
Claude bởi cùng một thay đổi.**

### 4.2 Đường dẫn `.claude/` hard-code trong văn bản skill

26 chỗ chỉ dẫn agent đọc `.claude/rules/...`. Dưới Codex không tồn tại `.claude/`.

**Hướng xử lý:** tham chiếu rule theo đường dẫn **gốc repo** (`rules/…`) — nơi chúng vốn đã nằm
trong nguồn, và nơi cả hai runtime đều đọc được. Bản sao `.claude/rules/` chỉ còn là fixture phục
vụ auto-load của Claude, không còn là địa chỉ được nêu cho ai. Việc viết lại văn bản lúc deploy bị
bác bỏ tường minh vì mờ đục và không kiểm thử được.

### 4.3 Subagent

Contract *ngữ nghĩa* vốn đã trung tính runtime và đã được ghi trong `rules/orchestration.md`:
reviewer chỉ đọc, verdict spec/quality tách bạch, summary có cấu trúc 150–300 từ, không dump file
thô. Chỉ **cách mã hoá** là khác (Markdown+frontmatter vs TOML), nên `agents/*.md` vẫn là nguồn và
adapter Codex sinh ra TOML.

Hai điểm cần mang sang khi triển khai:

- `sandbox_mode = "read-only"` của Codex là bảo đảm độc lập **mạnh hơn** whitelist tool — nó được
  cưỡng chế bởi sandbox chứ không bởi danh sách tool. Tính độc lập của reviewer *tốt lên* dưới
  Codex, không xấu đi.
- Codex "không tự động spawn subagent" — việc uỷ nhiệm phải tường minh trong prompt. Phần dispatch
  theo wave của `subagent-driven-development` vốn đã tường minh; việc này cần xác minh, không cần
  thiết kế lại.

### 4.4 Cú pháp gọi và file điểm vào

`/skill-name` (Claude) vs `$skill`/model tự chọn (Codex); `CLAUDE.md` vs `AGENTS.md`. Nguồn nên
gọi *tên skill*, không gọi *cú pháp* ("invoke the feature-intake skill"). `AGENTS.md` đã tồn tại
trong repo này và được adapter sinh ra từ cùng nội dung tạo ra `CLAUDE.md`.

---

## 5. Parity là điều kiện release — hai tầng

**Quyết định D2 đưa Codex thành runtime ngang hàng**, nên parity là điều kiện release chứ không
phải một danh sách bào chữa. Nhưng Codex CLI là một tiến trình tốn tiền, không tất định và phụ
thuộc mạng — chặn mọi PR bằng việc chạy Codex thật sẽ khiến CI chậm, đắt và hay lỗi vặt. Vì vậy
thiết kế tách điều kiện này theo đúng trục mà repo đã dùng cho các mức bằng chứng:

| Tầng | Chứng minh điều gì | Chi phí | Chạy khi nào |
|---|---|---|---|
| **Static parity** (traceability) | Mọi skill, agent, rule và hook harness ship ra đều *được sinh* cho cả hai runtime; khối runtime trong manifest nhất quán nội tại; adapter không trôi dạt. | Miễn phí, tất định | **Mọi PR**, chặn |
| **Behavioural parity** (truth) | Một bộ golden nhỏ các hành vi harness — phân loại lane, chạy plan, một commit bị chặn, một review receipt — cho ra artifact tương đương khi được *điều khiển* bởi từng runtime. | Tốn tiền, không tất định | Theo lịch + trước release, chỉ chặn ở release |

`harness-manifest.json` — vốn đã là nguồn sự thật duy nhất cho từ vựng và mode của hard-gate —
được bổ sung một **khối runtime**: với mỗi gate, runtime nào cưỡng chế, ở cường độ nào
(block / warn / không khả dụng), và vì sao. Static parity được kiểm tra dựa trên khối đó bằng một
drift guard theo khuôn mẫu `check_manifest.py` và kiểm tra parity của embedded gate modes hiện có.

**Dưới quy chế ngang hàng, sổ đối chiếu đổi vai trò.** Nó không còn là "đây là các khoảng trống";
nó là một danh sách ngoại lệ ngắn, **có chủ sở hữu và có hạn**. Mỗi mục `unavailable` mang theo
người chịu trách nhiệm và điều kiện thoát — nếu không, "ngang hàng" thoái hoá thành một từ ngữ và
sổ đối chiếu trở thành thứ *che giấu* khoảng trống thay vì phơi bày nó.

---

## 6. Chế độ advisory — chuyển tiếp, không phải trạng thái ổn định

**Quyết định D2 và D3 mâu thuẫn nhau, và thiết kế không được lấp liếm điều đó.** Runtime ngang hàng
nghĩa là parity là điều kiện release. Chế độ advisory nghĩa là Codex ship ra với cưỡng chế cơ học
yếu hoặc không có. Một runtime ship ở chế độ advisory thì, xét trên tầng cưỡng chế, *theo định
nghĩa là chưa ngang hàng*.

Cách giải quyết là nói chính xác **tầng nào đạt ngang hàng vào lúc nào**:

| Tầng | Ngang hàng lúc ship? | Căn cứ |
|---|---|---|
| Bề mặt chỉ dẫn (skills, agents, rules) | **Có** | Cùng nguồn, adapter sinh ra, kiểm tra tĩnh được |
| Artifact + workflow (lane, schema `specs/`, FSM run-state, review receipt) | **Có** | Lõi logic trung tính runtime, vốn đã khả chuyển |
| Cưỡng chế (hooks) | **Không — advisory, theo dõi đến khi đóng** | Hook Codex còn experimental, phụ thuộc flag/trust/OS, còn lỗ hổng độ phủ ở upstream |

Vậy: **ship advisory, tuyên bố ngang hàng ở hai trong ba tầng, và mang tầng thứ ba như một ngoại lệ
có tên, có chủ, có hạn trong sổ parity.** Advisory là trạng thái chuyển tiếp có điều kiện thoát,
không phải một hạng mức vĩnh viễn.

Về mặt cơ chế, điều đó nghĩa là:

- Trình cài đặt **dò** khả năng chạy hook và **báo cáo** kết quả thay vì mặc định giả sử có.
- Khi không có hook, harness chạy ở chế độ advisory: skill, artifact, lane, quy tắc bằng chứng và
  chuỗi review vẫn hoạt động — chỉ thiếu phần đối chứng cơ học.
- Chế độ advisory phải **hiển thị và được ghi lại** — nêu ra lúc bắt đầu phiên và ghi vào artifact
  — để một `SUMMARY.md` sinh ra khi không có đối chứng không bao giờ bị nhầm với bản đã qua đối
  chứng.

Phương án còn lại (âm thầm ship một harness mà các gate không làm gì, dưới nhãn "ngang hàng") chính
là kiểu thất bại "đọc traceability thành truth" mà quy tắc gate-verifiability của repo sinh ra để
ngăn chặn.

---

## 6a. Tính đa dạng ensemble phải nhận biết runtime

**Quyết định D1 kéo theo một hệ quả phải được thiết kế, không được nuốt trôi.** Hiện nay reviewer
ngoài khác chủng loại trên PR *chính là* Codex, và giá trị của nó đến từ việc nó thuộc dòng model
khác với chuỗi Claude đã xây dựng phần việc đó — riêng PR #173 đã 16 vòng phát hiện độc lập. Một khi
Codex cũng **điều khiển** harness, thì một PR do Codex xây dựng và được Codex review sẽ dùng chung
cả dòng model lẫn chính các prompt của harness. Tính đa dạng từng làm nên giá trị của vòng review đó
sụp đổ — âm thầm, không tín hiệu nào báo là nó đã xảy ra.

**Hướng xử lý:** biến oracle thành một hàm của người xây dựng, thay vì một hằng số.

- **Review receipt được thêm trường `runtime`** cho mỗi review đã ghi — runtime nào tạo ra nó.
  Receipt vốn đã là artifact provenance ghim vào một HEAD sha; ghi runtime vào đó là chỗ tự nhiên,
  và biến tính chất này thành kiểm tra được thay vì mặc định giả sử.
- Quy tắc độc lập trở thành **chéo runtime**: oracle bên ngoài phải khác runtime đã xây dựng thay
  đổi. Nhánh do Claude xây dựng thì Codex review ngoài (đúng như hiện nay, không đổi); nhánh do
  Codex xây dựng thì Claude review ngoài.
- Review PR bên ngoài vẫn **mù với harness** trong cả hai chiều — nó không được chạy chính các
  prompt review của harness, nếu không nó lại thừa hưởng điểm mù của oracle bên trong, bất kể dòng
  model nào.

Việc này biến một tính chất repo đang ngầm dựa vào thành một tính chất tường minh và kiểm chứng
được — và nó chỉ trở nên cần thiết *bởi vì* Codex được nâng từ oracle lên peer driver.

---

## 7. Phân kỳ

Sắp xếp sao cho giá trị và việc giảm rủi ro đến trước khi tồn tại bất kỳ file đặc thù Codex nào.

| Giai đoạn | Sản phẩm | Vì sao theo thứ tự này |
|---|---|---|
| **0 — Spike** | Xác nhận thực nghiệm payload hook của Codex, alias tên tool, độ phủ sự kiện, ngân sách `SessionEnd`, thư mục discovery của skills, **và việc một wave subagent thực sự dispatch và trả kết quả dưới Codex**. | Tài liệu mâu thuẫn ở vài chỗ và còn bug độ phủ đang mở ở upstream. **Chặn** — mọi thứ phía sau dựng trên các dữ kiện này. D1 thêm phép dò subagent: nếu wave dispatch không chạy thì quy chế peer-driver là bất khả thi. |
| **1 — Trung tính hoá** | Trung tính hoá đường dẫn rule, Read rule tường minh phổ quát, shim input cho hook, văn bản gọi skill trung tính. **Không file Codex nào.** | Refactor thuần phần harness hiện có, chứng minh được bằng bộ test sẵn có. Tạo giá trị (đóng một lỗ hổng thật phía Claude) kể cả khi sau này bỏ hỗ trợ Codex. |
| **2 — Adapter** | Target deploy cho Codex: skills, `agents/*.toml`, `hooks.json`, `AGENTS.md`. | **Nằm trên đường găng do D1** — Codex điều khiển các agent nghĩa là bộ sinh TOML và cách ly reviewer bằng `sandbox_mode` là thành phần chịu lực, không phải tuỳ chọn. |
| **3 — Parity + trung thực** | Khối runtime trong manifest, static-parity drift guard (mỗi PR), dò năng lực, báo cáo chế độ advisory, **trường `runtime` trong review receipt + quy tắc độc lập chéo runtime**. | Biến sai khác thành thứ kiểm tra được thay vì truyền miệng, và biến tính đa dạng ensemble thành thứ kiểm chứng được (§6a). |
| **4 — Điểm vào** | `install-harness.sh --runtime claude\|codex\|both`, tài liệu, cập nhật `HARNESS.md`. | Cuối cùng: chưa có gì để cài cho tới khi 2–3 thành hình. |
| **5 — Behavioural parity** | Bộ golden các hành vi harness chạy trên cả hai runtime; điều kiện theo lịch + trước release. | **Do D2 thêm vào.** Đây là thứ biến "ngang hàng" từ một tuyên bố thành bằng chứng mức truth. Để sau cùng vì đây là giai đoạn duy nhất tốn tiền mỗi lần chạy. |

**Giai đoạn 1 có giá trị độc lập và ship được độc lập.** Điều này là cố ý — nghĩa là quyết định về
Codex có thể đảo ngược sau Giai đoạn 1 mà không mất gì.

**D2 dời vạch đích, không dời vạch xuất phát.** Quy chế ngang hàng chỉ thành sự thật khi Giai đoạn 5
tồn tại; Giai đoạn 0–4 là cùng khối lượng công việc dù chọn hướng nào. Tuyên bố ngang hàng trước
Giai đoạn 5 tức là tuyên bố dựa trên bằng chứng tĩnh — chấp nhận được nếu nói thẳng ra (§6), không
chấp nhận được nếu để ngầm hiểu.

---

## 8. Ngoài phạm vi (non-goals)

- **Fork skill theo từng runtime.** Một nguồn duy nhất, nếu không thì thiết kế đã thất bại.
- **Một workflow riêng cho Codex.** Cùng lane, cùng artifact, cùng gate — nếu không, các tuyên bố
  của harness hết so sánh được giữa các runtime.
- **Hỗ trợ Cursor / OpenCode ngay bây giờ.** Đường nối adapter mở đường cho việc đó về sau; thêm
  ngay lúc này là thiết kế dựa trên ẩn số.
- **Sao chép mô hình cloud manager-worker sandbox của Codex.** Ngoài phạm vi; chỉ CLI cục bộ.
- **Thay thế bản dựng `.claude/`.** Claude Code vẫn là target hạng nhất, hành vi không đổi.

---

## 9. Các quyết định

Ghi nhận 2026-08-08. Đây từng là ba câu hỏi mở của thiết kế; cả ba đã được chốt.

| # | Quyết định | Hệ quả trong thiết kế này |
|---|---|---|
| **D1** | **Codex chạy luôn các agent** — là peer driver đầy đủ, không chỉ là reviewer ngoài. | Bộ sinh TOML cho subagent và cách ly reviewer bằng `sandbox_mode` chuyển lên đường găng (§4.3, Giai đoạn 2). Wave dispatch subagent được thêm vào spike chặn ở Giai đoạn 0. Tính đa dạng ensemble phải nhận biết runtime (§6a). |
| **D2** | **Codex là runtime ngang hàng**, không phải best-effort. | Parity thành điều kiện release, tách làm hai tầng: static (mỗi PR, miễn phí) và behavioural (theo lịch/trước release, tốn tiền) (§5). Thêm Giai đoạn 5. Sổ parity chuyển thành danh sách ngoại lệ có chủ, có hạn — không còn là bản kê khoảng trống. |
| **D3** | **Ship advisory** — không chờ độ phủ hook ở upstream. | Advisory được định nghĩa là trạng thái chuyển tiếp có điều kiện thoát, và quy chế ngang hàng được tuyên bố theo từng tầng thay vì tuyên bố trọn gói (§6). |

### Mâu thuẫn duy nhất còn lại

**D2 và D3 kéo ngược nhau**, và thiết kế xử lý chứ không che: quy chế ngang hàng được tuyên bố ở
tầng chỉ dẫn và tầng artifact/workflow ngay khi ship, còn tầng cưỡng chế ship ở chế độ advisory và
được mang như một ngoại lệ có tên, có chủ, cho tới khi độ phủ hook của Codex hoàn thiện ở upstream.
Mọi cách khác hoặc làm chậm việc ship (vi phạm D3), hoặc để chữ "ngang hàng" mang nghĩa nhẹ hơn
những gì nó nói (vi phạm chính quy tắc gate-verifiability của repo).

**Rủi ro còn lại cần canh:** một danh sách ngoại lệ không có hạn chính là cách "advisory" âm thầm
trở thành vĩnh viễn. Điều kiện thoát và người chịu trách nhiệm trên mục sổ đó mới là cơ chế kiểm
soát — không phải ý định sẽ sửa sau.

---

## 10. Nguồn tham khảo

Các tuyên bố về năng lực Codex CLI trong tài liệu này được đọc từ tài liệu Codex của OpenAI
(hook contract, skills discovery, schema TOML của subagent) và đối chiếu chéo với các tài liệu
tham khảo bên thứ ba cùng hai issue độ phủ đang mở ở upstream. Chúng là bằng chứng **mức
traceability** — đã đọc, chưa chạy — và đó chính là lý do Giai đoạn 0 tồn tại.

- [Codex — Hooks](https://developers.openai.com/codex/hooks) ([URL hiện hành](https://learn.chatgpt.com/docs/hooks))
- [Codex — Build skills](https://developers.openai.com/codex/skills)
- [Codex — Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex — Custom prompts](https://developers.openai.com/codex/custom-prompts) (đã deprecated, thay bằng skills)
- [Codex — Configuration reference](https://developers.openai.com/codex/config-reference)
- [hookshot — Codex hook payload reference](https://github.com/CorridorSecurity/hookshot/blob/main/docs/reference-codex.md)
- [openai/codex#16732 — apply_patch không phát PreToolUse/PostToolUse](https://github.com/openai/codex/issues/16732)
- [openai/codex#20204 — độ phủ PreToolUse không nhất quán giữa các tool handler](https://github.com/openai/codex/issues/20204)
