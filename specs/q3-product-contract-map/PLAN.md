---
slug: q3-product-contract-map
status: active
owner: Minh Tran
created: 2026-07-08
---

# Q3 Product-Contract Map (Level A — static manifest)

> **For Claude:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan task-by-task.

**Goal:** Give the harness a contract→consumer map so an edit to a non-code contract surface (settings.json, a template column, the manifest) surfaces the consumers that must be re-verified — closing the Q3 gap where blast-radius is only file-level.

**Architecture:** Add a declarative `contracts` block to `harness-manifest.json` (`{surface[], consumers[]}` per contract). A new `scripts/check-contract-impact.sh` maps changed files → impacted contracts → consumers (advisory, exit 0). `scripts/check_manifest.py` gains a validation pass so every surface/consumer path must exist on disk. `scripts/harness-audit.sh` gets one advisory section that runs the mapper over the working-tree diff. No hook (`hooks/*`) is touched — the human chose `harness-audit.sh` wiring at intake to stay clear of the high-blast hard gate.

**Tech Stack:** Bash (advisory scripts), Python 3 stdlib (manifest parsing / checker), pytest + `.test.sh` suites wired into `scripts/run-tests.sh`.

---

## 1. Motivation

Q3 ("which product contract does this change affect?") is the weakest pillar in the MIN-24 audit. `blast-radius-check.sh` only compares file *paths* against a plan's `<files>`; it cannot say that editing `settings.json` breaks the CLAUDE.md hook table, or that renaming a `### Verify` column breaks `verify_summary.py`. Those are contracts with hidden consumers. This plan makes the map explicit and mechanically validated.

## 2. Non-goals

- **Level B** (auto-deriving consumers from `code-review-graph`) and **Level C** (contract tests asserting surface↔consumer behavior). Out of scope; noted as the upgrade path.
- **"Skill handoff edges" as a contract** — deferred. It is prose in `skills/README.md` with no mechanical consumer list; forcing it into Level A would be a fake mapping. Replaced by the mechanical `plan-schema` contract. **Confirmed by user at plan-review (2026-07-08)** after a blind reviewer flagged the divergence from MIN-64's verbatim contract list.
- **No new hook and no `settings.json` edit** — deliberately, to keep this out of the high-blast hard gate (intake decision).

## 3. Success Criteria

- `harness-manifest.json` has a `contracts` block with 5 entries, each `{surface[], consumers[]}`, all paths present on disk.
- `python3 scripts/check_manifest.py` stays green and now fails if a contract path is missing/misspelled.
- `bash scripts/check-contract-impact.sh templates/SUMMARY.template.md` prints the `artifact-schema-summary` consumers; `--changed` maps the working-tree diff.
- `bash scripts/harness-audit.sh` prints a contract-impact reminder section when a surface file is dirty, without inflating the drift `band`.
- `bash scripts/run-tests.sh` → `ALL GREEN`; `bash scripts/lint-doc-truth.sh` clean.

## 4. Tasks

### Task 1.1 — Add the `contracts` block to the manifest

```xml
<task id="1.1">
  <files>harness-manifest.json</files>
  <action>Add a top-level "contracts" object after "hard_gates" (keep JSON valid, stdlib-parseable). Each key is a contract slug; each value is {"surface": [...paths], "consumers": [...paths], "desc": "..."}. Use these 5 contracts with paths that all exist on disk:
  - "hook-registration": surface ["settings.json"], consumers ["CLAUDE.md", "scripts/lint-doc-truth.sh"]
  - "artifact-schema-summary": surface ["templates/SUMMARY.template.md"], consumers ["scripts/verify_summary.py", "scripts/check_lane_evidence.py", "hooks/commit-quality-gate.sh"]
  - "artifact-schema-plan": surface ["rules/plan-format.md"], consumers ["scripts/check_plan_format.py", "skills/visual-planner/render_plan.py"]
  - "lane-evidence-mapping": surface ["scripts/check_lane_evidence.py"], consumers ["skills/feature-intake/SKILL.md", "rules/auto-correct-scope.md"]
  - "hard-gate-vocabulary": surface ["harness-manifest.json"], consumers ["hooks/risk-corroboration.sh", "rules/auto-correct-scope.md", "skills/feature-intake/SKILL.md"]
  Add a "__doc__" key inside "contracts" pointing at scripts/check-contract-impact.sh as the reader.</action>
  <verify>cd "$(git rev-parse --show-toplevel)" && python3 -c "import json;c=json.load(open('harness-manifest.json'))['contracts'];assert len([k for k in c if k!='__doc__'])==5, c.keys()"</verify>
  <done>Manifest still valid JSON; 5 contract entries present.</done>
</task>
```

### Task 1.2 — Validate `contracts` in check_manifest.py (TDD)

```xml
<task id="1.2">
  <files>scripts/check_manifest.py, scripts/test_check_manifest.py</files>
  <action>TDD. (1) In test_check_manifest.py add MANIFEST_OK a minimal "contracts" block {"c1": {"surface": ["settings.json"], "consumers": ["CLAUDE.md"]}} and create those files in the tmp build() root; add test_contract_surface_missing() and test_contract_consumer_missing() asserting exit 1 + a "manifest: contracts drift" line when a surface/consumer path is absent. Run — expect FAIL (no check yet). (2) In check_manifest.py add section "C. contracts <-> disk": for each contract (skip "__doc__" key), for every path in surface + consumers, if not (root / path).exists() → problem("contracts", f"{slug} path '{path}' not found on disk"). Also assert each contract has non-empty surface and consumers lists. Re-run — expect PASS. Keep it stdlib-only; do not require the block to exist (older manifests without "contracts" must not break — guard with m.get("contracts", {})).</action>
  <verify>cd "$(git rev-parse --show-toplevel)" && python3 -m pytest scripts/test_check_manifest.py -q --no-header -p no:cacheprovider && python3 scripts/check_manifest.py</verify>
  <done>New tests pass; check_manifest.py green against the real manifest; missing-path drift is detected.</done>
</task>
```

### Task 2.1 — Create the contract-impact mapper (TDD)

```xml
<task id="2.1">
  <files>scripts/check-contract-impact.sh, tests/scripts/check-contract-impact.test.sh</files>
  <action>TDD. (1) Write tests/scripts/check-contract-impact.test.sh (follow the style of tests/scripts/harness-audit.test.sh + tests/lib.sh): build a tmp root with a harness-manifest.json carrying one contract {surface:["settings.json"],consumers:["CLAUDE.md","scripts/lint-doc-truth.sh"]}; assert (a) `check-contract-impact.sh settings.json` prints a line naming contract "hook-registration"-style match and lists both consumers; (b) a non-surface file prints nothing and exits 0; (c) exit code is always 0. Run — expect FAIL (script absent). (2) Write scripts/check-contract-impact.sh: `set -u`; args = file paths, OR `--changed` to use `git diff --name-only HEAD` (tracked changes) + `git ls-files --others --exclude-standard` (new files); `--root DIR` for tests; parse manifest via a python3 heredoc that, given the changed-file list on argv, emits one line per impacted contract: `contract <slug>: surface <file> → verify consumers: a, b, c`. Match is exact-path membership in a contract's surface list. Always exit 0 (advisory). Keep < ~60 lines.</action>
  <verify>cd "$(git rev-parse --show-toplevel)" && bash tests/scripts/check-contract-impact.test.sh && bash scripts/check-contract-impact.sh templates/SUMMARY.template.md | grep -q artifact-schema-summary</verify>
  <done>Mapper prints consumers for a known surface, silent for non-surfaces, exit 0; test suite green.</done>
</task>
```

### Task 2.2 — Wire an advisory section into harness-audit.sh

```xml
<task id="2.2">
  <files>scripts/harness-audit.sh, tests/scripts/harness-audit.test.sh</files>
  <action>Add section "7. contract surfaces dirty in working tree → remind consumers" AFTER the manifest-degraded check. It calls `bash scripts/check-contract-impact.sh --changed --root "$ROOT"` and prints each returned line as a reminder into its OWN counter CONTRACT_IMPACT (initialise =0 near the other counters). Do NOT add these to FINDINGS or the drift `band` — a changed surface is a reminder, not drift. In the human-readable tail print "  Contract-impact reminders: $CONTRACT_IMPACT" only when >0. For --json: the JSON is emitted by the `python3 -c` heredoc that slices `sys.argv[1:10]` and unpacks 9 positional vars (harness-audit.sh:196-213) — you MUST extend the slice to `sys.argv[1:11]`, add a `ci` var, append `"contract_impact": int(ci)` inside "checks", AND append `"$CONTRACT_IMPACT"` as the trailing arg of the invocation. Also update the check-list docstring at the top (harness-audit.sh:9-16) to enumerate check 7. Update tests/scripts/harness-audit.test.sh: add a case that dirties a surface file in the tmp root and asserts the reminder count appears in --json while `band`/`findings` are unchanged by it. Preserve `set -u` safety (guard the git calls; tmp roots may not be git repos → check-contract-impact must no-op cleanly when git returns nothing).</action>
  <verify>cd "$(git rev-parse --show-toplevel)" && bash tests/scripts/harness-audit.test.sh && bash scripts/harness-audit.sh --json | python3 -c "import json,sys;d=json.load(sys.stdin);assert 'contract_impact' in d['checks'], d"</verify>
  <done>harness-audit exposes contract-impact reminders separately from drift findings; both test suites green.</done>
</task>
```

### Task 3.1 — Full suite + doc-truth green

```xml
<task id="3.1">
  <files>specs/q3-product-contract-map/SUMMARY.md</files>
  <action>Run the full harness test suite and the doc-truth lint. Fill the SUMMARY.md `### Verify` table with the real commands + exit codes from this run. If lint-doc-truth flags a referenced-but-missing path introduced by this work, fix the reference (not the lint). No new production code in this task — it is the green-gate + evidence capture.</action>
  <verify>cd "$(git rev-parse --show-toplevel)" && bash scripts/run-tests.sh | tail -1 | grep -q "ALL GREEN"</verify>
  <done>run-tests.sh prints ALL GREEN; SUMMARY ### Verify rows reflect the actual run.</done>
</task>
```

## 5. Risks

- **Manifest JSON breakage** — a malformed `contracts` block would make `check_manifest.py` and every consumer that parses the manifest fail. Mitigated: Task 1.1 verify parses it; Task 1.2 hardens the checker; guarded with `m.get("contracts", {})` for back-compat.
- **harness-audit noise** — counting contract reminders as drift would flip the health band during normal work. Mitigated by the separate `CONTRACT_IMPACT` counter (Task 2.2), excluded from `band`.
- **`set -u` / non-git tmp roots** — test roots aren't git repos; the `--changed` git calls must degrade to empty, not error. Called out in Task 2.1/2.2.
- **Scope creep toward Level B/C** — explicitly out of scope (§2).

## 6. Status Log

- 2026-07-08 — Plan drafted (status: proposed). Normal lane (intake narrowed from high-risk by choosing `harness-audit.sh` over a hook). Awaiting execution handoff.
