# Draft an intent

Use this when the slug has no SUMMARY and `specs/<slug>/intent.md` is not both `Status: approved`
and identical to its last commit. Every "ask and stop" below writes no SUMMARY and makes no commit.

A message that only approves (`approve`, `done`) or asks to change the draft just shown answers a
pending draft. Never derive a slug from such a message. Use the first match in this order:

- the slug the message names
- else, the draft this conversation showed
- else, for `approve`/`done` only, the only slug with an intent.md and no SUMMARY

If none or several match, ask. Any other request starts its own slug.

1. **intent.md is absent → draft it.** Write it from `templates/INTENT.template.md` without the
   copy comment. Set `Author:` to the output of `git config user.name`. If that command prints
   nothing, set `Author:` to `unknown`. Set `Status: draft`. Fill each section from the chat.
   Where the chat says nothing, propose content and end the line with `(assumed)`. Never state a
   goal that the chat does not state. Append `## Original request` holding the chat request
   verbatim and in full. Classify the draft plus the chat (Steps 2–4 of `../SKILL.md`) without
   writing SUMMARY. Then act on the result:
   - **tiny + high:** set `Status: approved`, commit (step 3, with the auto-approve suffix), and
     continue at Step 1 of `../SKILL.md`. On this path, before Step 6 writes SUMMARY, check that
     classification. If it is not tiny + high, set `Status: draft`, commit (no suffix), and ask
     and stop. If it is tiny + high, SUMMARY's `### Intake notes` gets `auto-approved: tiny/high`.
   - **Any other result:** ask and stop as in step 2's last bullet.
2. **intent.md exists → never rewrite it from the template and never auto-approve it.** By the
   current message:
   - **It approves** (`approve`, or "edited, done", even if `Status: approved` is already set):
     set `Status: approved` if needed. Commit (step 3). Continue at Step 1 of `../SKILL.md`.
   - **It asks for changes** (even together with "approve"): edit the file. Append the message
     verbatim to `## Original request`, and add the section if it is missing. Then ask and stop.
   - **Anything else:** ask and stop. Show the file and the proposed lane and confidence. Ask the
     user to reply `approve`, request changes, or edit the file and say done.
3. **Commit** only intent.md.
   - If `git branch --show-current` prints `main` or `master`, first run
     `git switch -c <type>/<slug>` and stay on that branch. The shared branch then gets no
     commit. The rest of intake runs on that branch. The tiny route keeps it as its branch, and
     `using-git-worktrees` takes it over.
   - Run `git add -- specs/<slug>/intent.md`, then
     `git commit -m "docs(specs): intent for <slug>" -- specs/<slug>/intent.md`.
   - The auto-approve suffix appends ` (auto-approved: tiny/high)` to that subject.
   - If git reports nothing to commit, continue.
   - If the commit fails (a hook or git), stop, report its output, and say that intent.md is still
     staged. If it fails on the auto-approve path, also set `Status: draft` again.

Where an approved intent.md differs from its own `## Original request`, the approved file wins.
The user approved it, so this is not a chat conflict under Step 4 of `../SKILL.md`.
