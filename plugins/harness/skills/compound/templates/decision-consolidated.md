# Decision track: ADR input

The decision track does not write `docs/solutions/`. Write one JSON file and run
`python3 plugins/harness/scripts/write_adrs.py --input FILE`. The script numbers the ADRs and writes
them to `docs/adr/`. Shape and rules: `docs/adr/README.md`.

```json
{"run": "[slug]", "decisions": [{
  "ticket": "[issue number, or a non-numeric placeholder]",
  "stage": "[stage name]",
  "title": "[short title]",
  "context": "[Context from DECISION_TRACK_N]",
  "options": ["[one string per option from Options_Considered; at least two]"],
  "decision": "[the chosen option]",
  "why": "[the rationale from Decision_and_Rationale]",
  "consequences": "[Consequences; n/a when [none]]",
  "how_to_reverse": "[how to undo it]",
  "confidence": "high | medium | low",
  "needs_review": false,
  "adr": true,
  "decided_by": "claude",
  "date": "[optional, YYYY-MM-DD; default today]"
}]}
```

Add one object per DECISION_TRACK_N block. Applicable_When goes at the end of the context.
