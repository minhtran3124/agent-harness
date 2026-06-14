# FastAPI Backend — Architecture Reference

Authoritative architecture reference. Consult before implementing, debugging, or reviewing.

---

## Project Structure

```
apps/api/
├── app/
│   ├── main.py              # FastAPI entry: middleware, auth, router registration
│   ├── config/               # App config, streaming config, optional AI config
│   ├── database/             # DB connection, session manager, data fetchers
│   ├── dependencies/         # FastAPI shared deps (locking, shared resources)
│   ├── enums/                # Shared domain enums
│   ├── exceptions/           # AppException factory (400/401/403/404/500)
│   ├── models/               # SQLAlchemy ORM models
│   ├── redis/                # Redis connection, cache, pub/sub, streaming lock
│   ├── repositories/         # Data access layer (generic BaseRepository + specialized)
│   ├── routers/              # HTTP route handlers
│   ├── schemas/              # Pydantic v2 request/response models
│   ├── services/             # Business logic + external integrations
│   ├── tasks/                # Background tasks
│   ├── usecases/             # Orchestration layer (combines services + repos)
│   └── utils/                # Shared helpers (logger, token, SSE, dates, etc.)
│
├── alembic/                  # DB migrations
├── tests/                    # Test suite
└── scripts/                  # Utility/maintenance scripts
```

Background worker processes (real-time data, async processing) may run alongside the API as standalone packages under `apps/api/` when the project requires them.

---

## Request Flow

```
HTTP Request
  → Middleware (LogStreamingAPI → LogAPI → CORS)
  → Auth (JWT via get_current_user)
  → Router (Pydantic validation)
  → UseCase / Service (business logic)
  → Repository (async SQLAlchemy)
  → PostgreSQL (asyncpg pool)
  → Pydantic response → HTTP Response
```

Streaming endpoints (real-time data, optional AI chat) return `EventSourceResponse` with SSE chunks. Errors mid-stream are sent inside the stream (status is already 200).

---

## Layer Responsibilities

### Routers (`app/routers/`)
HTTP interface only — validate input, delegate to usecases/services, return response. No business logic or direct DB queries. Typically covers: auth, user, profile, payments, subscriptions, watchlists, templates, webhooks, and any SSE streaming endpoints. Routers are grouped by domain and mounted from a central registration point in `main.py`.

### Use Cases (`app/usecases/`)
Orchestration layer — combines multiple services and repositories for one business operation. No HTTP or low-level DB concerns. Typically covers: auth/signup flows, profile management, payment lifecycle, subscriptions, notifications, and user settings.

### Services (`app/services/`)
Business logic and external integrations, organized by domain. Common groupings:

- **Core** — App lifespan (startup/shutdown), system configuration management, and shared business logic.
- **Integrations** — Wrappers around external APIs, selected at runtime via a factory when multiple providers exist.
- **Optional AI/domain services** — If the project uses AI: streaming with retry + tool calling, conversation management, intent classification, token quota enforcement + cost tracking, and a retrieval/knowledge-base subsystem (document processing/chunking, embedding via pgvector, version-managed re-indexing, prompt templates, and external LLM clients).

### Repositories (`app/repositories/`)
Data access layer. Generic `BaseRepository` provides CRUD (get, create, upsert, soft delete); specialized repos extend it per domain entity (e.g. users, profiles, subscriptions, watchlists, settings, templates, products).

### Models (`app/models/`)
SQLAlchemy ORM models grouped by domain (e.g. users/profiles, subscriptions/products, plus any project-specific domain models). Most support soft deletes via `deleted_at`.

### Database (`app/database/`)
`DatabaseSessionManager` with async SQLAlchemy, connection pooling, pre-ping, retry with backoff. `get_db()` is the FastAPI dependency. Includes data-fetch helpers that load and shape data before it reaches the service/calculation layer.

### Redis (`app/redis/`)
Redis client, configuration, cache manager (get/set/invalidation), and distributed streaming lock (prevents duplicate concurrent streams).

### Schemas (`app/schemas/`)
Pydantic v2 `BaseModel` classes for all request/response validation. Never use raw dicts for I/O.

---

## Key Patterns

| Pattern | Implementation |
|---|---|
| Repository | `BaseRepository` + specialized repos |
| Factory | Integration/provider selection by type |
| Dependency Injection | `Depends(get_db)`, `Depends(get_current_user)` |
| Async I/O | All DB, Redis, HTTP use `async/await` |
| SSE Streaming | Real-time + optional AI via `EventSourceResponse` |
| pgvector RAG | Embeddings in PostgreSQL (when AI is used) |
| Soft Deletes | `deleted_at` + `BaseRepository.soft_delete()` |
| RORO | All I/O uses Pydantic models |
| Lifespan | Modern startup/shutdown context manager |

---

## Infrastructure

| Component | Technology |
|---|---|
| Database | PostgreSQL + pgvector (asyncpg + SQLAlchemy 2.0) |
| Cache / Pub-Sub | Redis |
| Auth | Auth provider (JWT) |
| Payments | Payments provider (webhooks + subscriptions) |
| AI (optional) | LLM provider (streaming, RAG, tool calling) |
| Error Monitoring | Error monitoring provider |
| Migrations | Alembic |
| Deployment | Cloud host |
