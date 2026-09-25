# Architecture Decision Records

This folder is where we write down the **important technical decisions** in Muninn:
what we chose, what else we considered, and *why*.

Code shows *what* we built. ADRs explain *why we built it that way*. A year from now,
when someone asks "why didn't you just use X?", the answer should be here.

## How it works

- One decision = one file: `NNNN-short-title.md`
- Copy [`0000-template.md`](0000-template.md) to start a new one
- Every ADR has a **status**:
  - `Proposed`: under discussion, open for comments
  - `Accepted`: decided, we build on it
  - `Superseded by NNNN`: replaced by a newer decision (we never delete old ADRs)
- To discuss a proposed ADR, open an issue or comment on its pull request

## Index

| # | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-language-and-stack.md) | Language and stack: Python backend, React + TypeScript frontend | Accepted |
| [0003](0003-backend-four-layer-architecture.md) | Backend: four layers (api / services / domain / adapters) | Accepted |
| [0004](0004-frontend-feature-based-structure.md) | Frontend: organize code by feature | Accepted |
| [0005](0005-monorepo-apps-layout.md) | Monorepo layout: `apps/backend` and `apps/dashboard` | Accepted |
| [0006](0006-own-agent-harness.md) | Agent harness: build our own, then evolve it | Accepted |
| [0007](0007-llm-providers.md) | LLM providers: OpenAI first, then Claude, then local models | Accepted |

## Coming next

- How we connect to WhatsApp (official Cloud API vs a self-hosted bridge)
- Speech-to-text engine for Hebrew and Russian (local Whisper / ivrit.ai vs hosted API)
- Storage and encryption at rest (SQLite + SQLCipher? Postgres + app-level encryption?)
- How memories are recalled (all in the prompt vs embeddings)
- Reminder scheduler and timezone handling
