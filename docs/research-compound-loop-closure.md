# Research — Liệu vòng lặp `/compound` có khép kín không?

> Câu hỏi: Sau khi chạy `/compound` và sinh ra file trong `docs/solutions/`, các session mới sau này có **tự đọc lại** không, và harness có **rút được kinh nghiệm** từ nó không?
> Phạm vi: repo `harness-skills`
> Ngày nghiên cứu: 2026-06-08
> Phương pháp: trace wiring thực tế (SKILL.md, settings.json, hooks/, CLAUDE.md) — không dựa vào mô tả README.

---

## Verdict

**Vòng lặp đang MỞ (semi-closed).** `/compound` **ghi** kiến thức bền vững thành công, nhưng harness **không có cơ chế tự kéo** kiến thức đó vào context của một session mới. Kiến thức chỉ quay lại khi **một người/skill chủ động pull**.

---

## Bằng chứng

### 1. `/compound` ghi gì (CONFIRMED)
`skills/compound/SKILL.md` ghi ra đúng 3 đường dẫn:
- `docs/solutions/<category>/<slug>.md` — entry theo track (bug/knowledge/decision/failure) — *line ~90*
- `docs/solutions/critical-patterns.md` — khi `severity = critical` — *line ~309*
- `docs/solutions/INDEX.md` — rebuild toàn bộ sau mỗi lần chạy — *line ~343*

### 2. Tự đọc lúc session start (NOT FOUND)
- ❌ Không có **SessionStart hook**: grep `"SessionStart"` toàn repo → 0 kết quả.
- ❌ `settings.json` / `settings.local.json` chỉ đăng ký SessionEnd (`state-breadcrumb.sh`), không có SessionStart.
- ❌ Không hook nào trong `hooks/` đọc/`cat` `docs/solutions/`.

### 3. Đọc bởi skill (pull, không phải push) — CONFIRMED
- **`/xia2`** (`skills/xia2/SKILL.md:93-99`): đọc INDEX trước → đọc `critical-patterns.md` **bất kể domain** → đọc tối đa **3** file solution theo recency. Fallback grep nếu không khai báo Index trong `PROJECT.md`.
- **`/brainstorming`** (`skills/brainstorming/SKILL.md:79-83`): `grep "problem_type: decision" docs/solutions/` → đọc các file decision để tránh đề xuất lại phương án đã bị loại.

### 4. Khoảng trống thực sự
```
Session 1: làm việc → phát hiện bug → /compound → ghi docs/solutions/foo/bar.md
   ↓ [kết thúc session 1]
Session 2 (mới): context KHÔNG chứa bar.md
   ↓
   ├─ Gọi /xia2 hoặc /brainstorming?  → CÓ: skill pull từ docs/solutions/
   └─ Không gọi?                       → kiến thức VÔ HÌNH trong session này
```
Không có đường nào để `critical-patterns.md` (hay entry bất kỳ) tự nạp vào context session mới nếu không có hành động chủ động.

### 5. Sắc thái: vì sao là "bán-khép" chứ không hoàn toàn mở
`CLAUDE.md` **được auto-load** mỗi session và chứa dòng:
> "Critical learnings (read at planning time): `docs/solutions/critical-patterns.md`"

→ Đây là **con trỏ tự nổi lên**, nhưng **nội dung thì không tự nạp**. Nó chỉ *nhắc* model đọc lúc planning — phụ thuộc model có tuân theo hay không. Pointer auto, content on-demand.

### 6. Thực trạng dữ liệu
`docs/solutions/` **chưa tồn tại** (scaffold-only) — chưa từng chạy `/compound` hay `/bootstrap-xia2`. Loop hiện chưa có dữ liệu để kiểm chứng end-to-end.

---

## Bảng tổng hợp

| Thành phần | Trạng thái | Bằng chứng |
|---|---|---|
| Compound ghi file | ✅ | `compound/SKILL.md` line ~90, ~309, ~343 |
| Auto-load lúc SessionStart | ❌ Không có | 0 SessionStart hook; grep 0 match |
| Hook đọc docs/solutions | ❌ Không có | chỉ SessionEnd `state-breadcrumb.sh` |
| `/xia2` pull | ✅ | `xia2/SKILL.md:93-99` (INDEX → critical-patterns → ≤3 file) |
| `/brainstorming` pull | ✅ | `brainstorming/SKILL.md:79-83` (grep decision) |
| critical-patterns tự nạp | ❌ | chỉ đọc khi gọi `/xia2` |
| docs/solutions/ hiện tại | TRỐNG | thư mục chưa tồn tại |
| **Trạng thái vòng lặp** | **MỞ / bán-khép** | resurface chỉ khi pull |

---

## Phương án khép vòng lặp (chưa triển khai — chỉ ghi nhận)

| Mức | Cách làm | Đánh đổi |
|---|---|---|
| **Nhẹ** | Sửa pointer trong `CLAUDE.md` thành imperative ("ALWAYS read `critical-patterns.md` before planning/implementation") | Vẫn phụ thuộc model tuân lệnh; 0 token nền |
| **Vừa (khuyến nghị)** | Thêm **SessionStart hook** in nội dung `INDEX.md` + `critical-patterns.md` (hoặc tiêu đề) vào context | Tốn ít token/session; khép loop thật, không phụ thuộc skill |
| **Nặng** | SessionStart hook + relevance-filter (chỉ surface entry khớp file/branch đang mở) | Phức tạp, cần script lọc |

> ⚠️ SessionStart hook + `settings.json` là **high-blast file** (Rule 4, `auto-correct-scope.md`) → cần xác nhận của người dùng trước khi sửa.

---

## Hệ quả thực tế
Cho tới khi loop được khép, để tái sử dụng kiến thức `/compound` ở session mới, cần **chủ động** một trong các cách:
1. Gọi `/xia2` (đọc INDEX + critical-patterns + ≤3 solution).
2. Gọi `/brainstorming` (đọc các decision liên quan).
3. Tự đọc `docs/solutions/INDEX.md` hoặc `critical-patterns.md` rồi dẫn vào prompt.
