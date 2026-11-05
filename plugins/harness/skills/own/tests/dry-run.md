# Own dry run (worked examples)

This file is a worked example, not a recorded session. No human was interviewed. It shows how
the rules in `skills/own/SKILL.md` change a grilling round and a brainstorm. A reviewer checks the
rules against these outcomes.

## Grill mode: `/harness:own grill #900`

Issue #900: "Add a CSV export to the reports page". The design tree is the same as in
`skills/grilling/tests/dry-run.md` (10 decisions, D1 to D10).

### Big decisions

| Decision | Why it is big |
|---|---|
| D1 Who can export? | Security: it decides who can take data out |
| D4 Delivery: download or email? | Hard to reverse: email needs a job queue and mail setup |
| D8 Large export behavior? | Behavior that users see, and low confidence (no usage data) |

The agent says: "I will ask you first on: D1 who can export, D4 delivery, D8 large exports."
The owner replies: "OK."

### D1 through the protocol

1. Agent: "Who should be able to export a report, and why?"
2. Owner: "Everyone who can see the report. If they can read it, they can copy it anyway."
3. Agent: "My recommendation is admin and member, not viewer. The roles in `lib/auth/roles.ts`
   give viewer read-only access to dashboards shared with external clients. A bulk export of a
   shared client dashboard leaks more than a screen copy. This differs from your answer on
   viewer."
4. Counter-argument against the agent's own recommendation: viewers can read the data already,
   so they will copy it by hand, and a role split is one more permission to maintain.
5. `AskUserQuestion`: "everyone" (the owner's answer, listed first) / "admin and member" / more
   facts. No option is marked as recommended. The owner takes "admin and member".

D4 and D8 follow the same steps. D2, D3, D5, D6, D7, D9 and D10 are small. They go in rounds as
in the grilling dry run, each with a recommended answer.

### Entry in `decision.md` (excerpt: Context, Options, Why, Consequences and Reverse are left out)

```text
### D1 Admin and member can export; viewer cannot
- Stage: grilling · Confidence: high · needs_review: no · owner_confirmed: yes
- Decision: admin and member
- Owner first answer: everyone who can see the report
- Agent recommendation: admin and member, not viewer
- Counter-argument: viewers can read the data already and will copy it by hand
```

### Output list

```text
Big decisions:
- D1 who can export: you said everyone, final admin and member (changed)
- D4 delivery: you said direct download, final direct download (kept)
- D8 large exports: you said cap at 100,000 rows, final refuse above 100,000 rows (kept)
```

## Brainstorm mode: `/harness:own brainstorm "store user sessions for the new login"`

1. The agent maps the open choices: storage, token lifetime, multi-device login, cookie name.
   Big: storage (data and running cost), multi-device (behavior that users see). Small: token
   lifetime (one config value), cookie name.
2. Sketch. The owner writes: "Put sessions in Redis, it is already running for the cache."
3. Approaches. A: Redis. B: a Postgres table. C: signed stateless tokens. The agent says A is
   closest to the sketch. The sketch did not cover eviction. The cache Redis uses `allkeys-lru`,
   so under memory pressure it can drop live sessions.
4. The sketch is the owner's first answer on the approach, so the agent does not ask again. The
   agent recommends B. The counter-argument against B is one more query per request. The final
   question lists A first, then B. The owner takes B.
5. Assumptions that would break this design:
   - "More than 2,000 requests per second hit the session table." Check: the current request
     rate in the metrics.
   - "Sessions must survive a database failover." Check: ask the platform owner.
6. Teach-back. The owner writes: "B, because sessions must not vanish and we need to list
   sessions per user. Redis loses on eviction." The agent names one gap: the reason against C
   (no way to revoke a token) is missing. No grade.
7. `specs/<slug>/design.md` gets `## Owner reasoning` with the teach-back text and
   `## Assumptions that would break this design` with the two items.
