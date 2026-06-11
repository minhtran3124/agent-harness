# Solutions Index

O(1) lookup of all entries in `docs/solutions/`. Read this first when searching for prior art.

## Entries

| Slug | Category | Module | Tags | Type | Confidence | Confirmed |
|---|---|---|---|---|---|---|
| _(empty — populated as `/compound` runs)_ |  |  |  |  |  |  |

## Critical Patterns

`critical-patterns.md` is always read regardless of query domain — do not skip it.

## Maintenance

- `/compound` appends a row here on every new solution file
- Downgrade confidence on rows whose `confirmed_at` has aged past the decay thresholds (see README.md)
- Remove rows only when the underlying file is deleted (add a tombstone line if needed)
