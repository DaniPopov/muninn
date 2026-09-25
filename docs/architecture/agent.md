# Agent Architecture

Status: **design**. There's no code yet; this document is the plan the code will follow.
Decisions: [ADR 0006](../architecture_decisions/0006-own-agent-harness.md) (our own harness),
[ADR 0007](../architecture_decisions/0007-llm-providers.md) (OpenAI first, then Claude, then local).

## What the agent does

One WhatsApp message in, one reply out. In between, the model may call our tools:

```
user:       "I lent Guy 200 shekels, remind me Friday to ask for it back"

step 1      model → tool calls: save_memory(text="Lent Guy 200 shekels")
                                create_reminder(text="Ask Guy for the 200 shekels",
                                                due_at="2026-10-02T10:00:00+03:00")
            harness runs both tools, sends the results back to the model
step 2      model → text: "Saved. I'll remind you Friday, Oct 2 at 10:00."

reply:      "Saved. I'll remind you Friday, Oct 2 at 10:00."
```

## Words we use

| Word | Meaning |
|---|---|
| **turn** | one user message and everything until the reply |
| **step** | one call to the model inside a turn. A turn has 1 or more steps |
| **tool** | a function the model may ask us to run (`save_memory`, `search_memories`, ...) |
| **tool call** | the model asking to run one tool with specific arguments |
| **history** | earlier messages of the chat, sent along so follow-ups work |
| **harness** | the loop that runs a turn: model, tools, model, ... until a text reply |

## Where it lives

```
domain/agent/                 pure Python, no SDK imports
├── models.py                 Role, Message, ToolCall, ToolDefinition, ModelResponse, TokenUsage
├── exceptions.py             LanguageModelError, LanguageModelUnavailableError
└── ports.py                  LanguageModel

services/agent/
├── harness.py                AgentHarness: runs one turn
├── tools.py                  Tool base class + ToolRegistry
├── exceptions.py             AgentUnavailableError
└── prompts/
    └── system.md             the system prompt, a file, not a string in code

adapters/llm/
├── fake.py                   FakeLanguageModel: scripted responses for tests
└── openai_compatible.py      OpenAI, and any server that speaks the same API
```

Dependency rule as everywhere ([backend.md](backend.md)): the harness knows the
`LanguageModel` port, never an SDK. **Provider SDK types never leave `adapters/llm/`.**

## Domain types

Our own types, so every provider maps to the same shapes:

```python
class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass(frozen=True)
class ToolCall:
    id: str                    # provider's id, echoed back with the result
    name: str
    arguments: dict[str, Any]  # already parsed from JSON by the adapter

@dataclass(frozen=True)
class Message:
    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()   # only on ASSISTANT messages
    tool_call_id: str | None = None         # only on TOOL messages

@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema of the arguments

@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int

@dataclass(frozen=True)
class ModelResponse:
    text: str                        # empty when the model only calls tools
    tool_calls: tuple[ToolCall, ...]
    usage: TokenUsage
```

## The port

```python
class LanguageModel(ABC):
    @abstractmethod
    async def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolDefinition]
    ) -> ModelResponse:
        """One model call. Raises LanguageModelUnavailableError on timeouts,
        rate limits, 5xx and network errors; LanguageModelError on anything else."""
```

One method on purpose. Streaming isn't needed: WhatsApp gets the whole reply at once.

## Tools

A tool is a small class: a name, a description the model reads, a Pydantic model for
its arguments, and `run()`. Each tool gets the services it needs in its constructor,
so a tool is a thin wrapper around an existing use-case.

```python
class SaveMemoryArgs(BaseModel):
    text: str = Field(description="What to remember, in the user's own words")

class SaveMemoryTool(Tool[SaveMemoryArgs]):
    name = "save_memory"
    description = "Save something the user wants remembered."
    args_model = SaveMemoryArgs

    def __init__(self, memories: MemoryService) -> None:
        self._memories = memories

    async def run(self, args: SaveMemoryArgs) -> str:
        memory = await self._memories.save(args.text)
        return f"Saved memory {memory.id}"
```

- The JSON Schema sent to the model comes from `args_model.model_json_schema()`.
  Pydantic validates the model's arguments before `run()` is called.
- A tool returns **text for the model**, not for the user. The model writes the reply.
- `ToolRegistry` holds the tools of a harness and turns them into `ToolDefinition`s.

### When a tool call goes wrong

The turn must not crash because the model made a mistake. Errors go **back to the model**
as the tool result, so it can fix its call or explain to the user:

| What happened | Tool result sent to the model |
|---|---|
| unknown tool name | `error: no tool named 'x'` |
| arguments fail validation | `error: invalid arguments: <pydantic message>` |
| domain `ValidationError` (e.g. reminder in the past) | `error: <the domain message>` |
| any other exception | `error: the tool failed` (details go to our log, not to the model) |

## The loop

```
run_turn(user_text, history) -> TurnResult

    messages = [system prompt] + history + [user message]

    for step in 1..MAX_STEPS:
        response = await model.complete(messages, tool_definitions)

        if response has no tool calls:
            return TurnResult(reply=response.text, ...)

        messages += assistant message with the tool calls
        for each tool call, in order:
            result = run the tool (errors become "error: ..." results, see above)
            messages += tool message(tool_call_id, result)

    return TurnResult(reply=FALLBACK_REPLY, ...)   # model never gave a text answer
```

- The whole turn runs inside `asyncio.timeout(TURN_TIMEOUT)`.
- Tool calls run **one after another** in v1. Simpler to follow and to log; running them
  in parallel is a later optimization.
- If the model is unavailable, the harness raises `AgentUnavailableError` (a
  `services.UnavailableError`). The caller decides what the user sees, for example
  "Sorry, I can't answer right now, try again in a minute."

### TurnResult

```python
@dataclass(frozen=True)
class TurnResult:
    reply: str
    new_messages: tuple[Message, ...]   # user message + everything the turn added
    steps: int
    usage: TokenUsage                   # summed over all steps
```

The harness is **stateless**: it gets history in and returns `new_messages` out. Storing
chat history is the job of the conversation service, not the harness.

### Limits (v1 defaults)

| Limit | Default | Why |
|---|---|---|
| `MAX_STEPS` | 5 | a normal turn needs 1–3; more means the model is stuck |
| `TURN_TIMEOUT` | 30 s | the user is waiting on their phone |
| model call timeout | 20 s | set in the adapter's HTTP client |
| history sent | last 20 messages | enough for follow-ups, keeps each call small and cheap |
| tool result length | 4,000 characters | a huge search result must not flood the context |

They start as constants in `harness.py` and become settings only if someone needs to
change them.

## The system prompt

`services/agent/prompts/system.md`, loaded once at startup. Placeholders are filled on
every turn:

- `{now}`: the current date and time with the user's timezone, so "Tuesday at 10"
  can be turned into an exact time.
- `{timezone}`: e.g. `Asia/Jerusalem`.

What the prompt tells the model, in short:

- You are Muninn, a memory assistant on WhatsApp.
- Reply in the language the user wrote in (Hebrew, Russian, English).
- Keep replies short. Confirm what you saved and when you'll remind.
- Only answer from saved memories. If nothing matches, say so. Never invent.

Prompts are files so they can be reviewed in pull requests like code.

## Logging (our tracing)

Every step writes one structured log line:

```
agent.step  turn_id=… step=2 model=… input_tokens=812 output_tokens=41 duration_ms=930
agent.tool  turn_id=… step=2 tool=save_memory ok=true duration_ms=4
agent.turn  turn_id=… steps=2 input_tokens=1510 output_tokens=77 duration_ms=1880
```

**Privacy rule:** message text, tool arguments and tool results are logged **only in
DEV**. In STAGE and PROD we log names, counts and durations, never what the user said.
The API key is a `SecretStr` and is never logged.

## The OpenAI-compatible adapter

`adapters/llm/openai_compatible.py` uses the official `openai` Python SDK with a
configurable base URL (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`).

- It uses the **Chat Completions API**, not OpenAI's newer Responses API. Chat
  Completions is the format Ollama, vLLM, OpenRouter and most other servers copy, so one
  adapter covers all of them ([ADR 0007](../architecture_decisions/0007-llm-providers.md)).
- It maps our `Message` / `ToolDefinition` to the API's format and the response back to
  `ModelResponse`, parsing tool-call arguments from JSON. Arguments that aren't valid
  JSON become an `error:` tool result instead of crashing the turn.
- It translates SDK errors: timeouts, rate limits, 5xx and connection errors become
  `LanguageModelUnavailableError`; everything else `LanguageModelError`.

The Claude adapter comes later and maps the same types to Anthropic's Messages API.

## Testing

`FakeLanguageModel` takes a script of responses and records what it received:

```python
model = FakeLanguageModel([
    ModelResponse(text="", tool_calls=(ToolCall("1", "save_memory", {"text": "floor 3"}),), ...),
    ModelResponse(text="Saved.", tool_calls=(), ...),
])
```

Tests for the harness, all offline:

- a text-only answer ends the turn in one step
- a tool call is run and its result reaches the model in the next step
- several tool calls in one step run in order
- unknown tool, invalid arguments, and a failing tool become `error:` results
- `MAX_STEPS` stops a model that never answers, with the fallback reply
- the turn timeout fires
- an unavailable model raises `AgentUnavailableError`
- history goes in, `new_messages` comes out, usage is summed

The OpenAI adapter's mapping is tested against recorded API responses, without a network.

## Trying it before WhatsApp exists

`apps/backend/scripts/chat.py`: a terminal chat with the real model and a couple of toy
tools (for example `get_current_time`). In DEV it prints each step, so you can watch
the loop work:

```bash
cd apps/backend && uv run python scripts/chat.py
```

## Not in v1

- Summarizing long conversations
- Retries and a fallback model
- Running tool calls in parallel
- Asking the user to confirm destructive tools
- Evaluation tests against real models in Hebrew and Russian

## Open questions

- Which OpenAI model goes into `LLM_MODEL` (cost against speed).
- How tools will know **who** the user is, once there's more than one user.
