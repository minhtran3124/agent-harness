# Draft an intent

Use this when the slug has no SUMMARY and `specs/<slug>/intent.md` is not both `Status: approved`
and committed. Every "ask and stop" below writes no SUMMARY and makes no commit.

1. **intent.md is absent → draft it.** Write it from `templates/INTENT.template.md` without the
   copy comment. `Author:` is the output of `git config user.name`, or `unknown` if it prints
   nothing; `Status: draft`. Fill each section from the chat. Where the chat says nothing,
   propose content and end the line with `(assumed)`; never state a goal the chat does not.
   Append `## Original request` holding the chat request verbatim and in full. Classify the
   draft plus the chat (Steps 2–4 of `../SKILL.md`) without writing SUMMARY. If tiny + high: set
   `Status: approved`, commit (step 3), continue at Step 1 of `../SKILL.md`, and add
   `auto-approved: tiny/high` to `### Intake notes`. Otherwise ask and stop as in step 2.
2. **intent.md exists → never rewrite it from the template and never auto-approve it.** By the
   current message:
   - it approves (`approve`, or "edited, done", even if `Status: approved` is already set): set
     `Status: approved` if needed, commit (step 3), continue at Step 1 of `../SKILL.md`;
   - it asks for changes (even together with "approve"): edit the file, then ask and stop;
   - anything else: ask and stop — show the file and the proposed lane and confidence; ask the
     user to reply `approve`, request changes, or edit the file and say done.
3. **Commit** only intent.md, on the current branch: `git add -- specs/<slug>/intent.md`, then
   `git commit -m "docs(specs): intent for <slug>" -- specs/<slug>/intent.md`, with the subject
   suffix `(auto-approved: tiny/high)` when step 1 approved it. Skip the commit when the file
   already matches HEAD. If a hook refuses the commit, stop and report its output; never bypass.
