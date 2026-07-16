# Ground truth — missing-await

- **Defect class:** async correctness — missing `await` on an async call.
- **Location:** `app/services/subscription_service.py`, `count = self.repo.count_active(user_id)`.
  `count_active` is `async def`, so `count` is a coroutine object, not an `int`. The
  `count < 0` comparison raises `TypeError` at runtime (coroutine vs int), and the coroutine
  is never awaited (RuntimeWarning, DB work never runs). Passes static/type checks if return
  types are loose.
- **Expected oracle:** `/correctness-review` (async-class bug; explicitly in its hunt list).
- **Expected verdict if caught:** flags the missing `await`, fix is `count = await self.repo.count_active(user_id)`.
- **What a false-positive would look like:** flagging the `if count < 0: return 0` guard as
  dead/unnecessary (it is defensive but not the planted bug), or claiming the method should
  not be `async`. Those are not the planted defect.
