#!/bin/bash
# Embedded gate-mode defaults — the block/warn policy for the nine detectable hard
# gates, mirroring harness-manifest.json hard_gates.detectable (7 block + 2 warn).
#
# WHY THIS FILE EXISTS: risk-corroboration.sh resolves gate modes from EXACTLY TWO
# index-safe sources — (a) `git show :harness-manifest.json` (the git INDEX) when it
# resolves, else (b) this file. It NEVER reads a worktree or `.claude/` policy file
# (invariant #2, asserted by tests/hooks/risk-corroboration.test.sh SC-8). A consumer
# repo that does not track the manifest gets this 2-warn/7-block parity instead of the
# old block-all fallback. These are compile-time constants inside the harness's own
# trust boundary — an unstaged edit cannot loosen them.
#
# DRIFT GUARD: scripts/check_gate_modes_smoke.py (SC-9) asserts this map is byte-
# consistent with harness-manifest.json. Change a mode in the manifest first, then
# mirror it here — the same slug spellings the hook's add_cat detectors use.
#
# Format: one "slug=mode" per line (block|warn). Consumed as $GATE_MODES_DEFAULT by
# category_mode(), which greps for an exact "slug=warn" line.
GATE_MODES_DEFAULT="auth=block
authorization=block
data-loss/migration=block
audit/security=block
external-provider=block
public-contract=block
weakening-validation=warn
high-blast=block
workflow-engine=warn"
