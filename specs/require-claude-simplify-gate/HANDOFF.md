# Handoff cho Claude Code — Require bundled `/simplify`

Ngày: 2026-07-30  
Repository: `/Users/minhtran/Documents/minhtran3124/developer/harness-skills`  
Branch hiện tại: `feat/require-claude-simplify-gate`  
HEAD hiện tại: `5a34cae feat(eval): re-anchor DRY guidance on duplication, not chain length`

## CẬP NHẬT VÒNG 3 — ACCEPT; Wave 2 hoàn tất, chờ xác nhận trước khi vào Wave 3

Vòng 3 (commit `5a34cae`) sửa lại tiêu chí reuse/DRY: thay vì hỏi "code được tái sử dụng có phức
tạp không", hỏi đúng câu "cùng một phép tính có xuất hiện ở ≥2 nơi không" (là duplication thật, đáng
gộp bất kể ngắn hay dài) so với "một hàm chỉ tình cờ dùng chung 1 lời gọi builtin như một phần của
phép tính khác lớn hơn" (không phải duplication). Một lượt review đã bắt lỗi bản nháp đầu dùng chữ
"verbatim" (dễ khiến model đòi khớp y hệt từng chữ, có thể trượt lại `cross-task-duplication` vì nó
chỉ khác ở một biến tạm) — đã sửa thành "cùng một phép tính... kể cả khi viết khác đôi chút".

Chạy lại baseline + candidate tại HEAD `5a34cae`:

```
python3 scripts/score_simplify_stage_eval.py --compare baseline.json candidate.json \
  --fixtures evals/skills/simplify-stage/fixtures --quality-gate
```
```json
{"quality_pass": true, "value_evaluated": true, "value_pass": true,
 "baseline_value_score": 0, "value_score": 4, "minimum_value_score": 3, "errors": []}
```

**Cả 8/8 fixture đúng kỳ vọng** — `already-simple` đúng `no_op`, `cross-task-duplication` và
`reuse-existing-helper` đúng `changed` (DRY thật được áp dụng, không còn file rác), 2 fixture
`abstraction-altitude`/`efficiency-materialization` vẫn đúng như trước. **Quality gate PASS, value
gate PASS** (`SC-8`, `SC-9` đều thoả). Chi tiết đầy đủ:
`evals/skills/simplify-stage/results/comparison.md` (mục "Round 3").

`evals/skills/simplify-stage/results/baseline.json` và `.../candidate.json` hiện tại **chính là**
bằng chứng ACCEPT cuối cùng (không cần đổi tên — đây là bộ chính thức theo đúng tên file Task 2.1
yêu cầu). Evidence 2 vòng trước vẫn giữ nguyên, đổi tên, không xóa (`*-rejected-*`,
`*-superseded-*`).

**Trạng thái: Wave 2 hoàn tất với ACCEPT.** Theo "Sau Wave 2" trong PLAN.md, Wave 3–6 (hard-gate
thật: `simplify_record.py`, wiring SDD, finishing-gate, docs/manifest, ship) **được phép** tiếp tục
— nhưng Wave 4 đụng vào file high-blast-radius (`skills/subagent-driven-development/SKILL.md`,
`hooks/risk-corroboration.sh`) mà `rules/auto-correct-scope.md` Rule 4 liệt kê là STOP+hỏi người
dùng. Phiên này đã dừng lại để báo kết quả ACCEPT và xin xác nhận tiếp tục vào Wave 3, chưa tự ý
triển khai tiếp.

**Việc cần làm khi phiên sau tiếp tục:**

1. Nếu người dùng đã xác nhận tiếp tục: bắt đầu Wave 3 (Task 3.1 — `simplify_record.py` +
   extend `check_review_receipt.py`) đúng theo PLAN.md, giữ nguyên contract prompt đã pin ở commit
   `5a34cae` (đừng sửa lại prompt trong `_collect_case()` nữa trừ khi có lý do thật — nó đã pass
   eval, thay đổi cần re-validate lại toàn bộ corpus).
2. Nếu chưa xác nhận: hỏi lại, không tự ý chọn.

---

## CẬP NHẬT VÒNG 2 (lịch sử) — vẫn REJECT, nguyên nhân khác

Sau khi trình bày kết quả REJECT vòng 1 (bên dưới) cho người dùng, họ chọn "xem lại corpus/prompt
rồi chạy lại" thay vì đóng tính năng. Đã sửa prompt gọi `/simplify` (`58156cb`, 2 lượt review độc
lập trước khi tốn token thật) để phân biệt "reuse target chứa một rule/logic thật" (đáng gộp) với
"reuse target chỉ là một lời gọi builtin một dòng" (không đáng thêm coupling) — không sửa
`truth.json`/fixture (sửa truth để pass sẽ là gaming eval).

Kết quả chạy lại tại HEAD `58156cb`: **`already-simple` đã đúng (no_op)** — safety miss vòng 1 đã
hết. Nhưng quality gate **vẫn FAIL** vì hai vấn đề mới:

1. `cross-task-duplication` để sót một file rỗng `target.diff` ngoài `allowed_changed_paths` —
   không liên quan gì đến việc sửa prompt reuse/DRY, có thể do model tạo file scratch rồi quên xóa.
2. **Overcorrection thật sự**: đúng đoạn prompt vừa sửa `already-simple` cũng khiến model bỏ qua
   DRY consolidation *đúng ra cần làm* trên `reuse-existing-helper` và `cross-task-duplication` (cả
   hai đều có `value_opportunity: true`) — model coi mọi chuỗi gọi stdlib ngắn (`.strip().lower()`,
   `.strip().title()`) là "trivial", bất kể nó có bị lặp lại ở nhiều nơi hay không.

Đã dừng lại thay vì tự thử phiên bản prompt thứ 3 (mỗi vòng tốn token/thời gian thật, và lần sửa
này đánh đổi 1 lỗi lấy 2 lỗi mới). Chi tiết đầy đủ:
`evals/skills/simplify-stage/results/comparison.md` (mục "Round 2").

Evidence vòng 2 đã giữ nguyên, đổi tên (không xóa):
- `candidate-rejected-stray-file-and-overcorrected-reuse.json` +
  `artifacts/`/`transcripts/candidate-rejected-stray-file-and-overcorrected-reuse/`
- `baseline-superseded-precommit-58156cb.json` (baseline cũ trước prompt fix, đã stale vì digest
  bind cả nội dung script)

**Việc cần làm khi phiên sau tiếp tục:** hỏi người dùng có muốn thử phiên bản prompt thứ 3 (phân
biệt rõ hơn: "lặp lại ở ≥2 nơi = rule thật" bất kể độ dài chuỗi gọi), hay chuyển hướng khác (đóng
tính năng, chấp nhận residual risk với mitigation, v.v.). Không tự ý chọn.

---

## CẬP NHẬT VÒNG 1 (lịch sử) — Wave 2 hoàn tất với quyết định REJECT lần đầu

Kể từ handoff gốc (commit `757420a`), phiên này đã sửa 4 bug hạ tầng liên tiếp (mỗi bug: fix +
unit test + review độc lập PASS + commit riêng), rồi thu được một kết quả candidate thật hợp lệ:

1. `0eb1287` — bug relative-path trong `collect()` (`--fixtures`/`--output`/`--claude` không được
   resolve tuyệt đối trước khi truyền cho subprocess có `cwd` khác).
2. `8c51780` — Bash tool lỗi `EPERM mkdir ~/.claude/session-env/<uuid>`; sửa bằng
   `CLAUDE_CONFIG_DIR=<runtime>/claude-config` trong sandbox env (verify thực nghiệm).
3. `f5ecf89` — Bash tool còn lỗi `EPERM` trên `/tmp/claude-<uid>/<dashed-cwd>/` (path hardcode,
   không theo `$TMPDIR`, không có override tài liệu hoá). Đây là **Rule-4 STOP thật sự đã xảy ra**:
   ghi `specs/require-claude-simplify-gate/ESCALATIONS.md` mục **E001** với 3 phương án, người
   dùng chọn **B** (allow cả `/tmp/claude-<uid>/`) qua `AskUserQuestion`. Quyết định đã ghi vào
   ESCALATIONS.md (`decision: B`, `decided_by: Minh Tran`, `decided_at: 2026-07-30`).
4. `50e3470` — sau khi Bash hoạt động, `git` bên trong sandbox vẫn lỗi (`/dev/null` write bị deny,
   và `git-common-dir` — object store thật của `seed/.git`, khác với `git-dir` per-worktree đã
   allow-list từ trước — chưa từng được allow-list). Đây **không** phải escalation mới: chỉ ảnh
   hưởng git repo tổng hợp dùng-một-lần của chính eval (`seed`/`worktree`, không liên quan
   `source_root` thật) và các device file an toàn tiêu chuẩn POSIX — không chạm gì dùng chung giữa
   các session như case E001. Tự sửa theo Rule 3, có test + review độc lập PASS.

Sau 4 fix trên, baseline cũ (`0eb1287`) bị stale so với candidate mới (`evaluation_input_digest()`
chủ đích bind nội dung `run_simplify_stage_eval.py`/`score_simplify_stage_eval.py`) — đã re-collect
baseline tại HEAD hiện tại (`50e3470`), giữ nguyên bản cũ (đổi tên
`baseline-superseded-precommit-0eb1287.*`, không xóa).

**Kết quả cuối cùng — quality gate FAIL, rollout REJECT:**

7/8 fixture đúng kỳ vọng (`truth.json`); fixture `already-simple` (kỳ vọng `no_op`, không đổi gì)
bị `/simplify` thật sửa `mean()` để gọi `total()` — một refactor DRY hợp lý nhưng nằm ngoài phạm
vi fixture chủ đích test (fixture này kiểm tra việc *không* refactor code biên giới khi không rõ
ràng cần thiết). Đây là safety miss thật, không phải bug hạ tầng. Value gate không chạy (quality
luôn chạy trước, theo Global Constraints của PLAN.md).

Chi tiết đầy đủ: `evals/skills/simplify-stage/results/comparison.md`.

**Trạng thái: dừng theo đúng thiết kế PLAN.md** — "Chỉ tiếp tục các wave hard-gate khi cả quality
và value đều pass" (mục "Sau Wave 2"). Waves 3–6 (`simplify_record.py`, wiring SDD, finishing-gate,
docs/manifest, ship) **không được tiếp tục** trên bằng chứng hiện tại. Đây không phải lỗi cần sửa —
đây là câu trả lời hợp lệ của Task 2.1 ("explicitly accept or reject required rollout"). Quyết định
tiếp theo (revisit corpus/prompt, chấp nhận residual risk có mitigation, hay dừng hẳn tính năng) là
quyết định của người dùng, chưa được đưa ra trong phiên này.

**Việc cần làm khi phiên sau tiếp tục:**

1. Đọc `evals/skills/simplify-stage/results/comparison.md` để hiểu đầy đủ finding.
2. Hỏi người dùng: chấp nhận REJECT và dừng hẳn tính năng (đóng plan ở trạng thái không ship), hay
   muốn thử một hướng khác (sửa corpus/prompt rồi re-run Wave 2, hoặc chấp nhận residual risk với
   mitigation nào đó)? Đây là quyết định sản phẩm, không tự ý chọn.
3. Không tự sửa `already-simple/truth.json` để "cho pass" — đó là gaming eval, vi phạm chủ đích
   toàn bộ Task 2.1.
4. Không xóa bất kỳ evidence bị reject/superseded nào (`*-rejected-*`, `*-superseded-*`) — giữ
   nguyên làm audit trail.

---

## Handoff gốc (giữ nguyên để tham chiếu lịch sử)

## Mục tiêu

Tiếp tục implement đến hết kế hoạch:

`specs/require-claude-simplify-gate/PLAN.md`

Thiết kế yêu cầu Claude Code bundled `/simplify` chạy đúng một lần theo signal, sau mọi task
review và trước branch package/final oracles/receipt. Không tạo local skill tên `simplify`.

Branch này stack trên `feat/superpowers-6-review-pipeline` tại `29a5419`; không rebase/reset
hoặc merge nhánh contributor. Kết thúc bằng push + draft PR để human review, tuyệt đối không merge.

## Trạng thái đã hoàn thành

Wave 1 đã implement, test, review độc lập và commit:

- `rules/simplify-stage.md`
- `scripts/check_claude_simplify.py`
- shadow-eval corpus/runner/scorer dưới `evals/skills/simplify-stage/` và `scripts/`
- Commit: `757420a`

Kết quả cuối trước commit:

- capability/policy: `103 passed`, self-test PASS
- focused Wave 1: policy `103 passed`; eval runner/scorer `23 passed`
- Ruff và `py_compile`: PASS
- hai review độc lập: PASS, không còn Important/Critical

Các contract quan trọng đã có:

- Claude Code tối thiểu `2.1.154`; eval pin `2.1.220`
- BASE/HEAD phải là SHA lowercase 40-hex, explicit và khác nhau
- classifier fail-closed, unknown path là reviewable
- candidate chạy trong disposable Git worktree và macOS Seatbelt
- filesystem content read chỉ allowlist worktree/gitdir/runtime/client/system runtime
- source, fixture truth, output, home, `.claude`, Keychain và sentinel ngoài scope không đọc được
- OAuth token được resolve ngoài sandbox bằng stream `security -> plutil`; raw aggregate Keychain
  JSON không vào parent process; token không được log/store
- trong sandbox, Claude `--safe-mode auth status` pass bằng token env; direct Keychain lookup
  trả exit 44, không có credential output
- exactly one `Skill(simplify)` tool-use phải có đúng một matching non-error `tool_result`
- HEAD/ref/git pointer không được thay đổi
- patch staged/cached bao phủ untracked/deleted/rename/binary
- artifacts immutable + SHA-256; checks artifact và history bundle được scorer cross-check
- collection SHA phải resolve và bằng HEAD tại thời điểm collect
- input digest bind runner/scorer/schema/scoring/public fixtures
- scorer cho phép collection SHA là ancestor của HEAD sau này, nhưng input digest phải còn current
- quality gate luôn chạy trước value gate

## Checkpoint hiện tại: Wave 2 bị dừng bởi RED bug

Lần advisory baseline đầu tiên không gọi model/token nhưng phát hiện output-relative-path bug:

```text
unable to create history bundle .../worktree/evals/skills/simplify-stage/results/...
```

Nguyên nhân: `git bundle create` chạy với `cwd=worktree` nhưng nhận bundle path tương đối.

Partial evidence đầu tiên đã được giữ nguyên và rename, không xóa:

- `evals/skills/simplify-stage/results/artifacts/baseline-rejected-relative-output/`
- `evals/skills/simplify-stage/results/transcripts/baseline-rejected-relative-output/`

Một RED regression đã được thêm nhưng chưa commit:

- `scripts/test_run_simplify_stage_eval.py::test_relative_output_and_fixtures_resolve_from_caller_cwd`

Hiện test này fail đúng lỗi trên:

```bash
python3 -m pytest \
  scripts/test_run_simplify_stage_eval.py::test_relative_output_and_fixtures_resolve_from_caller_cwd \
  -q
```

## Việc cần làm ngay

1. Sửa relative-path bug bằng cách resolve `fixtures`, `output` và executable path theo caller
   CWD tại boundary của `main`/`collect`. Mọi path truyền cho subprocess có `cwd` khác phải absolute.
   Artifact descriptor trong JSON vẫn phải relative với `output.parent`.
2. Chạy RED test trên đến GREEN.
3. Chạy:

   ```bash
   python3 -m pytest \
     scripts/test_run_simplify_stage_eval.py \
     scripts/test_score_simplify_stage_eval.py -q
   ruff check \
     scripts/run_simplify_stage_eval.py \
     scripts/score_simplify_stage_eval.py \
     scripts/test_run_simplify_stage_eval.py \
     scripts/test_score_simplify_stage_eval.py
   python3 -m py_compile \
     scripts/run_simplify_stage_eval.py \
     scripts/score_simplify_stage_eval.py
   ```

4. Review độc lập fix này; sau PASS commit focused, ví dụ:

   ```bash
   git add scripts/run_simplify_stage_eval.py scripts/test_run_simplify_stage_eval.py
   git commit -m "fix(eval): resolve simplify artifact paths"
   ```

5. Chạy lại advisory baseline:

   ```bash
   python3 scripts/run_simplify_stage_eval.py \
     --mode advisory \
     --fixtures evals/skills/simplify-stage/fixtures \
     --output evals/skills/simplify-stage/results/baseline.json \
     --expected-client-version 2.1.220
   ```

6. Chỉ khi baseline pass mới chạy candidate thật (sẽ dùng Claude token):

   ```bash
   python3 scripts/run_simplify_stage_eval.py \
     --mode candidate \
     --fixtures evals/skills/simplify-stage/fixtures \
     --output evals/skills/simplify-stage/results/candidate.json \
     --expected-client-version 2.1.220
   ```

7. Chạy quality trước:

   ```bash
   python3 scripts/score_simplify_stage_eval.py \
     --compare \
       evals/skills/simplify-stage/results/baseline.json \
       evals/skills/simplify-stage/results/candidate.json \
     --fixtures evals/skills/simplify-stage/fixtures \
     --quality-gate
   ```

8. Chỉ nếu quality pass mới chạy value:

   ```bash
   python3 scripts/score_simplify_stage_eval.py \
     --compare \
       evals/skills/simplify-stage/results/baseline.json \
       evals/skills/simplify-stage/results/candidate.json \
     --fixtures evals/skills/simplify-stage/fixtures \
     --value-gate
   ```

9. Viết `evals/skills/simplify-stage/results/comparison.md`, ghi cả rejected advisory run,
   version, source SHA, quality/value verdict, runtime/token usage và rollout decision.
10. Nếu candidate lỗi/fail gate: giữ nguyên first-run evidence, không overwrite/delete. Dùng output
    tên mới cho lần sau và dừng hard-gate rollout cho đến khi có bằng chứng pass.

## Sau Wave 2

Chỉ tiếp tục các wave hard-gate khi cả quality và value đều pass:

- Wave 3: `simplify_record.py` + extend `check_review_receipt.py`
- Wave 4: wire SDD ordering + finishing gate
- Wave 5: hook guidance, docs, manifest, `run-tests.sh`, adoption checker
- Wave 6: focused checks, full `bash scripts/run-tests.sh`, deploy, final correctness/intent/context
  reviews, receipt, push và draft PR

Chi tiết file, criteria và lệnh verify nằm trong `PLAN.md`. Không bỏ qua shadow-eval gate.

## Dirty worktree cần bảo toàn

Không sửa/stage/commit các thay đổi user-owned sau:

- `M specs/STATE.md`
- `?? .harness-state/`
- `?? docs/research/2026-07-29-superpowers-6-review-pipeline-comparison.md`
- `?? docs/research/2026-07-29-superpowers-6-review-pipeline-comparison.vi.md`

Các artifact của task hiện tại:

- `?? specs/require-claude-simplify-gate/` — research/design/summary/plan/handoff
- `?? evals/skills/simplify-stage/results/` — rejected partial evidence cần giữ
- `M scripts/test_run_simplify_stage_eval.py` — RED test relative-path chưa commit

Luôn stage bằng tên file cụ thể. Không dùng reset/checkout/stash làm mất dirty state.

## Baseline toàn repository

Trước khi sửa hooks/scripts lớn, full suite đã pass:

```bash
GOCACHE=/tmp/harness-skills-go-cache bash scripts/run-tests.sh
```

Kết quả: `278 passed`, toàn bộ shell contracts green.

Môi trường pytest ban đầu thiếu `pytest-cov`; đã cài vào shared environment. `.coverage` do lần chạy
test tạo ra đã được xóa, không phải artifact cần giữ.
