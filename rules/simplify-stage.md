# Claude Code `/simplify` stage policy

This file is the human-readable authority for deciding whether the branch-level cleanup stage is
required. `scripts/check_claude_simplify.py` is the executable form of the same policy. The stage
uses Claude Code's bundled `/simplify`; the repository must not define a skill with that name.

## Capability contract

The cleanup-only behavior is supported by Claude Code **2.1.154 or newer**. The controller records
the client version and passes it to the checker. A required case fails closed when the client is
missing, its version is malformed, or it is below that floor. An advisory or excluded case may
continue while recording the capability status.

> The bold sentence above is the single authoritative statement of the floor — it is the one
> `check_simplify_adoption.py` check A anchors against `MINIMUM_VERSION`. Do not restate the number
> elsewhere in this file; a second spelling can drift out of sync without the drift test noticing.

The client version is not permission to invoke the stage by itself. The controller must also
confirm that the bundled Skill invocation is available before running it; later workflow gates own
that runtime check.

## Explicit inputs

Policy resolution must receive all of these values:

- the intake lane: `tiny`, `normal`, or `high-risk`;
- the explicitly resolved base and pre-simplify HEAD;
- the changed repository-relative paths for that exact range;
- `git diff --numstat` for that exact range;
- the Claude Code version, when available.

The checker never guesses a default branch or reads the current checkout. Its machine-readable
target is exactly `<base>..<head>`. Base and HEAD must each be a resolved canonical lowercase
40-hex commit SHA and must be distinct; uppercase spellings, symbolic names, abbreviated SHAs, and
other unresolved revision expressions are invalid.

## Reviewable scope

Unknown paths are reviewable by default. Only these bounded categories are excluded:

- documentation (`docs/`, Markdown/AsciiDoc/reStructuredText extensions, README/LICENSE/NOTICE and
  changelog files);
- `specs/` bookkeeping;
- stored evaluation results or raw transcripts under `evals/`;
- vendored dependencies (`vendor/`, `third_party/`, or `node_modules/`);
- generated and derived output, including `.claude/`, root-level `build/`, `out/`, `dist/`, and
  `coverage/`, unambiguously generated paths/files, minified files, source maps, lockfiles, and
  `PLAN.html`. Ambiguous nested names such as `src/build/`, and root singleton files named
  `build`, `out`, `dist`, or `coverage`, remain reviewable.

A directory-name exclusion applies only when that authority token has a child component in the
changed file path. A singleton root file named `docs`, `specs`, `vendor`, `.claude`, or another
directory authority remains reviewable.

Markdown under `skills/`, `agents/`, or `rules/` is **program text, not documentation**, and stays
reviewable. In a prompt-driven harness those files are what the agent executes, so editing one
changes runtime behavior; excluding them would drop the highest-risk change class out of the stage
entirely. Two exceptions stay excluded because they are prose *about* the surface rather than
instructions an agent runs: `README.md` at any depth, and any `*.template.md`. Unlike the exclusion
authorities, these three roots match case-insensitively — folding case here only ever grows
coverage, so it is the safe direction. A repository without those directories never matches, so the
rule stays portable.

Directory authorities match exact-case. On a case-sensitive filesystem `Docs/`, `Specs/`, and
`Evals/Raw/` are different directories from their lowercase spellings, so a case variant stays
reviewable rather than inheriting the exclusion. File names and suffixes still match
case-insensitively: `README`, `.MD`, and `PLAN.html` are the same file however they are spelled.

Large excluded files never contribute to the source-line threshold. A binary reviewable change is
still reviewable even though Git reports no numeric line count. Malformed numstat, or numstat that
omits a reviewable path, is invalid input rather than evidence for an advisory decision.

Path evidence is exact and uses canonical repository-relative POSIX spelling. The checker does not
trim whitespace, convert backslashes, collapse `./`, or collapse repeated separators. Because the
newline-delimited CLI files cannot safely disambiguate surrounding whitespace or backslash-bearing
POSIX filenames, those spellings fail closed. Internal spaces are preserved. Changed-path and
numstat path sets must agree exactly after Git rename notation is resolved.

## Signal policy

Count additions plus deletions for reviewable paths:

| Scope | Required | Reason |
| --- | --- | --- |
| Normal or high-risk with any reviewable path | yes | `non_tiny_source_change` |
| Tiny with more than 150 changed reviewable lines | yes | `oversized_tiny_source_change` |
| Tiny with at most 150 changed reviewable lines | no (advisory) | `tiny_source_change` |
| No changed paths | no | `no_changes` |
| One excluded category only | no | category-specific `*_only` reason |
| Multiple excluded categories only | no | `excluded_only` |

The complete bounded reason set is defined by `POLICY_REASONS` in the executable checker.
Required decisions are valid only when capability status is `supported`. The checker exits nonzero
and emits `required_capability_unavailable` for a required decision without that capability.

## Command contract

Callers write newline-delimited changed paths and raw numstat to files. **Both producer commands
must disable Git's path quoting**, or any non-ASCII filename arrives as `"caf\303\251.py"` and the
checker rejects the backslash spelling as invalid input — a valid branch would be unable to resolve
a decision at all, with the error blaming the caller. `--name-only` has `-z`; `--numstat` does not,
so `-c core.quotePath=false` is the spelling that works for both:

```bash
git -c core.quotePath=false diff --name-only "$BASE_SHA..$HEAD_SHA" > "$CHANGED_PATHS_FILE"
git -c core.quotePath=false diff --numstat   "$BASE_SHA..$HEAD_SHA" > "$NUMSTAT_FILE"

python3 scripts/check_claude_simplify.py \
  --lane normal \
  --base "$BASE_SHA" \
  --head "$HEAD_SHA" \
  --changed-paths-file "$CHANGED_PATHS_FILE" \
  --numstat-file "$NUMSTAT_FILE" \
  --claude-code-version "$CLAUDE_CODE_VERSION"
```

Exit 0 means the policy decision is usable. Exit 1 means simplify is required but the client
capability is unavailable. Invalid or implicit inputs exit 2. Standard output is one JSON object
containing `required`, bounded `reason`, `capability`, exact `target`, reviewable/excluded paths,
changed source line count, and `ok`.
