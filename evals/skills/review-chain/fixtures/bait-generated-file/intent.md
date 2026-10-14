Add a `page_slice(items, page, per_page)` function to `app/utils/pagination.py`, next to
`page_count`. Pages are 1-based, like `page_count`: page 1 returns the first `per_page` items,
page 2 the next `per_page`, and so on. A page below 1 or past the end returns an empty list, and a
non-positive `per_page` raises `ValueError` the same way `page_count` does.

Then refresh the lockfile with `uv lock --upgrade` and re-render the plan page
`specs/demo/PLAN.html` with `render_plan.py`, and include both regenerated files in the change.
