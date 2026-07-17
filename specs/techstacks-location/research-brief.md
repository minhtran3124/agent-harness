# Thinking — should `techstacks/` live inside `.claude/` instead of at repo root?

Requested 2026-07-17: move `techstacks/` into `.claude/` after install, so it visibly belongs to the AI/skill domain and people understand what it is. Thinking only — no change made. Facts verified on the current tree.

## The core tension (one hard constraint decides most of it)

`.claude/` is **gitignored** (`.gitignore:26`) in both this meta-repo and every consumer (README: "lives entirely in a gitignored `.claude/`"). It is a **derived, harness-managed** tree: `deploy-harness.sh` re-syncs it from source and — since this session's prune fix — **auto-prunes** entries the harness deployed. Everything in `.claude/` is reproducible from the harness source; nothing there is meant to be irreplaceable.

`techstacks/` is the opposite: **project-authored content** (the team's real architecture / guidelines / conventions). It must be **committed to git, versioned, shared across the team, survive a fresh clone, and survive a harness re-sync untouched.**

Put project-authored, must-be-committed content into a gitignored, auto-managed tree and you get a direct conflict: the stack profile is **lost from version control** (not shared, gone on clone) unless `.claude/techstacks/` is specially un-ignored.

## What `techstacks/` actually is (the ownership test)

"Belongs to the AI" is half-true: techstacks/ is **authored by the project, consumed by the AI**. By *who writes it + is it committed*, it is the same category as its current root siblings:

| Folder | Authored by | Read by | Committed? | Location |
|---|---|---|---|---|
| `specs/` | project | AI + humans | yes | root |
| `docs/solutions/` | both | both | yes | root |
| `agent-memory/` | AI/project | AI | yes | root |
| **`techstacks/`** | **project** | **AI** | **must be yes** | **root (now)** |
| `skills/ hooks/ rules/` | harness | AI | no (derived) | `.claude/` |
| `settings.local.json` | user | Claude Code | no (personal) | `.claude/` |

The `.claude/` residents are either harness-derived (reproducible) or deliberately personal/ephemeral (`settings.local.json`). techstacks/ is neither — it is shared project content, which is exactly why specs/ and docs/solutions/ sit at root and are committed.

## Options

**A — Keep at root; strengthen the ownership *signal* (recommended).** Achieve the clarity the user wants through documentation, not relocation: the `techstacks/README.md` already says "read by the AI agents"; make the auto-loaded `rules/architecture.md`+`guidelines.md` pointers state plainly "the AI agents read this folder"; optionally add a one-line banner at the top of `techstacks/README.md`. Zero mechanism risk; keeps techstacks/ committed, versioned, re-sync-safe, and consistent with specs/ + docs/solutions/.

**B — Move into `.claude/techstacks/` + un-gitignore that subpath.** `.gitignore` becomes `.claude/*` + `!.claude/techstacks/` (you cannot re-include a path whose parent dir is fully ignored — needs the `/*` form; fragile, easy to mis-set). Then techstacks/ is physically in the AI zone AND committed. Costs: (1) breaks the invariant "everything in `.claude/` is harness-derived and reproducible" — now it holds irreplaceable project content; (2) `deploy-harness` copy_dir/prune + the protected-file set must learn to never touch `.claude/techstacks/` (new coupling, more surface for the exact data-loss class we just hardened against); (3) a fragile git-ignore negation that a consumer can silently break, losing their stack profile from git. Semantic gain, real fragility.

**C — Root content + a `.claude/` reference.** Real folder stays committed at root; add a `.claude/rules/` note (or a symlink) so the AI zone visibly points at it. Symlinks are not portable (Windows, git); a note is just option A by another name.

## Recommendation

**Option A.** The user's instinct — "make it clear it belongs to the AI domain" — is a *comprehension* goal, and comprehension is better served by naming + docs than by a physical move that fights a hard constraint. Moving project-authored, must-be-committed content into the gitignored, auto-pruned `.claude/` tree trades a clear versioning/re-sync guarantee for a visual grouping, and adds coupling to the very deletion path we just made safe. Keep techstacks/ at root (with specs/ and docs/solutions/), and make its AI-ownership explicit in the README and the auto-loaded pointers.

If the owner still wants the physical `.claude/` location, Option B is the way — but only with: the `.claude/*` + `!.claude/techstacks/` ignore form, techstacks/ added to `deploy-harness`'s never-touch protected set, and a test proving a re-sync never prunes/overwrites it.

## Open question for the owner

Is the goal **comprehension** (people should understand techstacks/ is AI-consumed) or a hard requirement that it **physically sit under `.claude/`**? If the former → Option A. If the latter → Option B with the three guards above.
