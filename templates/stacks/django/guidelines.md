# Django + DRF Backend — Engineering Guidelines

## Code Style

- Follow PEP 8. Line length: 88 characters (Black default).
- Type hints on all function signatures (params + return type). No `Any` unless unavoidable.
- Use descriptive names with auxiliary verbs: `is_active`, `has_permission`, `can_retry`.
- Lowercase with underscores for files, directories, and variables: `user_profile.py`.
- Class names in PascalCase; constants in UPPER_SNAKE_CASE.
- Prefer functions over classes. Use classes when state, inheritance, or DRF/Django base class integration is needed.
- Keep views thin — a view that is longer than ~30 lines is a signal that logic belongs in a service.

## Layer Discipline

```
URL conf → ViewSet / APIView → Serializer (validation) → Service → Model / Manager → DB
```

- **Views / ViewSets**: HTTP interface only. Parse the request, validate via serializer, call a service or queryset method, return a `Response`. No business logic, no raw SQL, no direct ORM mutations beyond a simple thin create/update.
- **Serializers**: Input validation and output representation. Complex writes with side effects go in services, not in `create()` / `update()`. Never pass raw dicts across the view boundary.
- **Services**: All business logic. Callable from views and Celery tasks alike. No dependency on `request` or HTTP context.
- **Models / Managers**: Schema, field constraints, computed single-model properties, and reusable query patterns. No cross-model orchestration and no external API calls.
- **Celery tasks**: Thin dispatch wrappers. Call a service function immediately; no business logic in the task body itself.

## Error Handling

- Guard clauses first — handle invalid or missing state at the top of a function with early returns or exceptions.
- Raise `rest_framework.exceptions.ValidationError` (or a subclass) for client errors surfaced via the serializer. DRF's exception handler converts these to 400 responses automatically.
- Define a single project-wide custom exception handler in `common/exceptions.py` and register it as `EXCEPTION_HANDLER` in DRF settings. This normalizes error response shape across all endpoints.
- Raise typed custom exceptions from services (e.g. `PaymentDeclinedError`, `QuotaExceededError`) — catch and re-raise as DRF exceptions at the view boundary, or handle in the custom exception handler.
- Never raise bare `Exception` in service or model code. Raise a specific exception class.
- Avoid deep nesting — use if-return (guard clauses) instead of nested else blocks.
- Log errors with context: `logger.error("[SERVICE] Failed to process payment: %s", e, exc_info=True)`.

## Data / ORM

- All database access through the ORM (QuerySet API). Raw SQL (`connection.execute`) only for queries that are provably impossible or materially worse via the ORM — and always wrapped in a migration or isolated utility.
- Eliminate N+1 queries at the query definition site. Use `select_related` for foreign-key traversal and `prefetch_related` for reverse relations and many-to-many. Add these in the custom manager or QuerySet method so callers get the optimization automatically.
- Use `QuerySet.only()` / `defer()` to avoid loading large text/blob fields when they are not needed.
- Wrap multi-step writes in `transaction.atomic()`. If a step fails, the entire operation rolls back. Do not commit partial state.
- Never call `.save()` in a loop — use `bulk_create()` / `bulk_update()` for batch writes.
- Respect soft delete: always filter `deleted_at__isnull=True` unless intentionally querying deleted rows. Attach a `SoftDeleteManager` as `objects` on soft-delete models so the safe filter is the default.
- Migrations discipline:
  - Run `makemigrations --check` in CI to catch missing migrations.
  - Review auto-generated migrations before committing — particularly for index creation on large tables (`CREATE INDEX CONCURRENTLY` must be a separate, non-transactional step).
  - Data migrations use `RunPython` with both a forward function and a reverse function. Never mutate data inside a schema migration.
  - Never edit a migration that has already been applied to production — create a new one.

## Async / Performance

- Django views are synchronous by default. For async views (ASGI only), use `async def` and `sync_to_async` / `async_to_sync` wrappers when calling ORM or other sync code.
- Offload slow operations (email sending, PDF generation, third-party API calls, large data exports) to Celery tasks. Never block a request/response cycle with work that takes more than ~200 ms.
- Use Redis (via `django-redis`) for caching. Cache at the queryset or service level, not at the view level — so Celery tasks benefit from the same cache.
- Invalidate cache entries on write: explicitly delete or update the relevant cache key in the service function that performs the write.
- Add database indexes for every column used in `filter()`, `order_by()`, or `JOIN` conditions that appear in common queries. Declare indexes in `Meta.indexes` rather than as raw SQL.
- Use `django.db.connection.queries` (with `DEBUG=True`) or `django-silk` / `django-debug-toolbar` in development to surface N+1 and slow query issues before they reach production.
- Configure the database connection pool (e.g. via `django-db-geventpool` or `pgbouncer`) for production — Django's default per-request connection handling does not pool effectively under load.

## Security

- Never trust user input. Validate all input through DRF serializers before it reaches the service or ORM layer.
- CSRF: enabled by default for session-authenticated endpoints. JWT endpoints are exempt (stateless), but do not disable CSRF globally.
- Authentication: set `DEFAULT_AUTHENTICATION_CLASSES` and `DEFAULT_PERMISSION_CLASSES` in DRF settings. Default to `IsAuthenticated`; opt out explicitly with `permission_classes = [AllowAny]` only where public access is intentional.
- Do not expose internal exception details in API responses in production. The custom exception handler must strip tracebacks; error monitoring captures the full detail.
- Never store secrets in source code or commit `.env` files. Load all secrets from environment variables via `os.environ` or a secrets manager.
- Sanitize file upload paths and validate MIME types when accepting file uploads.
- Use Django's `SECRET_KEY` for cryptographic signing (sessions, password reset tokens) — rotate it if compromised; do not reuse across environments.
- Apply `Content-Security-Policy`, `X-Frame-Options`, and `SECURE_HSTS_SECONDS` (and related settings) in `production.py`.

## Testing

- Framework: `pytest` + `pytest-django`. Run: `pytest`.
- Mark tests with `@pytest.mark.django_db` (or `@pytest.mark.django_db(transaction=True)` for transaction semantics). Do not hit the real database in pure unit tests — use mocks or factories without DB access where possible.
- Use markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`.
- Use `factory_boy` factories (in `tests/factories.py`) to create model instances — never hardcode raw `Model.objects.create()` calls spread across test files.
- Use DRF's `APIClient` (or `pytest-django`'s `client` fixture) for view-level integration tests. Test authentication by calling `client.force_authenticate(user=user)`.
- Test the serializer independently: instantiate with data, call `.is_valid()`, assert errors or validated data. Do not rely on view tests alone for validation coverage.
- Test services independently by passing in mock dependencies or using the actual DB (integration test).
- Coverage target: 80% minimum (`--cov-fail-under=80`).
- Always test: happy path, validation failure paths, permission denial, and boundary conditions.

## Logging

- Use a module-scoped logger: `logger = logging.getLogger(__name__)`.
- Prefix log messages with context: `[SERVICE]`, `[TASK]`, `[SERIALIZER]`.
- Use `%s`-style formatting in log calls (lazy interpolation), not f-strings: `logger.info("[SERVICE] User %s created subscription %s", user_id, sub_id)`.
- Never log sensitive data: passwords, tokens, full credit card numbers, or PII that does not need to be in logs.
- Log at the right level: `DEBUG` for diagnostic detail, `INFO` for normal operational events, `WARNING` for recoverable anomalies, `ERROR` for failures requiring attention (always include `exc_info=True`).
- Configure `LOGGING` in settings to route application logs and Django internals to the appropriate handlers (stdout in containers, file or log aggregator in production).

## Code Quality Checklist

Before finalizing any code:

- [ ] Type hints on all functions (params + return)
- [ ] Correct layer placement (view → serializer → service → model/manager → DB)
- [ ] All API I/O flows through DRF serializers (no raw dicts at view boundaries)
- [ ] Business logic in services, not in views or serializers
- [ ] No raw SQL unless provably necessary and isolated
- [ ] N+1 queries eliminated (`select_related` / `prefetch_related` in manager/queryset)
- [ ] Multi-step writes wrapped in `transaction.atomic()`
- [ ] Soft delete respected (`deleted_at__isnull=True`) where applicable
- [ ] Custom exception handler normalizes error responses (no bare `Exception` raised)
- [ ] Guard clauses at function top; no deep nesting
- [ ] Celery tasks delegate to service functions immediately (no logic in task body)
- [ ] Cache invalidated on write
- [ ] Migrations reviewed: no missing migrations, data migrations have a reverse function
- [ ] Authentication and permission classes set explicitly on ViewSets
- [ ] No secrets in source code or committed config files
- [ ] Tests exist for new functionality (view, serializer, service levels)
- [ ] Logging uses module-scoped logger with `%s` formatting; no sensitive data logged
