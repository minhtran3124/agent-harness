# Audiences

The `--audience` flag changes tone and detail. It never changes which facts appear: the same PRs are cited for every audience.

| Audience | Reader | Tone and detail |
|---|---|---|
| `stakeholder` (default) | Manager or sponsor | Outcomes first. One line per change. No code names, no flag names. State the effect on users or on the business. |
| `client` | Customer who uses the product | Say what the user can now do or no longer needs to do. Use the product's own words. Give the exact action in `What you need to do:`. Do not mention internal teams or ticket numbers. |
| `team` | Engineers on the project | Name the module, endpoint or flag when the facts name it. Keep the PR number beside each line. Add the limit or the trade-off when a PR states it. |

## Writing for a human reader

The `asd-ste100` skill is the base, adapted. Keep these habits:

- One idea per sentence. Aim for 20 words or fewer.
- Active voice. Say who does what.
- One word for one thing. Do not switch between "release" and "version" for the same item.
- No hedging words such as "might" or "should" for a fact. If the fact is unsure, tag it `[NEEDS HUMAN]`.

Drop the rules that fit a maintenance manual and not a summary: the fixed dictionary, the strict verb forms and the hard sentence caps. A summary may use a short heading and a plain list.
