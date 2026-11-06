# Decisions that write no ADR

Run `write_adrs.py` with `--table-out <file>`. The script lists every merged decision in that file. A decision that wrote no file in `docs/adr/` is not recorded.

For each such decision, put this line in the report: `not recorded: <reason>`. Give the true reason, for example "fewer than two options" or "same as ADR 0012".

A decision needs at least two real options. If a decision has fewer than two, ask the owner once for the option that the team rejected. If the owner does not answer, do not invent one. Report `not recorded: no rejected option`.

Add no link to `critical-patterns.md` for a decision that has no ADR. A link points only to an ADR path that `write_adrs.py` printed.
