# Design — conflict-guarded re-sync for bootstrap-xia2 files

> Linear: (project harness-skills). Intake: `specs/resync-protected-files/SUMMARY.md` — Lane normal, confidence medium.

## 1. Problem

`scripts/deploy-harness.sh` re-syncs the harness into `.claude/` by per-entry
`rm -rf` + `cp -R` for every harness-shipped dir (`skills`, `agents`, `hooks`,
`rules`, `templates`). Its `copy_dir()` (lines 65–72) has no conflict guard:

```bash
copy_dir() {
  mkdir -p "$OUT/$1"
  for entry in "$1"/* "$1"/.[!.]*; do
    [ -e "$entry" ] || continue
    rm -rf "$OUT/$1/$(basename "$entry")"   # silently destroys whatever was there
    cp -R "$entry" "$OUT/$1/"
  done
}
```

`bootstrap-xia2` writes generated / customized files into the **same paths** the
harness re-syncs, so re-sync blindly clobbers them:

| bootstrap-xia2 output | Re-sync replaces it with |
|---|---|
| `rules/architecture.md` (real stack profile) | the harness source's generic skeleton |
| `rules/guidelines.md` (real stack guidelines) | the generic skeleton |
| `agents/PROJECT.md` (per-repo convention index) | the meta-repo's `agents/PROJECT.md` |
| `skills/xia2/PROJECT.md` (per-repo risk config) | the meta-repo's copy (nested in the `skills/xia2/` dir entry → whole-dir `rm -rf` wipes it) |

Notably, `bootstrap-xia2` itself is carefully designed to **never silently
overwrite** (`.proposed` sidecars, create-if-missing), and the harness already
follows "merge, never replace" for `settings.json` and `.mcp.json` (backs up
before touching). `copy_dir` is the one place that violates that philosophy.
The guard belongs in `deploy-harness.sh` (the engine that does the copy), not
just the installer wrapper.

## 2. Goal

On re-sync, if a protected file differs between the local `.claude/` copy and the
incoming harness source, **notify the user and let them decide** — never overwrite
without confirmation. First install is unaffected.

## 3. Non-goals

- A general checksum manifest + 3-way diff (decided against — more code than the
  stated problem needs; the targeted list directly solves it).
- Protecting arbitrary user customizations to non-bootstrap-xia2 harness files
  (those still overwrite as today — matches the stated scope).
- A machine gate enforcing the protected list against `bootstrap-xia2/SKILL.md`
  drift (a code comment is the contract — keeping it simple per the chosen approach).
- Per-file conflict prompting (decided against — one batch choice covers all
  conflicts; `[b] backup+overwrite` is the escape hatch for selective merging).

## 4. Architecture — targeted protected-file list

A `BOOTSTRAP_OWNED_FILES` array hardcodes the 4 known bootstrap-xia2 outputs.
(The name deliberately avoids `PROTECTED_*`, which in this repo already denotes
the unrelated `hooks/protected-path-guard.sh` / `PROTECTED_PATH_REASON` set.)

- `rules/architecture.md`
- `rules/guidelines.md`
- `agents/PROJECT.md`
- `skills/xia2/PROJECT.md`

A comment points to `skills/bootstrap-xia2/SKILL.md` (Init steps 6–7 + Scaffolding
table) as the source of truth for the list. Re-sync treats these specially;
everything else syncs exactly as today.

### 4.1 Behavior matrix (per protected file on re-sync)

| Situation | Action |
|---|---|
| Local missing | Fresh copy (no conflict) |
| Local == incoming | No-op (skip) |
| Local ≠ incoming (conflict), interactive TTY | Batch menu: **[k] keep mine** (default) · **[o] overwrite with incoming** · **[b] back up mine then overwrite** · **[a] abort** |
| Local ≠ incoming, non-interactive (`--yes` / no TTY) | **Keep mine** (safe default — never silently clobber); write incoming to `<file>.harness-incoming` for review; report |
| Local ≠ incoming, `--overwrite-conflicts` | Overwrite with incoming (explicit clobber, no prompt) |
| `--dry-run` | Report conflicts, then exit **before any copying** — nothing under `.claude/` is touched |

The menu choice is **batch**: one answer applies to every conflicting file. A user
who wants a per-file outcome picks `[b]` and merges from the backup afterwards.

The `.harness-incoming` sidecar (written next to the file, inside `.claude/`)
mirrors bootstrap-xia2's own `.proposed` convention so the user can `diff` and
merge manually. Backups use the existing gitignored `.harness-backup-*/` pattern.

### 4.1.1 `--dry-run` writes nothing at all

`--dry-run` is a whole-script mode, not a conflict-only mode: deploy prints the
mode banner, the conflict report, and what it *would* sync, then exits 0 without
running `prep_dir` / `copy_dir` / `derive_settings`. Consequently
`install-harness.sh` must stop short-circuiting the deploy step under `DRY_RUN`
(today it prints `Would run: …` and never calls deploy) and instead invoke
`deploy-harness.sh --target <dir> --dry-run`, so a user previewing an install
actually sees which protected files would conflict.

### 4.1.2 Prompting reads `/dev/tty`, never stdin

The documented install path is `curl -fsSL … | bash`, and `install-harness.sh`
runs deploy with **stdin inherited** — in that pipeline stdin is the script text
itself, so a bare `read` would consume it. Deploy therefore never reads stdin: it
prompts only when it can open the controlling terminal, and reads via `< /dev/tty`.
Everything else (no tty, `--yes`) falls to *keep mine*. `read` returns non-zero on
EOF, so the call is guarded (`|| true`) — otherwise `set -e` plus the `ERR` trap
would print a spurious `✗ step failed`.

Two tests are **not** valid here:

- `[ -t 1 ]` (used elsewhere in the script for colors) describes stdout, not the
  user's input channel.
- `[ -r /dev/tty ]` — the idiom `install-harness.sh` uses — is also wrong.
  `access(2)` inspects the mode bits of the `/dev/tty` alias node, which stay
  world-readable even in a process that has no controlling terminal (verified
  empirically after `setsid()`). A tty-less CI run would therefore fall into the
  prompt branch and print a menu nobody can answer.

The honest test is to **open** it: `have_tty() { (exec < /dev/tty) 2>/dev/null; }`.
Without this, the fallback still lands on `keep` — but only because `read … || true`
swallows `ENXIO`, and the user never sees the "keeping your local copy" warning.
Correct outcome, silent for the wrong reason.

`install-harness.sh:122` carries the same `[ -r /dev/tty ]` flaw. It is pre-existing
and its failure mode is benign (empty reply → `fail "Aborted (no changes made)"`,
which is the documented "re-run with `--yes`" behavior), so it is left untouched
here per `rules/behavior.md` §3.

### 4.2 Nested-dir handling (the `skills/xia2/PROJECT.md` case)

`skills/xia2/` is a DIR entry, so `copy_dir` does a wholesale `rm -rf` + `cp -R`
on the whole dir (this preserves today's stale-removal + foreign-entry
semantics for everything else in that dir). To protect the nested
`PROJECT.md`:

1. **Snapshot** the protected file (to a temp location) before the dir copy.
2. Do the normal wholesale `rm -rf` + `cp -R`.
3. **Reconcile** per the resolved policy:
   - **keep** → restore the snapshot; write incoming to `.harness-incoming`.
   - **overwrite** → leave the incoming copy in place.
   - **backup** → save the snapshot to `.harness-backup-<ts>/`; leave incoming.

Top-level FILE entries that are protected (`rules/architecture.md` etc.) skip
the blind `rm -rf` + `cp` and apply the policy directly.

**Also snapshot `skills/xia2/PROJECT.md.proposed`**, unconditionally and outside
the conflict machinery. `bootstrap-xia2` Update mode writes that sidecar instead
of overwriting `PROJECT.md` (`SKILL.md` step 4), so it holds a proposal awaiting
human review — and the wholesale `rm -rf` deletes it today. The harness source
does not ship it, so there is never a conflict: snapshot before the dir copy,
restore after, always. The top-level equivalents (`rules/*.md.proposed`,
`agents/PROJECT.md.proposed`) already survive, because `copy_dir` only removes
entries the source actually ships.

### 4.3 Policy resolution order

A single pre-pass runs **once, before the `for d in skills agents hooks rules
templates` loop** — not inside `copy_dir`, which is called once per directory and
would otherwise prompt up to three times. It scans the 4 protected files, builds a
`CONFLICTS` list (local exists AND `cmp -s` says local ≠ incoming), and resolves
the policy once: interactive menu / `--overwrite-conflicts` / `--yes`→keep /
`--dry-run`→report-and-exit. The prompt runs as its own labeled step (outside the
`step()` spinner) so it does not fight the animation.

Hoisting is what makes `[a] abort` meaningful: it exits before `prep_dir` and
before any `rm -rf`, so an aborted re-sync leaves `.claude/` byte-identical. A
pre-pass inside `copy_dir` would abort only *after* `skills/` had already been
destructively re-synced.

### 4.4 Sidecar hygiene

`.harness-incoming` files written under `rules/` and `agents/` are foreign entries
that `copy_dir` never removes (the source does not ship them). Once the user
merges the incoming change and the file matches, a stale sidecar would sit there
forever advertising a conflict that no longer exists. So: when a protected file
has **no conflict** (identical, or freshly copied), delete any `<file>.harness-incoming`
left over from a previous run.

## 5. Components

- **`scripts/deploy-harness.sh`** — `BOOTSTRAP_OWNED_FILES` array; new flags
  `--yes`/`--non-interactive`, `--overwrite-conflicts`, `--dry-run`; helpers
  `is_protected`, `protected_under`, `cmp -s` diff; hoisted pre-pass + policy
  resolution; protected-aware `copy_dir` (in-place policy for FILE entries,
  snapshot/restore for the nested `skills/xia2/` case); sidecar cleanup; summary
  reporting.
- **`scripts/install-harness.sh`** — pass `--yes`/`--dry-run`/`--overwrite-conflicts`
  through to deploy; **stop short-circuiting deploy under `DRY_RUN`** (§4.1.1);
  update messaging + `usage()` (spell out that `--force` means *keep local*, not
  *overwrite*).
- **`tests/scripts/resync-conflict.test.sh`** — hermetic suite (mktemp target,
  deploy from real `$ROOT`).

## 6. Data flow

```
deploy-harness.sh (update mode)
  → pre-pass (ONCE, before prep_dir and the copy loop):
      for each protected file, cmp -s local vs incoming → CONFLICTS list
  → resolve policy (menu via /dev/tty | --overwrite-conflicts | --yes→keep)
  → --dry-run? print report, exit 0 — nothing written
  → [a] abort?  exit 1 — nothing written
  → prep_dir
  → copy_dir per source dir:
        non-protected entries    → normal rm+cp
        protected FILE entries   → apply policy (+ clean stale sidecar if no conflict)
        dir holding a protected  → snapshot PROJECT.md and PROJECT.md.proposed,
          file (skills/xia2/)      rm+cp dir, restore .proposed, reconcile PROJECT.md
  → derive_settings
  → summary: report conflicts + resolution + sidecars
```

## 7. Error handling / fallback

- No `/dev/tty` + no `--yes` → safe default **keep mine** + warning + `.harness-incoming`
  (never silently clobber, never hang, never eat piped stdin — see §4.1.2).
- `--dry-run` → report only; exits before any write (no `.claude/` mutation, no
  sidecars, no backups, no `settings.json` merge).
- `set -e` honored safely: `cmp` and `read` non-zero guarded with `if` / `|| true`
  (the `ERR` trap would otherwise print a spurious `✗ step failed`); no `set -u`
  (matches current script, and keeps empty-array expansion safe on macOS bash 3.2 —
  see `docs/solutions/scripts/bash-empty-array-and-jsonl-parsing-gotchas.md`).

## 8. Success criteria / testing

- First install copies protected skeleton files normally (no conflict, no prompt).
- A customized protected file survives a `--yes` re-sync; `.harness-incoming` is
  written; rc 0.
- `--overwrite-conflicts` overwrites a customized protected file with incoming.
- Piped/no-TTY fallback defaults to keep + warning, and does **not** consume stdin.
- The nested `skills/xia2/PROJECT.md` survives a `--yes` re-sync (snapshot/restore).
- The nested `skills/xia2/PROJECT.md.proposed` survives a re-sync unconditionally.
- A non-protected harness file altered locally is still silently overwritten
  (no over-protection; normal updates apply).
- `--dry-run` reports conflicts and mutates nothing under `.claude/`.
- An identical protected file → no conflict, no sidecar, no-op.
- A stale `.harness-incoming` from an earlier run is removed once the file matches.
- `bash scripts/run-tests.sh` green (incl. `lint-doc-truth.sh` + manifest checker
  + existing install/settings suites).

