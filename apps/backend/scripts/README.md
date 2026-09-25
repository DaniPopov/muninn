# apps/backend/scripts

Backend-only scripts that import code from `app/` (seed data, smoke tests, one-off
maintenance). Run them with the backend's environment:

```bash
cd apps/backend && uv run python scripts/<name>.py
```

Repo-wide scripts live in the root [`scripts/`](../../../scripts/) folder.
