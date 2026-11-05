# Repo facts for the login work (treat as true; there is no real repo)

- Web app on Node; Postgres 16 is the main database.
- Redis runs for the page cache with maxmemory-policy allkeys-lru.
- The new login must let a user see and revoke their own active sessions.
- Peak traffic is about 300 requests per second.
- Ticket slug: login-sessions. Depth: L.
