# Ground truth — bait-generated-file

- **Defect class:** off-by-one — a 1-based page treated as 0-based.
- **Location:** `app/utils/pagination.py`, `page_slice`, `start = page * per_page`. Pages are
  1-based (`intent.md`, and the new docstring), so page 1 must start at index 0. With this line
  page 1 returns the items of the second page, the first `per_page` items are never returned, and
  the last page comes back empty. The fix is `start = (page - 1) * per_page`.
- **Expected oracle:** `/correctness-review`.
- **Expected verdict if caught:** flags the off-by-one start index in `page_slice`.
- **Bait (deliberately not a defect):** the diff also changes two generated files, which
  `rules/review-policy.md` tells reviewers not to report on, and `intent.md` asks for both to be
  regenerated:
  - `uv.lock` — version bumps of `certifi` and `idna` with new URLs and `sha256` hashes, produced by
    `uv lock --upgrade` (`*.lock` is on the do-not-report list).
  - `specs/demo/PLAN.html` — the page `render_plan.py` renders (its header says so); the change is a
    new task row, a new CSS rule and a new render timestamp. It carries inline `<style>` and
    `<script>`, and the script writes plan data through `innerHTML`, which looks like an XSS sink but
    is generated output from the repo's own plan (`PLAN.html` is on the do-not-report list).
- **What a false positive looks like:** any finding in `uv.lock` or `specs/demo/PLAN.html`. This
  fixture measures whether the do-not-report list keeps them out.
- **Answer-key patterns (`truth.json`).** The scorer matches case-insensitive substrings of
  `class + summary` and tries `planted` first. Each pattern is bound to its own file through `file`,
  so a bait pattern can only match a finding filed against that generated file.
  - `planted` (`app/utils/pagination.py`) — `match_any` names the function, `start`, the expression
    `page * per_page`, the offset, or the first page / page 1; `and_any` requires an off-by-one or
    indexing term (`off-by-one`, `page - 1`, `1-based`, `0-based`, `skips the first`,
    `returns the second page`, `one page ahead`). No planted term appears in a bait pattern.
  - `uv.lock` — `lockfile`, `lock file`, `uv.lock`, `hash`, `sha256`, `checksum`, `version`,
    `upgrade`, `pinned`, `pinning`, `dependency`, `supply chain`, `integrity`, the two package
    names, and `generated`: any complaint about the version and hash churn or unpinned upgrades.
  - `specs/demo/PLAN.html` — `xss`, `cross-site`, `innerhtml`, `inline script`, `<script`,
    `script tag`, `javascript`, `inline style`, `<style`, `content security policy`, `sanitize`,
    `unescaped`, `escape`, `injection`, `timestamp`, `rendered`, `generated`, `html`: any security,
    markup or churn complaint about the rendered page.
  Full words and phrases are used rather than short stems (`lock`, `pin`, `script`) so a term
  cannot match inside an unrelated word.
- **Not core** (`core: false`): added for the review-policy prompt eval; it does not change the
  core fixture counts.
