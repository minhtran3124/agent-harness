# Hỗ trợ Codex — Thiết kế tổng thể

> Bản tiếng Anh: [`design.md`](./design.md)

**Trạng thái:** chỉ cập nhật thiết kế; chưa triển khai adapter runtime hay thay đổi cơ chế cưỡng
chế trong PR này.
**Bằng chứng được làm mới:** 2026-08-10, dựa trên Codex CLI 0.147.0, tài liệu OpenAI hiện hành và
nhánh `simplify`.
**Mục tiêu:** người dùng OpenAI Codex nhận được cùng lane, artifact, workflow và release gate như
người dùng Claude Code, từ một nguồn chân lý ngữ nghĩa duy nhất.

---

## 1. Tính khả thi và đường cơ sở năng lực hiện tại

Codex hiện có đủ ba bề mặt mở rộng mà harness cần: skill, lifecycle hook và custom subagent. Vì
vậy adapter ngang hàng là khả thi, nhưng hai runtime không tương đương từng field. Thiết kế chia sẻ
**ngữ nghĩa** và biểu diễn rõ các ánh xạ policy theo runtime.

| Phụ thuộc của harness | Claude Code | Codex | Kết luận thiết kế |
|---|---|---|---|
| Chương trình prompt | `skills/<name>/SKILL.md` | skill `SKILL.md`, được tìm từ các skill root được hỗ trợ hoặc plugin | dùng chung nguồn skill; kiểm tra discovery trong từng kiểu đóng gói |
| Cưỡng chế | lifecycle hook nhận JSON qua stdin | lifecycle hook bật mặc định, nhưng chịu ràng buộc trust của project và độ phủ của handler | dùng chung logic hook sau normalizer payload; phát hiện độ phủ hiệu lực từ bên ngoài hook |
| Context cô lập | agent Markdown, allowlist model/tool | `.codex/agents/*.toml`, developer instructions, policy sandbox/config | dùng chung contract agent; sinh runtime binding đã kiểm thử thay vì chuyển field máy móc |
| Chỉ dẫn repository | `CLAUDE.md` và rules | chuỗi `AGENTS.md` phân cấp từ root đến CWD | giữ nguyên `AGENTS.md` hiện có; chỉ quản lý một vùng hoặc con trỏ có ranh giới rõ |

Bản nháp trước coi Codex hook là thử nghiệm, phải opt-in và phần lớn không phủ `apply_patch`.
Nhận định đó đã cũ. Tại ngày thu thập bằng chứng:

- Codex bật hook mặc định và `codex features list` báo `hooks` ở trạng thái stable;
- probe cô lập thực tế quan sát được `PreToolUse` và `PostToolUse` cho cả shell và `apply_patch`;
- payload `apply_patch` chứa raw patch trong `tool_input.command`, không phải một
  `tool_input.file_path` duy nhất;
- hook cấp project vẫn phụ thuộc trust/cấu hình; hosted tool không có lifecycle coverage, và một
  số đường tool chuyên biệt có thể không tham gia.

Vì vậy rủi ro là **payload không khớp và độ phủ hiệu lực không khớp**, không phải giả định Codex
không phát event cho thao tác sửa file.

### 1.1 Đường cơ sở nền tảng được hỗ trợ

Hook hiện tại phụ thuộc Bash, `jq`, Git và Python. Tập nền tảng Codex được hỗ trợ đầu tiên vì thế là
macOS, Linux và WSL có đủ các dependency này. Chưa tuyên bố hỗ trợ Windows native cho đến khi mọi
hook có `commandWindows` hoặc có adapter native. Runtime doctor (§5) phải báo nền tảng không được hỗ
trợ là advisory, không được âm thầm gắn nhãn ngang hàng.

---

## 2. Kiến trúc — một lõi ngữ nghĩa, runtime binding tường minh

Repository đã tách nguồn chỉnh sửa khỏi bản cài `.claude/` được sinh cho Claude. Hỗ trợ Codex giữ
một lõi ngữ nghĩa duy nhất, sau đó thêm runtime binding và các bề mặt được sinh/cài đặt.

```
              NGUỒN NGỮ NGHĨA                         RUNTIME BINDING
  ┌──────────────────────────────────────┐      ┌─────────────────────────┐
  │ skills/  agents/  rules/  hooks/     │─────►│ Ánh xạ policy Claude    │──► .claude/
  │ templates/  runtime/  scripts/       │      └─────────────────────────┘
  │ harness-manifest.json                │      ┌─────────────────────────┐
  └──────────────────────────────────────┘─────►│ Policy + đóng gói Codex │──► plugin/config project
                                                └─────────────────────────┘
```

Bốn quy tắc chi phối đường nối này:

1. **Workflow policy chỉ có một chủ sở hữu.** Lane, artifact, điều kiện STOP, trách nhiệm review và
   quy tắc bằng chứng vẫn nằm trong nguồn chung.
2. **Năng lực runtime là binding tường minh.** Tên model, quyền tool, sandbox policy, policy fork
   context, matcher alias và vị trí package có thể khác nhau; tất cả phải được ánh xạ và kiểm thử.
   Gọi toàn bộ phép chuyển đổi là “máy móc” sẽ che giấu policy thật.
3. **File sinh ra phải tái lập được và được validate.** Cùng revision nguồn và input adapter phải
   cho output ổn định theo byte; TOML/JSON sinh ra phải qua strict config parser của runtime.
4. **Mọi phân kỳ đều được khai báo.** Năng lực thiếu phải là ngoại lệ có owner, hạn dùng và điều
   kiện thoát trong runtime manifest, không phải khoảng trống best-effort im lặng.

### 2.1 Quyết định đóng gói: mặc định hybrid

OpenAI khuyến nghị plugin cho gói tái sử dụng, và plugin Codex có thể chứa skill cùng hook. Custom
agent cấp project và tích hợp `AGENTS.md` ở repository có quyền sở hữu và cách xử lý xung đột khác.
Do đó lựa chọn ưu tiên là hybrid:

- **plugin sở hữu:** skill tái sử dụng và đăng ký/tài nguyên hook;
- **project adapter sở hữu:** `.codex/agents/*.toml` được sinh, trạng thái runtime và tích hợp
  `AGENTS.md` có ranh giới ở §6;
- **fallback:** sync trực tiếp toàn bộ asset Codex vào project chỉ khi spike đóng gói chứng minh
  plugin discovery, trust hoặc cài đặt local-development không đáp ứng contract harness.

Phase 2 ghi lại lựa chọn bằng probe discovery chạy được. Nguồn ngữ nghĩa và parity test không đổi
nếu phải dùng fallback.

### 2.2 Mức khả chuyển theo tầng

| Tầng | Ví dụ | Mức khả chuyển kỳ vọng | Trách nhiệm adapter |
|---|---|---|---|
| Lõi logic | FSM run-state, schema, template, manifest | hoàn toàn | không có ngoài đường dẫn executable |
| Bề mặt chỉ dẫn | skill và rule | cao | discovery, câu chữ trung tính cú pháp gọi, delivery rule tường minh |
| Cưỡng chế | logic shell của hook | cao sau chuẩn hoá | config, matcher alias, chuẩn hoá payload, chẩn đoán coverage |
| Policy agent | vai trò reviewer/implementer | chỉ dùng chung ngữ nghĩa | binding model, tool, sandbox, MCP, nesting và context fork |
| Điểm vào/config | `CLAUDE.md`, `AGENTS.md`, settings | đặc thù runtime | sinh mới hoặc tích hợp vào vùng quản lý hữu hạn |

---

## 3. Contract cưỡng chế — ma trận event chính xác và một đường chuẩn hoá

Khi triển khai phải ghim một ma trận event/tool đã kiểm thử, thay vì coi “có hỗ trợ hook” là một
boolean duy nhất.

| Nhu cầu harness | Đường event/tool Codex | Đường cơ sở đã quan sát hoặc có tài liệu | Kiểm soát bắt buộc |
|---|---|---|---|
| Gate lệnh Git | `PreToolUse` trên shell/unified execution | probe thực tế thấy event trước/sau shell | fixture matcher + chuẩn hoá command |
| Cô lập khi sửa file | `PreToolUse` trên `apply_patch` | probe thực tế thấy event | parse mọi path trong patch; input không rõ đi theo fail policy tường minh của từng gate |
| Kiểm tra sau sửa | `PostToolUse` trên `apply_patch` | probe thực tế thấy event | chuẩn hoá tập path; không bao giờ giả định một file |
| Hướng dẫn scope prompt | `UserPromptSubmit` | lifecycle event có tài liệu | golden payload fixture |
| Nạp knowledge | `SessionStart` | lifecycle event có tài liệu | chỉ bổ trợ; không thể tự chứng minh hook đang hoạt động |
| Breadcrumb bền vững | `SessionEnd` | event có tài liệu với timeout ngắn | benchmark dưới timeout và giới hạn khối lượng công việc |
| Hosted/tool chuyên biệt | tuỳ handler | hosted tool nằm ngoài lifecycle coverage; đường chuyên biệt có thể opt-out | doctor báo coverage; đường sửa file chưa hỗ trợ không được gọi là blocking parity |

### 3.1 Kiểu fail hiện tại

Bốn edit hook hiện đọc `.tool_input.file_path` rồi fallback về rỗng. Event `apply_patch` của Codex
lại chứa patch envelope trong `tool_input.command`. Không có adapter, các hook này có thể âm thầm
không thấy path và cho phép thao tác. Đây là fail-open thực sự dù event vẫn được phát.

### 3.2 Input hook đã chuẩn hoá

Mọi hook dùng chung một normalizer đọc stdin đúng một lần và cung cấp:

- danh tính runtime và event;
- loại tool chuẩn (`shell`, `edit`, `mcp` hoặc `other`);
- tập đầy đủ, loại trùng các path trong repository bị tác động;
- shell command, prompt text và kết quả tool khi phù hợp;
- trạng thái parse: `known`, `partial` hoặc `unknown`.

Patch nhiều file mặc định là dữ liệu dạng tập. `branch-isolation-guard`, `blast-radius-check`,
`ruff-on-edit` và `render-plan-on-write` phải xét mọi path phù hợp. Lỗi parse phải nhìn thấy được.
Mỗi gate khai báo `partial`/`unknown` sẽ block, warn hay unavailable; mặc định không bao giờ là
thành công im lặng.

Golden fixture bao phủ payload Claude và Codex, patch nhiều file, rename/delete, input hỏng, path có
khoảng trắng và path ngoài repository. Matcher test riêng chứng minh tool handler nào thực sự đi
đến normalizer.

### 3.3 Công việc cuối session vẫn ở SessionEnd

`state-breadcrumb.sh` hiện thuộc `SessionEnd`. Codex dành ngân sách cho event này nhỏ hơn nhiều so
với hook thường, nên script phải được đo và thu gọn nếu cần. **Không** chuyển thẳng sang `Stop`:
Stop có thể lặp trước khi session kết thúc, và tính idempotent theo session hiện tại có thể giữ lại
snapshot đầu tiên đã cũ. Muốn chuyển phải thiết kế snapshot có thể thay thế và test sự lặp; đó là
thay đổi riêng, không phải kế hoạch adapter mặc định.

---

## 4. Contract agent — dùng chung vai trò, policy bảo mật theo runtime

Các file `agents/*.md` hiện chứa model ID và tool allowlist của Claude. `sandbox_mode` của Codex
không tương đương các allowlist đó: filesystem read-only tự nó không tắt nested agent, shell, MCP
hay mọi side effect ngoài filesystem. Vì vậy chuyển field trực tiếp từ Markdown sang TOML không thể
bảo toàn contract vai trò.

Schema agent chung phải biểu diễn năng lực, không phải field theo vendor:

- chỉ dẫn vai trò và contract output;
- quyền filesystem (`none`, `read-only` hoặc `workspace-write`);
- shell policy và network policy;
- MCP server/tool được phép;
- có được delegation lồng nhau hay không;
- context policy (`fresh`, `bounded` hoặc inherited);
- yêu cầu lớp model và binding model theo runtime.

Mỗi adapter sở hữu ánh xạ đã kiểm tra từ các năng lực trên sang runtime. Năng lực chưa có mapping là
lỗi adapter, không được ngầm dùng default.

### 4.1 Profile reviewer

Review agent tối thiểu cần:

- filesystem read-only;
- tắt delegation nested-agent;
- không có MCP tool gây side effect ngoài kiểm soát;
- context fresh hoặc bounded tường minh, giữ ranh giới plan-blind/intent-blind;
- contract verdict có cấu trúc đã được harness định nghĩa.

Probe Codex thực tế xác nhận thêm một ràng buộc: có thể chọn custom agent profile khi fork fresh hoặc
bounded, còn full-history fork kế thừa agent type của parent và từ chối override đó. Chỉ dẫn dispatch
được sinh và behavioural test phải dùng đường fresh/bounded được hỗ trợ. Nếu runtime không cưỡng chế
được một năng lực, parity ledger ghi đúng ngoại lệ; không mô tả `sandbox_mode` là mạnh hơn tool
allowlist một cách khái quát.

---

## 5. Cưỡng chế hiệu lực và chế độ advisory

Để hook tự báo trạng thái tạo ra vòng lặp logic: khi hook bị tắt, chưa trust, sai cấu hình hoặc bị
bỏ qua, `SessionStart` không thể thông báo điều đó. Vì vậy phát hiện capability phải nằm **bên
ngoài** hệ hook.

Adapter cung cấp `harness doctor --runtime codex` (tên minh hoạ ở giai đoạn thiết kế). Doctor chạy
khi cài đặt và từ entry/skill cấp cao nhất, không chỉ từ hook. Nó ghi nhận và đánh giá:

- phiên bản Codex CLI và trạng thái tính năng hook được khai báo;
- OS được hỗ trợ và executable bắt buộc;
- trust hiệu lực của project cùng hash cấu hình hook đã trust;
- hash cấu hình cài đặt/package so với output kỳ vọng;
- coverage matcher event/tool bắt buộc từ ma trận capability đã ghim;
- discovery của skill và custom agent;
- probe live hoặc deterministic thành công gần nhất và độ mới của nó.

Kết quả load-bearing không rõ hoặc quá cũ đều dẫn đến advisory. Khi hook chạy, thông báo
`SessionStart` có thể nhắc lại kết quả nhưng không phải nguồn chân lý.

### 5.1 Ngữ nghĩa mode

| Mode | Ý nghĩa | Tuyên bố được phép |
|---|---|---|
| `enforced` | mọi đường blocking bắt buộc đều đã trust, còn mới, được hỗ trợ và có coverage | cưỡng chế ngang hàng trong phạm vi ma trận đã khai báo |
| `advisory` | workflow dùng được nhưng một hay nhiều kiểm soát cơ học bị thiếu, cũ hoặc không rõ | không được tuyên bố gate blocking đã corroborate run |
| `unsupported` | thiếu năng lực runtime/platform bắt buộc | không được tuyên bố Codex ngang hàng |

Mode đang hoạt động và mã bằng chứng doctor được ghi vào metadata run artifact/SUMMARY. `unknown`
không bao giờ được thu gọn thành `enforced`. Cài lại, sửa config, nâng CLI hoặc đổi trust hash đều
làm vô hiệu chẩn đoán cache.

D3 (“ship advisory”) cho phép người dùng alpha chạy với cưỡng chế yếu hơn khi mọi khoảng trống đều
hiển thị. Nó không biện minh cho nhãn peer GA trước khi gate behavioural và effective-enforcement
đạt yêu cầu.

---

## 6. Delivery chỉ dẫn và quyền sở hữu `AGENTS.md`

### 6.1 Rule và path

Cơ chế tự nạp `paths:` theo path của Claude không có đảm bảo tương đương ở Codex và vốn đã không an
toàn cho context cô lập. Cơ chế này chỉ còn là tối ưu:

- mọi skill/agent sử dụng đều đọc tường minh từng rule load-bearing;
- câu chữ tham chiếu path nguồn trong repository (`rules/...`), không dùng `.claude/rules/...`;
- `context-propagation-audit` chứng minh delivery đến từng context cô lập;
- từ chối viết lại prose lúc adapter chạy và từ chối inline policy trùng lặp.

### 6.2 `AGENTS.md` gốc hiện có thuộc quyền người dùng

Codex tìm các file `AGENTS.md` phân cấp từ root repository đến thư mục làm việc. Nó **không** dùng
`.codex/AGENTS.md` làm điểm vào chỉ dẫn repository. Repo này đã track một `AGENTS.md` ở root với nội
dung chủ ý khác `CLAUDE.md`.

Installer không bao giờ được thay toàn bộ file đó. Nó có thể chọn một trong hai chiến lược không ghi
đè sau đây, được quyết định và test ở phase đóng gói:

1. vùng được quản lý nằm giữa hai sentinel và trỏ tới chỉ dẫn entry chung của harness; hoặc
2. một dòng con trỏ tường minh do người dùng chọn thêm, còn nội dung harness sinh ra nằm ở file khác.

Contract test phải bao phủ cài mới, cài khi đã có nội dung custom, cài lại, chỉnh sửa local trong/
ngoài sentinel và xung đột với bản mới. Khi xung đột, giữ file local và ghi bản incoming để review,
phù hợp hành vi protected-file hiện tại của repository.

### 6.3 Câu chữ trung tính cú pháp gọi

Nguồn chung gọi tên skill (“invoke skill `feature-intake`”), không dùng `/feature-intake` hay
`$feature-intake`. Tài liệu entry có thể hướng dẫn cú pháp riêng của từng runtime.

---

## 7. Parity và provenance là release gate

Trạng thái peer có hai tầng bằng chứng.

| Tầng | Chứng minh điều gì | Chạy khi nào |
|---|---|---|
| Contract adapter deterministic | TOML/JSON sinh ổn định theo byte, strict config parsing, skill/agent discovery, coverage matcher/payload hook, manifest parity và cài đặt không ghi đè | mọi PR, blocking |
| Behavioural parity | lane, artifact, thao tác bị block, resume, ranh giới review subagent và review receipt tương đương giữa Claude và Codex | theo lịch và trước release; blocking cho GA |

Test do model điều khiển là bằng chứng behavioural, không phải deterministic config test. Fixture của
chúng ghim input, output invariant kỳ vọng, phiên bản CLI/runtime và field nondeterministic được phép.

### 7.1 Review receipt nhận biết runtime

Chỉ ghi runtime của reviewer là chưa đủ: không thể đánh giá độc lập khi thiếu provenance của builder.
Về mặt khái niệm, receipt phát triển thành:

```json
{
  "builder": {
    "runtime": "claude|codex|mixed",
    "client_version": "...",
    "model_family": "..."
  },
  "reviews": [
    {
      "runtime": "...",
      "model_family": "...",
      "origin": "internal|external",
      "harness_blind": true
    }
  ]
}
```

Schema cuối vẫn giữ reviewed-SHA, loại review, finding và verdict hiện có của receipt.

- `builder.runtime = mixed` nghĩa là nhiều hơn một runtime đã góp thay đổi implementation kể từ
  ranh giới review được chấp nhận gần nhất; artifact ghi tập runtime/model tham gia.
- External oracle phải harness-blind và, khi có thể, dùng runtime/model family không nằm trong tập
  builder.
- Nếu không có oracle tách biệt, run cần ngoại lệ có owner tường minh hoặc human review; không được
  âm thầm tuyên bố đã có corroboration dị thể.

Checker cưỡng chế hình dạng provenance và tính độc lập chéo runtime/model tách biệt với tính đúng
của review. Nó không được tuyên bố nhãn khác nhau bảo đảm suy luận độc lập.

---

## 8. Các phase triển khai và gate

| Phase | Deliverable | Gate thoát |
|---|---|---|
| **1 — Đường cơ sở capability** | ma trận event/tool/platform có version; fixture live cho shell, `apply_patch`, trust/config, agent dispatch và thời gian SessionEnd | mọi claim load-bearing đã được quan sát hoặc đánh dấu unknown |
| **2 — Quyết định đóng gói** | spike plugin/hybrid so với direct sync; hành vi discovery, upgrade và conflict | chọn một đường package với tiêu chí fallback được ghi lại |
| **3 — Trung tính hoá ngữ nghĩa** | tham chiếu rule từ repo root, mọi explicit Read, prose trung tính cú pháp gọi, capability agent trung tính và binding map | hành vi Claude không đổi; context-delivery audit đạt |
| **4 — Đường nối hook** | payload normalizer, unknown policy theo gate, fixture matcher/event chính xác | không còn silent fail-open cho đường tool được hỗ trợ |
| **5 — Codex alpha adapter** | agent/config sinh ra, tích hợp `AGENTS.md` không ghi đè, runtime doctor, ghi mode | deterministic adapter suite đạt trên macOS/Linux/WSL baseline |
| **6 — Parity gate mỗi PR** | runtime block trong manifest, strict config/discovery/install check, schema review provenance | deterministic check chặn drift trên mọi PR |
| **7 — Behavioural parity** | golden workflow chéo runtime và test ranh giới subagent | golden bắt buộc đạt trên các phiên bản hỗ trợ đã ghim |
| **8 — GA** | installer/docs công bố Codex là peer; review mọi ngoại lệ còn lại | không có ngoại lệ vô chủ/quá hạn; claim enforced hoặc advisory được giới hạn rõ |

Phase 1–4 là điều kiện trước khi nối Codex alpha adapter vào hệ thống, không phải cleanup tuỳ chọn
sau adapter. Phase 5 là **alpha**, không phải GA. Claim peer của D2 chỉ đúng sau Phase 6–7; D3 cho
phép alpha advisory sớm hơn nhưng không dời đích đó.

---

## 9. Các quyết định

| # | Quyết định | Hệ quả |
|---|---|---|
| **D1** | Codex chạy agent như một workflow runtime đầy đủ. | mapping capability agent, dispatch fresh/bounded và behavioural test subagent nằm trên critical path |
| **D2** | Codex hướng đến trạng thái peer. | deterministic parity chạy mỗi PR; behavioural parity chặn GA |
| **D3** | ship alpha advisory trước khi mọi đường cơ học đều enforce được. | mode do doctor xác định phải hiển thị và được ghi lại; advisory không bị gọi ngầm là enforced |
| **D4** | dùng chung nguồn ngữ nghĩa, không dùng chung field cấu hình runtime. | adapter chứa policy binding tường minh, được review |
| **D5** | ưu tiên đóng gói hybrid plugin/project. | plugin sở hữu skill/hook tái sử dụng; project adapter sở hữu agent và tích hợp repository hữu hạn, tuỳ bằng chứng Phase 2 |
| **D6** | bảo toàn `AGENTS.md` gốc. | không sinh/ghi đè toàn file; tích hợp vùng quản lý phải có conflict test |

---

## 10. Ngoài phạm vi

- Fork skill hoặc workflow policy theo runtime.
- Tuyên bố hỗ trợ Windows native trước khi có adapter hook Windows.
- Mô phỏng orchestration cloud của Codex; thiết kế này nhắm tới CLI/runtime local.
- Thay đường cài Claude hiện tại hoặc đổi ngữ nghĩa workflow của Claude.
- Coi riêng nhãn runtime là bằng chứng review độc lập.

---

## 11. Nguồn và tầng bằng chứng

Các claim capability đã được làm mới từ tài liệu chính thức của OpenAI và kiểm tra bằng probe local
cô lập trên Codex CLI 0.147.0. Tài liệu là bằng chứng traceability; fixture deterministic/live được
lưu ở Phase 1 sẽ trở thành bằng chứng provenance/behavioural. Các lỗ hổng hook lịch sử không còn được
dùng làm tiền đề kiến trúc hiện tại.

- [Codex hooks](https://developers.openai.com/codex/hooks)
- [Codex skills](https://developers.openai.com/codex/skills)
- [Codex subagents](https://developers.openai.com/codex/subagents)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference)
- [Codex plugins](https://developers.openai.com/plugins/build/plugins)
- [Chỉ dẫn repository bằng AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [openai/codex#16732](https://github.com/openai/codex/issues/16732) — issue coverage
  `apply_patch` lịch sử, nay đã đóng; chỉ giữ để giải thích vì sao thiết kế cũ có thể lỗi thời
