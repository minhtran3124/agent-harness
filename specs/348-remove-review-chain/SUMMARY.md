# 348-remove-review-chain — Summary

Lane: high-risk
Confidence: high
Reason: Deletes two skills, the evals tree and eval scripts; one reference edit lands under templates/, a CI hard-gate path.
Flags: high-blast, deletion
Affects: skills/, evals/, scripts/, templates/structure/docs-solutions-README.md
Input-type: harness improvement

### Intent

Implement GitHub issue #348 [P4] Remove correctness-review, context-propagation-audit, evals and scoring: delete both skills, evals/ and the score and eval scripts with their tests, and remove every reference.

## What changed

Removed skills/correctness-review, skills/context-propagation-audit, evals/ and all eval and scoring scripts with their tests. Removed the correctness stages from the runtime-entry binding and the prompt composer. Reworded references in rules, agents, skills README and docs. The only templates/ change is one sentence in a docs README template.

### Rationale

/code-review replaces the in-house review chain, and the evals measured the old harness.

### Alternatives considered

- none

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| manifest consistency | `python3 scripts/check_manifest.py` | 0 | |
| skill tool conformance | `python3 scripts/check_skill_tool_conformance.py` | 0 | |
| runtime entry bindings | `bash tests/scripts/runtime-entry-bindings.test.sh` | 0 | |
| prompt delivery matrix | `python3 scripts/render_skill_prompt.py --check-all` | 0 | |

### Not auto-verified

- Historical docs under docs/ were reworded, not deleted — reached traceability only.

### Rollback

- `git revert <sha>` for each commit on feat/348-remove-review-chain

### Harness-Delta

- none
