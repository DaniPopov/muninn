# Contributing to Muninn

Thanks for wanting to help! Muninn is in its **design phase**, so right now the
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

## Checks before every commit

After cloning, install the git hooks once:

```bash
make hooks
```

From then on, every `git commit` runs these checks automatically
(config: [`.pre-commit-config.yaml`](.pre-commit-config.yaml)):

| Check | Tool |
|---|---|
| No secrets (API keys, tokens, private keys) | gitleaks, detect-private-key |
| File hygiene (YAML/TOML/JSON valid, no huge files, no merge markers, trailing whitespace) | pre-commit-hooks |
| Backend lint + format | ruff |
| Backend types | mypy `--strict` |
| `uv.lock` matches `pyproject.toml` | uv |
| Commit message format | conventional-pre-commit |

Run everything by hand with `make check` (all checks + tests). Skipping hooks with
`--no-verify` only moves the failure to CI.

## CI (GitHub Actions)

| Workflow | Runs on | What it checks |
|---|---|---|
| [`checks`](.github/workflows/checks.yml) | every push and PR | the pre-commit hooks above, on all files |
| [`backend`](.github/workflows/backend.yml) | changes under `apps/backend/` | tests with coverage (`make coverage`); builds the Docker image and checks `/health` in PROD mode |
| [`security`](.github/workflows/security.yml) | every push and PR, and weekly | secrets in the full git history (gitleaks), known-vulnerable dependencies (`make audit`), CodeQL, dependency review on PRs |

[Dependabot](.github/dependabot.yml) opens weekly PRs to update Python packages,
GitHub Actions and Docker base images.

If a check fails because it **fixed** something (formatting, whitespace), just
`git add` the changes and commit again.

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
