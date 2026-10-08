Reject an empty/whitespace-only `name` on BOTH the create-watchlist (`POST /watchlists`) and
update-watchlist (`PUT /watchlists/{watchlist_id}`) endpoints — return 400 on an empty name.
Only the owner of a watchlist may update it; updating a watchlist that does not exist or belongs to another user returns 404.
