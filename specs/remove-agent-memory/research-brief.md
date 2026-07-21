# Research — Remove the unused `agent-memory` feature end to end

Status: research complete. Requested 2026-07-20: remove every live `agent-memory`
surface, including fresh-install and reinstall behavior.

All facts below were verified against the working tree and git history on 2026-07-20.

## 1. What exists today

The repository currently has three different persistence mechanisms that must not be
conflated:

| Mechanism | Location | Writer / reader | Observed state |
|---|---|---|---|
| Tracked per-agent convention | `agent-memory/` | No runtime reader or writer | README only; no entry has ever existed in git history |
| Claude subagent memory | `.claude/agent-memory/<agent>/` | Claude Code when an agent declares `memory: project` | Directories for coding/reviewer/test-runner exist locally, all empty |
| Shared harness knowledge | `docs/solutions/` | `/compound` writes; `session-knowledge.sh` loads INDEX + critical patterns | Active and independently tested |

Claude Code's main auto-memory under `~/.claude/projects/<project>/memory/` is also active,
but it is product-owned machine-local state outside this repository. It is not the tracked
`agent-memory/` feature and is out of scope for removal.

## 2. Why the root feature does not work

The root README declares `agent-memory/` the version-controlled shared home and describes
confidence decay through `confirmed`, `confidence`, and `review-by` metadata. Nothing implements
that contract:

- no agent, skill, hook, or script reads or writes root `agent-memory/<agent>/` entries;
- no code parses the metadata or downgrades expired confidence;
- no synchronization copies `.claude/agent-memory/` to the root store;
- Claude Code loads a per-agent `MEMORY.md` from `.claude/agent-memory/<agent>/`, not the
  unrelated root directory;
- `.claude/` is gitignored, so the configured `memory: project` stores are effectively local,
  despite the upstream scope being intended for version-controlled sharing.

The repository's 2026-07-03 deep review independently classified the confidence-decay protocol
as dead prose. The 2026-07-17 owner decision kept the folder only because coordinated deletion
cost more than retaining one file; it did not establish a runtime consumer.

## 3. Live change surface

### Runtime agent configuration

- `agents/coding.md`
- `agents/reviewer.md`
- `agents/test-runner.md`

Each declares `memory: project`. Removing those fields prevents future deploys/installs from
creating or enabling `.claude/agent-memory/<agent>/` stores for these bundled agents.

### Tracked store and source template

- `agent-memory/README.md`
- `templates/structure/agent-memory-README.md`

The two files are byte-identical. Both should be deleted; otherwise either the source tree or a
future scaffold still advertises the removed feature.

### Structural initialization

- `scripts/init-structure.sh` has one template-to-destination row for
  `agent-memory/README.md`.
- `tests/scripts/init-structure.test.sh` pins seven generated files and seven
  `created`/`exists` messages.

After removal, the initializer must scaffold exactly six files: two under `specs/`, three under
`docs/solutions/`, and `techstacks/README.md`. A negative assertion must prove it does not create
`agent-memory/`.

### Installation

- `scripts/install-harness.sh` names `agent-memory/` in its header and dry-run message, and calls
  `init-structure.sh` during a real install.
- `tests/scripts/install-harness.test.sh` currently requires
  `<target>/agent-memory/README.md` after a fresh install.

Fresh install must instead prove all remaining structural files exist and
`<target>/agent-memory` does not. Dry-run output must not mention the removed feature. Reinstall
must retain the installer's non-destructive contract: it does not recreate `agent-memory/`, but
it also does not delete a pre-existing consumer-owned directory.

### Current documentation and lint vocabulary

- `README.md`
- `skills/README.md`
- `skills/xia2/README.md`
- `scripts/lint-doc-truth.sh`

The docs must route committed team knowledge solely through `docs/solutions/` and stop claiming
that installation scaffolds agent memory. `agent-memory` must leave `KNOWN_ROOTS` because that
root no longer exists; the existing doc-lint suite is sufficient once the full suite and a live
reference grep are run.

## 4. Historical references

Research, review, solution, and shipped-spec documents under `docs/` and `specs/` contain dated
mentions of `agent-memory`. They are audit records describing what existed when written. Editing
them would falsify history and greatly enlarge the change without affecting runtime behavior.

The removal should therefore guarantee **zero live references** in runtime sources, current
product docs, templates, and tests, while retaining historical references under `docs/` and
`specs/`. The new removal spec itself is necessarily an additional historical mention.

## 5. Recommended removal path

1. Remove `memory: project` from all three bundled agent definitions.
2. Delete the tracked root README and its structural template.
3. Reduce structural initialization from seven files to six and add a negative assertion.
4. Remove install/dry-run claims and make install tests prove the removed directory is not created.
5. Rewrite current docs and lint vocabulary around the single shared committed store,
   `docs/solutions/`.
6. Run targeted tests, a live-surface zero-reference grep, then the full CI-equivalent suite.

This removes the feature without replacing it. Building a sync layer, confidence-decay daemon,
or alternate per-agent memory is out of scope: those would reintroduce the complexity this change
is explicitly removing.
