# ---- builder: resolve and install dependencies with uv ------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

# Dependencies first so this layer stays cached until pyproject/uv.lock change.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime: slim image, no uv, not root -------------------------------------
FROM python:3.14-slim-bookworm
WORKDIR /app
RUN useradd --create-home --uid 1000 muninn \
    && mkdir -p /app/data && chown muninn:muninn /app/data
COPY --from=builder --chown=muninn:muninn /app/.venv /app/.venv
COPY --from=builder --chown=muninn:muninn /app/app /app/app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER muninn
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
