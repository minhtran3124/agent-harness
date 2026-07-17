Lane: tiny
Confidence: high
Reason: Adds a guard-clause input validation plus its unit test to one existing service method — only the existing-behavior flag is arguably touched, and no hard gate fires (validation is being added/tightened, not weakened or removed, and a service method is not a public API contract).
Flags: existing-behavior (8)
Escalate: no
