# Draft an intent

Use this when the slug has no SUMMARY and `specs/<slug>/intent.md` is not both `Status: approved`
and identical to its last commit. Every "ask and stop" below writes no SUMMARY and makes no commit.

A message that only approves (`approve`, `done`) or asks to change the draft just shown answers a
pending draft, so never derive a slug from it: use the slug it names, else the draft this
conversation showed, else (for `approve`/`done` only) the only slug with an intent.md and no
SUMMARY. If none or several match, ask. Any other request starts its own slug.

1. **intent.md is absent → draft it.** Write it from `templates/INTENT.template.md` without the
   copy comment. `Author:` is the output of `git config user.name`, or `unknown` if it prints
   nothing; `Status: draft`. Fill each section from the chat. Where the chat says nothing,
   propose content and end the line with `(assumed)`; never state a goal the chat does not.
   Append `## Original request` holding the chat request verbatim and in full. Classify the
   draft plus the chat (Steps 2–4 of `../SKILL.md`) without writing SUMMARY. If tiny + high: set
   `Status: approved`, commit (step 3, with the auto-approve suffix), and continue at Step 1 of
   `../SKILL.md`; before Step 6 writes SUMMARY, if that classification is not tiny + high, set
   `Status: draft`, commit (no suffix), and ask and stop — else SUMMARY's `### Intake notes` gets
   `auto-approved: tiny/high`. Otherwise ask and stop as in step 2's last bullet.
2. **intent.md exists → never rewrite it from the template and never auto-approve it.** By the
   current message:
   - it approves (`approve`, or "edited, done", even if `Status: approved` is already set): set
     `Status: approved` if needed, commit (step 3), continue at Step 1 of `../SKILL.md`;
   - it asks for changes (even together with "approve"): edit the file, append the message
     verbatim to `## Original request` (add the section if missing), then ask and stop;
   - anything else: ask and stop — show the file and the proposed lane and confidence; ask the
     user to reply `approve`, request changes, or edit the file and say done.
3. **Commit** only intent.md. If `git branch --show-current` prints `main` or `master`, first run
   `git switch -c <type>/<slug>` and stay on it: the shared branch gets no commit, the rest of
   intake runs there, the tiny route keeps it as its branch, and `using-git-worktrees` takes it
   over. Run `git add -- specs/<slug>/intent.md`, then
   `git commit -m "docs(specs): intent for <slug>" -- specs/<slug>/intent.md`; the auto-approve
   suffix appends ` (auto-approved: tiny/high)` to that subject. If git reports nothing to commit,
   continue. If the commit fails (a hook or git), stop and report its output, say that intent.md
   is still staged, and on the auto-approve path set `Status: draft` again.

Where an approved intent.md differs from its own `## Original request`, the approved file wins:
the user approved it, so this is not a chat conflict under Step 4 of `../SKILL.md`.
