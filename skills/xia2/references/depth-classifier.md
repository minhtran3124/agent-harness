# Portable depth classifier

Use this reference with `rules/research-depth.md`.

Deep signals are:

- migration/schema/data loss
- high-blast files
- new external integrations or dependencies
- shared runtime configuration
- auth/session/transaction scope

Quick requires all of:

- no Deep signal
- no more than one file
- no new public callable in shared code
- no dependency or public API change
- no entry-point work

Examples:

- A typo or internal display method can be Quick.
- An endpoint or shared helper is Standard.
- A migration, provider integration, dependency addition, or shared configuration edit is Deep.
