# scripts

Helper scripts for the **whole repo**: setup, backups, code generation, release.

| Where | What goes there | How it runs |
|---|---|---|
| `scripts/` (here) | scripts that touch more than one app or the stack itself | `./scripts/<name>.sh`, or a `make` target that calls it |
| `apps/backend/scripts/` | scripts that import backend code (seed data, smoke tests) | `cd apps/backend && uv run python scripts/<name>.py` |

Rules:
- Every script starts with a comment that says what it does and how to run it.
- Shell scripts use `set -euo pipefail` and are executable (`chmod +x`).
- Anything people run often gets a `make` target, so `make help` stays the one place to look.
- Scripts read config from `.env`. They never hardcode secrets or domains.
