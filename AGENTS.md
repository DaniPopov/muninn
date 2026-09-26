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

**Status:** early development (Phase 1 in the [README roadmap](README.md#roadmap)).

| Built and tested | Not built yet |
|---|---|
| Backend skeleton: config, `/health`, error mapping, Docker, CI, security checks | Memories (next) |
| Agent harness: tool loop, limits, logging (`services/agent/`) | Reminders |
| OpenAI-compatible adapter (`adapters/llm/`), tested offline and against the real API | WhatsApp (Twilio adapter), voice / speech-to-text |
| ngrok tunnel for local webhooks (`make tunnel-up`) | Storage (in-memory only), dashboard |
| Terminal chat with demo tools (`make chat`) | |

Decisions so far (details in the ADRs): Python + FastAPI backend in four layers, React +
TypeScript + Tailwind dashboard by feature, `apps/` monorepo, **our own agent harness**
(no framework), **OpenAI first** (`gpt-6-luna`), then Claude, then local models,
**WhatsApp through Twilio first**. Open: speech-to-text engine, storage and encryption,
how memories are recalled. Check `git log` for the latest.

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
    config.py          Settings (APP_ENV, APP_DOMAIN, LLM_*); see "Configuration" below
    bootstrap.py       composition root: builds adapters and services
    main.py            create_app() factory
  tests/               mirrors app/
  scripts/             backend-only scripts
apps/dashboard/        React + TypeScript + Tailwind, by feature (no code yet)
docs/                  architecture/ (how it works now), architecture_decisions/ (ADRs), assets/
scripts/               repo-wide scripts
Makefile               every command; run `make` to list them
.env.example           every config key; copy to .env (gitignored)
ngrok.example.yml      local tunnel config; copy to ngrok.yml (gitignored)
```

## Commands

```bash
make env          # create .env from .env.example
make sync         # install backend dependencies (uv)
make hooks        # install git hooks (once per clone)
make run          # backend locally with hot reload: http://localhost:8000/docs
make chat         # talk to the agent in the terminal (real model, demo tools)
make check        # everything CI runs: pre-commit checks + tests. Green before every commit.
make test         # backend tests only
make coverage     # tests with a coverage report
make audit        # dependencies vs known vulnerabilities
make dev-up       # full stack in Docker (DEV); make dev-down to stop
make tunnel-up    # ngrok: public HTTPS URL to your local backend, for Twilio webhooks
```

## Configuration

Everything comes from environment variables, documented in [.env.example](.env.example).
One `.env` at the repo root feeds both Docker Compose and the backend.

| Variables | What |
|---|---|
| `APP_ENV`, `APP_DOMAIN` | DEV / STAGE / PROD, and the public domain |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_REASONING_EFFORT` | the model. With `gpt-6-luna` over Chat Completions, `LLM_REASONING_EFFORT=none` is **required** or tool calls are rejected (400) |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` | WhatsApp through Twilio (not wired yet) |
| `NGROK_AUTHTOKEN` | DEV tunnel only |
| `BACKEND_PORT`, `DASHBOARD_PORT`, `DASHBOARD_DEV_PORT` | ports on the host |

Deployment config and secrets live in `.env`. Settings people will change while the app
runs (model, timezone) are planned to move to the database and the dashboard later;
API keys stay in `.env`.

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
- Tests use `FakeLanguageModel`; the adapter is tested with a fake HTTP server. Real API
  calls cost money and are only for manual checks.

**Security and privacy**
- Never commit secrets. Real keys go in `.env` (gitignored). `.env.example` has empty values.
  `ngrok.yml` is gitignored too (it has a personal domain); `ngrok.example.yml` is the template.
- Never read or print the values in `.env`. To check config, print whether a value is set.
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
