# AGENTS.md: working on Muninn

Instructions for anyone working in this repo: new contributors, and AI coding
assistants (Claude Code, Codex, Cursor, Copilot, ...) starting a fresh session.
`CLAUDE.md` just points here, so there is one source of truth.

## What Muninn is

A self-hosted AI assistant on WhatsApp that remembers things for people: save a memory
("I parked on floor 3"), find it later ("where did I park?"), get reminders at the right
time. Voice notes in Hebrew and Russian are the most important input. Data is stored on
the user's own server. It's also a teaching project: code and docs are written to be
read by junior developers.

**Status:** early. The backend skeleton and the agent harness exist. No WhatsApp,
memories, reminders or dashboard code yet. Check `git log` and the roadmap in
[README.md](README.md) for where things are.

## Read these first

1. [docs/architecture/backend.md](docs/architecture/backend.md): the four layers and the dependency rule
2. [docs/architecture/agent.md](docs/architecture/agent.md): the agent harness, tools, the `LanguageModel` port
3. [docs/architecture_decisions/](docs/architecture_decisions/): every significant decision and why (ADRs)
4. [docs/architecture/dashboard.md](docs/architecture/dashboard.md): only if touching the web dashboard

**Docs first:** `docs/` is the source of truth. If code would contradict a doc, update
the doc in the same change (or ask first). A significant new technical choice gets a new
ADR (next number, copy `0000-template.md`). Accepted ADRs are never rewritten, only
superseded by a newer one.

## Layout

```
apps/backend/          Python 3.12 + FastAPI, four layers (backend.md)
  app/
    domain/            entities, rules, PORTS (abstract classes). Standard library only.
    services/          use-cases; services/agent/ is the harness (agent.md)
    adapters/          port implementations (llm/, clock/, ...). Only bootstrap imports these.
    api/               FastAPI routers + schemas; api/v1/ is versioned
    config.py          Settings (APP_ENV, APP_DOMAIN, LLM_*)
    bootstrap.py       composition root: builds adapters and services
    main.py            create_app() factory
  tests/               mirrors app/
  scripts/             backend-only scripts
apps/dashboard/        React + TypeScript + Tailwind, by feature (no code yet)
docs/                  architecture/ (how it works now), architecture_decisions/ (ADRs), assets/
scripts/               repo-wide scripts
Makefile               every command; run `make` to list them
.env.example           every config key; copy to .env
```

## Commands

```bash
make env          # create .env from .env.example
make sync         # install backend dependencies (uv)
make hooks        # install git hooks (once per clone)
make run          # backend locally with hot reload: http://localhost:8000/docs
make check        # everything CI runs: pre-commit checks + tests. Green before every commit.
make test         # backend tests only
make coverage     # tests with a coverage report
make audit        # dependencies vs known vulnerabilities
make dev-up       # full stack in Docker (DEV); make dev-down to stop
```

## Rules

**Backend**
- `uv` only: `uv add`, `uv run`. Never `pip`, never `requirements.txt`.
- Python 3.12+, `from __future__ import annotations`, async for anything that does I/O.
- Dependency rule: `api -> services -> domain <- adapters`. Ports live in
  `domain/<feature>/ports.py`. Only `bootstrap.py` and tests import `adapters/`.
- No globals: no global `settings`, no global `app`, no global clients. Everything is
  built in `bootstrap.py` and passed through constructors or `api/deps.py`.
- Pydantic checks shape; the domain checks rules. Don't duplicate rules in schemas.
- Errors: raise a subclass of a category (`ValidationError`, `NotFoundError`,
  `ConflictError`, `UnavailableError`). `api/errors.py` maps them to HTTP. Never raise
  `HTTPException` for business failures.
- File paths never come from counting folder levels. Use a setting or a marker file.
- `ruff` and `mypy --strict` must pass. Tests mirror `app/`; use fakes, not the network.

**Agent**
- Provider SDK types never leave `adapters/llm/`. The harness only knows `domain/agent` types.
- Tools are thin: they call a service. Business rules stay in the domain.
- Prompts are files in `services/agent/prompts/`, not strings in code.
- Never log what users said (messages, tool arguments, tool results) outside DEV.

**Security and privacy**
- Never commit secrets. Real keys go in `.env` (gitignored). `.env.example` has empty values.
- Secrets are `SecretStr` in settings, so they never print.
- Never put real personal data in tests, fixtures, issues or logs. Use made-up examples.

**Docs**
- English, plain words, short sentences. Explain *why*, not only *what*.
- No emojis in docs.
- Code comments explain *why*; don't narrate what the code obviously does.

**Git**
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `refactor:`, `test:`).
  A git hook checks the format.
- Small, focused commits. `make check` green first.

## For AI coding assistants

- Read the docs listed above before changing code. Follow the existing patterns.
- Commit or push only when asked.
- Ask before: adding a dependency, creating a new ADR, deleting files, or changing
  anything under `.github/`.
- When a request is a question ("do we need X?"), answer and recommend; don't implement
  until asked.
- Run `make check` before saying a change is done, and report failures honestly.
