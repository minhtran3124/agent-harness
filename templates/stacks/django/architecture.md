# Django + DRF Backend — Architecture Reference

Authoritative architecture reference. Consult before implementing, debugging, or reviewing.

---

## Project Structure

```
project/
├── config/
│   ├── settings/
│   │   ├── base.py          # Shared settings: installed apps, middleware, auth backends
│   │   ├── development.py   # Dev overrides: DEBUG, local DB, email backend
│   │   └── production.py    # Prod overrides: ALLOWED_HOSTS, security headers, storage
│   ├── urls.py              # Root URL conf: mounts versioned API routers + admin
│   └── wsgi.py / asgi.py    # WSGI / ASGI entry point
│
├── apps/
│   └── <app_name>/
│       ├── __init__.py
│       ├── models.py         # ORM models; custom managers defined here or in managers.py
│       ├── managers.py       # Custom QuerySet / Manager classes (optional, for complex domains)
│       ├── serializers.py    # DRF serializers: validation, representation, write logic
│       ├── views.py          # DRF ViewSets / APIViews: HTTP interface only
│       ├── urls.py           # App-level URL patterns + DRF router registration
│       ├── services.py       # Business logic: orchestrates models, external calls, side effects
│       ├── admin.py          # Django admin registration
│       ├── apps.py           # AppConfig (signal connection, app-level setup)
│       ├── permissions.py    # DRF Permission classes specific to this app
│       ├── filters.py        # django-filter FilterSet classes (optional)
│       ├── tasks.py          # Celery tasks: thin wrappers that delegate to services
│       ├── tests/
│       │   ├── test_models.py
│       │   ├── test_serializers.py
│       │   ├── test_views.py
│       │   └── test_services.py
│       └── migrations/
│           └── 0001_initial.py
│
├── common/                   # Project-wide shared code
│   ├── exceptions.py         # Custom exception classes + DRF exception handler
│   ├── models.py             # Abstract base models (TimestampedModel, SoftDeleteModel)
│   ├── pagination.py         # Shared DRF pagination classes
│   ├── permissions.py        # Project-wide permission classes
│   └── utils.py              # Shared helpers (dates, tokens, formatting)
│
├── conftest.py               # Top-level pytest fixtures (DB, API client, user factories)
├── manage.py
└── requirements/
    ├── base.txt
    ├── development.txt
    └── production.txt
```

Background workers (Celery beat + worker processes) run as separate processes but share the same Django app configuration and database.

---

## Request Flow

```
HTTP Request
  → WSGI/ASGI server (gunicorn / uvicorn)
  → Django Middleware stack (SecurityMiddleware → SessionMiddleware → CORS → Auth → ...)
  → URL dispatcher (config/urls.py → app urls.py)
  → DRF Request parsing + content negotiation
  → DRF Authentication (JWT / session / token)
  → DRF Permission checks
  → ViewSet / APIView (dispatch → action method)
  → DRF Serializer (input validation + deserialization)
  → Service layer (business logic)
  → Model / ORM (QuerySet → SQL)
  → PostgreSQL
  → Serializer (output representation)
  → DRF Response → HTTP Response
```

Background task flow:
```
View / Service → Celery task (enqueue via .delay() / .apply_async())
  → Broker (Redis)
  → Celery worker → Service layer (same business logic, no HTTP context)
  → DB / external APIs
```

---

## Layer Responsibilities

### URLs / Routing (`urls.py`)
URL conf maps URL patterns to ViewSets or APIViews. Use DRF's `DefaultRouter` or `SimpleRouter` for standard resource endpoints. App-level `urls.py` is included from `config/urls.py` under a versioned prefix (e.g. `/api/v1/`). No logic here — routing only.

### Views / ViewSets (`views.py`)
HTTP interface only. `ModelViewSet` for standard CRUD; `APIView` for custom, non-resource endpoints. Responsibilities: parse the DRF request, call the serializer for input validation, delegate to a service or queryset, return a `Response`. No business logic, no raw SQL, no direct model mutations beyond what a thin create/update path requires. Typically covers: auth endpoints, user/profile, payment webhooks, resource CRUD, and any streaming or webhook ingestion endpoints.

### Serializers (`serializers.py`)
Validation and representation. `ModelSerializer` for model-backed I/O; plain `Serializer` for non-model shapes. Responsibilities: field-level and object-level validation (`validate_<field>`, `validate()`), deserialization into validated data, `create()` / `update()` for simple model writes, and output representation. Complex write logic that touches multiple models or has side effects belongs in the service layer, not in `create()` / `update()`. Never return raw dicts from views — always serialize through a serializer.

### Services (`services.py`)
Business logic and external integrations. A service is a plain Python module (or class when state is needed) that receives validated data and coordinates models, external APIs, caching, and side effects. Services are the correct place for: multi-model transactions, third-party API calls (payments, email, SMS), domain rule enforcement, quota checks, and any logic that must be reusable from both views and Celery tasks. Services must not import from `views.py` or use `request` objects directly.

### Models / ORM (`models.py`)
SQLAlchemy-equivalent layer: define schema, relationships, field-level constraints, and `Meta` options. Business logic that is purely about a single model's invariants (e.g. a `is_active` property, a `full_name` computed field) may live on the model. Cross-model logic belongs in services. All models inherit from a shared `TimestampedModel` (adds `created_at` / `updated_at`). Soft-delete models additionally inherit from `SoftDeleteModel` (adds `deleted_at` and a scoped manager that excludes deleted rows by default).

### Managers / QuerySets (`managers.py`)
Custom `QuerySet` and `Manager` classes for reusable query patterns. Name managers descriptively: `ActiveManager`, `PublishedQuerySet`. Attach as `objects = SoftDeleteManager()` or `published = PublishedManager()`. Use `select_related` / `prefetch_related` in manager methods to avoid N+1 at the query definition site. Never put business logic (side effects, external calls) in managers — queries only.

### Migrations (`migrations/`)
Django-managed schema evolution. Each migration is auto-generated via `makemigrations` and reviewed before committing. Migrations are the only mechanism for schema changes — no raw `ALTER TABLE` outside of a migration. Data migrations use `RunPython` with a forward and a reverse function.

### Settings (`config/settings/`)
Split into `base.py` / `development.py` / `production.py`. Secrets and environment-specific values loaded from environment variables (never hardcoded). `INSTALLED_APPS`, middleware order, authentication backends, DRF defaults (`DEFAULT_AUTHENTICATION_CLASSES`, `DEFAULT_PERMISSION_CLASSES`, `DEFAULT_PAGINATION_CLASS`), and Celery configuration all live in settings.

---

## Key Patterns

| Pattern | Implementation |
|---|---|
| Service layer | Plain module/class in `services.py`; called from views and Celery tasks |
| Fat models (bounded) | Single-model invariants and computed properties on the model; cross-model logic in services |
| Custom managers | `QuerySet` subclass + `Manager` for reusable, named query patterns |
| RORO via serializers | All API I/O flows through DRF serializers — no raw dicts at view boundaries |
| Soft deletes | `deleted_at` field on `SoftDeleteModel`; default manager filters `deleted_at IS NULL` |
| Signals (sparingly) | `post_save` / `pre_delete` for decoupled side effects (audit logs, cache invalidation); avoid for business logic |
| Celery tasks (thin) | Tasks in `tasks.py` delegate immediately to service functions; no business logic in the task body |
| Django admin | Register models in `admin.py` with `list_display`, `search_fields`, `list_filter`; use `readonly_fields` for computed data |
| Permission classes | DRF `BasePermission` subclasses; apply at ViewSet level via `permission_classes` |
| Exception handler | Single custom `EXCEPTION_HANDLER` in DRF settings normalizes all error responses |

---

## Infrastructure

| Component | Technology |
|---|---|
| Framework | Django (LTS) + Django REST Framework |
| Database | PostgreSQL (psycopg2 / psycopg3) |
| Cache / Broker | Redis (django-redis for cache; Celery broker + result backend) |
| Async tasks | Celery + Celery Beat (scheduled tasks) |
| Auth | JWT (djangorestframework-simplejwt) or session auth |
| Payments | Payments provider (webhooks ingested via DRF view) |
| AI (optional) | LLM provider client called from service layer |
| Error Monitoring | Error monitoring provider (Sentry, etc.) |
| Migrations | Django migrations (`manage.py migrate`) |
| Admin | Django admin (`/admin/`) |
| Deployment | Cloud host (gunicorn behind reverse proxy, or uvicorn for ASGI) |
