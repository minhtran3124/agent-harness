# Kiểm tra prompt: cấu hình Claude Code của `agent-harness`

## Giả định

**Model đích:** Sonnet 5.5, tức model đang chạy phiên này. Các file agent ghim model (`claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`) đều là thế hệ hiện tại, nên không có model đã ngừng dùng nào.

**Phạm vi đã tìm thấy:**
- File hướng dẫn của project: `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`.
- `~/.claude/CLAUDE.md`.
- `.claude/` của project: 10 file rule, 6 file agent, 16 skill cùng `skills/README.md`.
- Skill cấp user: `autopilot`, `create-pr`, `ink-artifact`.
- Plugin `harness` (`plugins/harness/`): 8 agent và 23 skill. Chỉ báo cáo, không đề xuất sửa.

**Không tìm thấy:**
- `CLAUDE.md` hoặc `AGENTS.md` ở thư mục cha: không có ở ba cấp cha.
- `CLAUDE.md` của managed-policy: `/etc/claude-code` không tồn tại.
- Import `@` trong `CLAUDE.md`: không có.
- Command hoặc output style: không có, ở cả hai cấp.

**Không đọc, theo yêu cầu của brief:**
- File settings (`settings*.json`), `hooks.json`, `.mcp.json` và `~/.claude.json`.
- Skill symlink `~/.claude/skills/wednesday-pulse` và `weekly-digest` (trỏ sang repo khác).
- Skill của plugin bên thứ ba (vercel, compound-engineering, cloudflare, v.v.), nằm ngoài phạm vi tôi kiểm tra được.

**Chỉ đọc một phần:**
- Rule legacy trong `.claude/`: `plan-format`, `wave-parallelism`, `review-policy`, `auto-correct-scope`, `terminology`, `research-depth`.
- Skill legacy trong `.claude/` và skill của plugin `harness`. Với các file này tôi dùng diff, grep theo mẫu tín hiệu và kiểm tra đường dẫn có tồn tại; tôi không đọc hết từng file.

**Sửa file trong `~/.claude/` ảnh hưởng mọi project.** Các mục đó được đánh dấu bên dưới.

## Tóm tắt

**1. Bản `.claude/` bị gitignore là bản harness đã triển khai và đã cũ, nhưng vẫn được nạp cùng plugin.**
- `.gitignore:23` bỏ qua `.claude/`, và `.claude/.harness-deployed` là manifest của nó.
- Mười skill trùng tên ở hai nơi nhưng nội dung khác nhau: `brainstorming`, `xia2`, `writing-plans`, `finishing-a-development-branch`, `using-git-worktrees`, `intent-review`, `compound`, `diagnosing-bugs`, `session-retro` và `asd-ste100` (lệch 4 dòng).
- `.claude/agents/task-reviewer.md` giống hệt bản của plugin. `coding` và `test-runner` trùng với `harness:implementer` và `harness:test-runner`.
- Rule legacy dùng từ vựng khác `CLAUDE.md`: `PLAN.md`, `SUMMARY.md`, `feature-intake`, lane `tiny|normal|high-risk`, so với `plan.md`, `summary.md`, `intake` và depth `S|M|L`. `skills/README.md:10-14` mô tả "Codex advisory alpha" và `docs/codex-alpha-install.md` không tồn tại, trong khi `CLAUDE.md:3` nói Claude Code là runtime duy nhất được hỗ trợ.
- Cả hai bản `behavior.md` đều được nạp vào mỗi phiên, và chúng khác nhau.

**2. `AGENTS.md` và `CLAUDE.md` không khớp với repo.**
- `AGENTS.md` ghi "six subagent role files" (thực tế có tám) và "four Bash hooks" (thực tế có sáu).
- `CLAUDE.md:77` nói mọi hook trừ `merge-guard.sh` đều fail open, nhưng dòng `stop-evidence.sh` ngay trong file đó nói nó chặn ở ngưỡng rủi ro.
- `CLAUDE.md:65` nói "Every skill above exists … now", nhưng `qa-writer` và `security-reviewer` là agent, còn `/code-review` không phải skill của plugin.

**3. `CLAUDE.local.md:38-52` trỏ tới skill và thuật ngữ chỉ có trong bản legacy.** Ví dụ `feature-intake`, lane, `Evidence Ledger`, `visual-planner --review` và `context-propagation-audit`. Workflow hiện tại ở `CLAUDE.md:52-63` không có cái nào trong số đó. Hai skill cấp user là `autopilot` và `create-pr` cũng có tham chiếu hỏng hoặc dành riêng cho project khác.

**Số lượng**

| Nhóm | Phát hiện |
|---|---|
| 1. Văn bản prompt lỗi thời | 0 mức cao hoặc trung bình; 2 mục flag mức thấp. Ngôn ngữ nhấn mạnh rất ít, các chỗ `MUST`/`NEVER` đều là ràng buộc thật. |
| 2. File cấu hình dễ gãy | 11 |
| 3. Mô tả tool | 1 |
| 4. Danh sách agent | 1 (agent trùng lặp) |

Theo độ tin cậy: 7 cao, 6 trung bình và 5 thấp hoặc chỉ flag.

## Phát hiện

### Độ tin cậy cao

| # | Vị trí | Bằng chứng | Mẫu | Vì sao lỗi thời | Hành động |
|---|---|---|---|---|---|
| H1 | `AGENTS.md:11` | "the six subagent role files" | G2 chi tiết dễ đổi | `plugins/harness/agents/` có 8 file: advisor, implementer, intent-reviewer, qa-writer, researcher, security-reviewer, task-reviewer, test-runner. | rewrite |
| H2 | `AGENTS.md:12` | "plus four Bash hooks: rule delivery …, secrets scan …, PR-opened reminder, merged-worktree cleanup" | G2 dữ kiện cũ, tự mâu thuẫn | `plugins/harness/hooks/` có sáu hook Bash, thêm `merge-guard.sh` và `stop-evidence.sh`. Chính `AGENTS.md:39` nhắc tới `merge-guard.sh`, và `CLAUDE.md:79-86` liệt kê sáu hook. | rewrite |
| H3 | `.claude/rules/behavior.md:37` (cả `:17-19`) | "`render_plan.py` lives under `skills/visual-planner/`"; "`agents/reviewer.md` and `skills/correctness-review/…`" | G2 chi tiết dễ đổi, xung đột | `find . -name render_plan.py` ngoài `.claude/` và `.git/` không trả về gì. Bản này thiếu đoạn "workflow stopped early", đoạn "Done needs real command output" và §6. `CLAUDE.md:69` coi `plugins/harness/rules/behavior.md` là nguồn duy nhất, và hook đầu phiên đã nạp bản đó. | remove |
| H4 | `.claude/agents/PROJECT.md:11,13,27` | "`techstacks/` is empty by design"; "`AGENTS.md` → *Coding Style & Naming Conventions* and *Testing Guidelines*"; ánh xạ tới `scripts/install-harness.sh`, `tests/scripts/install-harness.test.sh`, `skills/visual-planner/test_render_plan.py` | G2 chi tiết dễ đổi | Không có thư mục `techstacks/`. `AGENTS.md` không có các mục đó (các mục là Layout, Commands, Style and tests, Commits and pull requests). Ba đường dẫn trong ánh xạ không tồn tại. Nơi đọc file này là `coding` và `test-runner` legacy, còn `test-runner` của plugin đọc `CLAUDE.md` → `## Run and test` (có tại `CLAUDE.md:5`). | remove, cùng M3 |
| H5 | `.claude/skills/README.md:10-14` | "**Codex advisory alpha** … `docs/codex-alpha-install.md`" | G2 xung đột, dữ kiện cũ | Tài liệu này không tồn tại. `CLAUDE.md:3` nói Claude Code là runtime duy nhất được hỗ trợ. | gộp vào F1 |
| H6 | `~/.claude/skills/create-pr/SKILL.md:77` (mọi project) | `python3 .claude/skills/create-pr/scripts/check_pr_body.py …` | G2 chi tiết dễ đổi | Script nằm ở `~/.claude/skills/create-pr/scripts/check_pr_body.py`. Đường dẫn tương đối theo project không tồn tại ở đây. | rewrite |
| H7 | `.claude/rules/*`, `.claude/skills/*` so với `CLAUDE.md` | `PLAN.md`, `SUMMARY.md`, `feature-intake`, lane so với `plan.md`, `summary.md`, `intake`, depth S/M/L | G2 file hướng dẫn mâu thuẫn nhau | Hai bộ từ vựng cho cùng artifact và cùng cổng kiểm soát được nạp cùng lúc. | xem F1 |

### Độ tin cậy trung bình

| # | Vị trí | Bằng chứng | Mẫu | Vì sao lỗi thời | Hành động |
|---|---|---|---|---|---|
| M1 | `CLAUDE.md:65` | "Every skill above exists in `plugins/harness/skills/` now" | G1d cách nói theo kiểu migration, không chính xác | Câu này là diff so với trạng thái trước. `qa-writer` và `security-reviewer` là agent, và `/code-review` không nằm trong thư mục đó. | rewrite |
| M2 | `CLAUDE.md:77` so với `CLAUDE.md:85` | "all hooks fail open except `merge-guard.sh`" và "fails open, except on the risk floor" | G2 xung đột trong cùng một file | Dòng `stop-evidence.sh` nói nó chặn ở ngưỡng rủi ro. `docs/hooks.md:10` lặp lại cách nói "all except `merge-guard.sh`", nên cũng cần sửa. File đó không phải văn bản hướng dẫn nên nằm ngoài diff. | rewrite |
| M3 | `.claude/agents/coding.md`, `test-runner.md`, `task-reviewer.md` | `coding` ghim `claude-opus-5-5` và trỏ tới `agents/PROJECT.md`; `task-reviewer` giống hệt bản plugin | G4 agent chuyên biệt trùng lặp | `harness:implementer` có cùng mô tả ở Sonnet 5.5, và `CLAUDE.md:23` giao coding cho Sonnet 5.5. `test-runner` của plugin đã đổi con trỏ PROJECT.md sang `CLAUDE.md`. Hướng xử lý là giả định: plugin được theo dõi bằng git thắng bản deploy không được theo dõi. | remove |
| M4 | `CLAUDE.local.md:38-52` | "feature-intake … lane … `multi-domain` / high-blast flags"; "Evidence Ledger"; "visual-planner `--review` … `.plan-review.json`"; "context-propagation-audit"; "same-wave overlap" | G2 cũ và xung đột | Các thuật ngữ này chỉ có trong skill legacy của `.claude/` (0 kết quả trong skill, agent và template của plugin). Workflow ở `CLAUDE.md:52-63` dùng `intake`, depth và `/code-review`. | rewrite |
| M5 | `CLAUDE.local.md:24-34` | Bảng chín tool `mcp__code-review-graph__*` với cột "Use when" | G3 danh sách bằng văn xuôi lặp lại danh sách tool thật | MCP server đã liệt kê các tool và mô tả của chúng. Giữ phần hướng dẫn câu hỏi nào cần dùng graph. | rewrite |
| M6 | `~/.claude/skills/autopilot/SKILL.md:28` so với `:23,:29,:32,:26,:64` (mọi project) | Rule 7: "the project's CLAUDE.md / AGENTS.md apply and win over this skill"; rule 8: "not blindly `main` even if CLAUDE.md says…"; rule 10: "this overrides a project default"; Mode B merge PR | G2 xung đột trong cùng một file | Rule nói "project thắng", rồi ba chỗ khác ghi đè lại. | rewrite |
| M7 | `~/.claude/skills/autopilot/SKILL.md:11,23,30,34,39,41,46,53` (mọi project) | "Vietnamese in most past runs"; "past runs hit the 25-watched-artifact cap…"; "`apps/api/.env`"; "(past run: #46 was skipped…)"; "tokscope: `pr-assets`"; "~20 minutes"; "travel-pi's Anthropic milestone" | G2 kể lại lịch sử, chi tiết dễ đổi | Thẩm quyền của một rule nằm ở hành vi nó quy định. Giữ lý do, bỏ ID sự cố và tên project. | rewrite |

### Độ tin cậy thấp hoặc chỉ flag (không có trong diff)

| # | Vị trí | Ghi chú |
|---|---|---|
| F1 | Cây `.claude/` so với plugin | Xung đột ở cấp cả cây. `.claude/` không có lịch sử git nên blame không cho biết bên nào mới hơn. Hướng giả định: plugin được theo dõi và `CLAUDE.md` là bản hiện hành. **Bạn quyết định:** xóa bản deploy cũ hoặc deploy lại. Có file khác phụ thuộc vào nó. `create-pr/SKILL.md:90` và `:167` ở đây chỉ phân giải được qua `asd-ste100` và `finishing-a-development-branch/references/pr-body.md` legacy. `finishing-a-development-branch` của plugin không có `references/`, nên con trỏ đó sẽ hỏng nếu xóa cây này. Hook `branch-isolation-guard.sh` đã chặn việc ghi báo cáo này cũng đến từ bản deploy legacy đó. |
| F2 | `~/.claude/skills/autopilot` so với project | `/autopilot` ("never ask, never use AskUserQuestion", Mode B merge PR) xung đột với `/harness:autopilot` (hỏi trước) và với `merge-guard.sh`, vốn từ chối merge trong subagent. Đây là xung đột giữa các phạm vi nên không đề xuất sửa. |
| F3 | `~/.claude/skills/create-pr/SKILL.md:161` | "Tone: `CLAUDE.local.md` §11". `CLAUDE.local.md` của repo này không có mục đánh số. Viết cho project khác, nên chỉ flag. |
| F4 | `CLAUDE.md:28-31, 36-38` | "It thinks for itself … Effort is not fixed" lặp lại `:20-22`, và rule spawn song song nhắc lại mặc định của tool. Các bản sao khớp nhau nên áp dụng mục 8 của danh sách giữ lại. |
| F5 | `CLAUDE.local.md:56-58` | "even a familiar one" lặp lại chỉ dẫn của chính server Context7. Độ tin cậy thấp là nó gây kích hoạt thừa. |
| F6 | Plugin, chỉ báo cáo | `plugins/harness/agents/test-runner.md:16`: "Legacy fallback (one release)" là điều khoản gắn với thời điểm. `plugins/harness/skills/tickets/SKILL.md:13`: danh sách `## NEVER`, có vẻ là ràng buộc thật. `asd-ste100/SKILL.md` dài khoảng 2.660 từ. |

**Sạch:**
- `~/.claude/CLAUDE.md` (một dòng, khớp với skill `cloudflare:cf-cli`).
- `ink-artifact`, trừ vài ghi chú nguồn gốc ("taken from the user's tokscope dashboard screenshots").

## Diff đề xuất

Chưa áp dụng gì. Lấy từng hunk một.

```diff
--- AGENTS.md
@@ H1 (line 11)
-- `plugins/harness/agents/` - the six subagent role files (model, effort and tools are in their frontmatter).
+- `plugins/harness/agents/` - the subagent role files (model, effort and tools are in their frontmatter).
@@ H2 (line 12)
-- `plugins/harness/hooks/` - `hooks.json` plus four Bash hooks: rule delivery at session start, secrets scan on commit, PR-opened reminder, merged-worktree cleanup.
+- `plugins/harness/hooks/` - `hooks.json` plus the Bash hooks listed in the `CLAUDE.md` Hooks table.

--- CLAUDE.md
@@ M1 (line 65)
-Decisions made on the way are recorded as ADRs in `docs/adr/`. Every skill above exists in `plugins/harness/skills/` now, and runs as `/harness:<name>`.
+Decisions made on the way are recorded as ADRs in `docs/adr/`. The skills above live in `plugins/harness/skills/` and run as `/harness:<name>`; `qa-writer` and `security-reviewer` are agents in `plugins/harness/agents/`.
@@ M2 (line 77)
-all hooks fail open except `merge-guard.sh`, which fails closed.
+all hooks fail open except `merge-guard.sh`, which fails closed, and `stop-evidence.sh` on its risk floor.

--- CLAUDE.local.md
@@ M4 (lines 38-52, replace the "Where it fits" list)
-- **feature-intake** — before assigning the lane, run `get_impact_radius_tool` … `multi-domain` / high-blast flags.
-- **xia2** — … cite the graph query in the research brief's Evidence Ledger as `Local` evidence, then confirm by reading the file.
-- **writing-plans** — … spot a file two tasks would both touch (same-wave overlap).
-- **visual-planner `--review`** — fill the `.plan-review.json` sidecar …
-- **correctness-review / task review** — …
-- **context-propagation-audit** — …
+- **intake** — run `get_impact_radius_tool` on the files the request names; a wide radius is evidence for depth M or L.
+- **xia2** — map local reuse and consumers with `semantic_search_nodes_tool` and `query_graph_tool` (`callers_of`, `tests_for`) before reading files one by one, then confirm by reading the file.
+- **writing-plans** — use `get_impact_radius_tool` per planned file to size the Files list and to spot a file two steps would both touch.
+- **/code-review, task-reviewer** — `detect_changes_tool` and `get_review_context_tool` on the diff; `query_graph_tool` (`callers_of`) for every changed public function before claiming "no caller breaks".
@@ M5 (lines 24-34, replace the tool table)
-| Tool | Use when |
-| `build_or_update_graph_tool` | Refresh … |
- … (nine rows)
+Refresh the graph with `build_or_update_graph_tool` at session start or after a pull or merge. Use `query_graph_tool` for callers, callees, imports and tests, and `get_impact_radius_tool` for blast radius.

--- .claude/rules/behavior.md        # H3: xóa file
--- .claude/agents/coding.md         # M3: xóa (đã có harness:implementer thay)
--- .claude/agents/task-reviewer.md  # M3: xóa (giống hệt harness:task-reviewer)
--- .claude/agents/test-runner.md    # M3: xóa (đã có harness:test-runner thay)
--- .claude/agents/PROJECT.md        # H4: xóa (nơi đọc đã bị xóa; trỏ tới đường dẫn không tồn tại)
```

**Sửa trong `~/.claude/` (ảnh hưởng mọi project):**

```diff
--- ~/.claude/skills/create-pr/SKILL.md
@@ H6 (line 77)
-python3 .claude/skills/create-pr/scripts/check_pr_body.py --title "<title>" <body.md>
+python3 ~/.claude/skills/create-pr/scripts/check_pr_body.py --title "<title>" <body.md>

--- ~/.claude/skills/autopilot/SKILL.md
@@ M6 (rule 7)
-7. Repo conventions: the project's CLAUDE.md / AGENTS.md apply and win over this skill.
+7. Repo conventions: the project's CLAUDE.md / AGENTS.md apply and win over this skill, except where rules 8 and 10 and Mode B state an override.
@@ M7 (rules 9, 11, 12, 17 và các tham chiếu Mode A)
-(Vietnamese in most past runs)
+(match the owner's language)
-(past run: #46 was skipped on a data scan, and the owner had to say "do it yourself")
+(a skipped repro leaves the issue open and says so)
-Never one artifact per assumption: past runs hit the 25-watched-artifact cap and flooded the session with notices.
+Never one artifact per assumption: watched artifacts are capped at 25.
-using keys in `apps/api/.env`
+using the project's documented key file
-(tokscope: `pr-assets`, per `uat.md`)
+(the project's asset branch, per its UAT rule)
-(tokscope: `REVIEW.md` "Pick the reviewers first": …)
+(the project's review rules, if it has them)
-(written for travel-pi's Anthropic milestone, so replace its repo, …)
+(replace its repo, test and lint commands, issue numbers, tasks, base branch and phase titles)
-It can take ~20 minutes, so
+It can be slow, so
```

## Ghi chú kiểm chứng

- Tôi kiểm tra đường dẫn bằng `ls` và `find`. Tôi không chạy lệnh nào có trong các file được kiểm tra.
- Các hunk H1, H2 và M1 khớp với danh sách file ở trên. Việc xóa theo M3 và H3 phụ thuộc vào hướng xử lý của F1, nên áp dụng cùng quyết định đó. Hãy sao lưu `.claude/` trước, vì nó không được git theo dõi nên git không khôi phục được.
- Trước khi áp dụng M4 hoặc các lần xóa, hãy grep toàn hệ thống theo đúng đoạn văn bản. `scripts/lint-doc-truth.sh` kiểm tra các đường dẫn được ghi trong tài liệu, và `AGENTS.md:25` yêu cầu chạy nó.
