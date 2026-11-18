# Late decisions (#653)

An ADR file is written only for a decision made before a ticket is implemented.

- Early stages, matched exactly (ignoring case and surrounding spaces): `intake`, `grilling`, `intent`, `research`, `design`, `plan`, `plan-review`.
- A decision with `adr: true` and two real options from any other stage (`qa`, `implement`, `review`,
  a `-fix` stage, ...), or with no `stage`, is late: no file, its `## Decisions` row says
  `late decision, no file`, and `needs_review` is forced true (also for an `owner_confirmed` one), so it
  is listed under `## Needs your decision`. In a manual run, `--needs-out FILE` writes that list.
- When duplicates merge, an `adr: true` item from an early stage wins over a later one.
- A decision without `stage` does not make `write_adrs.py` exit 2: it is late.
