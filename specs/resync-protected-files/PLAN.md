---
slug: resync-protected-files
status: shipped
owner: Minh Tran
created: 2026-07-09
---

# Conflict-Guarded Re-Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans (or subagent-driven-development) to implement this plan task-by-task.

**Goal:** Stop `deploy-harness.sh` from silently clobbering the files
`bootstrap-xia2` generates/customizes. On re-sync, differing protected files
prompt the user (or keep mine by default when non-interactive) — never overwrite
without confirmation.

**Architecture:** Targeted `BOOTSTRAP_OWNED_FILES` list in `deploy-harness.sh`
(`rules/architecture.md`, `rules/guidelines.md`, `agents/PROJECT.md`,
`skills/xia2/PROJECT.md`); pre-pass conflict detection via `cmp -s`, hoisted above
the copy loop; protected-aware `copy_dir` with nested-dir snapshot/restore;
`.harness-incoming` sidecars; flags `--yes` / `--overwrite-conflicts` / `--dry-run`
wired through the installer.

**Tech Stack:** Bash (deploy/install scripts), bash contract tests. "Tests" here
are the hermetic `tests/scripts/resync-conflict.test.sh` + `run-tests.sh`
(incl. `lint-doc-truth.sh`) — not pytest. `run-tests.sh` globs
`tests/scripts/*.test.sh`, so the new suite self-registers.

**Resolved decisions (from design.md):** (1) targeted list, not a manifest;
(2) non-interactive default = keep mine + `.harness-incoming` (safe, never clobber);
(3) `--force` stays an alias of `--yes` (safe keep-local default, NOT auto-overwrite);
(4) nested dir handled by snapshot/restore, not per-file copy;
(5) `--dry-run` writes nothing at all and exits before any copying — `install-harness.sh`
stops short-circuiting deploy under `DRY_RUN` (design §4.1.1);
(6) the conflict menu is **batch** (one answer for all conflicts), not per-file;
(7) prompting reads `/dev/tty`, never stdin (design §4.1.2) — `curl | bash` would
otherwise feed the script's own text to `read`.

## 1. Motivation

See `design.md` §1 — `copy_dir`'s blind `rm -rf` + `cp -R` clobbers bootstrap-xia2
outputs on every re-sync; the rest of the harness already follows merge-never-replace.

## 2. Non-goals

- General manifest / 3-way diff (decided against).
- Protecting non-bootstrap-xia2 customizations.
- A machine gate for list-vs-SKILL.md drift (comment is the contract).

## 3. Success Criteria

- 4 protected files survive a customized re-sync under `--yes` (keep mine) with
  `.harness-incoming` written.
- `skills/xia2/PROJECT.md.proposed` survives a re-sync unconditionally.
- `--overwrite-conflicts` clobbers them explicitly.
- Non-protected harness files still overwrite on re-sync (no over-protection).
- `--dry-run` reports conflicts and mutates nothing under `.claude/`.
- A piped (`curl | bash`) re-sync never consumes stdin and never hangs.
- `bash scripts/run-tests.sh` green (incl. doc-truth lint + manifest checker).

## 4. Tasks

> **Waves are strictly sequential.** 1.2's `<verify>` runs `install-harness.test.sh`,
> which executes `scripts/deploy-harness.sh` from the checkout root — the file 1.1
> rewrites. They cannot share a wave even though their `<files>` are disjoint.

### Task 1.1 — Add conflict guard to deploy-harness.sh

```xml
<task id="1.1" wave="1">
  <files>scripts/deploy-harness.sh</files>
  <action>Add a BOOTSTRAP_OWNED_FILES array (rules/architecture.md, rules/guidelines.md, agents/PROJECT.md, skills/xia2/PROJECT.md) with a comment pointing at skills/bootstrap-xia2/SKILL.md as the list source of truth. Do NOT name it PROTECTED_* — that prefix already denotes hooks/protected-path-guard.sh's unrelated set. Extend the arg loop with --yes/--non-interactive, --overwrite-conflicts, --dry-run. Add helpers is_protected &lt;rel&gt; and protected_under &lt;entry-rel&gt; (for the nested skills/xia2/ case). Add a pre-pass function that runs ONCE in update mode BEFORE prep_dir and before the `for d in skills agents hooks rules templates` copy loop — never inside copy_dir, which is called per-directory and would prompt up to three times and make [a] abort fire after skills/ was already destroyed. The pre-pass cmp -s each owned file (local .claude/&lt;rel&gt; vs source &lt;rel&gt;), builds a CONFLICTS list, and resolves one batch policy: interactive menu ([k] keep / [o] overwrite / [b] backup+overwrite / [a] abort) only when [ -r /dev/tty ], reading via `read ... &lt; /dev/tty || true`; --overwrite-conflicts → overwrite all; --yes or no /dev/tty → keep mine + warning; --dry-run → print the report and exit 0 before any write; [a] → exit 1 before any write. Never test [ -t 0 ] or [ -t 1 ] for interactivity — under `curl | bash` stdin is the script text and a bare read would eat it. Then make copy_dir protected-aware: top-level FILE entries that are owned skip the blind rm -rf + cp and apply the policy directly; the DIR entry holding an owned file (skills/xia2/) snapshots BOTH PROJECT.md and PROJECT.md.proposed to a temp path, does the normal wholesale rm -rf + cp -R, restores .proposed unconditionally (the source never ships it, so it can never conflict), then reconciles PROJECT.md per policy: keep → restore snapshot + write incoming to &lt;file&gt;.harness-incoming; overwrite → leave incoming; backup → save snapshot to .harness-backup-&lt;ts&gt;/ + leave incoming. When an owned file has NO conflict, delete any stale &lt;file&gt;.harness-incoming left from a previous run. Run the prompt as its own labeled step outside the step() spinner. Update the final summary to report conflicts + resolution + sidecars. Guard cmp and read non-zero with if / || true so set -e and the ERR trap do not print a spurious step-failed; no set -u (matches current script).</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && bash -n scripts/deploy-harness.sh && tmp=$(mktemp -d) && bash scripts/deploy-harness.sh --target "$tmp" >/dev/null 2>&1 </dev/null && [ -d "$tmp/.claude/skills" ] && [ -f "$tmp/.claude/rules/architecture.md" ] && printf 'mine\n' > "$tmp/.claude/rules/architecture.md" && bash scripts/deploy-harness.sh --target "$tmp" --yes >/dev/null 2>&1 </dev/null && grep -qx mine "$tmp/.claude/rules/architecture.md" && [ -f "$tmp/.claude/rules/architecture.md.harness-incoming" ] && rm -rf "$tmp"</verify>
  <done>First install builds a valid .claude/; a customized protected file survives a --yes re-sync with a .harness-incoming sidecar beside it; the script parses clean.</done>
</task>
```

### Task 1.2 — Wire flags through install-harness.sh

```xml
<task id="1.2" wave="2">
  <files>scripts/install-harness.sh</files>
  <action>Pass --yes to deploy when ASSUME_YES or FORCE is set (so a non-interactive re-sync keeps protected files instead of hanging on a prompt). Add an --overwrite-conflicts flag and pass it through. Restructure the DRY_RUN branch around the deploy call: today it prints "Would run: …" and never invokes deploy, so a --dry-run pass can never report protected-file conflicts. Instead invoke `bash "$SRC/scripts/deploy-harness.sh" --target "$TARGET_DIR" --dry-run`, which per design §4.1.1 exits before any write. Keep --force as an alias of --yes, and spell out in usage() that it means "re-sync without asking, keeping local protected files" — NOT "overwrite" — since --force reads as auto-clobber to most users. Update the "Existing harness found … re-synced" message and usage() to mention protected-file handling and the .harness-incoming review sidecars.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && bash -n scripts/install-harness.sh && bash tests/scripts/install-harness.test.sh</verify>
  <done>install-harness.sh forwards --yes/--dry-run/--overwrite-conflicts to deploy, --dry-run now actually reaches deploy, and the existing install suite stays green.</done>
</task>
```

### Task 1.3 — Add resync-conflict.test.sh

```xml
<task id="1.3" wave="3">
  <files>tests/scripts/resync-conflict.test.sh</files>
  <action>Create a hermetic suite mirroring tests/scripts/settings-merge.test.sh (mktemp target, deploy from real $ROOT, assert via lib.sh). run-tests.sh globs tests/scripts/*.test.sh, so no registration step is needed. Every deploy invocation must redirect stdin from /dev/null so a stray prompt fails loudly instead of hanging CI. Cases: (1) first install copies protected skeleton files normally, no sidecar; (2) customize .claude/rules/architecture.md then --yes re-sync → kept + .harness-incoming written + rc 0; (3) same customization + --overwrite-conflicts → overwritten with incoming; (4) no-/dev/tty fallback (no --yes, stdin from a here-string that must NOT be consumed) → keep + warning + rc 0, and assert the here-string is still readable; (5) nested: customize .claude/skills/xia2/PROJECT.md then --yes → kept (snapshot/restore); (6) nested sidecar: write .claude/skills/xia2/PROJECT.md.proposed then re-sync → still present; (7) non-protected harness file (skills/compound/SKILL.md) altered locally → re-sync → silently overwritten (no over-protection); (8) --dry-run on a conflicting target → reports the conflict, and the whole .claude/ tree is byte-identical afterwards (compare a `find | sort` + checksum snapshot before/after); (9) protected file identical to incoming → no conflict, no sidecar, no-op; (10) stale sidecar cleanup: leave a .harness-incoming next to an identical protected file → re-sync removes it.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && bash tests/scripts/resync-conflict.test.sh</verify>
  <done>All 10 cases pass; the suite is hermetic (mktemp only, real repo git status unchanged, this repo's own .claude/ untouched).</done>
</task>
```

### Task 1.4 — Docs

> **Do NOT hand-edit `VERSION` or `CHANGELOG.md`.** `scripts/bookkeeping.sh` (driven by
> `.github/workflows/post-merge-maintenance.yml`) bumps VERSION and inserts the dated
> CHANGELOG section on merge — that automation is exactly what v0.3 Phase 1 replaced the
> manual append with. A manual bump here would be double-bumped at merge.

```xml
<task id="1.4" wave="4">
  <files>CLAUDE.md, README.md, specs/resync-protected-files/SUMMARY.md</files>
  <action>Add a Gotchas bullet to CLAUDE.md on conflict-guarded re-sync + --overwrite-conflicts + the &lt;file&gt;.harness-incoming review sidecars (use &lt;…&gt; placeholder phrasing so lint-doc-truth.sh stays green). In README.md § Installation → "Add to an existing project": amend the update sentence on line 81 (currently "`.claude/` is merge-synced, non-harness entries kept" — extend it to say bootstrap-xia2-generated files are kept too, and a differing one is reported with a &lt;file&gt;.harness-incoming sidecar), and add --overwrite-conflicts to the flag list on line 84, noting --force/--yes keep local files rather than overwriting them. The one-liner on line 78 already passes --yes, which is the safe keep-local path — leave it as is. Leave VERSION and CHANGELOG.md alone (see the note above). Fill SUMMARY.md's ### Verify rows from the runs actually executed, and replace the placeholder ### Rollback with a real one: `git revert &lt;sha&gt;` restores this repo, but a botched deploy destroys files in a TARGET repo that no revert here can recover — record the .harness-backup-&lt;ts&gt;/ restore path too. Record a Harness-Delta: backlog in SUMMARY.md for the bookkeeping gap described in Task 1.5.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && bash scripts/run-tests.sh && python scripts/check_lane_evidence.py resync-protected-files</verify>
  <done>Docs reflect the new re-sync behavior; full suite green incl. doc-truth lint + manifest checker; lane evidence check passes; VERSION and CHANGELOG.md untouched in the diff.</done>
</task>
```

### Task 1.5 — ESCALATION: bookkeeping's minor-bump regex omits `scripts/`

```xml
<task id="1.5" wave="4">
  <files>specs/resync-protected-files/ESCALATIONS.md</files>
  <action>Do not silently fix this — it changes the repo's versioning contract, which rules/orchestration.md classifies as "redefining the system" (escalate). Write an ESCALATIONS.md block (shape: templates/ESCALATIONS.template.md) recording the gap: CHANGELOG.md lines 4-6 promise "minor for ... a changed skill/hook contract", but scripts/bookkeeping.sh line 76 only matches ^(hooks/|settings\.json|skills/). scripts/deploy-harness.sh is the deploy engine every consuming project runs, and this PR changes its contract (new flags, new conflict behavior) — yet the automation will bump patch (0.8.1 -> 0.8.2), not minor. Present the options: (a) accept the patch bump for this PR and file a follow-up; (b) widen the regex to include scripts/deploy-harness.sh or scripts/install-harness.sh (touches the versioning contract; needs its own lane + tests/scripts/bookkeeping.test.sh update). Deny-on-no-response: do not widen the regex as part of this PR without a recorded decision.</action>
  <verify>cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills && test -s specs/resync-protected-files/ESCALATIONS.md && ! git diff --name-only "$(git merge-base HEAD v2)"...HEAD -- scripts/bookkeeping.sh VERSION CHANGELOG.md | grep -q .</verify>
  <done>ESCALATIONS.md records the decision request; bookkeeping.sh, VERSION, and CHANGELOG.md are absent from this PR's diff.</done>
</task>
```

## 5. Status Log

- 2026-07-09 — plan approved after review; `proposed` → `active`. Four issues and two gaps folded
  into `design.md` before Task 1.1 (hoisted pre-pass, `/dev/tty` prompting, `--dry-run` semantics,
  wave split, `.proposed` snapshot, sidecar hygiene).
- 2026-07-10 — Tasks 1.1–1.5 complete, each two-stage reviewed. Three real defects were found by
  the review chain, not by the plan: the `--dry-run` install claiming success (`64b02cd`), the dead
  `[ -r /dev/tty ]` interactivity test (`ac7f472`), and — via `/correctness-review` — a false
  premise in `design.md` §4.2 that made the `.proposed` restore freeze a consumer's copy forever
  (`cfff07c`). `/intent-review` found no gap against the original request.
- 2026-07-10 — shipped via `feat/resync-protected-files`.
- 2026-07-10 — follow-up on PR #50, from manually exercising the installer end-to-end: the
  `have_tty()` fix (`ac7f472`) was never ported to `install-harness.sh`, whose own
  `[ -r /dev/tty ]` killed a tty-less re-sync with a raw shell error, and
  `--overwrite-conflicts` did not consent to the re-sync it names. Fixed in `78be4bc` with
  `tests/scripts/install-tty-gate.test.sh` (4/7 assertions fail pre-fix). Separately,
  `rules/behavior.md` — a hand-tuned skeleton, not a `bootstrap-xia2` output — was outside
  `BOOTSTRAP_OWNED_FILES` and got clobbered silently; added in `3c1b753` with case 11.

