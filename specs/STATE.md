# Workflow State

Source of truth for the currently-active spec. Updated by skills and by the `state-breadcrumb.sh` hook.

## Active Spec

- **Slug:** review-chain-benchmark
- **Phase:** shipped  <!-- design | research | plan | implement | review | shipped -->
- **Last skill:** _(none — manual fixture adjudication)_
- **Last action:** review-chain fixtures v3 — fixed intent-gap store bug (#59) + resolved none-deref answer-key contradiction (#58); committed `5fb15c1`, both issues closed.
- **Updated:** 2026-07-15

## Recent Specs

<!-- Populated as specs are created. Keep last 10. -->

| Slug | Created | Last phase | Status |
|---|---|---|---|

## Notes

- Skills update the "Active Spec" block when they start/finish
- `state-breadcrumb.sh` (SessionEnd hook) writes a snapshot here for resumption
- `/session-tracker` reads this file to resume work across sessions
- If the Active Spec block is stale (>7 days without update), treat as idle

## Session End Log

### 2026-06-11T15:24:59Z
- session_id: dfde87b4-0c31-4055-bc09-81b1bc1eeb1c
- exit: 
- last_commit: 9c49ba1 Merge pull request #11 from minhtran3124/test/harness-phase1
- user_turns: 0


### 2026-06-11T15:26:14Z
- session_id: 5ea10468-2498-4b43-b185-b300f3493a25
- exit: 
- last_commit: 9c49ba1 Merge pull request #11 from minhtran3124/test/harness-phase1
- user_turns: 0


### 2026-06-11T15:26:17Z
- session_id: b1437d95-d17f-4a61-894f-533537ea03f9
- exit: 
- last_commit: 9c49ba1 Merge pull request #11 from minhtran3124/test/harness-phase1
- user_turns: 0


### 2026-06-12T01:58:19Z
- session_id: 2601603e-1d2d-406e-a602-f034c2f63521
- exit: 
- last_commit: f7d2d58 feat(harness): add project configuration and signal remapping documentation
- user_turns: 0


### 2026-06-12T01:58:23Z
- session_id: 6a5183a1-b5b3-4d90-8eb3-1fd7b5b69651
- exit: 
- last_commit: f7d2d58 feat(harness): add project configuration and signal remapping documentation
- user_turns: 0


### 2026-06-12T02:29:15Z
- session_id: ed909097-cd7a-41f6-95b4-45334796712d
- exit: 
- last_commit: d76738c chore(harness): record intent-review-stage execution in plan status log
- user_turns: 0


### 2026-06-12T03:42:56Z
- session_id: f6bbf487-294e-4904-9dcc-f52b89dc7794
- exit: 
- last_commit: cd914a3 docs(harness): translate intent-review-stage PLAN + SUMMARY to English
- user_turns: 0


### 2026-06-12T07:04:52Z
- session_id: 88e95876-a935-4067-ba7b-b39e4467065c
- exit: 
- last_commit: cd914a3 docs(harness): translate intent-review-stage PLAN + SUMMARY to English
- user_turns: 0


### 2026-06-12T07:05:07Z
- session_id: 54c39ee1-ec0b-4a69-894c-e3e3fb818fe6
- exit: 
- last_commit: cd914a3 docs(harness): translate intent-review-stage PLAN + SUMMARY to English
- user_turns: 0


### 2026-06-12T09:23:28Z
- session_id: fdda53f6-e823-470c-96e4-aed3da15a8ca
- exit: 
- last_commit: 46ab307 Merge pull request #17 from minhtran3124/feat/enhance-skills
- user_turns: 0


### 2026-06-12T09:23:30Z
- session_id: 485a1313-c877-4d4c-9ae9-b7f7fbbeb5fa
- exit: 
- last_commit: 46ab307 Merge pull request #17 from minhtran3124/feat/enhance-skills
- user_turns: 0


### 2026-06-13T06:22:07Z
- session_id: 5734a09a-3319-44ee-bd35-a44efc84adb1
- exit: 
- last_commit: 46ab307 Merge pull request #17 from minhtran3124/feat/enhance-skills
- user_turns: 0


### 2026-06-13T06:22:23Z
- session_id: b2844d17-0d0d-49a9-b4d3-16c3561849f1
- exit: 
- last_commit: 46ab307 Merge pull request #17 from minhtran3124/feat/enhance-skills
- user_turns: 0


### 2026-06-13T06:26:17Z
- session_id: 0be71a45-be6d-488c-8dc2-2de0dcb81a3a
- exit: 
- last_commit: 46ab307 Merge pull request #17 from minhtran3124/feat/enhance-skills
- user_turns: 0


### 2026-06-13T06:26:24Z
- session_id: 27393b9d-8529-4fe1-9673-5b644d77ab59
- exit: 
- last_commit: 46ab307 Merge pull request #17 from minhtran3124/feat/enhance-skills
- user_turns: 0


### 2026-06-13T06:26:30Z
- session_id: 5f3271e2-e649-48f6-99d0-50b7dfec1d8d
- exit: 
- last_commit: 46ab307 Merge pull request #17 from minhtran3124/feat/enhance-skills
- user_turns: 0


### 2026-06-13T06:26:34Z
- session_id: 948f14a8-75d0-43d7-80ef-bb6855cc1ef6
- exit: 
- last_commit: 46ab307 Merge pull request #17 from minhtran3124/feat/enhance-skills
- user_turns: 0


### 2026-06-13T06:28:32Z
- session_id: 5040b1b8-9e7e-42f5-9cd2-fe8abcf84ce6
- exit: 
- last_commit: 46ab307 Merge pull request #17 from minhtran3124/feat/enhance-skills
- user_turns: 0


### 2026-06-14T04:19:16Z
- session_id: 9aafc1b0-32ed-4b8b-956b-034d751be3ea
- exit: 
- last_commit: 4dd42df feat: harness gap-closure research + Phase 1 (ratchet + drift audit)
- user_turns: 0


### 2026-06-14T04:33:38Z
- session_id: 4ebdc1f9-333d-47a5-a061-71c9a9de1d86
- exit: 
- last_commit: 50f5fec Merge pull request #18 from minhtran3124/feat/harness-gap-closure-phase1
- user_turns: 0


### 2026-06-14T06:14:17Z
- session_id: 0f3e66f0-f530-445b-81a5-44a1de8159a4
- exit: 
- last_commit: 09b74e8 Merge pull request #23 from minhtran3124/feat/compound-harness-learnings
- user_turns: 0


### 2026-06-14T06:20:46Z
- session_id: 63f976bd-c23f-4c9b-a366-7d70a98f2d69
- exit: 
- last_commit: d1ee6f9 docs: reframe README "Why this exists" + fix skill-workflow drift
- user_turns: 0


### 2026-06-14T07:33:25Z
- session_id: a47d5523-5b07-4330-ab71-2cd3ad9b9262
- exit: 
- last_commit: 87046f9 docs(plan): MIN-25 stack-agnostic rules/ — intake + design + research + plan
- user_turns: 0


### 2026-06-15T02:19:12Z
- session_id: 7da8ac49-355d-499a-946f-0193d9788f1c
- exit: 
- last_commit: a87f829 Merge pull request #26 from minhtran3124/feat/stack-profiles
- user_turns: 0


### 2026-06-15T14:46:09Z
- session_id: ce1ff788-e5a5-4a8e-a3cb-c916eb3c5539
- exit: 
- last_commit: a87f829 Merge pull request #26 from minhtran3124/feat/stack-profiles
- user_turns: 0


### 2026-06-17T04:36:05Z
- session_id: 4b6c53c2-9092-43f0-902e-21cf9a77ac12
- exit: 
- last_commit: c85a88a fix(workflow): auto-create feature branch before implementation
- user_turns: 0


### 2026-06-17T04:46:18Z
- session_id: 17e51233-52d8-40e7-ac49-8ee2307c74d7
- exit: 
- last_commit: f349937 feat(deploy-harness): enhance settings.json merging logic
- user_turns: 0


### 2026-06-17T08:37:18Z
- session_id: 7d6eed75-a9a3-46a1-a027-d1583feffe95
- exit: 
- last_commit: 0f2b9cc fix(deploy-harness): back up invalid .claude/settings.json instead of overwriting
- user_turns: 0


### 2026-06-17T09:50:45Z
- session_id: 12036cfb-95cc-4914-8de9-7b42eb357930
- exit: 
- last_commit: 9f668a0 Merge pull request #28 from minhtran3124/fix/deploy-merge-invalid-json
- user_turns: 0


### 2026-06-17T09:54:03Z
- session_id: 99af7943-bd61-4955-b28d-0a18264d44ca
- exit: 
- last_commit: a837b65 Merge pull request #29 from minhtran3124/docs/worktree-branch-naming
- user_turns: 0


### 2026-06-17T10:03:45Z
- session_id: fc400835-b754-4b7a-a766-62b012e9f1d8
- exit: 
- last_commit: a837b65 Merge pull request #29 from minhtran3124/docs/worktree-branch-naming
- user_turns: 0


### 2026-06-17T10:21:53Z
- session_id: c0b41201-0489-4207-982d-75d1f97a5dc0
- exit: 
- last_commit: a837b65 Merge pull request #29 from minhtran3124/docs/worktree-branch-naming
- user_turns: 0


### 2026-06-19T10:47:38Z
- session_id: bc868a64-644a-425e-8ecc-27e69c5f2667
- exit: 
- last_commit: b5a4e8f fix(worktree): deploy harness into new worktrees via deploy-harness.sh --target
- user_turns: 0


### 2026-07-04T13:47:48Z
- session_id: 5453e6d8-2c5e-42c6-8160-9bbe49df7011
- exit: 
- last_commit: cf6aedc docs(v03): mark Wave 4 merged (PR #42) + close out Wave 6 REQ.md/PR_TEMPLATE.md note
- user_turns: 0


### 2026-07-04T13:47:55Z
- session_id: 6b07626c-9492-407f-81ae-83145837f2b7
- exit: 
- last_commit: cf6aedc docs(v03): mark Wave 4 merged (PR #42) + close out Wave 6 REQ.md/PR_TEMPLATE.md note
- user_turns: 0


### 2026-07-05T01:10:01Z
- session_id: a3dadc73-9cb1-4229-ad16-0dd4ad8bdca9
- exit: 
- last_commit: da10684 Merge pull request #43 from minhtran3124/chore/bookkeeping-42
- user_turns: 0


### 2026-07-05T13:32:36Z
- session_id: f2d6aebd-1406-45ea-af53-7c37b39994c3
- exit: 
- last_commit: da10684 Merge pull request #43 from minhtran3124/chore/bookkeeping-42
- user_turns: 0


### 2026-07-08T03:11:21Z
- session_id: 968b30a6-b244-4279-b108-9e8e3c2e8786
- exit: 
- last_commit: da10684 Merge pull request #43 from minhtran3124/chore/bookkeeping-42
- user_turns: 0


### 2026-07-08T03:11:40Z
- session_id: 15dbef00-2685-431c-b5f9-772e409db2b2
- exit: 
- last_commit: da10684 Merge pull request #43 from minhtran3124/chore/bookkeeping-42
- user_turns: 0


### 2026-07-08T03:12:02Z
- session_id: f9ff5d1a-6365-4012-a8cc-9ec95030d2a1
- exit: 
- last_commit: da10684 Merge pull request #43 from minhtran3124/chore/bookkeeping-42
- user_turns: 0


### 2026-07-08T03:16:16Z
- session_id: 0215681c-2b04-4293-8040-a6fd812cafc0
- exit: 
- last_commit: 5033c4e chore(state): update session logs with new entries and last commits
- user_turns: 0


### 2026-07-13T04:20:10Z
- session_id: a42ff726-922e-42dd-b9bb-e93eba0b48ac
- exit: 
- last_commit: d424183 Merge pull request #49 from minhtran3124/chore/bookkeeping-48
- user_turns: 0


### 2026-07-13T08:52:37Z
- session_id: 4d94a817-911a-4863-ba31-a8e36de0276c
- exit: 
- last_commit: 46e3260 fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback
- user_turns: 0


### 2026-07-13T08:52:37Z
- session_id: 1649c77a-2a2b-4a8a-b5f5-ea27ccd9f065
- exit: 
- last_commit: 46e3260 fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback
- user_turns: 0


### 2026-07-13T08:52:37Z
- session_id: 47f77ba5-50ee-40d3-a240-4d8f7bfe99ec
- exit: 
- last_commit: 46e3260 fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback
- user_turns: 0


### 2026-07-13T08:52:37Z
- session_id: fec3e153-9e9e-408a-a598-8720f3937791
- exit: 

### 2026-07-13T08:52:37Z
- session_id: 8a0761b6-cd01-42ff-89ae-9fcacbce8c86
- exit: 
- last_commit: 46e3260 fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback
- user_turns: 0

- last_commit: 46e3260 fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback
- user_turns: 0


### 2026-07-13T08:52:37Z
- session_id: 31192efe-db37-4eeb-8ccf-524c6a98d9ea
- exit: 
- last_commit: 46e3260 fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback
- user_turns: 0


### 2026-07-13T08:52:37Z
- session_id: b1ed0146-0751-4498-9adf-b94bfd9e8a80
- exit: 
- last_commit: 46e3260 fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback
- user_turns: 0


### 2026-07-13T08:52:37Z
- session_id: 948b5e3c-9464-4a09-88b1-586e26a81592
- exit: 
- last_commit: 46e3260 fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback
- user_turns: 0


### 2026-07-13T08:53:00Z
- session_id: a5f50f28-c2ce-469a-a7f5-b1541565a332
- exit: 
- last_commit: 46e3260 fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback
- user_turns: 0


### 2026-07-13T08:54:53Z
- session_id: 48c09fe2-e229-4273-b4d8-93b3173f245f
- exit: 
- last_commit: a2139c7 docs(claude-md): use plain path refs instead of @-imports; record session breadcrumbs
- user_turns: 0


### 2026-07-13T09:21:29Z
- session_id: d9e5b3e2-e3cf-4f1e-950c-f378f273c061
- exit: 
- last_commit: 7a30639 fix(summary): make the regression-lock Verify row machine-re-runnable
- user_turns: 0


### 2026-07-13T11:31:22Z
- session_id: 7f2e13b9-7860-4e18-bd85-92226c259c79
- exit: 
- last_commit: 57cde1e Merge remote-tracking branch 'github/v2' into feat/correctness-review-altitude
- user_turns: 0


### 2026-07-14T02:17:47Z
- session_id: bf3cf3e6-9a2a-4f5b-9be5-7aea138e4364
- exit: 
- last_commit: 839f040 bench(review-chain): run SCORE end-to-end — 0 false positives reach the fix-loop
- user_turns: 0


### 2026-07-15T05:04:46Z
- session_id: ed6d21ff-b011-429d-bbd3-fcab786fc5f9
- exit: 
- last_commit: 8dfccc8 Merge remote-tracking branch 'github/v2' into feat/correctness-review-altitude
- user_turns: 0


### 2026-07-15T05:08:44Z
- session_id: 64896fd6-1096-4248-82f8-de0b70a69af4
- exit: 
- last_commit: cebdcaf Merge pull request #62 from minhtran3124/chore/bookkeeping-51
- user_turns: 0


### 2026-07-15T05:11:55Z
- session_id: dd49f675-5c8b-4005-a16e-618ff6982009
- exit: 
- last_commit: 2b3f73e chore: gitignore CLAUDE.local.md; session breadcrumb
- user_turns: 0


### 2026-07-15T06:20:25Z
- session_id: 28b12f6b-3a36-4556-8b0a-fb922d905763
- exit: 
- last_commit: 2b3f73e chore: gitignore CLAUDE.local.md; session breadcrumb
- user_turns: 0


### 2026-07-15T06:36:35Z
- session_id: 82bb1ab3-644b-4767-ab61-f826ffb51296
- exit: 
- last_commit: 3267c72 docs(specs): intake + design + plan for plan-at-a-glance (#54)
- user_turns: 0


### 2026-07-15T07:33:30Z
- session_id: 7bb69cb3-0a86-437d-81b5-7a048ddfdf83
- exit: 
- last_commit: 3267c72 docs(specs): intake + design + plan for plan-at-a-glance (#54)
- user_turns: 0

