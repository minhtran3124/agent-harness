Lane: high-risk
Confidence: high
Reason: Editing hooks/commit-quality-gate.sh touches a high-blast-radius hooks/* file — a hard gate that forces high-risk regardless of the low flag count.
Flags: 4 (audit/security — secrets scan), 8 (existing behavior)
Escalate: yes — hard gate hit (high-blast hooks/* file); a human must confirm high-risk or narrow scope
