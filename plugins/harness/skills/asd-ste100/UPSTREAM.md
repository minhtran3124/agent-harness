# Upstream source

This skill is a vendored copy of an upstream skill.

- Source repo: `danyuchn/asd-ste100-skill` on GitHub.
- Commit: `3944283c18`.
- Version: 0.4.0.
- The upstream SKILL.md has a sha256 that starts `39940a0db3d1`.
- The upstream linter (scripts/ste-lint.py in the upstream repo) has a sha256 that starts `32263de1b6b7`.

## Differences from upstream

The vendored copy has these three differences from upstream. There are no other differences.

1. `SKILL.md` frontmatter has one added line: `allowed-tools: Read, Bash(python3 *)`. The harness repo check `scripts/check-allowed-tools.sh` needs this line.
2. Two upstream files are not vendored: README.md and examples/linter-edge-cases.md. The upstream README.md gives install paths for other runtimes. The harness does not ship those paths.
3. `SKILL.md` names the linter as `${CLAUDE_SKILL_DIR}/scripts/ste-lint.py`. Upstream names it as scripts/ste-lint.py. This change is on two lines only. The plugin loader fills in the skill directory, so the path resolves in a consuming repo.

## Re-vendor steps

1. Get the new upstream commit of `danyuchn/asd-ste100-skill`.
2. Copy these upstream files into `skills/asd-ste100/`: SKILL.md, LICENSE, references/writing-rules.md, examples/before-after.md, and scripts/ste-lint.py.
3. Do not copy README.md or examples/linter-edge-cases.md.
4. Apply differences 1 and 3 again.
5. Write the new commit, version, and sha256 prefixes in this file.
6. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/ste-lint.py --selftest`. Make sure that it exits 0.
7. In the harness repo, run `bash scripts/check-allowed-tools.sh` and `bash scripts/lint-doc-truth.sh`. Make sure that each one exits 0.
