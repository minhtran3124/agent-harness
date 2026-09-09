# Học được gì từ `spotify/portal-ai-plugins`

> Ngày: 2026-09-09 · Đọc tại commit `3c24ca3` của Spotify, repo mình tại `e61fc51`
>
> Bản tiếng Việt rút gọn của [`2026-09-09-spotify-portal-ai-plugins.md`](2026-09-09-spotify-portal-ai-plugins.md).
> Bản tiếng Anh là bản đầy đủ: mọi trích dẫn file:line, phần phân tích `shunt` chi tiết,
> và mục "những gì chưa kiểm tra" đều nằm ở đó.
>
> Cách làm: 4 agent chạy song song (skills của Spotify, plugin `shunt`, đóng gói đa runtime,
> kiến trúc repo mình) cộng với việc luồng chính tự đọc toàn bộ 36 file của repo Spotify và
> chạy cả hai bộ test.

## Kết luận

Repo của Spotify **không** tinh vi hơn repo mình. Nó **nhỏ hơn và đóng gói tốt hơn** — và đó
chính là bài học. Một câu tóm gọn cả bài so sánh:

> **Họ đo chi phí nhưng không đo chất lượng phán đoán. Mình đo phán đoán nhưng chưa bao giờ đo
> chi phí.**

---

## 1. Hai repo khác nhau về bản chất

Phải làm rõ chỗ này trước thì phần so sánh sau mới trung thực.

**`spotify/portal-ai-plugins`** là *client* gọi một dịch vụ bên ngoài. Nó bọc Portal CLI
(`npx @spotify/portal-cli`) trong sáu tài liệu prompt — thiết lập auth, chẩn đoán, tìm kiếm
catalog, tóm tắt service, gọi action, gửi feedback — rồi đóng gói cho ba coding agent khác nhau
cài được. Kèm một plugin phụ tên `shunt` chuyển các thao tác đọc file tốn kém sang một model rẻ
hơn. Hết.

**Repo mình** là *bộ khung quản trị* cho chính con agent. Nó phân loại yêu cầu thay đổi vào một
risk lane, quyết định lane đó nợ bao nhiêu bằng chứng, điều phối các subagent cô lập, và chặn
commit khi lane khai báo không khớp với diff đã stage. Nó không gọi dịch vụ ngoài nào cả — thứ
nó vận hành lên chính là hành vi của agent.

Chênh lệch kích thước là hệ quả của khác biệt đó, và nó lớn:

| | Spotify | Mình |
|---|---|---|
| Số file (không tính `.git`) | 36 | ~1.100 |
| Dòng code + docs | 1.744 | ~102.000 |
| Skills | 8 (6 portal + 2 shunt) | 12 |
| Hooks | 2 | 11 đang đăng ký |
| Scripts | 3 | 76 |
| Commits | 6 | 868 |
| Bộ test | 51 case, **~5 giây**, không cần credential | 200+ shell case + 582 pytest, **3 phút 25** |

*(Số file và dòng lấy bằng `find`/`wc` trên cả hai cây thư mục; số commit bằng
`git rev-list --count HEAD`. Cả hai bộ test đều được đo bằng cách chạy thật: của họ
`bash plugins/shunt/evals/run.sh` → 51 passed, 0 failed. Của mình `bash scripts/run-tests.sh`
→ ALL GREEN trong 3:25.)*

Vậy "Spotify đơn giản hơn" không phải một phát hiện. Câu hỏi đúng hẹp hơn: **trong cái phạm vi
nhỏ mà họ làm, họ có lựa chọn nào đáng copy không?** Có, vài thứ.

---

## 2. Phần hay nhất: năm mẹo viết prompt

Đây là thứ ít hiển nhiên nhất và dễ mang đi nhất trong cả repo. Mỗi cái chỉ một dòng prose
nhưng làm việc mang tính **cấu trúc**.

**1. Anti-trigger đặt ngay trong description.** `skills/search/SKILL.md:3`:

> Dùng khi người dùng hỏi để tìm service, API, system, component, owner hoặc tài liệu Portal
> **và chưa biết entity reference chính xác.**

Mệnh đề kích hoạt mang một điều kiện **phủ định**, nên skill tự từ chối chạy khi đã có đường rẻ
hơn. Đó là chặn định tuyến với chi phí điều phối bằng 0 — không dispatcher, không bảng ưu tiên,
chỉ một mệnh đề. Không description nào trong 12 skill của mình có thứ này, trong khi mình có ít
nhất hai cặp skill chồng lấn cần nó: `xia2` vs `brainstorming`, và `correctness-review` vs
`intent-review`.

**2. Mơ hồ là một trạng thái đầu ra có tên, không phải lỗi.** `skills/doctor/SKILL.md:53-54`:

> Khi tồn tại nhiều instance và không có target nào được cung cấp, hãy báo cáo sự mơ hồ thay vì
> tự chọn một cái.

Thứ làm luật này *dính* là nó được đưa tiếp vào schema đầu ra ở `skills/doctor/SKILL.md:75` —
`| Authentication | Ready, ambiguous, or blocked |`. Một câu prose trần sẽ không sống sót qua
lúc viết báo cáo; một giá trị thứ ba trong enum thì có. Đây cùng một bản năng với verdict
`unconfirmed` trong `evals/context-boundaries/README.md` của mình, và đáng để tổng quát hóa:
**luật nào nói "đừng đoán" thì format đầu ra phải có sẵn một ô cho "không biết".**

**3. Enum trạng thái khai báo ngay trong bảng đầu ra.** `skills/doctor/SKILL.md:71-76` cho mỗi
check một bộ từ vựng *khác nhau* — Plugin là "Ready, warning, or blocked", Authentication là
"Ready, ambiguous, or blocked", CLI và Actions là "Ready or blocked". Sáu dòng bảng kiêm luôn
vai trò spec từ vựng trạng thái, diệt drift mà không cần tài liệu schema riêng.

**4. `--yes` bị đảo thành dấu hiệu đã xin phép.** `skills/actions/SKILL.md:29`:

> Chỉ thêm `--yes` khi action được đánh dấu destructive **và** người dùng đã cho phép.

Hai điều kiện nối bằng "và" khiến cờ auto-approve không bao giờ dùng được để giảm ma sát. Nó
trở thành *bằng chứng rằng việc xin phép đã xảy ra* — ngược hẳn với phản xạ thông thường. So
sánh với `BRANCH_ISOLATION_REASON` của mình: cùng một phép đảo, và có ghi log.

**5. Vi phạm policy thì báo lên, đừng lặng lẽ sửa.** `skills/feedback/SKILL.md:25`:

> Không đưa secret, token, dữ liệu cá nhân hay URL nội bộ vào text. Nếu lời của người dùng có
> chứa những thứ đó, **hãy bảo họ viết lại thay vì tự sửa trong im lặng.**

Sửa ngầm sẽ phá vỡ cam kết "nguyên văn" đưa ra ngay dòng trên (`skills/feedback/SKILL.md:24`).
Đẩy ngược về cho con người giữ được dấu vết audit thay vì tẩy trắng nó. Mình cũng có cam kết
nguyên văn y hệt trong `templates/SUMMARY.template.md` — khối `### Intent` ghi rõ "do NOT
paraphrase or summarize" vì nó là oracle cho intent-review — nhưng mình **chưa bao giờ nói phải
làm gì khi chính cái text nguyên văn đó là vấn đề**.

### Về cấu trúc skill: khác biệt nhỏ hơn tôi tưởng lúc đầu

Lần đọc đầu tôi kết luận skill của họ có skeleton chung còn của mình thì không. Kiểm tra kỹ thì
khác biệt nhỏ hơn — và thú vị hơn.

**Không repo nào dùng lại tên heading cả.** Sáu skill của Spotify sinh ra 14 heading H2 với
**không cái nào lặp**. Mình sinh 29 heading trên 12 skill, chỉ `## References` (4 lần) và
`## Arguments` (2 lần) là lặp. Xét trên tiêu chí chữ nghĩa, họ không chuẩn hóa hơn mình.

Thứ họ thực sự có là skeleton **theo vị trí, không theo tên** — bốn thứ luôn nằm đúng chỗ, dù
mang tên gì tùy lĩnh vực:

1. H1 là một cụm động từ mệnh lệnh ("Diagnose Spotify Portal", "Invoke Portal Actions").
2. Một câu khai báo nguồn-sự-thật quanh dòng 8 ("Use the Portal CLI as the source of truth").
3. Đúng một mục quy trình có đánh số — đặt tên `<gì đó> workflow` ở 4/6 skill.
4. Một dòng cấm đoán ở cuối cùng ("Never infer successful execution from a dry run.").

Điểm 4 tự nó đã là một mẹo hay: ràng buộc mạnh nhất được đặt vào vị trí dễ nhớ nhất của tài
liệu. Skill của mình không có trật tự lặp lại nào, cũng không có quy ước chỗ đặt điều cấm.

Ngoài ra, `description:` của họ là một template hai mệnh đề cứng ở cả sáu file —
`<câu mô tả năng lực>. Use when <danh sách trigger>.` Chính sự nhất quán đó làm khuyến nghị ở
mục 3.2 dưới đây rẻ để thực hiện: có sẵn một cái khuôn để copy, không chỉ là giọng văn.

---

## 3. Năm thứ đáng lấy

### 3.1 Cài như plugin, đừng copy file — giá trị cao nhất

Cài của Spotify là hai dòng người dùng gõ một lần:

```bash
claude plugin marketplace add spotify/portal-ai-plugins
claude plugin install portal@portal
```

Của mình là `scripts/install-harness.sh`: một script `curl … | bash` clone repo vào thư mục
tạm, merge-sync chín mục top-level vào `.claude/` của project đích, merge một entry vào
`.mcp.json`, dựng `specs/` và `docs/solutions/`, và mang theo cả một giao thức xử lý xung đột
(file `.harness-incoming`) — vì nó đang tự làm bằng tay đúng việc của một package manager.

Cơ chế thì gần như đã có sẵn: mình đã có manifest plugin Codex sinh tự động ở
`adapters/codex/plugin/.codex-plugin/plugin.json`. Nhưng **không có `.claude-plugin/` ở gốc
repo** — tôi đã kiểm: `ls -d .claude-plugin` báo lỗi, `git ls-files | grep marketplace` chỉ ra
fixture test.

Một rào cản thật: `settings.json` đăng ký hook bằng đường dẫn **tương đối**
(`hooks/pre-bash-dispatch.sh`), chỉ chạy được vì mình copy cả cây vào project. Spotify dùng
`${CLAUDE_PLUGIN_ROOT}/hooks/check-file-size`. Chuyển sang đường dẫn theo plugin-root chính là
phần việc thật.

**Kết quả spike (2026-09-09): đóng gói chạy được, nhưng nó lộ ra một vấn đề tệ hơn cái tôi dự
đoán.** Tôi dựng một plugin vứt đi đúng một hook, cài vào, rồi chạy một session headless trên một
repo test có index và worktree cố tình khác nhau. Ba đáp án:

| Câu hỏi | Kết quả |
|---|---|
| Hook plugin có CWD là project không? | ✅ `PWD` là thư mục project |
| Đọc được git index của project không? | ✅ `git show :file` trả về nội dung **đã stage**, phân biệt đúng với worktree |
| `${CLAUDE_PLUGIN_ROOT}` phân giải thế nào? | ✅ Trỏ đúng thư mục plugin, **và** `CLAUDE_PROJECT_DIR` được set song song |

Hai biến cùng có mặt — đúng thứ hook của mình cần: lib của plugin cộng git state của project. Giả
định ban đầu đứng vững.

**Nhưng rào cản thật nằm chỗ khác, và nó nguy hiểm.** Tám trong mười một hook của mình suy ra
repo-root **từ vị trí của chính chúng**:

```bash
REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
```

(`blast-radius-check`, `branch-guard`, `commit-quality-gate`, `render-plan-on-write`,
`risk-corroboration`, `ruff-on-edit`, `scope-gate`, và `check-untracked-py` qua lib của nó). Chỉ
`branch-isolation-guard.sh:27` và `pre-bash-dispatch.sh:21` dùng `CLAUDE_PROJECT_DIR`.

Dưới dạng plugin, `$SCRIPT_DIR` nằm ngoài project. Tôi đo hai kịch bản:

- **Plugin không nằm trong git repo nào** → `exit 128`, `REPO_DIR` rỗng. Hỏng, nhưng hỏng **ồn ào**.
- **Plugin nằm trong một git repo** → `exit 0`, và `git show :probe-target.txt` trả về
  `DECOY-INDEX-CONTENT-from-plugin-repo` — index của **plugin**, không phải của project. Gate chạy
  xanh trong khi soi nhầm repository.

Kịch bản thứ hai không phải giả định: `claude plugin marketplace add <github-repo>` **clone** repo
về, nên plugin cài từ marketplace **luôn** nằm trong một git repo. Đường cài bình thường chính là
đường rơi vào chế độ sai âm thầm. Đây là dạng nặng hơn của lỗi "green can mean skipped" — ở đây
green có nghĩa là *đã audit nhầm repo*.

**Hệ quả cho kế hoạch.** Việc thật không phải "đổi đường dẫn hook sang `${CLAUDE_PLUGIN_ROOT}`", mà là:

1. Chuyển cả 8 hook sang `CLAUDE_PROJECT_DIR` làm nguồn repo-root; `SCRIPT_DIR` chỉ còn dùng để
   định vị lib của chính hook.
2. Thêm guard fail-closed: nếu `CLAUDE_PROJECT_DIR` rỗng **và** root suy từ `SCRIPT_DIR` khác CWD
   thì chặn, đừng đoán. Không có guard này thì chế độ sai-âm-thầm còn tiếp cận được mãi.
3. Chỉ sau đó mới bàn tới marketplace manifest.

Bước 1 và 2 đáng làm **bất kể có bao giờ ship plugin hay không** — chúng vá một giả định vốn đã
mong manh ngay hôm nay. Nên tách khỏi mục này và làm sớm hơn.

**Có một cái lợi miễn phí ngay hôm nay.** `AGENTS.md` của Spotify ghi
`claude plugin validate --strict .` là một bước kiểm tra. Tôi đã chạy trên cả hai repo:

- Spotify: `✔ Validation passed`
- Mình: `✘ Validation failed` — ba cảnh báo cùng một dạng. `agents/README.md`,
  `agents/PROJECT.md` và `agents/PROJECT.template.md` nằm trong `agents/` nên bị đọc như định
  nghĩa agent, mà lại không có frontmatter.

Sửa mất khoảng 10 phút, rồi thêm một dòng vào CI. Hiện `.github/workflows/harness-ci.yml`
không chạy lệnh này bao giờ.

### 3.2 Viết lại `description:` bằng ngôn ngữ người dùng

Trường `description:` **chính là** tín hiệu định tuyến — model đọc nó để quyết định skill có áp
dụng không. So sánh:

**Của họ** (`skills/service/SKILL.md:3`):

> Dùng khi người dùng hỏi ai sở hữu một service, service có khỏe không, runbook hay tài liệu
> của nó ở đâu, hoặc yêu cầu một bản tóm tắt service.

**Của mình** (`skills/subagent-driven-development/SKILL.md:2`):

> Dùng để thực thi một PLAN.md nhiều task đã duyệt: các wave gồm implementer subagent cô lập,
> review theo từng task, resume qua session khác, và các gate delivery/correctness/intent cuối
> trước khi ship.

Của mình mô tả **cơ chế**, bằng từ vựng nội bộ. Của họ mô tả **tình huống của người dùng**, bằng
lời người dùng. Người nói "làm nốt cái plan mình chốt hôm qua đi" không nói "execute an approved
multi-task PLAN.md".

Ba việc cụ thể, đều thấy được trong repo của họ:

- **Theo template hai mệnh đề** — `<câu năng lực>. Use when <danh sách trigger>.`
- **Viết danh sách trigger thành tình huống người dùng**, không phải tên cơ chế.
- **Thêm anti-trigger ở chỗ skill chồng lấn** (mục 2, mẹo 1).

Điều này lộ ra một điểm yếu trong chính corpus eval của mình.
`evals/skills/prompt-refactor/activation/` yêu cầu tám case trigger mỗi skill, nghe rất chặt —
nhưng đọc `feature-intake.json` thì case 1–6 là **cùng một câu** gắn thêm tiền tố khác nhau
("Please do this in the repository: classify this change request into a risk lane…" / "This is
time-sensitive, but classify this change request into a risk lane…"). Cái đó đo độ bền với tiền
tố, không đo activation. Case activation thật phải được viết theo cách người dùng thực sự mở
đầu một session: *"thêm rate limiting cho endpoint login được không?"*

### 3.3 Đưa hướng dẫn theo ngữ cảnh ra khỏi phần always-on

Mình đã có ý đúng — `rules/*.md` chia hai tầng, 4/9 file có frontmatter `paths:` để nạp theo
nhu cầu. Nhưng tỉ lệ lệch:

| Always-on | Theo ngữ cảnh (`paths:`) |
|---|---|
| `architecture.md`, `behavior.md`, `guidelines.md`, `orchestration.md`, `research-depth.md` | `auto-correct-scope.md`, `plan-format.md`, `terminology.md`, `wave-parallelism.md` |

Cộng thêm `CLAUDE.md` 16 KB — khoản always-on lớn nhất và **không được phân tầng chút nào**.
Riêng `rules/orchestration.md` đã 6,6 KB, mà phần lớn nội dung (checklist escalation, contract
trả về của subagent) chỉ liên quan khi một plan đang thực sự chạy.

`shunt` cho thấy hướng khác: hướng dẫn sống trong chính cái hook thi hành nó, và chỉ xuất hiện
khi liên quan. Trong `hooks/check-file-size:3` họ ghi thẳng:

> Self-contained: all routing logic lives here, no CLAUDE.md needed

Dạng tổng quát: **luật nào có trigger cơ học thì đặt nội dung của nó vào chính thứ trigger đó.**
`hooks/scope-gate.sh:44` của mình đã làm đúng vậy rồi — nó bơm hướng dẫn về lane dưới dạng
`additionalContext` đúng lúc một prompt mang ý định implement mà chưa có plan. Đoạn text đó
không cần nằm thêm trong `CLAUDE.md` nữa.

Một lưu ý, lấy từ chính `CLAUDE.md`: thêm `paths:` vào một rule sẽ **loại** nó khỏi tập
always-on. Đó là thay đổi **hành vi**, không phải thay đổi định dạng, và
`tests/scripts/rule-loading-tiers.test.sh` sẽ bắt được. Coi mọi thao tác kiểu này là một thay
đổi thật, cần review thật.

### 3.4 Đo chi phí của harness, không chỉ đo tính đúng

`plugins/shunt/evals/benchmarks.json` cộng với nhánh `--benchmark` trong `run.sh` in ra bảng:

| Kịch bản | Dòng | Không có shunt | Có shunt | Tiết kiệm |
|---|---|---|---|---|
| Một file lớn | 4.014 | 33.684 token | 5.737 token | 82% |
| Cặp source + test | 7.408 | 75.990 token | 4.148 token | 94% |

Công thức ước lượng rất thô — số ký tự ÷ 4, token đầu ra nhân hệ số 5 — và `run.sh:290` in
đúng cái công thức đó ngay dưới bảng. **Thô mà nói rõ vẫn hơn chính xác mà giấu.**

Mình không đo gì tương tự. Tôi đã grep `evals/`, `docs/` và `scripts/` tìm bất kỳ hạch toán
token hay chi phí nào — không có. Eval của mình đo catch-rate, độ chính xác phân loại lane, và
việc chỉ thị có đến nơi không — toàn về tính đúng. Trong khi lời phàn nàn thực tế phổ biến nhất
về harness gần như chắc chắn là **chi phí nghi thức**: chuỗi đầy đủ cộng thêm bao nhiêu lượt,
bao nhiêu token, bao nhiêu thời gian cho một thay đổi lane normal? Hôm nay không ai trả lời
được — nghĩa là không ai tranh luận được một gate cụ thể có đáng giá hay không.

Bản rẻ nhất: ghi số lượt và thời gian trôi qua theo lane vào ngay header `SUMMARY.md` đang có,
rồi công bố một bảng cuộn. Nó biến "harness nặng quá" từ cảm giác thành con số — để hành động,
hoặc để bảo vệ.

### 3.5 Công bố giới hạn đã biết, và nói thật

`plugins/shunt/README.md` kết bằng ba điểm yếu thật trong thiết kế của chính nó: `code-writer`
không có hook nào ép cả (chỉ `bulk-reader` có), trần `ARG_MAX` cho kích thước request vì input
đi qua argv, và timeout mà các lần sinh code lớn có thể vượt. Mỗi cái nói rõ hỏng ở đâu và làm
gì thì thoát.

Mình có kỷ luật này ở mức **từng thay đổi** — khối `### Not auto-verified` trong mọi
`SUMMARY.md`. Nhưng không có ở mức **sản phẩm**. `README.md` và `HARNESS.md` mô tả harness thi
hành những gì; không file nào có mục nói nó **không** thi hành gì. Người đọc phải tự dựng lại
từ đoạn "Gate verifiability" trong `CLAUDE.md`, vốn viết cho người đóng góp chứ không phải cho
người đang cân nhắc có nên dùng.

---

## 4. Năm chỗ mình đang hơn

Ghi lại để khỏi bắt chước mù quáng lựa chọn của một repo nhỏ hơn.

**4.1 Gate của mình chạy bằng code — nhưng chỉ ở ranh giới commit.**
Skill `actions` của họ *yêu cầu* agent dry-run trước khi mutate. `risk-corroboration.sh` của
mình tự suy lại mức rủi ro từ diff đã stage và exit 2 khi lane khai báo quá thấp. Đó là khác
biệt giữa một lời hứa và một phép kiểm.

Có một minh chứng sống xuất hiện ngay khi viết báo cáo này: lần đầu tôi lưu file thì bị
`hooks/branch-isolation-guard.sh` chặn, vì đang ở `main` và chưa cắt nhánh. Gate bắn trúng
chính người đang viết tài liệu về gate.

**Nhưng cần khoanh vùng lại, và đây là điều chỉnh quan trọng nhất trong báo cáo.** Thứ được thi
hành bằng cơ học là *ranh giới commit và edit* — 11 cái hook. Còn *bản thân chuỗi skill* thì
được nối bằng prose, y hệt Spotify. Có ba script kiểm tra artifact — `verify_summary.py`,
`check_plan_contract.py`, `check_review_receipt.py` — nhưng mọi cái đều kiểm **hình dạng và nội
dung** của artifact, **không kiểm thứ tự** của chuỗi. Không có gì xác minh rằng brainstorming
đã thực sự chạy trước planning, rằng research đi trước plan, hay rằng route bắt buộc của một
lane đã được đi thay vì bị bỏ qua. Tôi đã kiểm:
`grep -rlniE 'design\.md|research-brief|brainstorm' hooks/*.sh` trả về đúng một kết quả, và đó
là một **comment** ở dòng 118 của `commit-quality-gate.sh`, không phải một phép kiểm.

Đáng nói thẳng, vì `CLAUDE.md` gọi việc bỏ một bước là "a hard gate violation" — nghe như có
thứ gì đó đang kiểm tra. Với ranh giới commit thì có thật. Với chuỗi skill thì gate chính là
việc model chịu tuân theo prose. **Hai tầng thi hành khác nhau nằm dưới cùng một từ.**

**4.2 Thông điệp chặn của mình đã tốt hơn của họ.** `shunt` chặn thì nêu một lựa chọn thay thế.
Của mình nêu nhiều, kèm cả lối thoát hiểm. Từ `hooks/branch-isolation-guard.sh:91`: nhận biết
lane, đưa hai đường sửa (tiny lane thì `git checkout -b`, normal/high-risk thì gọi skill
`using-git-worktrees`), và một override có ghi log (`BRANCH_ISOLATION_REASON`). Đây là xác nhận
cách mình làm đúng, không phải một khoảng trống.

**4.3 Hook của mình fail-closed khi không parse được input.**
`hooks/pre-bash-dispatch.sh:47` chặn (exit 2) khi không phân loại được payload, kèm comment
"blocking to fail safe". Hook của `shunt` thì fail **open** ở mọi nhánh — input hỏng, thiếu
field, lệnh lạ đều trả `allow`. Đó là lựa chọn đúng cho một tối ưu chi phí, và sẽ là một lỗ
hổng nếu đặt vào một gate quản trị.

**4.4 Hạ tầng test của mình sâu hơn ở mọi trục trừ tốc độ.**
`tests/lib.sh` cho mình một DSL thật: mỗi case chạy hook bên trong một git repo `mktemp` dùng
một lần, không đụng gì tới working tree. Hỗ trợ env theo từng case, file đã stage, và trạng
thái `xfail` cho bug đã biết.

Cái `xfail` đó quan trọng. `evals/bash-hook-evals.json` case 17 của Spotify mã hóa một bug
parser thật thành `expected_decision: "allow"` với lý do "Parser bug: -n and 5 are separate
args". Nó in ra **PASS**. Bug được ghi trong một chuỗi không ai đọc và vô hình ở dòng tổng kết.
`xfail` của mình in `xfail <case> — known bug: <reason>` ở mọi lần chạy, nên bug vẫn hiện hình
mà suite vẫn xanh. Cách của mình tốt hơn.

Chỗ họ thắng là thời gian: 51 case xong trong khoảng năm giây, không cần chuẩn bị gì, so với
3 phút 25 của mình. Nếu không ai chịu chạy suite ở máy local thì độ sâu của nó hết ý nghĩa —
nên thêm một tập con chạy nhanh là đáng.

**4.5 Eval hành vi của mình ở đẳng cấp khác.**
`evals/README.md` và `evals/skills/prompt-refactor/README.md` mô tả fixture có nhãn, các lần
chạy mù (skill không bao giờ thấy `truth.md`), luật "lần chạy đầu là bản ghi" cấm chạy lại tới
khi xanh, và một scorer coi chuyển dịch `pass → blocked` là *độ phủ chưa đo được* chứ không
phải regression. `evals/context-boundaries/README.md` còn đi xa hơn: dò theo từng execution
context xem một chỉ thị có thực sự tới nơi không — được xây sau một sự cố P1 thật (#141/#143)
khi một rule được *nhắc tới* trong dispatch prompt nhưng chưa bao giờ được *giao* cho subagent.

Spotify có `evals.json` với ba case hành vi và — tôi đã kiểm `run.sh` — **không có runner nào
chạy nó**. `run.sh` chỉ chạy `hook-evals.json`, `bash-hook-evals.json` và `transport-evals.sh`.
Eval hành vi của họ là nguyện vọng; của mình là một quy trình.

---

## 5. Hai thứ không nên copy

**Tư thế fail-open của hook họ.** Đúng cho `shunt`, sai cho mình. Luật tổng quát đáng ghi lại:
*tư thế khi hỏng của một hook phải khớp với mục đích của nó.* Một hook tối ưu mà fail-closed
sẽ chặn công việc người dùng chỉ vì lỗi parse. Một gate quản trị mà fail-open thì không còn là
gate. Hiện mình áp một tư thế (fail-closed) cho tất cả — đúng ở thời điểm này vì mọi hook mình
ship đều là gate, nhưng nên nói rõ ra trước khi có ngày thêm một hook tối ưu.

**Ghi bug đã biết thành test pass.** Đã nói ở mục 4.4. Dùng `xfail`.

---

## 6. Khuyến nghị, xếp theo giá trị ÷ chi phí

| # | Việc | File | Chi phí | Vì sao lúc này |
|---|---|---|---|---|
| **0** | **Chuyển 8 hook `git -C "$SCRIPT_DIR"` sang `CLAUDE_PROJECT_DIR`, + guard fail-closed khi hai root lệch nhau** | `hooks/*.sh` (8 file), `tests/hooks/*.test.sh` | ~nửa ngày | **Do spike tìm ra (mục 3.1).** Là điểm yếu của *hôm nay*, không phải tương lai; gate soi nhầm repo mà vẫn exit 0. Độc lập với việc có ship plugin hay không |
| 1 | Sửa `claude plugin validate --strict .` và thêm vào CI | 3 file trong `agents/`, một step trong `.github/workflows/harness-ci.yml` | ~30 phút | Tín hiệu đúng đắn miễn phí mà mình đang trượt; tiền đề cho #3 |
| 2 | Viết lại `description:` của cả 12 skill bằng ngôn ngữ người dùng | `skills/*/SKILL.md` | ~2 giờ | Cải thiện activation trực tiếp, không đổi cơ chế |
| 3 | Thêm `.claude-plugin/marketplace.json` + `plugin.json` ở gốc; chuyển hook path sang `${CLAUDE_PLUGIN_ROOT}` | `settings.json`, `.claude-plugin/` mới, `scripts/install-harness.sh` | ~1 ngày + spike chứng minh gate đọc index vẫn chạy | Bỏ được installer và giao thức xung đột của nó |
| 4 | Cắt bớt phần always-on: gắn `paths:` cho `orchestration.md`, tách `CLAUDE.md` | `rules/orchestration.md`, `CLAUDE.md` | ~nửa ngày | ~7K token mỗi session; xem lưu ý ở 3.3 |
| 5 | Thêm chiều chi phí vào eval — số lượt + thời gian theo lane trong `SUMMARY.md` | `templates/SUMMARY.template.md`, script mới | ~nửa ngày | Biến tranh luận về chi phí nghi thức thành có số liệu |
| 6 | Thêm tập con chạy nhanh cho `run-tests.sh` (`--quick`), mục tiêu <10 giây | `scripts/run-tests.sh` | ~2 giờ | 3 phút 25 là bộ test người ta chạy trên CI và bỏ qua ở local |
| 7 | Thêm mục "Known limitations" vào `README.md` | `README.md` | ~1 giờ | Trung thực khi người khác cân nhắc dùng |
| 8 | Thêm luật "chạy `--help` trước khi dựa vào một flag" | `rules/behavior.md` | ~15 phút | Chốt chặn hallucination rẻ mà mình đang thiếu |
| 9 | Mở rộng `allowed-tools` cho 9 skill còn thiếu | `skills/*/SKILL.md` | ~1 giờ | Least-privilege mình đã dùng ở 3/12; không có lý do để lệch |
| 10 | Định nghĩa **thứ tự** section chuẩn cho SKILL.md (không phải bộ heading cố định) | `skills/*/SKILL.md`, `templates/` | ~nửa ngày | Skill của mình không có trình tự lặp lại; của họ có, và điều đó giúp đọc lướt |
| 11 | Mỗi luật "đừng đoán" phải có một ô tương ứng trong format đầu ra | `templates/SUMMARY.template.md`, prompt review | ~2 giờ | Mục 2, mẹo 2 — luật không có chỗ ghi "không biết" sẽ bị âm thầm giải quyết bừa |
| 12 | Nói rõ phải làm gì khi text nguyên văn của user tự nó vi phạm policy | khối `### Intent` trong `templates/SUMMARY.template.md` | ~30 phút | Mục 2, mẹo 5 — mình hứa giữ nguyên văn nhưng chưa xử lý trường hợp có secret |

Các mục 1, 2, 7, 8, 9 và 12 độc lập với nhau và có thể làm xong trong tuần. Mục 3 là mục lớn và
cần một vòng thiết kế riêng — nó thay đổi cách harness được phân phối, tức là chạm trigger
*redefine the system* trong `rules/orchestration.md`, nên phải escalate chứ không làm tự động.

**Một khuyến nghị mà báo cáo này cố tình KHÔNG đưa ra:** "áp dụng `shunt`". Chuyển việc đọc file
sang model rẻ hơn là ý hay, nhưng nó phụ thuộc vào một Portal instance có bật AiKA — thứ mình
không có. Phần mang đi được là **mẫu thiết kế** — một hook chặn thao tác tốn kém rồi chỉ ra
đường rẻ hơn — chứ không phải phần đường ống.

---

## 7. Những gì tôi chưa kiểm tra

Nói thẳng để không ai suy diễn quá những gì báo cáo này chứng minh được.

- **Chưa chạy nhánh `--benchmark` của họ.** Nó cần một Portal instance và auth. Bảng tiết kiệm
  82–94% trong `plugins/shunt/README.md` lấy từ "một monorepo Java 162K dòng" không có trong
  repo, nên fixture `benchmarks.json` đã commit **không tái tạo được** đúng những con số đó.
  Hãy coi các phần trăm đó là *tuyên bố của họ*, chưa được kiểm chứng.
- ~~Chưa kiểm hook cài qua plugin có đọc được git index của project không.~~
  **Đã giải quyết 2026-09-09 bằng spike — xem mục 3.1.** Đọc được. Nhưng spike tìm ra một vấn đề
  khác và nghiêm trọng hơn: 8/11 hook suy repo-root từ vị trí của chính chúng, và dưới dạng plugin
  nó âm thầm phân giải sang repo của *plugin* với exit 0. Giờ là khuyến nghị #0.
  Vẫn chưa kiểm: hành vi này có giống nhau trên Linux không, và `CLAUDE_PROJECT_DIR` có được set
  ở **mọi** loại hook event không (tôi chỉ quan sát được với PreToolUse/Bash).
- **Chưa đánh giá bản thân Portal CLI** — chỉ đánh giá các tài liệu prompt gọi nó.
- **Chưa cài plugin của họ trên Codex hay Cursor.** `.codex-plugin/plugin.json` của họ có khối
  `interface` (màu thương hiệu, logo, prompt gợi ý) mà manifest Claude không có; tôi đọc schema
  chứ chưa chạy thử loader.
- **Chưa xác định contract đầu ra nào của hook là chuẩn.** Dạng `{"decision": …}` top-level của
  Spotify và dạng `hookSpecificOutput.permissionDecision` của mình đều chạy được hôm nay; tôi
  chưa tra tài liệu Claude Code xem cái nào thay thế cái nào. Đây là một câu hỏi mở, không phải
  một phát hiện.
- **Cả hai số đo thời gian test đều là một lần chạy trên một máy** (macOS, laptop này), không
  phải benchmark. Đúng về bậc độ lớn, không phải con số chính xác.
- **Một tuyên bố của agent không qua được khâu kiểm, và lý do đáng ghi lại.** Một subagent báo
  rằng "đúng một mắt xích trong chuỗi skill được code xác minh". Grep ra ba script xác minh chứ
  không phải một. Tuyên bố đã sửa ở mục 4.1 hẹp hơn và đúng: ba script kiểm *hình dạng*
  artifact; không có gì kiểm *thứ tự* chuỗi. Ghi lại ở đây vì bản gốc là **bản nghe hay hơn**,
  và nó sai.
- **Một tuyên bố của chính tôi cũng vậy.** Bản nháp đầu viết skill của Spotify có skeleton
  chung còn của mình thì không. Kiểm lại: heading của họ **cũng** không cái nào lặp. Khác biệt
  thật nằm ở *vị trí*, không phải *tên* — mục 2 đã sửa lại cho đúng.
