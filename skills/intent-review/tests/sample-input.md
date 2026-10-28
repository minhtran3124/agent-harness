# Sample input: merged PR #353

No run has been made yet. This file records the exact two inputs to pass to the `intent-reviewer`
agent so a run can be done later. Nothing else (no plan, design, ADR or summary) goes in.

## Input 1: request (verbatim body of issue #339)

Source: `gh issue view 339 --repo minhtran3124/agent-harness --json body -q .body`

```text
Freeze the current harness as a tag, then delete the Codex advisory alpha. It is about 11.7k lines across 76 tracked files and is not GA.

## Tasks

- [ ] Tag `legacy-v2.37.0` on the `sdlc` head (c5dd856) and push the tag
- [ ] Delete `adapters/codex/`, Codex scripts (`render_codex_adapter.py`, `deploy-codex-adapter.sh`, `codex_harness_doctor.py`, `check_codex_*`, `probe_codex_packaging.sh`, `capture_codex_capabilities.sh`, `install-codex-harness.sh`) and their tests
- [ ] Delete `docs/codex-alpha-install.md` and Codex sections in README, HARNESS.md, skills/README.md
- [ ] Remove the `codex-alpha-contract.test.sh` step from `.github/workflows/harness-ci.yml`

## Done when

- `git ls-files | grep -ic codex` prints 0, or only CHANGELOG history lines
- `bash scripts/run-tests.sh` passes
- CI passes on the PR

Part of the Harness v5 epic: #338
```

## Input 2: diff range

```text
c5dd856..9667be7
```

Merged PR #353 of this repo.
