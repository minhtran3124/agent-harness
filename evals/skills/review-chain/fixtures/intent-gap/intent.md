Reject an empty/whitespace-only `name` on BOTH the create-watchlist (`POST /watchlists`) and
update-watchlist (`PUT /watchlists/{watchlist_id}`) endpoints — return 400 on an empty name.
