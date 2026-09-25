# 0006. Agent harness: build our own, then evolve it

- **Status:** Accepted
- **Date:** 2026-09-25
- **Deciders:** @DaniPopov

## Context

The agent is the heart of Muninn. It reads a message ("I lent Guy 200 shekels",
"where's my passport?", "remind me Tuesday at 10 to call the doctor"), decides what
to do, calls our code (save a memory, search memories, create a reminder) and replies.

The **harness** is the code around the LLM that makes this work: the loop that sends
messages and tool definitions to the model, runs the tools it asks for, feeds the
results back, and stops when it has an answer.

What Muninn's agent work looks like:

- **Short turns.** One WhatsApp message in, usually 0–3 tool calls, one reply out.
  No long-running tasks, no multi-step plans.
- **Few tools.** Around six: save / search / edit / delete memories, create / list /
  cancel reminders.
- **Latency matters.** A person is waiting for the reply on their phone.
- **Any LLM provider.** Self-hosters must be able to choose, including a local model
  for full privacy. Which provider is the default is a separate decision.
- **Fits our architecture.** Business logic stays in `domain/` and `services/`, outside
  systems stay behind ports ([ADR 0003](0003-backend-four-layer-architecture.md)).
- **It's a learning project.** Muninn is open source and a teaching example. The
  harness is the most interesting part of the system, so we want to understand and
  own every line of it, not configure a black box.

## Options considered

### Option A: [deepagents](https://github.com/langchain-ai/deepagents) (LangChain, built on LangGraph)

An opinionated agent harness for long-horizon work: planning, sub-agents, a filesystem,
shell commands, context summarization, pluggable memory, human-in-the-loop.

- Pro: Many features ready on day one (context summarization, human approval, tracing
  through LangSmith).
- Pro: Model-agnostic through LangChain, including local models (Ollama, vLLM).
- Con: Built for long, multi-step tasks. Most of its features (planning, sub-agents,
  filesystem, shell) we would have to switch off.
- Con: Shell and filesystem tools are a real risk in an app that stores personal data
  and accepts messages from outside. We'd have to actively remove attack surface.
- Con: Heavy dependency tree (LangChain + LangGraph), and it wants to own the loop, the
  state and the persistence, which competes with our own ports and storage.
- Con: Least control over latency.

### Option B: [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)

A lighter framework: agents, tools, handoffs, guardrails, sessions, tracing.

- Pro: Lightweight dependencies. Sessions, guardrails and tracing included.
- Pro: Works with non-OpenAI models through LiteLLM / any-llm.
- Con: Its types (`Agent`, `Runner`, tool decorators) would spread into our services
  layer, or we'd wrap them and gain little.
- Con: For ~6 tools and short turns, it mostly replaces a small loop with a dependency.

### Option C: Our own harness

A small agent loop we write, behind our own ports.

- Pro: Exactly the features we need, nothing we have to remove.
- Pro: Fits the four layers natively: tools are plain service methods, the model sits
  behind a `LanguageModel` port, adapters per provider.
- Pro: Full control over latency: the number of model calls, timeouts, what goes into
  the context.
- Pro: Every line is readable, which is the point of a teaching project.
- Con: We build what frameworks give for free: tracing, retries, context trimming.
- Con: We own the bugs. The loop must be well tested.

## Decision

**Option C: we build our own harness, start small, and grow it when a real need appears.**

### Where it lives

```
domain/agent/
  models.py      Message, ToolCall, ToolResult, ModelResponse: our own types, no SDK types
  ports.py       LanguageModel: "given messages + tool definitions, return text or tool calls"
services/agent/
  harness.py     the loop
  tools.py       tool definitions; each tool calls an existing service (MemoryService, ...)
  prompts/       system prompt(s) as files, not strings buried in code
adapters/llm/
  fake.py        scripted responses, for tests
  openai_compatible.py   one adapter for OpenAI, Ollama, vLLM, OpenRouter and other
                         servers that speak the OpenAI chat API
```

A Claude adapter (and others) can be added next to it. Provider SDK types never leave
`adapters/llm/`.

### Version 1 includes

- **The loop.** Call the model; if it asks for tools, run them and feed back results;
  repeat until it answers with text. With a **maximum number of steps** and a **timeout**,
  so a confused model can't loop forever.
- **Tool definitions from Pydantic models**, so arguments are validated before our code runs.
  A tool that fails returns an error message to the model instead of crashing the turn.
- **Short conversation context:** the last N messages of the chat, so follow-ups
  ("and how much does he owe me?") work. This is separate from saved memories.
- **A structured log of every step:** model call, tool name, arguments, result, duration.
  This is our tracing.
- **Tests with the fake model:** the loop, the step limit, tool errors, and each tool,
  all without a network.

### Added later, when needed

- Summarizing long conversations
- Retries and a fallback model
- Human confirmation before destructive tools (for example "delete all memories")
- Evaluation tests against real models (Hebrew and Russian conversations)

### When to reconsider

Write a new ADR and look at frameworks again if Muninn needs:

- multi-step planning or long-running background work,
- sub-agents or several cooperating agents,
- features that would take us weeks to build but a framework already has.

Because the harness sits behind our own types and ports, a framework-based harness
could then be added as another implementation without changing `domain/` or the
feature services.

## Consequences

- We write and maintain the loop, tool schemas, step logging and context handling.
- The agent is fully testable offline with the fake model.
- Switching LLM provider is an adapter plus configuration, never a rewrite.
- Still open, in separate ADRs: the default LLM provider (and how that fits the
  privacy promise), and how memories are recalled (all in the prompt vs embeddings).
