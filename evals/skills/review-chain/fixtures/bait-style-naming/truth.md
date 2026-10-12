# Ground truth — bait-style-naming

- **Defect class:** runtime error — division by zero on a path the request covers.
- **Location:** `app/reports/sales.py`, `average_order_value`. The guard `if not orders: return 0.0`
  checks the whole list, but the mean divides by the number of *completed* orders
  (`data["total"] / data['count']`, where `count` is `len(c)`). A non-empty list whose orders are
  all pending or cancelled passes the guard, leaves `c` empty, and raises `ZeroDivisionError`.
  `intent.md` says that case returns `0.0`, so the bug is knowable from the request and the diff.
- **Expected oracle:** `/correctness-review`.
- **Expected verdict if caught:** flags the `ZeroDivisionError` when no order is completed; the fix
  is to guard on the completed list (`if not c: return 0.0`).
- **Bait (deliberately not a defect):** the diff also carries only style, naming, formatting and
  maintainability issues, which `rules/review-policy.md` tells correctness review and intent review
  not to report: single-letter and vague names (`c`, `t`, `x`, `data`), an over-long line (the `c =`
  line with its trailing comment), inconsistent quoting (`'count'` beside `"total"`), a missing
  docstring (`total_revenue` has one, the new function does not), a `TODO` comment, and an
  intermediate dict that makes the code harder to read. None of them changes behavior. There is no
  second runtime defect.
- **Policy source:** `rules/review-policy.md` is added by PR #288 (branch `feat/review-policy`); it
  does not exist on this branch until that PR merges, and these fixtures measure the do-not-report
  list as written there. The bait in this fixture relies on these two lines of its "Do not report"
  section:
  - "Lint and format findings that a linter or formatter wired into the project's CI or hooks
    already checks."
  - "In correctness review and intent review only: style, naming, formatting and maintainability.
    These belong to the task reviewer's quality verdict."
- **What a false positive looks like:** any correctness finding that reports one of the bait items
  above. This fixture measures whether the do-not-report list keeps them out.
- **Answer-key patterns (`truth.json`).** Every pattern is bound to `app/reports/sales.py`. The
  scorer matches case-insensitive substrings of `class + summary` and tries `planted` first.
  - `planted` — `match_any` names the function, the completed orders, the count or `len(c)`, or
    zero; `and_any` requires a division-by-zero term or a phrase naming the trigger (no completed
    orders, all pending, all cancelled, every order is cancelled, `len(c) is 0`), so a finding that
    names the cancelled or pending case without saying `ZeroDivisionError` still scores. Hyphenated
    and reworded variants are listed too (`division-by-zero`, `zero-division`, `divide-by-zero`,
    `no order has status completed`, `no order is completed`, `no orders are completed`,
    `every order is pending`, `all orders are pending`, `all orders cancelled`, `count is zero`,
    `is zero`) after a correctness review showed three correct findings scoring as `other`. No planted term appears in any bait pattern, so a planted finding cannot
    be scored as bait and a bait finding needs one of the division or trigger phrases to be scored
    as planted.
  - naming — `single-letter`, `variable name`, `naming`, `non-descriptive`, `vague name`,
    `descriptive name`, `unclear name`, `rename`: a finding about the names.
  - docstring — `docstring`: the missing docstring.
  - line length — `line length`, `long line`, `line too long`, `over-long`, `e501`,
    `characters long`: the over-long `c =` line.
  - quoting — `quoting`, `quote style`, `inconsistent quotes`, `mixed quotes`, `single quotes`,
    `double quotes`: the mixed quote characters.
  - formatting — `formatting`, `formatter`, `pep 8`, `code style`, `style`: a general style or
    format complaint.
  - todo — `todo`: the `TODO` comment.
  - maintainability — `maintainability`, `readability`, `intermediate dict`, `dictionary`,
    `simplify`, `refactor`: the needless dict and other clean-up suggestions.
- **Not core** (`core: false`): added for the review-policy prompt eval; it does not change the
  core fixture counts.
