# Diagnosis template

Copy the block below to `specs/<slug>/diagnosis.md`. Keep the six fields in this order.
Replace each secret with `<REDACTED>`.

```markdown
# <slug> — Diagnosis

Loop: <the command> — red output:
<the redacted output that shows the bug>
<!-- One command that goes red on this bug. Paste the output of one real run. -->

Repro: <the minimised input>
<!-- Each element that remains is necessary. Name the elements that you deleted. -->

Hypotheses:
- H1: <cause> — prediction: <what a probe shows when H1 is true>
- H2: <cause> — prediction: <what a probe shows when H2 is true>
- H3: <cause> — prediction: <what a probe shows when H3 is true>
<!-- Three to five entries, H1 to H5, ranked from most likely to least likely. -->

Probes:
- DEBUG-xxxx <probe> — tests: H<n> — result: <observed value> — <supports | refutes>
<!-- One probe for each prediction. Write the tag without brackets so the cleanup search does not match this file. -->

Confirmed: H<n>
<!-- One hypothesis ID from the list above, with the probe that supports it. -->

Seam: <where the red test goes> — catches: <the symptom>; misses: <what this seam cannot see>
<!-- Use the seam form of rules/plan-format.md. The seam point is the text before " — catches:". With no valid seam, write: Seam: none — <reason> -->
```
