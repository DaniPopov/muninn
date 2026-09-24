# Contributing to Muninn

Thanks for wanting to help! 🐦‍⬛ Muninn is in its **design phase**, so right now the
most valuable contributions are ideas, feedback and research, not code.

## Ways to help

- **Comment on a proposed ADR.** Read [`docs/architecture_decisions/`](docs/architecture_decisions/)
  and open an issue if you agree, disagree, or know something we missed.
- **Share STT experience.** Tested Whisper / ivrit.ai / other models on Hebrew or
  Russian voice notes? Numbers and war stories are gold.
- **Report bugs or suggest features** using the issue templates.
- **Write code** once Phase 1 starts. Look for issues labeled `good first issue`.

## Workflow

1. **Open an issue first** for anything bigger than a typo, so we can agree on the
   approach before you spend time on it.
2. Fork the repo and create a branch: `feat/voice-notes`, `fix/reminder-timezone`, `docs/setup-guide`.
3. Keep pull requests small and focused. One change per PR.
4. Fill in the pull request template.
5. Be patient and kind in review. We're all volunteers.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: transcribe Russian voice notes
fix: send reminders in the user's timezone
docs: add ADR for storage encryption
```

## Making an architecture decision

If your change affects the architecture (new dependency, new service, storage format,
anything hard to undo), add an ADR in the same PR. Copy
[`0000-template.md`](docs/architecture_decisions/0000-template.md) and set the status to `Proposed`.

## Privacy rule for contributors

Muninn stores people's personal lives. **Never** put real personal data (real voice
notes, phone numbers, messages) in issues, tests, fixtures or logs. Use made-up examples.

## Code of Conduct

By taking part you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
