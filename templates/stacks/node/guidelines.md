# Node.js + TypeScript Backend — Engineering Guidelines

## Code Style

- Enable `strict` mode in `tsconfig.json`. No `any` unless unavoidable and explicitly suppressed with a comment.
- Use `async/await` for all I/O-bound operations. Never use `.then()` chains in new code.
- Type all function signatures — parameters and return types. Use `void` for functions with no meaningful return.
- Use descriptive names with auxiliary verbs: `isActive`, `hasPermission`, `canRetry`.
- `camelCase` for variables, functions, and file names (`userSettings.ts`). `PascalCase` for classes, interfaces, and type aliases.
- Use typed DTOs or domain interfaces for all service/repo I/O — never `any` or raw `object` at boundaries (RORO pattern).
- Prefer functions over classes. Use classes for repositories, services with injected state, and error types.

## Layer Discipline

```
Route → Controller → UseCase → Service → Repository → DB
```

- **Routes**: Register path + method + middleware only. No logic.
- **Controllers**: HTTP interface only. Parse validated input, call use case or service, return DTO. No business logic, no DB calls.
- **UseCases**: Orchestrate multiple services/repos for one business operation. No HTTP or DB concerns.
- **Services**: Business logic and external integrations. May use repos and other services. No `req`/`res` references.
- **Repositories**: Data access only. Extend `BaseRepository` for standard CRUD. No business logic.
- **Pure logic**: Isolated functions — receive inputs, return results. No DB, no side effects. Keep these in `utils/` or colocated with the service so they stay unit-testable without mocks.

## Error Handling

- Guard clauses first — validate and reject at the top of functions with early returns.
- Use a shared `AppError` class with typed subtypes: `AppError.badRequest(msg)`, `.notFound()`, `.unauthorized()`, `.serverError()`.
- Never throw plain `new Error()` across layer boundaries — always use `AppError` or a domain-specific subclass so the error middleware can handle it consistently.
- Avoid deep nesting — use the if-return pattern rather than else blocks.
- The Express/Fastify error middleware is the single exit point for error responses. Route handlers must call `next(err)` (Express) or `reply.send(err)` (Fastify) rather than writing error responses inline.
- Log errors with context: `logger.error('[SERVICE] Failed to process request', { error: e, userId })`.

## Data Access

- All DB access through repositories. Controllers and services never import ORM clients directly.
- `BaseRepository` must provide: `findById`, `findBy`, `findAll`, `create`, `update`, `upsert`, `softDelete`.
- Respect soft delete: all queries must filter `deletedAt IS NULL` (or `deletedAt: null` in ORM) unless explicitly fetching deleted records.
- Use parameterized queries or ORM query builders exclusively — never string-interpolate user input into queries.
- Wrap multi-step writes in a transaction. Pass the transaction/client object through the call chain; do not open nested transactions.
- Background/worker code must use an isolated DB connection — never reuse a request-scoped client outside its request lifecycle.

## Async & Performance

- Never block the event loop — CPU-bound work belongs in a worker thread (`worker_threads`) or an offloaded job queue.
- Use a connection pool (pg Pool, Prisma's built-in pooler, or PgBouncer) with bounded size; configure `idleTimeoutMillis` and `connectionTimeoutMillis`.
- Cache frequently read, rarely written data (e.g. config, user preferences) in Redis. Invalidate on write — do not rely on TTL alone for correctness.
- Use distributed locking (Redis `SET NX`) when a unit of work must not run concurrently across processes.
- Use cursor- or keyset-based pagination for large result sets; avoid `OFFSET` on tables that grow unboundedly.
- Set timeouts on all outbound HTTP calls. Never leave a fetch/axios call without an `AbortController` timeout or a library-level timeout option.

## Validation

- Parse all untrusted input (request body, query params, path params, env variables) through a schema at the outermost boundary — before it enters any service or repository.
- Use Zod (or equivalent) schemas colocated in `src/schemas/` for request/response shapes. Infer TypeScript types from the schema (`z.infer<typeof MySchema>`) rather than maintaining parallel type declarations.
- Validate environment variables at startup using a schema. If required env vars are missing or malformed, crash fast with a clear message rather than failing silently at runtime.
- Never trust data from the DB as already-validated — re-validate when the shape matters (e.g. JSON columns, external webhook payloads stored verbatim).

## AI / Streaming (optional — only if the project has AI streaming)

- Centralize model selection and limits (model name, max tokens, context window) in one config object; load from DB/env with sensible defaults.
- Use lightweight models for fast tasks (intent classification, planning); reserve larger models for the main generation work.
- SSE events must follow the streaming provider's event format via shared stream-helper utilities.
- Log token usage on every call — including on interruption or failure (record the failure, not just success).
- Streaming errors mid-stream must be sent as SSE error events. The HTTP status is already 200; do not attempt to change it.

## Testing

- Framework: `vitest` or `jest` + `ts-jest`. Run: `npx vitest run` or `npx jest`.
- Use markers/labels: `unit`, `integration`, `edge_case`, `slow` (via `describe` grouping or custom labels).
- Mock the DB layer with jest mocks or `vi.fn()` stubs — never hit a real DB in unit tests. Use a dedicated test database for integration tests.
- Shared fixtures in `tests/setup.ts` or `tests/helpers/` — e.g. `mockDb`, `mockCurrentUser`, domain data builders.
- Use test factory functions in `tests/factories/` for constructing domain objects consistently.
- Coverage target: 80% minimum for branches and lines (`--coverage`).
- Always test: happy path, error/edge cases, boundary conditions, and auth guard (401 on unauthenticated requests).

## Dependency Injection

- Pass dependencies (db client, cache, config, services) via constructor injection or a DI container (`tsyringe`, `awilix`). Avoid module-level singletons that make tests hard to isolate.
- Auth-protected routes attach the auth middleware at the router level, not inside individual controllers.
- Instantiate services and repositories inside the request lifecycle (or at app startup for true singletons like config). Do not import and call service instances from module scope.

## Logging

- Use a structured logger (`pino`, `winston`) configured at app startup; export a module-scoped instance.
- Prefix log messages with layer context: `[SERVICE]`, `[REPO]`, `[CONTROLLER]`.
- Log at `info` for normal operations, `warn` for recoverable anomalies, `error` for failures.
- Never log sensitive data — tokens, passwords, PII, or full request bodies in production.
- In development, pretty-print logs. In production, emit structured JSON (for log aggregators).

## Code Quality Checklist

Before finalizing any code:

- [ ] TypeScript strict mode; no `any` without suppression comment
- [ ] `async/await` for all I/O operations; no unhandled promise rejections
- [ ] Correct layer placement (route → controller → usecase → service → repository)
- [ ] Typed DTOs for all service/repo I/O (no raw `object` or `any` at boundaries)
- [ ] `AppError` factory used — no plain `new Error()` thrown across boundaries
- [ ] Guard clauses at function top
- [ ] Soft delete respected (`deletedAt IS NULL`)
- [ ] No business logic in controllers or routes
- [ ] No direct DB client imports outside repositories
- [ ] Multi-step writes wrapped in a transaction
- [ ] All untrusted input parsed through a Zod (or equivalent) schema
- [ ] Outbound HTTP calls have timeouts set
- [ ] Background/worker code uses an isolated DB connection
- [ ] AI calls use centralized model config (if applicable)
- [ ] Token usage logged, including failures (if applicable)
- [ ] Tests exist for new functionality
- [ ] Logging uses a structured, module-scoped logger
