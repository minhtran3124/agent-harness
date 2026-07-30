# Simplify-stage shadow evaluation

This corpus measures whether Claude Code's bundled `/simplify` skill is safe and
useful enough to become a conditional branch-level gate. Collection and scoring
are intentionally separate:

- `run_simplify_stage_eval.py` sees `fixture.json`, `base/`, and `candidate/`.
  It never opens `truth.json`.
- `score_simplify_stage_eval.py` reads the hidden truths only after every raw
  transcript and diff has been captured.
- Quality is an absolute gate. Value is not evaluated after any unsafe
  mutation, failed verification, failed final-review check, missing case, or
  artifact-integrity failure.

## Corpus

Positive opportunities cover existing-helper reuse, cross-task duplication,
avoidable materialization, and abstraction altitude. Negative controls cover
required behavior, a public contract, documentation-only work, and already
simple code.

Each fixture is a tiny Git history:

- `base/` becomes the base commit;
- `candidate/` is overlaid and committed as the implementation checkpoint;
- `fixture.json` contains public verification commands;
- `truth.json` contains scorer-only safe outcomes, path boundaries, and value
  expectations.

The candidate runs in a disposable `git worktree` behind a fail-closed macOS
Seatbelt profile. Source checkout, fixture/truth directory, output destination,
and the user's entire home—including `.claude`, `.claude.json`, and all
Keychains—are unreadable. Content reads are limited to the worktree, external
Git metadata, ephemeral runtime, resolved bundled-client directory, and a
bounded set of macOS system/runtime roots. Unrelated content in `/private/tmp`,
`/Users/Shared`, and mounted volumes remains unreadable. Filesystem writes are
limited to the worktree and runtime directory, with the worktree Git pointer
and external Git metadata read-only. Path-bearing environment variables are
removed. There is no prompt-only or unsandboxed candidate fallback.

Authentication is converted to the narrowest process credential before the
sandbox starts. An existing `ANTHROPIC_API_KEY` or
`CLAUDE_CODE_OAUTH_TOKEN` is preferred. Otherwise, macOS `security` streams the
Claude credential directly into `plutil`, and the parent captures only the
extracted OAuth access token—not the aggregate Keychain JSON. Only that token is
passed to Claude. An auth-status preflight must succeed inside the exact same
Seatbelt profile before any run artifact is created. Although the system
`security` executable may start there as normal client machinery, the
read-denied profile prevents it from retrieving the Claude Keychain credential;
a genuine Seatbelt regression probe requires its lookup to fail.

Claude runs with `--safe-mode`, so project/user hooks, plugins, settings, and
local skills cannot replace the bundled behavior while normal OAuth/keychain
authentication, the selected model, built-in tools, and permissions remain
available. The raw verbose `stream-json` must contain exactly one `Skill`
tool-use whose input is `simplify`; zero, repeated, or differently named calls
reject collection. Its tool-use ID must have exactly one matching, non-error
`tool_result`; missing, mismatched, error, and duplicate results also reject
collection. Resolved and symbolic HEAD plus the worktree Git pointer must
remain unchanged.

After Claude exits, the controller stages the complete mutation and captures a
cached binary/rename-aware patch, including untracked and deleted files. The
runner commits the observed mutation inside the disposable repository solely
to obtain stable SHAs and a Git history bundle. The source repository is never
used as the candidate worktree.

## Collection

The runner refuses to overwrite a result or any raw artifact directory. Pin the
exact installed client version. The supplied source SHA must resolve to a commit
and equal the source checkout's current HEAD:

```bash
python3 scripts/run_simplify_stage_eval.py \
  --mode advisory \
  --fixtures evals/skills/simplify-stage/fixtures \
  --output evals/skills/simplify-stage/results/baseline.json \
  --expected-client-version 2.1.220

python3 scripts/run_simplify_stage_eval.py \
  --mode candidate \
  --fixtures evals/skills/simplify-stage/fixtures \
  --output evals/skills/simplify-stage/results/candidate.json \
  --expected-client-version 2.1.220
```

`candidate` invokes the bundled skill and can consume external Claude tokens.
It requires macOS `sandbox-exec` and an authenticated Claude client.
`--safe-mode` skips user workflow customization while retaining normal
OAuth authentication through the injected token. Unit tests substitute a fake
executable and never make an external model call. `advisory` queries the client
version but does not invoke the skill.

Every case records immutable SHA-256-addressed pre, simplify-delta, and post
diffs; a raw Claude transcript; a hashed checks artifact; a Git history bundle
used to cross-check every diff/metadata claim; base/pre/post SHAs; changed
paths; check and review outcomes; elapsed time; and token usage. Even rejected
Skill-invocation evidence is written before the collector fails.

## Scoring

Run quality first:

```bash
python3 scripts/score_simplify_stage_eval.py \
  --compare \
    evals/skills/simplify-stage/results/baseline.json \
    evals/skills/simplify-stage/results/candidate.json \
  --fixtures evals/skills/simplify-stage/fixtures \
  --quality-gate
```

Only after it passes, request the value gate with `--value-gate`. The scorer
validates the complete collection schema, matching source commit and public
fixture digests, artifact hashes, fixture check commands, transcript claims,
raw stream events, check outcomes against the hashed checks artifact, and all
diff metadata against the history bundle. The candidate must improve over
advisory and meet `fixtures/scoring.json`. Smaller diffs never compensate for a
safety failure. Preserve rejected first runs; use a new output name for a later
candidate.

Each collection also records one deterministic input digest over the runner,
scorer, schema, scoring policy, and all public fixture manifests/base/candidate
content. Scoring requires baseline, candidate, and current inputs to have the
same digest, while each case retains its narrower public-fixture digest. Hidden
`truth.json` files remain excluded from collection and from these public-input
digests. Baseline and candidate source SHAs must match, resolve to an existing
commit, and remain ancestors of current HEAD; later evidence/documentation
commits may advance HEAD without invalidating an otherwise current evaluation.
