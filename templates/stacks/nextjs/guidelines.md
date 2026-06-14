# Next.js (App Router) — Engineering Guidelines

## Code Style

- TypeScript strict mode everywhere. No `any` unless a third-party type forces it; add a comment explaining why.
- Type all function parameters and return types explicitly. Avoid inferring return types on exported functions.
- Use descriptive names with auxiliary verbs: `isLoading`, `hasPermission`, `canSubmit`.
- Kebab-case for files and directories: `user-profile.tsx`, `use-auth.ts`.
- PascalCase for React component files: `UserAvatar.tsx`. Kebab-case is also acceptable if the team is consistent — pick one and stick to it.
- Named exports for components and utilities. Default exports only where Next.js requires them (`page.tsx`, `layout.tsx`, `error.tsx`, `loading.tsx`, `route.ts`).
- `cn()` (clsx + tailwind-merge) for conditional class composition. Never string-concatenate Tailwind classes.

## Component Discipline

```
Server Component (default)
  → Client Component ('use client')
    → Server Action ('use server')
```

- Default to Server Components. Add `'use client'` only when you need: event handlers, `useState`, `useEffect`, browser APIs, or third-party client-only libraries.
- Push `'use client'` to the leaves. A large layout should not be a Client Component just because one button in it needs `onClick` — extract the button.
- Never import a Server Component from a Client Component directly (breaks the boundary). Pass Server Component output as `children` or a prop if needed.
- Never use `useEffect` for data fetching in Client Components. Fetch in Server Components or Server Actions instead; Client Components receive the data as props.
- Context providers are always Client Components. Wrap them as high as needed, as low as possible. Keep providers out of `layout.tsx` unless the entire subtree needs them.

## Data Fetching

- Fetch data in Server Components as close to the consumer as possible — this enables parallel fetch without waterfall.
- Use `React.cache()` to deduplicate identical fetches within a single request (e.g. a helper called in multiple components on the same page):
  ```ts
  // lib/db/user.ts
  export const getUser = React.cache(async (id: string) => {
    return prisma.user.findUniqueOrThrow({ where: { id } });
  });
  ```
- Use `fetch()` with `next: { revalidate: N }` or `next: { tags: ['tag'] }` for ISR-style caching. Use `cache: 'no-store'` for per-request fresh data.
- Use `unstable_cache()` for Prisma queries and other non-`fetch` async calls that need ISR semantics.
- Avoid sequential awaits (waterfall) in a single Server Component when the calls are independent — use `Promise.all()` or separate parallel segments.
- Never use `getServerSideProps` / `getStaticProps` — those are Pages Router APIs.

## Error Handling

- Guard clauses first — handle auth, validation, and not-found cases at the top before any business logic.
- `error.tsx` catches unhandled errors in a segment and shows a recovery UI. Always provide one at the `(app)` layout level and at route boundaries that do risky work.
- `not-found.tsx` + `notFound()` for missing resource errors. Do not throw a generic error for 404s.
- Server Actions return typed discriminated unions — never `throw` to the client:
  ```ts
  // Good
  return { success: false, error: 'User not found' } as const;
  // Bad
  throw new Error('User not found'); // becomes an opaque error on the client
  ```
- Route Handlers return explicit `NextResponse.json({ error: '...' }, { status: 4xx })`. Match the error shape across all handlers.
- Log errors server-side with context before returning a sanitized message to the client. Never leak stack traces or internal details in API responses.

## State & Forms

- Use Server Actions for all form submissions. Pair with `useFormState` (React 18) or `useActionState` (React 19) in Client Components for pending state and error display.
- Validate all Server Action inputs with Zod at the action boundary — do not rely on HTML validation alone:
  ```ts
  'use server';
  import { z } from 'zod';

  const schema = z.object({ email: z.string().email() });

  export async function updateEmail(formData: FormData) {
    const parsed = schema.safeParse({ email: formData.get('email') });
    if (!parsed.success) return { success: false, error: parsed.error.flatten() };
    // ...
  }
  ```
- Check authorization in every Server Action before any write — never assume the caller is authenticated based on UI state alone.
- For complex client-side UI state (multi-step forms, drag-and-drop, optimistic UI), prefer `useReducer` over many `useState` calls. Use Zustand for state that must survive navigation.
- URL state (filters, pagination, tabs) belongs in `searchParams` — use `nuqs` or manual `useSearchParams` + `router.push`. Do not duplicate URL state into `useState`.

## Performance

- Favor Server Components — they have zero JS bundle cost on the client.
- Use `next/image` for all images. Always provide `width`, `height` (or `fill`), and meaningful `alt` text. Set `priority` on above-the-fold images.
- Use `next/font` for all custom fonts. Load fonts in the root `layout.tsx` to avoid layout shift.
- Dynamic import Client Components that are large or below the fold: `const HeavyChart = dynamic(() => import('@/components/HeavyChart'), { ssr: false })`.
- Use `loading.tsx` and `<Suspense>` to stream in slow data without blocking the entire page.
- Avoid `use client` + `useEffect` for data that could be fetched server-side — each Client Component is additional JS shipped to the browser.
- Use `generateStaticParams` for routes with a known set of params (e.g. blog posts, product pages) to pre-render at build time.

## Accessibility

- Every interactive element must be keyboard-accessible and have a visible focus ring. Do not remove `outline` without replacing it.
- Use semantic HTML: `<button>` for actions, `<a>` for navigation, heading hierarchy (`h1` → `h2` → `h3`) per page.
- `aria-label` on icon-only buttons. `alt` text on all images — empty string (`alt=""`) for purely decorative images.
- Ensure color contrast meets WCAG AA (4.5:1 for text, 3:1 for large text and UI components).
- Prefer Radix UI primitives (via shadcn/ui) for complex accessible widgets (dialogs, dropdowns, tooltips) — they manage focus trapping and ARIA attributes correctly.

## Testing

- Framework: Vitest (unit/component) + Playwright (E2E). Run: `npx vitest` / `npx playwright test`.
- Use markers / test organization: `describe` blocks per component or action, `it` for individual behaviors.
- Unit test Server Actions with mocked Prisma (via `vitest.mock` or a manual mock module). Never hit a real database in unit tests.
- Component tests with React Testing Library: test user behavior, not implementation details. Prefer `getByRole` over `getByTestId`.
- E2E tests cover critical user flows: sign-up, core mutation, checkout. Run against a real (seeded) database.
- Shared fixtures in `tests/fixtures/` — typed factory functions for building test data objects.
- Coverage target: 80% minimum on `lib/` and `actions/`. UI components: E2E covers the happy path; unit tests for complex logic only.
- Always test: happy path, validation rejection, auth guard (unauthenticated call returns error), and not-found behavior.

## Conventions

- File co-location: keep a component's styles, tests, and sub-components near the component file unless the project uses a flat test directory.
- Re-export barrel files (`index.ts`) are acceptable for `components/ui/` and `lib/` to avoid deep import paths. Avoid barrels in `app/` — Next.js needs the file system to match routes.
- Environment variables accessed only server-side must not be prefixed `NEXT_PUBLIC_`. Validate all env vars at startup with a Zod schema in `lib/env.ts`.
- Never import `process.env` directly in components — route all env access through the validated `env` object.

## Logging

- Use a module-scoped logger (e.g. Pino or a thin `console` wrapper) — one per module.
- Prefix log messages with context: `[ACTION]`, `[API]`, `[DB]`.
- Never log sensitive data: tokens, passwords, full request bodies in production.
- Client-side errors that reach `error.tsx` should be reported to the error monitoring service via `captureException`.

## Code Quality Checklist

Before finalizing any code:

- [ ] TypeScript strict — no `any`, explicit return types on exported functions
- [ ] Server Component by default — `'use client'` only when interaction or browser API is required
- [ ] `'use client'` boundary pushed to the leaves
- [ ] No `useEffect` for data fetching — data fetched in Server Components or Server Actions
- [ ] Server Action inputs validated with Zod before any DB write
- [ ] Authorization checked in every Server Action before any write
- [ ] Server Actions return typed discriminated unions, not thrown errors
- [ ] Route Handlers return `NextResponse.json()` with explicit status codes
- [ ] `revalidatePath` / `revalidateTag` called after mutations
- [ ] `next/image` used for all images with `width`, `height`, `alt`
- [ ] `next/font` used for custom fonts
- [ ] No sequential awaits for independent data fetches — use `Promise.all()` or parallel segments
- [ ] Environment variables accessed via validated `env` object, not bare `process.env`
- [ ] Tests exist for new Server Actions and data helpers
- [ ] No sensitive data in logs or API error responses
