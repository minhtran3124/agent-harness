# Design — Remove `agent-memory` from the harness

Status: proposed. Companion: `research-brief.md`.

## Requirement (owner, 2026-07-20)

Remove the entire unused `agent-memory` feature, including everything that currently causes
`scripts/install-harness.sh` to scaffold or advertise it in a consuming repository.

## Decision

Delete the tracked agent-memory convention and disable bundled subagent memory. Keep
`docs/solutions/` as the only committed, harness-managed knowledge store.

This is a removal, not a repair. There will be no replacement schema, synchronization step,
confidence-decay implementation, or compatibility alias.

## End state

After implementation:

- the repository has no root `agent-memory/` directory or structural template for it;
- `coding`, `reviewer`, and `test-runner` no longer declare persistent memory;
- `init-structure.sh` creates six structural files and never creates `agent-memory/`;
- a fresh harness install creates no target-root `agent-memory/` directory;
- install dry-run and current documentation never advertise agent memory;
- shared durable learnings continue through `/compound` → `docs/solutions/` →
  `session-knowledge.sh`;
- Claude Code's own main auto-memory remains untouched because it lives outside the repository
  and is not installed by the harness.

## Component design

### 1. Remove subagent memory configuration

Delete `memory: project` from:

- `agents/coding.md`
- `agents/reviewer.md`
- `agents/test-runner.md`

Do not replace it with `memory: local` or `memory: user`: the requirement is complete removal of
this harness-owned capability. Deployment and installation already copy these definitions into
`.claude/agents/`, so removing the source fields also removes memory from future deployed copies.

No task will mutate this checkout's live, gitignored `.claude/`; verification uses source files
and throwaway install targets only.

### 2. Delete the store and its template

Delete both:

- `agent-memory/README.md`
- `templates/structure/agent-memory-README.md`

Deleting only the root README is insufficient because `init-structure.sh` would recreate it from
the template. Deleting only the template would leave a tracked directory that still claims the
feature exists.

### 3. Reduce structural initialization from seven files to six

Remove the `agent-memory-README.md|agent-memory/README.md` row from
`scripts/init-structure.sh`.

Update `tests/scripts/init-structure.test.sh` so:

- `DESTS` contains the six surviving structural files;
- expected `created` and `exists` counts are six;
- the bare-repo case explicitly asserts `agent-memory/` does not exist;
- idempotency and no-clobber behavior remain unchanged.

### 4. Remove the feature from install behavior

Update `scripts/install-harness.sh`:

- remove `agent-memory/` from the header's structural-dir list;
- remove it from the dry-run scaffold message;
- keep the real-install call to `init-structure.sh`, which now creates only the six remaining
  files.

Update `tests/scripts/install-harness.test.sh` to prove:

- dry-run output does not contain `agent-memory` and writes nothing;
- fresh install creates the remaining structural files but not `agent-memory/`;
- the installed `.claude/agents/{coding,reviewer,test-runner}.md` definitions contain no
  `memory:` field;
- reinstall does not recreate `agent-memory/`;
- a pre-existing target `agent-memory/` is left untouched.

The last case preserves the installer's explicit never-delete/never-overwrite guarantee. Removing
old consumer data automatically would be a destructive migration and is intentionally rejected.
Consumers who want to remove an existing directory may delete it themselves after inspecting it.

### 5. Remove current claims and path vocabulary

Update current, user-facing documentation:

- `README.md`: the inheritance answer names only `/compound` + `docs/solutions/`; installation
  lists only `specs/` and `docs/solutions/` as structural dirs.
- `skills/README.md`: remove agent-memory from scaffold/adoption instructions and delete the
  Agent Memory section.
- `skills/xia2/README.md`: remove agent-memory from all three init-structure descriptions.
- `scripts/lint-doc-truth.sh`: remove `agent-memory` from `KNOWN_ROOTS`.

Historical documents under `docs/` and `specs/` remain unchanged. They are evidence of past
design and decisions, not live consumers or installation instructions.

## Verification contract

The change is complete only when all of the following hold:

1. Targeted init and install suites pass.
2. No root store or source template exists.
3. All three source agent definitions have no `memory:` field.
4. A fresh throwaway install contains neither target-root `agent-memory/` nor memory-enabled
   bundled agent definitions.
5. A live-surface grep finds no `agent-memory` or `memory: project` outside historical
   `docs/`, historical `specs/`, and this removal spec.
6. `scripts/run-tests.sh` is green.

## Non-goals

- Do not delete or edit `~/.claude/projects/<project>/memory/`.
- Do not mutate the live `.claude/agent-memory/` directory in this checkout.
- Do not change `/compound`, `docs/solutions/`, or `session-knowledge.sh`.
- Do not build a migration, compatibility shim, memory daemon, or confidence-decay parser.
- Do not rewrite dated research, review, solution, or shipped-spec history merely to obtain a
  repository-wide zero-hit grep.
- Do not automatically delete pre-existing `agent-memory/` data from consuming repositories.

## Risks and rollback

- A consumer may have manually populated the otherwise-unused root directory. The installer
  leaves it untouched, avoiding data loss.
- Removing `memory: project` means bundled subagents cannot accumulate private per-role context.
  Current runtime directories are empty, and durable shared knowledge already has a functioning
  path through `docs/solutions/`, so the observed regression risk is low.
- Documentation may retain a live stale reference outside the known list. The scoped zero-hit grep
  plus widened doc-truth lint catches that before completion.
- Rollback is a normal `git revert`; no repository or consumer data migration occurs.
