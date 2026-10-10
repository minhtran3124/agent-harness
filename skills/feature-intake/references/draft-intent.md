# Draft an intent

Use this when the slug has no SUMMARY and `specs/<slug>/intent.md` is not both `Status: approved`
and identical to its last commit. Every "ask and stop" below writes no SUMMARY and makes no commit.

A reply (`approve`, `done`, or a requested change) answers a pending draft, so never derive a slug
from it: use the slug it names, else the draft this conversation showed, else the only slug with an
intent.md and no SUMMARY. If none or several match, ask.

1. **intent.md is absent → draft it.** Write it from `templates/INTENT.template.md` without the
   copy comment. `Author:` is the output of `git config user.name`, or `unknown` if it prints
   nothing; `Status: draft`. Fill each section from the chat. Where the chat says nothing,
   propose content and end the line with `(assumed)`; never state a goal the chat does not.
   Append `## Original request` holding the chat request verbatim and in full. Classify the
   draft plus the chat (Steps 2–4 of `../SKILL.md`) without writing SUMMARY. If tiny + high: set
   `Status: approved`, commit (step 3), and continue at Step 1 of `../SKILL.md`. If Step 1 then
   still classifies tiny + high, SUMMARY's `### Intake notes` gets `auto-approved: tiny/high`;
   otherwise set `Status: draft`, commit, and ask and stop. Otherwise ask and stop as in step 2's
   last bullet.
2. **intent.md exists → never rewrite it from the template and never auto-approve it.** By the
   current message:
   - it approves (`approve`, or "edited, done", even if `Status: approved` is already set): set
     `Status: approved` if needed, commit (step 3), continue at Step 1 of `../SKILL.md`;
   - it asks for changes (even together with "approve"): edit the file, append the message
     verbatim to `## Original request` (add the section if missing), then ask and stop;
   - anything else: if the message states a request, append it the same way; then ask and stop —
     show the file and the proposed lane and confidence; ask the user to reply `approve`, request
     changes, or edit the file and say done.
3. **Commit** only intent.md. If `git branch --show-current` prints a shared branch (`main` or
   `master`), first run `git switch -c <type>/<slug>`; the lane's branch or worktree step then
   builds on that branch. Run `git add -- specs/<slug>/intent.md`, then
   `git commit -m "docs(specs): intent for <slug>" -- specs/<slug>/intent.md`, with the subject
   suffix `(auto-approved: tiny/high)` when step 1 approved it. If git reports nothing to commit,
   continue. If the commit fails (a hook or git), stop and report its output, say that intent.md
   is still staged, and on the auto-approve path set `Status: draft` again.

Where an approved intent.md differs from its own `## Original request`, the approved file wins:
the user approved it, so this is not a chat conflict under Step 4 of `../SKILL.md`.
