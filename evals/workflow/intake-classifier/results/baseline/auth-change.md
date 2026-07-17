Lane: high-risk
Confidence: high
Reason: Auth hard gate fired (JWT refresh-token expiry + login-handler token rotation is core session/auth behavior), which forces high-risk regardless of flag count; existing-behavior change also fires.
Flags: Auth (1), Existing behavior (8)
Escalate: yes
