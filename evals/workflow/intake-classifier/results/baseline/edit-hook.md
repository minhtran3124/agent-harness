Lane: high-risk
Confidence: high
Reason: Editing hooks/commit-quality-gate.sh trips the high-blast-radius-file hard gate (any hooks/* script), which forces high-risk regardless of flag count; the security/secrets-scan nature also fires the audit/security flag.
Flags: audit/security (flag 4)
Escalate: yes
