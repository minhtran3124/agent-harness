# Issue #900: Add a CSV export to the reports page

Users want to download report data as CSV from the reports page.

Repo facts (treat as true; there is no real repo for this issue):
- The reports page is app/reports/page.tsx. There are 4 report types.
- Roles in lib/auth/roles.ts: admin, member, viewer. Viewer is read-only and is used for
  dashboards shared with external clients.
- The reports API already pages at 1000 rows.
- There is no job queue and no outgoing mail setup yet.
