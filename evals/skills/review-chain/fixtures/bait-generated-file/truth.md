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
- **Policy source:** `rules/review-policy.md` is added by PR #288 (branch `feat/review-policy`); it
  does not exist on this branch until that PR merges, and these fixtures measure the do-not-report
  list as written there. The bait in this fixture relies on this line of its "Do not report"
  section:
  - "Findings in generated files: `PLAN.html`, `.plan-review.json`, deployed harness copies, and
    `*.lock` files."
- **What a false positive looks like:** any finding in `uv.lock` or `specs/demo/PLAN.html`. This
  fixture measures whether the do-not-report list keeps them out.
- **Answer-key patterns (`truth.json`).** The scorer matches case-insensitive substrings of
  `class + summary` and tries `planted` first. Each pattern is bound to its own file through `file`,
  so a bait pattern can only match a finding filed against that generated file.
  - `planted` (`app/utils/pagination.py`) — `match_any` names the function, the expression
    `page * per_page`, the start index or offset, or the first page / page 1 (no bare `start`, which
    would match inside `restart`); `and_any` requires a phrase that names the bug (`off-by-one`,
    `page - 1`, `treated as 0-based`, `treats page as zero-based`, `skips the first`,
    `returns the second page`, `one page ahead`). Bare `1-based` / `0-based` are deliberately absent:
    the docstring itself says 1-based, so a harmless comment about the docstring must not score as
    the planted bug. Hyphen and phrasing variants that name the bug itself are listed too
    (`off by 1`, `off-by-1`, `treats page as 0-indexed`, `treated as zero-indexed`,
    `0-indexed page number`, `wrong offset for page 1`, `wrong items for page 1`,
    `returns the wrong items`, `starts at per_page`, `one page late`, `one page off`,
    `first page skipped`, `first page is skipped`, `skips page 1`, `page 1 is skipped`,
    `never returns the first`), so a correct finding is not scored as `other` because of its wording.
    Bare index-base terms (`0-indexed`, `zero-indexed`, `1-based but`, `1-based, so`, …) and bare
    `wrong offset` / `wrong page` are deliberately absent: they matched docstring and rename comments
    such as "pages are 1-based, so clarify" and "start = page * per_page reads as 0-indexed". No
    planted term appears in a bait pattern, and no bait term appears in a planted one.
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
