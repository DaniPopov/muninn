# 0002. Language and stack: Python backend, React + TypeScript frontend

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** @DaniPopov

## Context

Muninn has three main parts:

1. **Backend**: receives WhatsApp messages, runs the AI agent, stores memories,
   schedules reminders.
2. **Speech-to-text (STT)**: turns Hebrew and Russian voice notes into text. This is
   the most important feature for our target users.
3. **Frontend**: a small web dashboard to browse, edit and delete memories and reminders.

Things that matter for this decision:

- **Privacy.** "Your data stays on your server" is a core promise. That pushes us
  toward running STT *locally* instead of sending voice notes to a cloud API.
- **Hebrew STT quality.** The best open Hebrew models (e.g. [ivrit.ai](https://www.ivrit.ai/)
  fine-tuned Whisper) and the main local runtimes (`faster-whisper`, Hugging Face
  `transformers`) are Python-first.
- **Contributors.** A common, simple stack makes it easier for people to contribute.
- **Maintainer experience.** The maintainer's existing agent backends are FastAPI.

## Options considered

### Option A: Python backend (FastAPI) + React/TypeScript frontend

- Pro: Direct access to the Python ML ecosystem: local Whisper / ivrit.ai models in
  the same process, no extra service.
- Pro: Mature LLM SDKs, encryption libraries (`cryptography`, SQLCipher bindings).
- Pro: FastAPI generates an OpenAPI schema, so the frontend can **generate TypeScript
  types** from it. We still get end-to-end type safety.
- Pro: Matches the maintainer's existing experience.
- Con: Two languages in the repo, two toolchains (`uv` + `pnpm`).

### Option B: Full TypeScript (Node backend + React frontend)

- Pro: One language, one toolchain, shared types without codegen.
- Pro: Large pool of JS/TS contributors.
- Con: Local STT is harder: we'd need `whisper.cpp` Node bindings (limited model
  choice, harder to use ivrit.ai checkpoints) **or** a Python sidecar anyway,
  which removes the "one language" benefit.
- Con: Weaker ecosystem for ML and audio processing.

### Option C: TypeScript backend + Python STT microservice

- Pro: Each part uses its best ecosystem.
- Con: Two services to deploy and debug for a project whose principle is *"boring to run"*.
  Too much for a self-hosted app for one family.

## Decision

**Option A.**

| Part | Stack |
|---|---|
| Backend | Python 3.12, FastAPI, `uv`. Structured as 4 layers, see [ADR 0003](0003-backend-four-layer-architecture.md) |
| Frontend | React + TypeScript (strict), Vite, **Tailwind CSS**, `pnpm`. Organized by feature, see [ADR 0004](0004-frontend-feature-based-structure.md) |
| Glue | TypeScript types generated from the backend's OpenAPI schema |
| Running it | Docker Compose at the repo root |

The deciding factor: voice is our most important feature, and the best way to do
private, high-quality Hebrew/Russian STT today is in Python. Picking TypeScript would
most likely end in Option C, which breaks our "boring to run" principle.

## Consequences

- Monorepo layout: `backend/` (Python, `uv`), `frontend/` (React, TS, `pnpm`), `docs/`.
- CI must run two toolchains.
- If we ever need a Node-only library (for example a WhatsApp bridge), it runs as a
  separate container behind an HTTP interface. We will **not** rewrite the backend.
- Worth revisiting if a strong Node-native Hebrew STT option appears.
