# Next.js (App Router) — Architecture Reference

Authoritative architecture reference. Consult before implementing, debugging, or reviewing.

---

## Project Structure

```
src/
├── app/                          # Next.js App Router root
│   ├── layout.tsx                # Root layout: fonts, global providers, metadata
│   ├── page.tsx                  # Home route
│   ├── globals.css               # Global styles
│   ├── (auth)/                   # Route group: auth pages (no shared layout segment)
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (app)/                    # Route group: authenticated app shell
│   │   ├── layout.tsx            # Shared nav, sidebar, auth guard
│   │   ├── dashboard/page.tsx
│   │   └── settings/
│   │       ├── page.tsx
│   │       └── loading.tsx
│   ├── api/                      # Route Handlers (REST endpoints, webhooks)
│   │   ├── auth/[...nextauth]/route.ts
│   │   └── webhooks/stripe/route.ts
│   └── error.tsx                 # Root error boundary
│
├── components/
│   ├── ui/                       # Primitive, unstyled or lightly-styled atoms (Button, Input, Dialog)
│   └── [domain]/                 # Feature-specific composed components (DashboardCard, UserMenu)
│
├── lib/
│   ├── db/                       # Prisma client, query helpers, connection singleton
│   ├── auth/                     # Auth config, session helpers, permission checks
│   ├── cache/                    # Cache helpers (unstable_cache, Redis wrappers)
│   ├── validations/              # Zod schemas for forms, API I/O, server action args
│   └── utils.ts                  # Shared pure helpers (cn(), dates, formatters)
│
├── actions/                      # Server Actions (mutations, form submissions)
│   └── [domain]/                 # e.g. actions/user.ts, actions/posts.ts
│
├── hooks/                        # Client-side React hooks
├── types/                        # Shared TypeScript types and interfaces
└── middleware.ts                 # Auth redirect, locale, A/B gates (runs on Edge)
```

`public/` holds static assets. Configuration files (`next.config.ts`, `tailwind.config.ts`, `tsconfig.json`) live at the repo root.

---

## Request / Render Flow

### Page request (Server Component, default)

```
Browser Request
  → middleware.ts (Edge: auth check, redirects, headers)
  → Next.js router matches segment
  → Server Component renders (async, direct DB/fetch access)
      → Child Server Components render in parallel (Promise.all semantics)
      → Client Components hydrate on client (serialized props boundary)
  → Streaming HTML → Browser (React Suspense shells flush progressively)
```

### Mutation (Server Action)

```
User interaction (form submit / button)
  → Client Component calls server action (RPC over POST)
  → Server Action validates input (Zod)
  → Server Action calls data layer (Prisma / fetch)
  → revalidatePath / revalidateTag / redirect
  → React re-renders affected segments
```

### API Route Handler

```
External request / webhook / mobile client
  → app/api/[route]/route.ts
  → Auth check (getServerSession or token verify)
  → Validate body/params
  → Call lib/ helpers or data layer
  → Return NextResponse
```

Streaming responses (`new Response(readable)`) are used for AI or large data; Server-Sent Events go through route handlers with `text/event-stream` content type.

---

## Layer Responsibilities

### Server Components (`app/**/page.tsx`, `app/**/layout.tsx`, non-`'use client'` components)
The default rendering unit. Fetch data directly — no client overhead. No event handlers, no `useState`, no browser APIs. Pass serializable props to Client Components at the leaf. Keep data fetching as close to the consumer as possible to enable parallel fetch and fine-grained Suspense.

### Client Components (`'use client'` directive)
Handle interactivity: event handlers, browser APIs, React state and context. Mark `'use client'` as high up the tree as necessary, but as low as possible to keep the Server Component boundary wide. Never fetch sensitive data in Client Components — receive it as props from Server Components or from a public API route.

### Server Actions (`actions/[domain].ts`)
The mutation layer. Declared with `'use server'`. Validate all inputs with Zod before touching the DB. Handle authorization checks before any write. Return typed results — not raw errors — using a discriminated union (`{ success: true, data }` / `{ success: false, error }`). Call `revalidatePath` or `revalidateTag` after mutations to invalidate the cache. Do not call Server Actions from other Server Components for read operations; those are direct `await`s.

### Route Handlers (`app/api/**/route.ts`)
HTTP surface for external consumers: webhooks, mobile clients, third-party integrations. Validate auth headers and request bodies. Return `NextResponse.json()` with explicit status codes. Keep business logic out — delegate to `lib/` helpers or shared service functions. Not a substitute for Server Actions on internal mutations.

### Data Layer (`lib/db/`)
All database access through the Prisma client singleton. No raw SQL outside of `$queryRaw` for performance-critical paths (document in a comment). Helpers that shape query results live here, not in components or actions. The Prisma client is imported from a single module to prevent connection pool exhaustion in development.

### UI Components (`components/`)
`components/ui/` holds generic, unstyled atoms that wrap a component library (e.g. shadcn/ui, Radix). `components/[domain]/` holds composed components specific to a feature. Components never import from `app/` — the dependency flows one way. Server Components may live in `components/` too; only add `'use client'` when the component truly needs it.

### Middleware (`middleware.ts`)
Runs on the Edge runtime before every matched request. Responsible for: auth-based redirects, locale detection, custom request headers. Keep it fast — no database calls, no heavy computation. Use `NextResponse.next()` with mutated headers to pass context downstream.

---

## Key Patterns

| Pattern | Implementation |
|---|---|
| RSC-by-default | All components are Server Components unless `'use client'` is declared |
| Server Actions for mutations | `'use server'` functions in `actions/`; never bare fetch POSTs from the client |
| Collocated data fetching | Each Server Component fetches its own data; `React.cache()` deduplicates within a request |
| Streaming / Suspense | `loading.tsx` + `<Suspense fallback>` for progressive rendering; `generateStaticParams` for static segments |
| Typed RORO | All action inputs/outputs and API bodies are Zod-validated typed objects — no raw `any` |
| Route groups | Parenthesized folders `(group)` share layouts without adding URL path segments |
| Parallel routes | `@slot` convention for simultaneous rendering of independent segments (modals, split panes) |
| Intercepting routes | `(.)path` for in-place modal overlays that intercept navigation |
| Cache-and-revalidate | `fetch()` with `next: { revalidate }` or `unstable_cache()` for ISR-style caching; `revalidateTag` for on-demand purge |
| Soft Deletes (optional) | `deletedAt` timestamp on Prisma models; filter `deletedAt: null` in all standard queries |

---

## Infrastructure

| Component | Technology |
|---|---|
| Framework | Next.js 14 / 15 (App Router) |
| Language | TypeScript (strict mode) |
| UI | React 18 / 19 |
| Styling | Tailwind CSS + shadcn/ui (Radix primitives) |
| Database ORM | Prisma (PostgreSQL) |
| Auth | NextAuth.js v5 / Auth.js |
| Cache | Next.js fetch cache + Redis (optional, for shared invalidation) |
| Payments (optional) | Stripe (webhooks via route handler) |
| AI (optional) | Vercel AI SDK (streaming via `useChat` / route handler) |
| Error Monitoring | Sentry / provider |
| Deployment | Vercel (Node.js runtime; Edge runtime for middleware) |
