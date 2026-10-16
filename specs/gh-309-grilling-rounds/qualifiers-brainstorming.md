# Scope qualifiers — brainstorming

Source: python3 scripts/check_scope_qualifiers.py --base 996f50d --head 4a64270

The script printed `- none` for this range: no condition word was dropped from the step 2 hunk.
The two lines for `any` and `still` record the removed over-probe sentence (design D4). The old
hunk starts at line 22.

- skills/brainstorming/SKILL.md:22 "any" replaced: The tree holds purpose, constraints, success criteria, and boundaries. Approach choice belongs to step 3. Section detail belongs to step 4.
- skills/brainstorming/SKILL.md:22 "still" replaced: Step 2 ends when the frontier is empty and the user confirms a shared understanding.
- skills/brainstorming/SKILL.md:22 "only when" kept: Use a visual artifact only when seeing the answer is materially clearer than reading it.
