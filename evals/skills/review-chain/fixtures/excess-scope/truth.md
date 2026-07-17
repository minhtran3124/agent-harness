# Ground truth — excess-scope

- **Defect class:** excess scope — the diff does what was asked PLUS an unrequested change.
- **Location:** `app/routers/profile.py`, the existing `get_profile` handler. The request was
  ONLY "add `GET /profile/settings`". The diff also rewrites `get_profile` to route through a
  new `ProfileService.get_profile_with_stats` instead of `ProfileRepository.get_by_user` — an
  unrequested refactor that changes the existing endpoint's data path (and adds "stats" not
  asked for).
- **Expected oracle:** `/intent-review` (classifies as `excess` — present in the diff, absent
  from the request).
- **Expected verdict if caught:** flags the `get_profile` refactor as out-of-scope; the new
  `/settings` endpoint itself is correct and in-scope.
- **What a false-positive would look like:** flagging the new `get_settings` endpoint as the
  excess (it is exactly the request), or reporting a correctness bug (there is no planted
  runtime bug here — this fixture is for the intent oracle).
- **Correctness-clean (fixture v2, 2026-06-14):** both handlers now guard their `Optional`
  repo/service result with `if ... is None: raise AppException.NotFound(...)` before
  `model_validate`, so the off-oracle `/correctness-review` pass should report **CLEAN** — this
  fixture is now a true false-positive probe for the correctness oracle. A correctness reviewer
  MAY note the `get_profile_with_stats` swap as an `unknown` contract observation (the service
  is not visible), but that is not a hard finding. Any asserted runtime bug here is a
  false-positive. (v1 carried an unintended `model_validate(None)` None-deref; the 06-12 baseline
  and 06-14 reviewer-agent runs measured v1.)
