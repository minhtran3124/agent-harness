# Use the feature-intake skill: scripts/x.sh exits 0 when its input file is missing; it should exit 1.
# 2.1.302 (Claude Code)
# fixture: scripts/x.sh added to the scratch base commit (exits 0 on missing input)
Skill feature-intake
Bash cat scripts/x.sh; ls specs 2>/dev/null
Bash cat .claude/harness-manifest.json | head -80; cat specs/README.md | head -40; ls
Bash cat .claude/skills/feature-intake/references/draft-intent.md; ls .claude/templat
Bash git branch --show-current; git config user.name; git log --oneline | head -3; ls
Bash mkdir -p specs/fix-x-sh-missing-input-exit && cat > specs/fix-x-sh-missing-input
Bash sed -n 60,200p .claude/skills/diagnosing-bugs/SKILL.md; cat .claude/skills/diagn
Bash cd .claude/runtime && python3 run_state.py --help 2>&1 | head -20; cd ../..; sed
Bash S=fix-x-sh-missing-input-exit; cat > specs/$S/SUMMARY.md <<'EOF' # fix-x-sh-miss
Bash S=fix-x-sh-missing-input-exit; python3 .claude/runtime/run_state.py init --slug
Bash S=fix-x-sh-missing-input-exit; python3 .claude/runtime/run_state.py transition -
Bash S=fix-x-sh-missing-input-exit; python3 .claude/runtime/run_state.py transition -
Bash S=fix-x-sh-missing-input-exit; bash -x scripts/x.sh /nonexistent/file 2>&1 | tai
Bash S=fix-x-sh-missing-input-exit; cat > specs/$S/diagnosis.md <<'EOF' # fix-x-sh-mi
Bash sed -n 30,80p .claude/skills/diagnosing-bugs/references/diagnosis-review-prompt.
Agent Diagnosis review
Read specs/fix-x-sh-missing-input-exit/diagnosis.md
Read specs/fix-x-sh-missing-input-exit/SUMMARY.md
Bash S=fix-x-sh-missing-input-exit sed -i 's|^Repro: .*|Repro: `scripts/x.sh /nonexis
Bash S=fix-x-sh-missing-input-exit git add tests/x_sh_test.sh specs/$S/diagnosis.md &
Bash grep -n -i "red.*green\|\`red\`" .claude/rules/auto-correct-scope.md | head -5;
Bash python3 .claude/scripts/run_at_commit.py ea47edb -- bash tests/x_sh_test.sh; ech
Bash S=fix-x-sh-missing-input-exit python3 - <<'EOF' p="specs/fix-x-sh-missing-input-
