# Ground truth — intent-gap

- **Defect class:** intent gap — the diff covers part of the request but not all of it.
- **Location:** `app/routers/watchlists.py`, the `update_watchlist` handler. The request asked
  for empty-name rejection on BOTH endpoints. The diff adds the
  `if not payload.name.strip(): raise AppException.BadRequest(...)` guard to `create_watchlist`
  only; `update_watchlist` still accepts an empty name.
- **Expected oracle:** `/intent-review` (classifies as `gap` — requested but absent from the
  diff).
- **Expected verdict if caught:** flags the missing validation on `update_watchlist`; the
  create-side validation is correct and in-scope.
- **What a false-positive would look like:** flagging the create-side guard as wrong/excess,
  or reporting a correctness bug in the create path (the guard is correct). Those are not the
  planted defect.
- **Correctness-clean (fixture v2, 2026-06-14):** `update_watchlist` now scopes the mutation by
  owner (`repo.update(watchlist_id, user_id=current_user.id, ...)`) and guards the `Optional`
  result (`if updated is None: raise AppException.NotFound(...)`), removing the v1 BOLA/IDOR and
  None-deref. The empty-name validation is **still intentionally absent** on the update path —
  that is the planted intent gap and MUST remain. So the off-oracle `/correctness-review` pass
  should now report **CLEAN**; any asserted runtime bug is a false-positive. (v1 carried an
  unintended P0 ownership gap + `model_validate(None)` None-deref; the 06-12 baseline and 06-14
  reviewer-agent runs measured v1.)
