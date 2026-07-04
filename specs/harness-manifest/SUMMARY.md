<!-- Header is machine-read by risk-corroboration.sh (Lane) + trust-metrics ledger. -->

# harness-manifest — Summary

Lane: high-risk
Confidence: high
Reason: Hard gate — establishes the single source for the hard-gate vocabulary that risk-corroboration.sh (a high-blast hook) enforces, and adds a CI checker; touches the gate-classification rules.
Flags: existing-behavior, audit-security, multi-domain
Affects: harness-manifest.json (new source), scripts/check_manifest.py, hooks/risk-corroboration.sh (referenced, not logic-changed), skills/feature-intake, rules/auto-correct-scope.md, scripts/run-tests.sh
Input-type: harness improvement

> Lane drives ceremony; Confidence drives interruption. Hard gate → high-risk; design (JSON
> source + CI consistency check, no runtime YAML-in-bash) decided, so confidence is high.

### Intent

Phase 2 của harness v0.3 (docs/harness-v03-plan-overview.md): một nguồn duy nhất cho hard-gate list. Deep review DR-4: hard-gate list lệch giữa 4 nguồn (feature-intake thiếu public-contract dù risk-corroboration block trên nó). Fix: `harness-manifest` là nguồn canonical (skills/hooks/agents + hard_gates); `scripts/check-manifest` probe theo kind + degrade ladder (register-vs-scan như repository-harness); 3 consumer hard-gate trỏ về manifest. Học tool-registry của họ nhưng KHÔNG bê ToolEntry/semver/SQLite.

## What changed

- **`harness-manifest.json`** (new, tracked) — the single source of truth for (a) the hard-gate
  vocabulary: 8 diff-**detectable** gates (each with block/warn mode) + 3 **judgment** gates
  (remove-functionality / session-scope / replace-service — Rule-4 STOP items that can't be
  regex-detected), and (b) the component inventory: hooks (with `wired`), skills, agents. JSON, not
  YAML, so the checker parses it with the Python stdlib (no pyyaml → CI-safe).
- **`scripts/check_manifest.py`** + `test_check_manifest.py` — mechanical consistency, run in CI:
  - **presence scan (register-vs-scan):** every manifest hook/skill/agent exists on disk and every
    disk component is in the manifest; each hook's `wired` flag matches `settings.json`.
  - **gate ↔ enforcer:** `hard_gates.detectable` slugs match `risk-corroboration.sh` exactly, both
    `add_cat` (detection) and `category_mode` (mode) — bidirectional, so the hook and the canonical
    list can never silently diverge.
- **`skills/feature-intake/SKILL.md`** — Step 3 hard-gate list gains the missing **public-contract**
  (DR-4) and points to `harness-manifest.json` as the canonical source.
- **`rules/auto-correct-scope.md`** — Rule 4 points to the manifest as the canonical gate list.
- The dependency-bump tension (Rule 3 auto-adds deps, but a dep-manifest edit trips
  external-provider) is documented in the manifest's `notes`, not silently reconciled.

### Rationale

DR-4 is a divergence bug: the intake classifier omitted a gate the commit hook enforces, so a
route change was classifiable as `normal` then blocked at commit. A single machine-read source +
a CI check that the enforcing hook matches it removes the divergence structurally. JSON+stdlib and
a consistency-check (not runtime YAML parsing in bash) is the low-risk shape — the hook keeps its
tested regexes; CI just guarantees its category list equals the manifest.

### Alternatives considered

- YAML manifest — rejected: needs pyyaml, absent in CI's stock python (Phase 1 hit this); JSON
  parses with stdlib.
- Make risk-corroboration.sh read the gate list from the manifest at runtime — rejected for this
  phase: bash-parsing a manifest + regenerating detection is a high-blast hook rewrite; a CI
  consistency check gets the single-source guarantee at far lower risk.
- Full tool-registry (ToolEntry/semver/arg-schema) like repository-harness — rejected (their
  compiled-tool shape; wrong altitude for a markdown/bash harness — per the 2026-06-09 research).

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| harness test suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN — 109 py (incl. 7 test_check_manifest) + L1 manifest-consistency step |
| manifest matches repo now (CI-safe, stdlib) | `python3 scripts/check_manifest.py` | 0 | manifest ↔ disk ↔ settings.json ↔ risk-corroboration.sh all agree |

### Rollback

- Revert the PR: `git revert <merge-sha>`.
- Per-file: `git checkout HEAD~1 -- harness-manifest.json scripts/check_manifest.py scripts/run-tests.sh skills/feature-intake/SKILL.md rules/auto-correct-scope.md`
- The checker is advisory-to-source: deleting `harness-manifest.json` + the run-tests wiring fully disables it.

### Review outcomes

- **correctness-review** (Opus) — **SOUND, no high/critical bug.** Verified the extraction regexes
  capture exactly the 8 gates (definition line, `*)` default, and warn-list branch correctly
  excluded; slashes matched), the presence scan does NOT wrongly pick up `hooks/lib/git-command.sh`,
  wiring classification is correct, and CI fails closed. Two low notes, **both addressed**: the
  `PROBLEMS` module-global (latent double-call trap) → made local to `check()`; the risk-corroboration
  consumer lacked a manifest pointer → added a header comment. One documented limitation kept: the
  checker enforces only the hook↔manifest half; feature-intake/Rule-4 **prose** can still drift — see
  Harness-Delta (deferred; the hook is the load-bearing enforcer, so prose drift is caught at commit
  by corroboration, not a safety gap).
- **intent-review** (independent model) — satisfies intent; DR-4 structurally fixed; register-vs-scan
  implemented; no excess (no ToolEntry/semver/SQLite), hook logic untouched. The one gap it raised
  (risk-corroboration had no textual manifest pointer) is now fixed.

### Harness-Delta

- fix-direct — closes DR-4 (4-way hard-gate divergence). Future: risk-corroboration could READ the
  manifest at runtime (true single-source) once a safe bash/JSON reader exists — noted, not done.
