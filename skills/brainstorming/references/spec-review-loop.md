# Design review and user approval

After writing `specs/<slug>/design.md`:

1. Dispatch `spec-document-reviewer-prompt.md` with the design path, the design text, and the
   absolute path of `references/design-template.md` as `[TEMPLATE_FILE_PATH]`, never the parent
   session history.
2. Fix reported issues and repeat until approved. After five iterations, stop, list the
   unresolved reviewer issues, and ask the user for direction.
3. Ask the user to review the written spec. If they request changes, update it and repeat the
   review loop. Do not invoke xia2 until they approve.
