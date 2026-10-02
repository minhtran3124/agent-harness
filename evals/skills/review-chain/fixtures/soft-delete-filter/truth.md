# Ground truth — soft-delete-filter

- **Defect class:** DB query — soft-delete not respected (`deleted_at IS NULL` missing).
- **Location:** `app/repositories/watchlist_repository.py`, the `list_for_user` query. The
  `Watchlist` model supports soft deletes via `deleted_at`, and `intent.md` states the
  convention: rows are soft-deleted by setting `deleted_at`, and repository reads exclude
  them. The query has no `.where(Watchlist.deleted_at.is_(None))`, so it returns
  soft-deleted watchlists the user already removed.
- **Expected oracle:** `/correctness-review` (DB-query class; soft-delete is named explicitly
  in its hunt list).
  Since fixture v4 (2026-10-02) `intent.md` states the soft-delete convention, so
  `/intent-review` can also catch it as a gap; that counts as caught, with the oracle not
  matching the expected one.
- **Expected verdict if caught:** flags the missing soft-delete filter, fix adds
  `.where(Watchlist.deleted_at.is_(None))`.
- **What a false-positive would look like:** flagging the `order_by` as a problem, or claiming
  an N+1 / unbounded-result issue (the result is per-user and bounded). Those are not the
  planted defect.
