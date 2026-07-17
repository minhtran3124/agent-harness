# install-scaffolds-structure — Summary

Lane: high-risk
Confidence: high
Reason: Edits scripts/install-harness.sh (installer, high-blast) and touches the root-write invariant born from a documented data-loss incident. Change is create-if-missing (never deletes/overwrites), so the incident hazard is not reintroduced; direction unambiguous (user asked to fold init-structure into install).
Flags: high-blast (install-harness.sh)
Affects: install-harness.sh (adds structural scaffolding step), README root-behavior claim, install-harness test contract
Input-type: harness improvement

### Intent

"update script scripts/init-structure.sh vào script install harness luôn đi, để user ko mất công chạy nhiều script. đảm bảo là nếu tồn tại thì bỏ qua, còn chưa có thì tạo mới" — fold init-structure.sh into the installer so users run one command; create-if-missing (skip if exists).

## What changed

install-harness.sh now runs `init-structure.sh --root <target>` after building `.claude/` — scaffolding `specs/`, `docs/solutions/`, `agent-memory/` **create-if-missing** as part of the one install command. Added `scripts/init-structure.sh` to PAYLOAD (so `--keep-sources` includes it). Dry-run reports "would scaffold" and writes nothing. The head comment + README root-behavior claim were corrected: the installer no longer "never stages files at the root" — it *adds* absent structural files, but still never overwrites or deletes (the historical incident was a prior installer *pruning* root-staged payload, which create-if-missing never does). Two new install tests: fresh install scaffolds the 6 structural files; a pre-existing structural file is not clobbered.

### Rationale

User wants one command. Folding in is safe precisely because init-structure is create-if-missing — it cannot reintroduce the deletion incident the "never touch root" invariant guarded against. The invariant's true core ("never overwrites or deletes") is preserved and now stated accurately; only the overly-broad "never stages at root" phrasing changed.

### Alternatives considered

- Opt-in flag (`--with-structure`): rejected — user explicitly wants it automatic ("ko mất công chạy nhiều script").
- Leave standalone + just print a hint: rejected — same, defeats the one-command goal.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| install-harness suite incl. 2 new scaffolding cases | `bash tests/scripts/install-harness.test.sh` | 0 | 8 passed |
| init-structure in PAYLOAD + invoked by install | `bash -c 'n="$(grep -c init-structure.sh scripts/install-harness.sh)"; [ "$n" -ge 2 ]'` | 0 | PAYLOAD entry + invocation |
| dry-run writes nothing to the target root | `bash -c 'T=$(mktemp -d); bash scripts/install-harness.sh --source "$PWD" --yes -d "$T" --dry-run >/dev/null 2>&1; n="$(ls -A "$T")"; rm -rf "$T"; [ -z "$n" ]'` | 0 | dry-run still no-writes |
| README root claim accurate (no false "never stages") | `bash -c '! grep -q "never stages files at your project root" README.md && grep -q "create-if-missing" README.md'` | 0 | truth fix |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | clean |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

### Rollback

- `git revert <commit>` — removes the scaffolding step, PAYLOAD entry, tests, and doc edits; installer returns to `.claude/`-only. No data migration; create-if-missing wrote nothing destructive to any consumer.

### Harness-Delta

- none
