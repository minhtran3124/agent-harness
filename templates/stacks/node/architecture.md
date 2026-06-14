# Node.js + TypeScript Backend — Architecture Reference

Authoritative architecture reference. Consult before implementing, debugging, or reviewing.

---

## Project Structure

```
src/
├── app.ts               # Express/Fastify entry: middleware registration, router mounting
├── server.ts            # Server bootstrap: port binding, startup/shutdown lifecycle
├── config/              # Env-validated config (e.g. via zod or envalid), constants
├── middleware/          # Request-scoped middleware: auth, logging, error handler, CORS
├── routes/              # Route definitions — thin; delegate immediately to controllers
├── controllers/         # HTTP handlers — parse input, call service/use-case, return DTO
├── usecases/            # Orchestration layer — combines services + repos for one operation
├── services/            # Business logic + external integrations, organized by domain
├── repositories/        # Data access layer (BaseRepository + specialized repos)
├── models/              # ORM/schema definitions (Prisma models, TypeORM entities, etc.)
├── schemas/             # Zod (or equivalent) request/response validation schemas
├── types/               # Shared TypeScript types, interfaces, and enums
├── errors/              # AppError class and typed error factory helpers
├── cache/               # Cache client, manager (get/set/invalidate), and key helpers
└── utils/               # Shared helpers (logger, token, date, SSE, pagination, etc.)

migrations/              # DB migration files (Prisma migrations, TypeORM, or Knex)
tests/                   # Test suite (unit/ + integration/)
scripts/                 # Utility/maintenance scripts
```

Background worker processes (job queues, real-time consumers, async processing) may run as standalone entry points alongside the main API server when the project requires them.

---

## Request Flow

```
HTTP Request
  → Middleware (cors → requestLogger → auth)
  → Route (schema validation via zod/class-validator)
  → Controller (parse + delegate)
  → UseCase / Service (business logic)
  → Repository (typed ORM queries)
  → PostgreSQL (connection pool)
  → Typed DTO response → HTTP Response
```

Streaming endpoints (Server-Sent Events, optional AI chat) write chunked `text/event-stream` responses. Errors mid-stream are sent as SSE error events — the HTTP status is already 200 at that point.

---

## Layer Responsibilities

### Routes (`src/routes/`)
Route registration only — map HTTP method + path to a controller handler. No business logic, no validation beyond middleware attachment. Routes are grouped by domain and mounted from a central router in `app.ts`.

### Controllers (`src/controllers/`)
HTTP interface layer — extract validated input from `req`, call the appropriate use case or service, and serialize the response DTO. No business logic. No direct repository or DB calls. One controller per domain (e.g. `UserController`, `PaymentController`).

### Use Cases (`src/usecases/`)
Orchestration layer — combines multiple services and repositories to fulfil one business operation. No HTTP or low-level DB concerns. Typically covers: auth/signup flows, profile management, payment lifecycle, subscriptions, notifications, and user settings.

### Services (`src/services/`)
Business logic and external integrations, organized by domain. Common groupings:

- **Core** — Startup/shutdown hooks, system configuration management, and shared business logic.
- **Integrations** — Wrappers around external APIs, selected at runtime via a factory when multiple providers exist (e.g. email, SMS, payment providers).
- **Optional AI/domain services** — If the project uses AI: streaming with retry + tool calling, conversation management, intent classification, token quota enforcement + cost tracking, and a retrieval/knowledge-base subsystem (chunking, embedding, vector search, prompt templates, LLM clients).

### Repositories (`src/repositories/`)
Data access layer. A generic `BaseRepository` provides standard CRUD (`findById`, `findBy`, `create`, `update`, `upsert`, `softDelete`, `findAll`); specialized repos extend it per domain entity (e.g. `UserRepository`, `SubscriptionRepository`, `WatchlistRepository`).

### Models / Entities (`src/models/`)
ORM-layer definitions. With Prisma: the schema file (`prisma/schema.prisma`) is the source of truth; generated types are imported from `@prisma/client`. With TypeORM: entity classes decorated with `@Entity`, `@Column`, etc. Most entities support soft deletes via a `deletedAt` timestamp column.

### Middleware (`src/middleware/`)
Request-scoped cross-cutting concerns:

- **Auth** — JWT verification; attaches `req.user` or rejects with 401.
- **Request logger** — structured log per request (method, path, status, latency).
- **Error handler** — centralized last-resort middleware; converts `AppError` (and unexpected errors) to consistent JSON error responses. Must be registered last.
- **CORS** — origin policy; configured from env.

### Cache (`src/cache/`)
Cache client (Redis or in-process), configuration, cache manager (get/set/invalidation by key or tag), and distributed lock helper when concurrent execution must be prevented.

### Schemas (`src/schemas/`)
Zod (or equivalent) schemas for all request/response validation. Never pass unvalidated `req.body` into services or repositories — always parse through a schema at the controller boundary.

---

## Key Patterns

| Pattern | Implementation |
|---|---|
| Repository | `BaseRepository<T>` + specialized repos per entity |
| Factory | Integration/provider selection by type or env config |
| Dependency Injection | Constructor injection or a lightweight DI container (e.g. `tsyringe`, `awilix`) |
| Async I/O | All DB, cache, and external HTTP calls use `async/await` |
| DTO Validation | Zod schemas (or class-validator) parsed at the controller boundary |
| SSE Streaming | Real-time + optional AI via chunked `text/event-stream` responses |
| Soft Deletes | `deletedAt` column + `BaseRepository.softDelete()` |
| RORO | All service/repo I/O uses typed DTOs or domain objects — no raw `any` |
| Centralized Error Handling | `AppError` class + Express/Fastify error middleware |
| Graceful Shutdown | `SIGTERM`/`SIGINT` handlers drain in-flight requests before closing DB pool |

---

## Infrastructure

| Component | Technology |
|---|---|
| Runtime | Node.js (LTS) + TypeScript (strict mode) |
| Framework | Express or Fastify |
| Database | PostgreSQL (via Prisma, TypeORM, or Knex + pg) |
| Cache / Pub-Sub | Redis (ioredis) |
| Auth | JWT (jsonwebtoken or jose) via auth middleware |
| Payments | Payments provider SDK (webhooks + subscriptions) |
| AI (optional) | LLM provider SDK (streaming, RAG, tool calling) |
| Error Monitoring | Error monitoring provider (e.g. Sentry) |
| Migrations | Prisma Migrate, TypeORM migrations, or Knex migrations |
| Deployment | Cloud host (containerized via Docker) |
