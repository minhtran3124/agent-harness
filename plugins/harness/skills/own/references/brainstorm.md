# Brainstorm mode: extra steps

These steps add to `brainstorming` and to the protocol in `skills/own/SKILL.md`.

1. Sketch. Before you present the approaches, ask the owner to sketch their own approach in 2-3
   sentences. Then wait.
2. Approaches. When you present them, say which one is closest to the sketch. Name what the
   sketch did not cover. The choice of approach is a big decision, and the sketch is the owner's
   first answer to it. Do not ask the owner to choose an approach again. Go on from protocol
   step 2.
3. Breaking assumptions. After the choice, write 2-3 assumptions that would make the design
   wrong if they were true. Give each one a way to check it.
4. Teach-back. Ask the owner to explain in 3-4 sentences why the chosen approach wins. Ask also
   why the main alternative loses. The owner can answer "skip". Name only the gaps. Do not grade
   and do not block.
5. Design file. Write `specs/<slug>/design.md` at every depth, from the template that
   `brainstorming` names. Add two sections:
   - `## Owner reasoning`: the teach-back text, or "skipped".
   - `## Assumptions that would break this design`: the items from step 3.

   The ADR stays depth L only, as `brainstorming` says.
