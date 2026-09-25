# Backend Architecture

Code: [`apps/backend/`](../../apps/backend). Status: **design**. There's no code yet; this document is the plan the code will follow.
Decisions: [ADR 0002](../architecture_decisions/0002-language-and-stack.md) (Python + FastAPI),
[ADR 0003](../architecture_decisions/0003-backend-four-layer-architecture.md) (four layers).

## The idea in one paragraph

Muninn's backend has a **core** that knows what a memory is, what a reminder is, and
how a conversation works. Around that core sit **adapters** for everything outside our
control: WhatsApp, speech-to-text, the LLM, the database, the clock. The core never
talks to them directly. It talks to **ports** (abstract classes) that it defines itself,
and the adapters implement them. That's why we can test the core with fakes and swap
local Whisper for a hosted API without touching business logic.

## The four layers

```
            ┌──────────────────────────────────────────────────────────┐
  HTTP in   │  api/        FastAPI routers + Pydantic schemas          │
            │              parse request → call service → return JSON  │
            ├──────────────────────────────────────────────────────────┤
            │  services/   use-cases: "handle incoming message",       │
            │              "save memory", "schedule reminder"          │
            │              orchestrate domain objects through ports    │
            ├──────────────────────────────────────────────────────────┤
  the core  │  domain/     entities, value objects, business rules,    │
            │              PORTS (abstract classes). Pure Python.      │
            ├──────────────────────────────────────────────────────────┤
  world out │  adapters/   port implementations: WhatsApp, Whisper,    │
            │              LLM, SQL, encryption, in-memory fakes       │
            └──────────────────────────────────────────────────────────┘
                      bootstrap.py wires adapters into services
```

### The dependency rule

Arrows mean "is allowed to import":

```
api ──► services ──► domain ◄── adapters
                        ▲
                  bootstrap.py  (the only module that imports adapters/)
```

| Layer | May import | Must NOT import |
|---|---|---|
| `domain/` | the standard library only | FastAPI, Pydantic, SQLAlchemy, any SDK, any other layer |
| `services/` | `domain/` | `adapters/`, `api/`, FastAPI, database drivers |
| `adapters/` | `domain/`, vendor SDKs and drivers | `services/`, `api/` |
| `api/` | `services/`, `domain/` (for mapping) | `adapters/` |
| `bootstrap.py` | everything | none |

**Why ports live in `domain/` and not in `adapters/`:** if the abstract class lived
next to its implementations, services would have to import `adapters/` to use it,
and the arrow would point the wrong way. The core says *what it needs*; adapters point
inward and provide it.

## Layout

```
apps/backend/
├── pyproject.toml               # uv, ruff, mypy --strict, pytest (asyncio auto)
├── Dockerfile                   # multi-stage: uv builder → slim non-root runtime
└── app/
    ├── main.py                  # create_app(): FastAPI factory + lifespan
    ├── config.py                # Settings (pydantic-settings), reads APP_ENV etc.
    ├── bootstrap.py             # composition root: Settings → adapters → services
    │
    ├── domain/
    │   ├── exceptions.py        # DomainError, ValidationError (base categories)
    │   ├── memories/
    │   │   ├── models.py        # Memory (entity), MemoryKind (note / location / loan ...)
    │   │   ├── exceptions.py
    │   │   └── ports.py         # MemoryRepository
    │   ├── reminders/
    │   │   ├── models.py        # Reminder, rules like "due time must be in the future"
    │   │   └── ports.py         # ReminderRepository, Clock
    │   ├── messaging/
    │   │   ├── models.py        # IncomingMessage (text | voice), OutgoingMessage
    │   │   └── ports.py         # MessagingChannel: send text, download media
    │   ├── transcription/
    │   │   ├── models.py        # Transcript (text, language, confidence)
    │   │   └── ports.py         # Transcriber
    │   └── agent/               # ADR 0006: our own harness
    │       ├── models.py        # Message, ToolCall, ToolResult, ModelResponse (no SDK types)
    │       └── ports.py         # LanguageModel
    │
    ├── services/
    │   ├── exceptions.py        # NotFoundError, ConflictError, UnavailableError, ...
    │   ├── agent/               # details: agent.md
    │   │   ├── harness.py       # the agent loop: model → tools → model, step limit, timeout
    │   │   ├── tools.py         # tool definitions; each calls a feature service
    │   │   └── prompts/         # system prompts as files
    │   ├── conversation/
    │   │   └── service.py       # ConversationService: the main flow, see below
    │   ├── memories/
    │   │   └── service.py       # MemoryService: save, search, edit, delete, export
    │   └── reminders/
    │       └── service.py       # ReminderService: schedule, list, cancel, fire due ones
    │
    ├── adapters/
    │   ├── messaging/
    │   │   ├── fake.py          # FakeChannel: records sent messages (tests, dev)
    │   │   └── whatsapp.py      # real WhatsApp adapter (integration method: ADR pending)
    │   ├── transcription/
    │   │   ├── fake.py          # returns a fixed transcript
    │   │   └── whisper.py       # local faster-whisper / ivrit.ai (ADR pending)
    │   ├── llm/
    │   │   ├── fake.py          # scripted responses for tests
    │   │   └── openai_compatible.py  # OpenAI, Ollama, vLLM, OpenRouter, ...
    │   ├── storage/
    │   │   ├── memory.py        # in-memory repositories (tests, dev)
    │   │   └── sql.py           # encrypted SQL storage (ADR pending)
    │   └── clock/
    │       └── system.py        # real clock; tests use a fixed clock
    │
    └── api/
        ├── deps.py              # FastAPI Depends(): pulls services from the container
        ├── errors.py            # exception category → HTTP status, in ONE place
        ├── health.py            # GET /health (unversioned)
        └── v1/
            ├── router.py        # mounts every feature router under /api/v1
            ├── webhooks/        # POST /webhooks/whatsapp: incoming messages
            ├── memories/        # CRUD for the dashboard
            └── reminders/       # list / cancel for the dashboard

scripts/                         # backend-only scripts that import app/ (seed data, smoke tests)
tests/                           # mirrors app/ (apps/backend/tests/): domain/ services/ adapters/ api/
```

## Example: a voice note travels through the layers

*(voice note) "I lent Guy 200 shekels"*

```
1. api/v1/webhooks/router.py      WhatsApp calls our webhook.
                                  Validate the payload shape (Pydantic),
                                  build an IncomingMessage, call the service.
                                  Return 200 right away; process in the background.

2. services/conversation          ConversationService.handle(message):
                                    a. voice? → Transcriber port → "I lent Guy 200 shekels"
                                    b. agent harness → LanguageModel port → the model
                                       asks for the save_memory tool
                                    c. the tool calls MemoryService.save(...)
                                    d. the model writes the reply
                                    e. MessagingChannel port → "Got it."

3. domain/memories                Memory(...) validates itself: text not empty,
                                  amount positive, etc. Pure Python rules.

4. adapters/                      whisper.py does the transcription,
                                  sql.py encrypts and stores,
                                  whatsapp.py sends the reply.
```

Notice that steps 2 and 3 never mention Whisper, SQL or WhatsApp by name. In tests we
use `FakeChannel`, a fake transcriber and in-memory storage, and the same code runs
with no network.

## Per-layer conventions

### domain/
- `@dataclass` entities and `@dataclass(frozen=True)` value objects. They validate
  in `__post_init__` and raise a `ValidationError` subclass with a machine-readable `code`.
- Business rules live **here and only here**.
- Ports are `abc.ABC` classes with `@abstractmethod`. All I/O ports are `async`.
- No framework imports. That's what makes domain tests instant.

### services/
- One folder per feature: `services/<feature>/service.py` (+ `exceptions.py`).
- Takes primitives in, builds domain objects (which validate), returns domain objects.
  Never accepts or returns Pydantic models.
- Gets its ports through the constructor: `MemoryService(memories=..., clock=...)`.
- Feature exceptions subclass a **category** from `services/exceptions.py`, so the API
  layer can map them without knowing the feature.

### adapters/
- One folder per port family: `adapters/<port>/<technology>.py`.
- Converting between domain objects and rows / API payloads happens **inside** the adapter.
- Every port has a **fake** adapter. That's what tests and local dev use.
- Every adapter of the same port passes the same **contract tests**.

### api/
- Versioned: feature routers in `api/v1/<feature>/`, mounted under `/api/v1`.
- Each feature has `router.py` + `schemas.py`. A router does three things:
  parse → call service → serialize. No business logic.
- Pydantic checks **shape** (types, required fields). The domain checks **rules**.
  We don't duplicate rules in Pydantic.
- Errors are mapped once in `api/errors.py`:

  | Exception category | HTTP |
  |---|---|
  | `domain.ValidationError` | 422 |
  | `services.NotFoundError` | 404 |
  | `services.ConflictError` | 409 |
  | `services.UnavailableError` | 503 |
  | other `DomainError` | 400 |
  | other `ServiceError` | 500 |

  Error body: `{"error": {"code": "reminder_in_past", "message": "..."}}`

### bootstrap.py
- The composition root. Reads `Settings`, picks the adapters, builds the services,
  and owns adapter lifecycle (open DB, load the Whisper model once, close on shutdown).

### No globals
- There is no global `settings` and no global `app`. Uvicorn starts the app with
  `uvicorn app.main:create_app --factory`, and tests call `create_app(settings)`.
- Clients (database engine, HTTP clients, the Whisper model) are created once in
  `bootstrap.py`, stored on the `Container`, and passed into services through their
  constructors. Routers get services through `api/deps.py`.
- Why: every dependency is visible in a constructor signature, nothing runs at
  import time, and a test can swap any piece without monkeypatching a module.
- File locations never come from counting folder levels. The root `.env` is found by
  looking for `.env.example`; anything else (like where data is stored) is a setting.

## Configuration and environments

One `.env` file at the repo root, read by both the backend (pydantic-settings) and
Docker Compose. Copy `.env.example` to `.env` to start. `.env` is gitignored.

`APP_DOMAIN` is the public domain (for example `muninn.example.com`), used for the
WhatsApp webhook URL, links and CORS. `APP_ENV` says where the app is running:

| `APP_ENV` | Used for | Behavior |
|---|---|---|
| `DEV` | your laptop | hot reload, debug logs, `/docs` (Swagger) on, fake adapters allowed |
| `STAGE` | a test server with a test WhatsApp number | production build, real adapters, `/docs` on |
| `PROD` | the real server | production build, real adapters, JSON logs, `/docs` off, refuses to start with fake adapters |

New settings get added to `.env.example` with a comment when the feature that needs
them is built. Secrets never go into the repo or into logs.

## Adding a feature: checklist

1. `domain/<feature>/`: `models.py` (rules), `exceptions.py`, `ports.py` if it needs the outside world.
2. `adapters/<port>/`: a `fake.py` first, then the real one. Add both to the contract tests.
3. `services/<feature>/service.py`: the use-case, exceptions subclass a category.
4. `api/v1/<feature>/`: `router.py` + `schemas.py`, then register the router in `api/v1/router.py`.
5. Wire it in `bootstrap.py`.
6. Tests in each mirrored folder under `tests/`.

## Tooling

| Tool | Purpose |
|---|---|
| `uv` | dependencies and virtualenv. Never `pip`, never `requirements.txt` |
| `ruff` | lint + format |
| `mypy --strict` | types |
| `pytest` + `pytest-asyncio` | tests (async everywhere) |
