# 0002. Language and stack: Python backend or full TypeScript

- **Status:** Proposed. Open for discussion.
- **Date:** 2026-09-24
- **Deciders:** @DaniPopov

## Context

Muninn has three main parts:

1. **Backend**: receives WhatsApp webhooks, runs the AI agent, stores memories,
   schedules reminders.
2. **Speech-to-text (STT)**: turns Hebrew and Russian voice notes into text. This is
   the most important feature for our target users.
3. **Frontend** *(later)*: a small web dashboard to browse, edit and delete memories.

The frontend will be **React + TypeScript** either way. The open question is the backend.

Things that matter for this decision:

- **Privacy.** "Your data stays on your server" is a core promise. That pushes us
  toward running STT *locally* instead of sending voice notes to a cloud API.
- **Hebrew STT quality.** The best open Hebrew models (e.g. [ivrit.ai](https://www.ivrit.ai/)
  fine-tuned Whisper) and the main local runtimes (`faster-whisper`, Hugging Face
  `transformers`) are Python-first.
- **WhatsApp.** The official Cloud API is plain HTTP and works from any language. The
  popular unofficial libraries (Baileys, whatsapp-web.js) are Node-only. See [ADR 0003](0003-whatsapp-integration.md).
- **Contributors.** Easier to attract contributors if the stack is common and simple.
- **Maintainer experience.** The maintainer's existing agent backends are FastAPI.

## Options considered

### Option A: Python backend (FastAPI) + React/TypeScript frontend

- 👍 Direct access to the Python ML ecosystem: local Whisper / ivrit.ai models in
  the same process, no extra service.
- 👍 Mature LLM SDKs, encryption libraries (`cryptography`, SQLCipher bindings).
- 👍 FastAPI generates an OpenAPI schema, so the frontend can **generate TypeScript
  types** from it. We still get end-to-end type safety.
- 👍 Matches the maintainer's existing experience.
- 👎 Two languages in the repo, two toolchains (`uv` + `pnpm`).
- 👎 If we ever want an unofficial WhatsApp bridge, it would be a separate Node sidecar.

### Option B: Full TypeScript (Node backend + React frontend)

- 👍 One language, one toolchain, shared types without codegen.
- 👍 Native access to Baileys / whatsapp-web.js if we go the unofficial-bridge route.
- 👍 Large pool of JS/TS contributors.
- 👎 Local STT is harder: we'd need `whisper.cpp` Node bindings (limited model
  choice, harder to use ivrit.ai checkpoints) **or** a Python sidecar anyway,
  which removes the "one language" benefit.
- 👎 Weaker ecosystem for ML and audio processing.

### Option C: TypeScript backend + Python STT microservice

- 👍 Each part uses its best ecosystem.
- 👎 Two services to deploy and debug for a project whose principle is *"boring to run"*.
  Too much for a self-hosted app for one family.

## Decision (proposed)

**Option A: Python (FastAPI) backend, React + TypeScript frontend**, with
TypeScript types generated from the backend's OpenAPI schema.

The deciding factor: voice is our most important feature, and the best way to do
private, high-quality Hebrew/Russian STT today is in Python. Picking TypeScript would
most likely end in Option C, which breaks our "boring to run" principle.

## Consequences

- Monorepo layout (proposed): `backend/` (Python, `uv`), `frontend/` (React, TS, `pnpm`),
  `docs/`.
- CI must run two toolchains.
- If [ADR 0003](0003-whatsapp-integration.md) ends up needing a Node-only WhatsApp
  bridge, we'll run it as an optional container behind an HTTP interface. We will
  **not** rewrite the backend.
- We should revisit this if a strong Node-native Hebrew STT option appears.
