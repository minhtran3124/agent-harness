Add a `WatchlistRepository.list_for_user(user_id)` method that returns all of a user's
watchlists. `Watchlist` rows are soft-deleted by setting `deleted_at`, and repository reads
exclude soft-deleted rows.
