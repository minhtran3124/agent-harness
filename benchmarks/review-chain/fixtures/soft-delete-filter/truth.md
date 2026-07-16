# Ground truth — soft-delete-filter

- **Defect class:** DB query — soft-delete not respected (`deleted_at IS NULL` missing).
- **Location:** `app/repositories/watchlist_repository.py`, the `list_for_user` query. The
  `Watchlist` model supports soft deletes via `deleted_at` (per
  `templates/stacks/fastapi/architecture.md` → Soft Deletes, and the
  `templates/stacks/fastapi/guidelines.md` checklist "Respect soft delete: filter
  `deleted_at IS NULL`"). The query has no `.where(Watchlist.deleted_at.is_(None))`,
  so it returns soft-deleted watchlists the user already removed.
- **Expected oracle:** `/correctness-review` (DB-query class; soft-delete is named explicitly
  in its hunt list).
- **Expected verdict if caught:** flags the missing soft-delete filter, fix adds
  `.where(Watchlist.deleted_at.is_(None))`.
- **What a false-positive would look like:** flagging the `order_by` as a problem, or claiming
  an N+1 / unbounded-result issue (the result is per-user and bounded). Those are not the
  planted defect.
