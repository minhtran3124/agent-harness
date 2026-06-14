# FastAPI Backend — Engineering Guidelines

## Code Style

- Use `async def` for all I/O-bound operations. Use `def` only for pure/CPU-bound functions.
- Type hints on all function signatures (params + return type). No `Any` unless unavoidable.
- Use descriptive names with auxiliary verbs: `is_active`, `has_permission`, `can_retry`.
- Lowercase with underscores for files and directories: `user_settings.py`.
- Use Pydantic models for all API input/output — never raw dicts at boundaries (RORO pattern).
- Prefer functions over classes. Use classes only when state or inheritance is needed (repos, services).

## Layer Discipline

```
Router → UseCase → Service → Repository → DB
```

- **Routers**: HTTP interface only. Validate input, delegate, return response. No business logic, no DB calls.
- **UseCases**: Orchestrate multiple services/repos for one business operation. No HTTP or DB concerns.
- **Services**: Business logic and external integrations. May use repos and other services.
- **Repositories**: Data access only. Extend a shared base repository (e.g. `BaseRepository`) for standard CRUD.
- **Pure logic**: Pure functions — receive their inputs, return results. No DB, no side effects. Keep these isolated so they stay unit-testable.

## Error Handling

- Guard clauses first — handle errors at function top with early returns.
- Use a shared exception factory for HTTP errors (e.g. `AppException.BadRequest(msg)`, `.NotFound()`, `.ServerError()`).
- Never use bare `HTTPException` outside auth/middleware boundaries.
- Avoid deep nesting — use if-return pattern instead of else blocks.
- Log errors with context: `logger.error(f"[SERVICE] Failed to process: {e}")`.

## Database & Sessions

- All DB access through repositories via `Depends(get_db)`.
- A shared base repository should provide: `get_by_id`, `get_by_field`, `create`, `update`, `upsert`, `soft_delete`, `get_all_by_conditions`.
- Respect soft delete: filter `deleted_at IS NULL` in queries where applicable.
- Streaming/background code must use an isolated session (e.g. `sessionmanager.session()`) — never the request-scoped `get_db`.
- Use `flush()` + `refresh()` instead of `commit()` inside repositories — let the session manager handle commit.

## Async & Performance

- Never block the event loop — all DB, cache, external HTTP, and other I/O calls must be async.
- Use a cache layer (e.g. Redis) for frequently accessed data. Invalidate on write.
- Use distributed locking when a unit of work must not run concurrently across processes.
- Use lazy loading for large datasets; avoid loading unbounded result sets.
- Configure the connection pool with pre-ping and bounded retry/backoff (e.g. via the session manager).

## AI / Streaming (optional — only if the project has AI streaming)

- Centralize model selection and limits (model name, max tokens, context window) in one config object; load from DB/env with sensible defaults.
- Use lightweight models for fast tasks (e.g. intent classification, planning); reserve larger models for the main work.
- SSE events must follow the streaming provider's event format via shared SSE helpers.
- Log token usage on every call — including on interruption/failure (record the failure, not just success).
- Streaming errors mid-stream must be sent as SSE error events (HTTP status is already 200).

## Testing

- Framework: `pytest` + `pytest-asyncio` (auto mode). Run: `python -m pytest`.
- Use markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.edge_case`, `@pytest.mark.slow`.
- Mock DB with `AsyncMock` sessions — never hit real DB in unit tests.
- Shared fixtures in `tests/conftest.py` — e.g. `mock_db_session`, `mock_current_user`, domain data fixtures.
- Test factories in `tests/factories.py` for creating test objects.
- Coverage target: 80% minimum (`--cov-fail-under=80`).
- Always test: happy path, error/edge cases, boundary conditions.

## Dependency Injection

- Use FastAPI `Depends()` for all shared resources: `get_db`, `get_current_user`, and other shared providers.
- Auth-protected routes use `dependencies=[Depends(get_current_user)]` at router level.
- Instantiate services/repos inside route handlers with the injected session — do not use global instances (except deliberate singletons like a loaded config).

## Logging

- Use a module-scoped logger: `Logger(__name__)` or `logging.getLogger(__name__)`.
- Prefix log messages with context: `[SERVICE_NAME]`, `[REPO]`, `[ROUTER]`.
- Never log sensitive data (tokens, passwords, full request bodies in production).

## Code Quality Checklist

Before finalizing any code:

- [ ] Type hints on all functions (params + return)
- [ ] Async for all I/O operations
- [ ] Correct layer placement (router → usecase → service → repo)
- [ ] Pydantic models for API I/O (no raw dicts)
- [ ] Shared exception factory for errors (not bare `HTTPException`)
- [ ] Guard clauses at function top
- [ ] Soft delete respected (`deleted_at IS NULL`)
- [ ] No business logic in routers
- [ ] No direct DB calls outside repositories
- [ ] Streaming uses an isolated session, not request-scoped `get_db`
- [ ] AI calls use centralized config (if applicable)
- [ ] Token usage logged, including failures (if applicable)
- [ ] Tests exist for new functionality
- [ ] Logging uses a module-scoped logger
