# 0005. Monorepo layout: `apps/backend` and `apps/dashboard`

- **Status:** Accepted (replaces the folder layout in [ADR 0002](0002-language-and-stack.md))
- **Date:** 2026-09-25
- **Deciders:** @DaniPopov

## Context

ADR 0002 put the code in `backend/` and `frontend/` at the repo root. Before writing
any code we looked again, because Muninn will probably grow more deployable parts:
a WhatsApp bridge container, a landing or docs website, maybe a separate
speech-to-text worker. We also want folder names that say what a thing *is*.

## Options considered

### Option A: `backend/` + `frontend/` at the root
- Pro: Simplest. Very common for two-part projects.
- Con: "frontend" stops being a clear name once there is a second web app.
- Con: New deployables pile up at the root next to `docs/` and config files.

### Option B: `apps/<name>/` (the Turborepo / Nx / pnpm-workspaces convention)
- Pro: Every deployable lives in one place. Adding one means adding one folder.
- Pro: Room for `packages/` later for shared code (for example generated API types).
- Pro: Widely recognized by contributors.
- Con: One extra folder level in paths.

We use `apps/` (plural), not `app/`: the backend's Python package is already called
`app`, and `app/backend/app/` would be confusing.

## Decision

**Option B.**

```
apps/
├── backend/     # Python + FastAPI (ADR 0003)
└── dashboard/   # React + TypeScript + Tailwind (ADR 0004)
```

The web app is called **dashboard** after its purpose, not "frontend" after its tier.

## Consequences

- Compose build contexts are `./apps/backend` and `./apps/dashboard`. The compose
  services are named `backend` and `dashboard`.
- A future deployable (for example `apps/whatsapp-bridge/`) gets its own folder under `apps/`.
- Shared code, if we ever need it, goes in `packages/<name>/`, never inside another app.
