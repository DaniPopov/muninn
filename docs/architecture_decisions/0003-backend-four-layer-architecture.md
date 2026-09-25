# 0003. Backend: four layers (api / services / domain / adapters)

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** @DaniPopov

## Context

Muninn talks to a lot of outside systems: WhatsApp, a speech-to-text engine, an LLM,
a database, an encryption key, a clock for reminders. **Every one of these will be
swapped at some point.** Local Whisper vs a hosted API, SQLite vs Postgres, one LLM
provider vs another, the real WhatsApp vs a fake one in tests.

We want the important logic (*what counts as a memory? when is a reminder due?*) to be
testable without any of these systems running, and we want swapping one of them to be
a config change, not a rewrite.

## Options considered

### Option A: Flat FastAPI app (routers call the database and SDKs directly)
- Pro: Fastest to start. Fewer files.
- Con: Business rules end up inside HTTP handlers. Hard to test without a real DB and real APIs.
- Con: Swapping STT or the LLM means editing code all over the place.

### Option B: Four layers, hexagonal style (ports & adapters)
- Pro: Business rules live in one place (`domain/`), in pure Python, and have instant unit tests.
- Pro: Every outside system sits behind an interface (a **port**). Swapping it means
  writing a new **adapter** and changing one line of config.
- Pro: Tests use in-memory / fake adapters, so there's no network, no GPU and no WhatsApp account in CI.
- Con: More files and a bit more ceremony for small features.

## Decision

**Option B.** Four layers with a strict dependency rule:

```
api ──► services ──► domain ◄── adapters
                        ▲
                  bootstrap.py (the only file that imports adapters/)
```

The full guide lives in [`docs/architecture/backend.md`](../architecture/backend.md).

## Consequences

- Adding a feature always follows the same checklist (domain → adapters → services → api).
- Contributors need to learn the dependency rule. The backend guide explains it with examples.
- Ports are defined in `domain/`, so the core never depends on any vendor SDK.
