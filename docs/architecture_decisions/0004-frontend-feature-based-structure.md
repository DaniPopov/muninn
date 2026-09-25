# 0004. Frontend: organize code by feature

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** @DaniPopov

## Context

The frontend is a small dashboard: browse and edit memories, manage reminders,
settings (export / delete all data). It will grow with the backend, one feature at a time.

## Options considered

### Option A: Organize by file type (`pages/`, `components/`, `hooks/`, `api/`)
- Pro: Familiar, fine for very small apps.
- Con: One feature ends up spread across 4–5 folders. To understand "reminders" you
  jump all over the tree.
- Con: Nothing stops one feature from reaching into another's internals.

### Option B: Organize by feature (`features/memories/`, `features/reminders/`, ...)
- Pro: Everything about one feature (API calls, components, hooks, types, page) lives
  in one folder. It mirrors the backend's per-feature folders.
- Pro: Each feature exposes a public `index.ts`, so boundaries are clear.
- Pro: Deleting or rewriting a feature touches one folder.
- Con: Needs a clear `shared/` folder for truly shared code, or duplication creeps in.

## Decision

**Option B.** Code is organized as `app/` (wiring), `features/<name>/` (features)
and `shared/` (reusable, feature-agnostic code). Styling is **Tailwind CSS**.

The full guide lives in [`docs/architecture/frontend.md`](../architecture/frontend.md).

## Consequences

- A feature may import from `shared/`, and from another feature only through its `index.ts`.
- `shared/` never imports from `features/`.
- Backend and frontend use the same feature names (`memories`, `reminders`, ...), so
  a change is easy to follow across both.
