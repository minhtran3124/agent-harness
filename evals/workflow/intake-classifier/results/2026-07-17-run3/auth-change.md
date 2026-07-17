Lane: high-risk
Confidence: high
Reason: Auth hard gate fired — the change alters JWT refresh-token expiry and refresh-token rotation in the login handler, which forces high-risk regardless of flag count.
Flags: Auth, Existing behavior
Escalate: yes
