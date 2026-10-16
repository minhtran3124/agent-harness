---
problem_type: knowledge
module: skills/context-propagation-audit/SKILL.md
tags: context-propagation, workflow-engine, paraphrase, stale-copy, audit-search-surface
severity: standard
applicable_when: You run a context-propagation audit on a changed rule or prompt sentence and look for other files that still state the old rule.
affects:
  - skills/context-propagation-audit/SKILL.md
supersedes: null
confidence: high
confirmed_at: 2026-10-16
---
## Applicable When

You run a context-propagation audit on a changed rule or prompt sentence. You look for other
files that still state the old rule, so that no consumer keeps a stale copy.

## Pattern

Search for the old rule's meaning, not only its exact words. Other files restate a rule in their
own words. In gh-309 the old step-2 rhythm "one clarifying question per message" also lived in
`agents/README.md` lines 47 and 55 as "one question at a time". A search for the exact phrase did
not find it.

## How to Use

- List two to four short key terms for the old rule, plus its likely paraphrases. For gh-312 the
  terms were `write tests`, `follow tdd`, `test-first`, `Interfaces`, and the reviewer's
  `quality verdict`.
- Search case-insensitively with `rg -i`. Exclude only generated or historical trees
  (`specs/`, `openwiki/`, `.claude/`, `docs/research/`, `CHANGELOG.md`, `evals/`).
- Read each hit and decide: it restates the changed rule (update it), it names the rule without
  stating it (keep it), or it is unrelated.
- Write the search commands and the excluded trees into the audit matrix, so a "no stale copy"
  result has a named search surface (`rules/behavior.md` §1).

## Related

- docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md
- docs/solutions/harness/ratchet-matches-spelling-not-property.md
