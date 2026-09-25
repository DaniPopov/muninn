# 0007. LLM providers: OpenAI first, then Claude, then local models

- **Status:** Accepted
- **Date:** 2026-09-25
- **Deciders:** @DaniPopov

## Context

[ADR 0006](0006-own-agent-harness.md) puts the model behind a `LanguageModel` port with
one adapter per provider API. We need to decide which provider we support first, and
how the connection is configured.

## Decision

### Order

1. **OpenAI**, through the `openai_compatible` adapter. The harness is built and tested
   against it first.
2. **Claude**, through its own adapter (Anthropic's API has a different shape for
   messages and tool calls).
3. **Local models** (Ollama, vLLM, llama.cpp server). Most of them speak the OpenAI chat
   API, so they mostly reuse the `openai_compatible` adapter with a different base URL.
   The work here is testing quality in Hebrew and Russian and adjusting prompts.

### Configuration

Generic names, not vendor names, because one adapter serves several providers:

| Variable | Meaning |
|---|---|
| `LLM_BASE_URL` | API base URL, e.g. `https://api.openai.com/v1` or `http://ollama:11434/v1` |
| `LLM_MODEL` | model name, as the provider calls it |
| `LLM_API_KEY` | secret; empty for local servers that don't need one |

When the Claude adapter arrives, a `LLM_PROVIDER` setting selects the adapter.

### Secrets

- `.env.example` lists the variable with an empty value. The real key lives in `.env`
  (gitignored) or, on a server, in a Docker secret file.
- In code the key is a `SecretStr`, so it prints as `**********` in logs and errors.
- CI never needs a real key: tests use the fake model.

## Consequences

- The harness and prompts are shaped by OpenAI's tool-calling behavior first. The Claude
  adapter must map to the same `domain/agent` types, which keeps us honest about not
  leaking SDK types.
- **Privacy:** with a hosted provider, message text and memories are sent to that
  provider to be processed. Storage stays on the user's server, but "nothing leaves
  your server" is only true with a local model. The README must say this clearly.
- Local-model support is a later milestone, not a day-one promise.
