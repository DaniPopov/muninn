# Frontend Architecture

Status: **design**. There's no code yet; this document is the plan the code will follow.
Decisions: [ADR 0002](../architecture_decisions/0002-language-and-stack.md) (React + TypeScript + Tailwind),
[ADR 0004](../architecture_decisions/0004-frontend-feature-based-structure.md) (organized by feature).

## Purpose and non-goals

WhatsApp is the main way people use Muninn. The web dashboard is the **second screen**:
a place to see everything Muninn remembers, fix a wrong memory, cancel a reminder,
and export or delete all of your data.

Non-goals, written down so we don't drift:
- No business logic in the browser. Every rule lives in the backend.
- No chat UI in the first versions. Conversations happen in WhatsApp.
- No SEO or server-side rendering. It's a private dashboard behind a login.

## Stack

| Concern | Choice | Why |
|---|---|---|
| Build / dev server | Vite | fast single-page-app dev loop; proxies `/api` to the backend |
| UI | React + TypeScript (strict) | [ADR 0002](../architecture_decisions/0002-language-and-stack.md) |
| Styling | Tailwind CSS v4 | utility classes, no separate CSS files to maintain |
| Server state | TanStack Query | caching, loading and error states out of the box |
| Routing | React Router | a handful of pages |
| API types | generated from the backend's OpenAPI schema (`openapi-typescript`) | frontend types can't drift from the backend |
| Package manager | pnpm | fast, strict `node_modules` |

## Layout

```
frontend/
├── index.html
├── vite.config.ts               # @ alias, Tailwind plugin, /api proxy
├── Dockerfile                   # build stage (node + pnpm) → nginx serving dist/
├── nginx.conf                   # serves the app, proxies /api to the backend container
├── public/                      # files served as-is: favicon, robots.txt
└── src/
    ├── main.tsx                 # React root
    ├── index.css                # Tailwind import + design tokens (colors, fonts)
    │
    ├── app/                     # wiring only: how the features fit together
    │   ├── App.tsx
    │   ├── router.tsx           # routes → feature pages
    │   └── providers.tsx        # QueryClientProvider, i18n, theme
    │
    ├── features/                # one folder per feature, same names as the backend
    │   ├── memories/
    │   │   ├── api.ts           # calls to /api/v1/memories + TanStack Query hooks
    │   │   ├── components/      # MemoryList, MemoryCard, EditMemoryDialog
    │   │   ├── pages/           # MemoriesPage
    │   │   ├── types.ts         # feature types (re-exported from generated types)
    │   │   └── index.ts         # PUBLIC API: the only file other code may import
    │   ├── reminders/
    │   │   └── ...              # same shape
    │   └── settings/
    │       └── ...              # export all data, delete all data, language
    │
    ├── shared/                  # reusable, knows nothing about any feature
    │   ├── api/
    │   │   ├── client.ts        # fetch wrapper: base URL, error envelope → ApiError
    │   │   └── schema.gen.ts    # generated from the backend OpenAPI; never edit by hand
    │   ├── ui/                  # Button, Card, Dialog, Input, EmptyState, ...
    │   ├── lib/                 # cn(), date and currency formatting
    │   └── hooks/               # generic hooks (useDebounce, ...)
    │
    └── assets/                  # images imported by components (bundled by Vite)
```

## The dependency rule

```
app ──► features ──► shared
           │
           └──► other features, ONLY through their index.ts
```

| Folder | May import | Must NOT import |
|---|---|---|
| `shared/` | libraries only | `features/`, `app/` |
| `features/<x>/` | `shared/`, another feature's `index.ts` | another feature's internal files, `app/` |
| `app/` | everything | none |

This is the same idea as the backend's dependency rule: every folder knows clearly
what it's allowed to depend on, so changing one feature doesn't break another.

## Inside a feature

Take `features/reminders/` as the example:

- **`api.ts`**: the only place in the feature that knows about HTTP. It exports hooks
  like `useReminders()` and `useCancelReminder()`. Query keys start with the feature
  name: `["reminders", "list"]`.
- **`components/`**: take typed props, render UI. They call hooks from `api.ts`;
  they never call `fetch`.
- **`pages/`**: compose components into a screen. One page per route.
- **`index.ts`**: exports what the rest of the app may use, usually the page(s)
  and maybe a small component. Everything else is private to the feature.

## Conventions

**Data**
- The backend's error body `{"error": {"code", "message"}}` becomes an `ApiError`
  in `shared/api/client.ts`. Components show a plain-language message, never raw JSON.
- The URL is the state for anything shareable (filters, search, selected item).
  `useState` is only for temporary UI state (a dialog being open).

**Languages and right-to-left**
- The UI supports **Hebrew, Russian and English**. Hebrew is right-to-left.
- `<html dir>` switches between `rtl` and `ltr` with the language.
- Use Tailwind's **logical** classes so layouts flip automatically:
  `ms-4` / `me-4` / `ps-4` / `pe-4` / `text-start`, never `ml-4` / `mr-4` / `text-left`.
- No hardcoded user-facing strings in components. They come from translation files
  (library to be chosen when the first page is built).

**Accessibility** (our users include older people)
- Large default font size and generous tap targets.
- Strong contrast, visible focus rings, `aria-label` on icon-only buttons.
- Works on a phone screen (375 px wide) first.

**Code**
- TypeScript strict. No `any`.
- `pnpm typecheck` and `pnpm lint` must pass before a commit.
- Never edit `schema.gen.ts` by hand. Regenerate it when backend schemas change.

## Images and other assets

| Where | What goes there | How it's used |
|---|---|---|
| `frontend/src/assets/` | images used inside the app (logo, illustrations, empty-state art) | `import logo from "@/assets/logo.svg"`, bundled and cache-busted by Vite |
| `frontend/public/` | files that need a fixed URL (favicon, `robots.txt`, social preview image) | referenced by absolute path: `/favicon.svg` |
| `docs/assets/` | images for the README and docs (logo, diagrams, screenshots) | Markdown: `![Muninn](docs/assets/logo.png)` |

Prefer SVG for logos and icons. Compress PNG/JPG before committing.

## Adding a feature: checklist

1. Make sure the backend endpoint exists, then regenerate `shared/api/schema.gen.ts`.
2. Create `features/<name>/` with `api.ts`, `components/`, `pages/`, `index.ts`.
3. Export the page from `index.ts` and add the route in `app/router.tsx`.
4. Add translation strings for Hebrew, Russian and English.
5. Check it on a phone-sized screen and in right-to-left mode.

## Running

| `APP_ENV` | How the frontend runs |
|---|---|
| `DEV` | Vite dev server with hot reload on `:5173`, proxies `/api` to the backend |
| `STAGE` / `PROD` | nginx serves the built `dist/` on `:80` and proxies `/api` to the backend container |
