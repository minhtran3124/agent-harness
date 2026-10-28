# Grilling dry run (worked example)

This file is a worked example, not a recorded session. No human was interviewed. It shows that the
rules in `skills/grilling/SKILL.md` produce a close in 3 rounds or fewer with one
"Confirmed decisions" comment. A reviewer checks the rules against this outcome.

## Sample ticket

Issue #900: "Add a CSV export to the reports page". Mode: interactive.

## Design tree (10 open decisions)

```
D1 Who can export?                    (root)
D2 Which reports?                     (root)
D3 Row limit?                         (root)
D4 Delivery: download or email?       (root)
D5 Column set and order?              below D2
D6 Date format?                       (root)
D7 Filename pattern?                  (root)
D8 Large export behavior?             below D3 and D4
D9 Audit log of exports?              below D1
D10 Rate limit per user?              below D1 and D3
```

The tree has 2 levels and 10 decisions. It is not deep, so no advisor call.

## Facts the agent found itself (not asked)

- The reports page is `app/reports/page.tsx`. The reports table has 4 report types.
- Roles exist as `admin`, `member`, `viewer` in `lib/auth/roles.ts`.
- The API already pages at 1000 rows.

## Round 1 (frontier: D1, D2, D3, D4, D6, D7)

1. Who can export? Recommended: admin and member, not viewer. Yes?
2. Which reports? Recommended: all 4 report types. Yes?
3. Row limit? Recommended: 50,000 rows. Yes?
4. Delivery? Recommended: direct download. Yes?
5. Date format? Recommended: ISO 8601 (`2026-10-28`). Yes?
6. Filename? Recommended: `<report>-<YYYY-MM-DD>.csv`. Yes?

Owner reply: "1 yes, 2 yes, 3 make it 100,000, 4 yes, 5 yes, 6 yes."

## Round 2 (frontier: D5, D8, D9, D10)

D5 opens after D2. D8 opens after D3 and D4. D9 and D10 open after D1 and D3.

7. Columns? Recommended: the columns shown on screen, in screen order. Yes?
8. Above 100,000 rows? Recommended: refuse and show a message to narrow the filter. Yes?
9. Audit log? Recommended: log user, report, row count, time. Yes?
10. Rate limit? Recommended: 5 exports per user per hour. Yes?

Owner reply: "yes to all."

The frontier is now empty. The "yes" to round 2 counts as confirmation, so there is no round 3.
Result: 2 rounds, 10 decisions, 0 assumptions.

## Evasive case (not hit here)

If the owner had answered question 10 with "not sure" in round 2 and again in round 3, then after
two rounds the skill records "5 exports per user per hour" with `needs_review: true` and moves on.

## Resulting comment (posted with `gh issue comment 900 --body-file ...`)

```
## Confirmed decisions

1. Who can export: admin and member. Viewer cannot.
2. Reports: all 4 report types.
3. Row limit: 100,000 rows.
4. Delivery: direct download.
5. Columns: those shown on screen, in screen order.
6. Date format: ISO 8601.
7. Filename: <report>-<YYYY-MM-DD>.csv
8. Above the limit: refuse and ask the user to narrow the filter.
9. Audit log: user, report, row count, time.
10. Rate limit: 5 exports per user per hour.

Assumptions (needs_review): none.
```
