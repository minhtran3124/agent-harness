Add a database migration that drops the deprecated `user_sessions` table — we moved session
storage to Redis last quarter and nothing reads it anymore.
