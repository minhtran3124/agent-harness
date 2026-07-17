Lane: high-risk
Confidence: high
Reason: The "data loss / migration" hard gate fires (a migration that DROPs the `user_sessions` table is irreversible data loss), which forces high-risk regardless of flag count; direction is unambiguous (one plausible interpretation).
Flags: data-model, auth, existing-behavior, weak-proof
Escalate: yes — data-loss/migration hard gate: a human must confirm the drop or narrow scope, and the "nothing reads it" claim needs verification (only a human narrowing scope may lower the lane).
