# Ground truth — none-deref

- **Defect class:** None / null dereference (correctness).
- **Location:** `app/routers/user_email.py`, the `return UserEmailResponse(email=user.email)`
  line — `user` is the result of `await repo.get_by_id(user_id)`, which is `Optional[User]`
  (None when the id is absent or soft-deleted). `user.email` raises `AttributeError` →
  unhandled 500 on a common path (any unknown/deleted id).
- **Expected oracle:** `/correctness-review` (None-class bug; explicitly in its hunt list).
- **Expected verdict if caught:** flags the unguarded Optional, suggests a guard clause →
  `AppException.NotFound` when `user is None`.
- **What a false-positive would look like:** flagging the auth/authz wiring as missing/incorrect
  (it is correct — see the authz note below), or claiming the response schema is wrong. Those are
  not the planted defect.
- **Authz-clean (fixture revision, 2026-07-15):** the route is an **intentional cross-user
  lookup** — `intent.md` asks for "the given user's email" by id — and is gated by
  `Depends(require_admin)` in addition to `Depends(get_current_user)`, so an authenticated
  **admin** may read any user's email **by design**. An IDOR/BOLA finding here is therefore a
  **false positive**. This is the deliberate contrast with `intent-gap`: a `Watchlist` is an
  owner-owned resource, so its by-id mutation *must* be owner-scoped (v2 correctly added
  `user_id=current_user.id`); a `require_admin`-gated directory lookup *must not* be — the two
  authz postures are both explicit, resolving the answer-key contradiction in issue #58. Before
  this revision the route carried only `Depends(get_current_user)`, leaving a live, unexplained
  authz ambiguity that two independent engines flagged; the fixture now carries the None-deref as
  its **sole** live defect.
