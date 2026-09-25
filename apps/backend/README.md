# Muninn backend

Python + FastAPI, built in four layers (api / services / domain / adapters).
Read [docs/architecture/backend.md](../../docs/architecture/backend.md) first.

```bash
make sync        # install dependencies (uv)
make check       # all pre-commit checks + tests
```

Use `uv` only: `uv add <package>`, `uv run <command>`. Never `pip`, never `requirements.txt`.
