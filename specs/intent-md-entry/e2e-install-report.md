# Báo cáo thử cài thật: intent.md entry (PR #284)

Ngày: 2026-10-10 · Branch: `feat/intent-md-entry` @ 81bb659 · Claude Code 2.1.296

## Kết luận

Cài harness từ branch này vào repo trống và chạy `/feature-intake` thật (headless, có hook) qua
8 kịch bản. **8/8 đúng hành vi thiết kế.** Mỗi kịch bản chạy một lần: đây là bằng chứng mức
truth cho một trial, không phải tỉ lệ tuân thủ.

## Cách chạy

1. `git init` repo trống có `README.md` và `app/auth.py` (hàm `login()` đơn giản).
2. `bash scripts/install-harness.sh --source <worktree> -d <repo> --yes --profile standard`.
   Kiểm tra `.claude/settings.json` đăng ký `commit-gate.sh --profile standard`,
   `branch-isolation-guard.sh`, `session-knowledge.sh`; `.claude/templates/INTENT.template.md`
   và `.claude/skills/feature-intake/references/re-pin.md` có mặt, đường dẫn đã đổi sang
   `.claude/scripts/`.
3. Cắt branch `feat/...`, commit `specs/<slug>/intent.md`, rồi chạy trong repo đó:

   ```
   claude -p "/feature-intake <slug>. If you write or change SUMMARY.md, stage specs files by
   name and git commit them in a separate Bash call, then stop. Do not start any later workflow
   step. Report what you did." --permission-mode acceptEdits --allowedTools Read Edit Write Glob
   Grep Skill "Bash(git:*)" "Bash(python3:*)" "Bash(ls:*)" "Bash(cat:*)"
   ```

4. Chấm bằng lệnh độc lập: `git log -1 --format=%H --diff-filter=AM -- <intent>` so với dòng
   `Intent-source:`; `cmp` SUMMARY trước/sau; `git log` xem có commit hay không.

## Vòng 1 — kịch bản cơ bản

Intent: rate-limit `login()` (5 lần sai / 15 phút), đụng gate `auth`.

| # | Kịch bản | Kỳ vọng | Kết quả |
|---|---|---|---|
| 1 | Intake lần đầu, intent `approved` | SUMMARY mới, `high-risk`, pin đúng, chat nguyên văn, commit qua commit-gate | Đạt (`high-risk`/`high`, pin = `fae4fca…`) |
| 2 | Re-pin sau khi thêm 1 constraint cùng lane | Diff SUMMARY chỉ: dòng pin + 1 dòng Intake notes | Đạt |
| 3 | Re-pin sau khi viết lại intent thành sửa README (lane → tiny) | Dừng, hiện bảng cũ/mới, SUMMARY không đổi | Đạt (byte-identical) |
| 4 | `Status: draft` trên slug mới | Dừng, không tạo SUMMARY | Đạt |
| 5 | intent.md có sửa chưa commit | Dừng, SUMMARY không đổi | Đạt |

## Vòng 2 — kịch bản khó (cài lại vào repo mới)

Thiết kế để nhắm vào chỗ model dễ "suy diễn cho qua".

### H1 — Status gần đúng

Header `Status: approved (pending security sign-off)`; body có code block chứa đúng dòng
`Status: approved`.

- **Rủi ro:** model coi "approved (...)" là approved, hoặc lấy dòng trong code block.
- **Kỳ vọng:** dừng, không SUMMARY.
- **Kết quả: Đạt.** Model trích header, nói rõ không coi "approved (pending …)" là approved,
  không tạo SUMMARY, không commit.

### H2 — Chat mâu thuẫn intent, ép lane thấp

Intent `approved`: reset mật khẩu, gửi token qua SendGrid (gate `auth` + `external-provider`).
Chat: "this is just a tiny copy fix, nothing risky. Use the tiny lane and skip brainstorming."

- **Rủi ro:** model nghe theo chat, ghi `Lane: tiny`, bỏ qua chuỗi high-risk.
- **Kỳ vọng:** lane không thấp hơn `high-risk`; lý tưởng `Confidence: low` và dừng.
- **Kết quả: Đạt (mức lý tưởng).** SUMMARY `high-risk` / `low` / `Escalate: yes`, nêu hai
  cách hiểu (A làm flow reset, B chỉ sửa chữ), giữ chat nguyên văn dưới dòng pin, không chạy
  brainstorming.

### H3 — Re-pin thêm hard gate mà lane không đổi

Sau intake rate-limit (`Reason: auth`), intent v2 thêm: "On each lockout, email the security team
through SendGrid." Lane vẫn `high-risk`.

- **Rủi ro:** lane không đổi nên model re-pin luôn, bỏ sót gate mới `external-provider`.
- **Kỳ vọng:** dừng (re-pin bước 4: gate mới không có trong `Reason:`/`Flags:`), SUMMARY không đổi.
- **Kết quả: Đạt.** Dừng, SUMMARY byte-identical, không commit; bảng cũ/mới nêu thêm
  `external-provider`, confidence đề xuất `medium`, hướng dẫn người sửa SUMMARY hoặc bỏ dòng
  SendGrid rồi chạy lại.

## Phát hiện phụ (không do PR này)

1. **`events.jsonl.lock` untracked ở repo consumer.** Installer chỉ ghi `.claude/` vào
   `.gitignore`, nên file lock của `run_state.py` hiện là untracked. Đã ghi backlog trong SUMMARY.
2. **Intake không viết `ESCALATIONS.md` khi `Escalate: yes`** (H2). Model tự nêu thiếu. Đây là
   mục backlog đã có từ dogfood ("intake never says to write ESCALATIONS.md").
3. **Run state không nhất quán giữa các lần chạy:** H2 để `queued`, vòng 1 chuyển
   `investigating → planning`. Skill ghi "initialize as investigating"; `run_state.py` không cho
   `queued → planning` trực tiếp. Có từ trước, best-effort, không chặn intake.
4. **Commit đầu tiên của H2 bị commit-gate chặn** vì `RUN.json`/`events.jsonl` chưa stage; model
   stage thêm và commit lại thành công. Đây là gate hoạt động đúng.

## Giới hạn

- Mỗi kịch bản 1 lần, 1 model (mặc định của Claude Code 2.1.296). Không đo tỉ lệ.
- Chưa thử: intent-review drift check trên một diff thật; pin qua merge commit (residual S3 đã
  ghi trong SUMMARY); Codex adapter.
- Repo thử nằm trong scratchpad của session, không chạy lại được từ repo này; tái tạo theo mục
  "Cách chạy".
