Lane: high-risk
Confidence: high
Reason: Dropping the `user_sessions` table is a destructive schema migration, which trips the data-loss/migration hard gate (also the data-model flag, and the table is session-related) — a hard gate forces high-risk and cannot be self-downgraded.
Flags: Data model (3), Auth-adjacent/sessions (1)
Escalate: yes — hard gate hit (data loss + migration); a human must confirm the drop / that nothing reads the table before the destructive migration runs.
