# Muninn: one entry point for running the stack.  Run `make` or `make help`.
#
#   dev-*    DEV:          docker-compose.yml + docker-compose.dev.yml (hot reload)
#   prod-*   STAGE / PROD: docker-compose.yml only (production build)
#
# Which one is STAGE and which is PROD is decided by APP_ENV in .env.

# The dashboard joins the stack automatically once it has a Dockerfile.
DASHBOARD_PROFILE := $(if $(wildcard apps/dashboard/Dockerfile),--profile dashboard,)

COMPOSE      := docker compose
COMPOSE_DEV  := $(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml $(DASHBOARD_PROFILE)
COMPOSE_PROD := $(COMPOSE) -f docker-compose.yml $(DASHBOARD_PROFILE)
BACKEND      := apps/backend

.DEFAULT_GOAL := help
.PHONY: help env \
        dev-up dev-down dev-restart dev-build dev-logs dev-ps \
        tunnel-up tunnel-down tunnel-logs \
        prod-up prod-down prod-restart prod-build prod-logs prod-ps \
        sync chat run hooks precommit lint fmt typecheck test coverage audit check \
        backend-shell dashboard-shell config clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Create .env from .env.example (never overwrites an existing .env)
	@if [ -f .env ]; then echo ".env already exists, leaving it alone"; \
	else cp .env.example .env && echo "created .env from .env.example"; fi

# ---- DEV ---------------------------------------------------------------------
dev-up: env ## Start DEV in the background: backend :8000 (/docs), dashboard :5173 once it exists
	$(COMPOSE_DEV) up -d --build

dev-down: ## Stop DEV (data volumes are kept)
	$(COMPOSE_DEV) down

dev-restart: ## Restart DEV containers
	$(COMPOSE_DEV) restart

dev-build: ## Rebuild DEV images without the cache
	$(COMPOSE_DEV) build --no-cache

dev-logs: ## Follow DEV logs (all services)
	$(COMPOSE_DEV) logs -f

dev-ps: ## Show DEV containers
	$(COMPOSE_DEV) ps

# ---- Tunnel (DEV): public HTTPS URL for Twilio webhooks ----------------------
tunnel-up: ## Start the ngrok tunnel to the backend (needs ngrok.yml + NGROK_AUTHTOKEN)
	@test -f ngrok.yml || { echo "ngrok.yml missing: cp ngrok.example.yml ngrok.yml"; exit 1; }
	@grep -qE '^NGROK_AUTHTOKEN=.+' .env 2>/dev/null || { echo "Set NGROK_AUTHTOKEN in .env"; exit 1; }
	$(COMPOSE_DEV) --profile tunnel up -d ngrok
	@echo "Inspector: http://localhost:4040"

tunnel-down: ## Stop the ngrok tunnel
	$(COMPOSE_DEV) --profile tunnel stop ngrok

tunnel-logs: ## Follow the ngrok tunnel logs
	$(COMPOSE_DEV) --profile tunnel logs -f ngrok

# ---- STAGE / PROD ------------------------------------------------------------
prod-up: env ## Start STAGE/PROD in the background: app on :80
	$(COMPOSE_PROD) up -d --build

prod-down: ## Stop STAGE/PROD (data volumes are kept)
	$(COMPOSE_PROD) down

prod-restart: ## Restart STAGE/PROD containers
	$(COMPOSE_PROD) restart

prod-build: ## Rebuild STAGE/PROD images without the cache
	$(COMPOSE_PROD) build --no-cache

prod-logs: ## Follow STAGE/PROD logs (all services)
	$(COMPOSE_PROD) logs -f

prod-ps: ## Show STAGE/PROD containers
	$(COMPOSE_PROD) ps

# ---- Quality checks (run `make check` before pushing) -----------------------
sync: ## Install backend dependencies (uv)
	cd $(BACKEND) && uv sync

chat: ## Chat with the agent in the terminal (real model from .env, demo tools)
	cd $(BACKEND) && uv run python scripts/chat.py

run: ## Run the backend locally without Docker, with hot reload (http://localhost:8000/docs)
	cd $(BACKEND) && uv run uvicorn app.main:create_app --factory --reload --port $${BACKEND_PORT:-8000}

hooks: ## Install the git hooks (once per clone): checks run on every commit
	uvx pre-commit install

precommit: ## Run every pre-commit check on every file: secrets, lint, format, types
	uvx pre-commit run --all-files

lint: ## Backend: ruff lint
	cd $(BACKEND) && uv run ruff check .

fmt: ## Backend: ruff format (rewrites files)
	cd $(BACKEND) && uv run ruff format . && uv run ruff check --fix .

typecheck: ## Backend: mypy --strict
	cd $(BACKEND) && uv run mypy app

test: ## Backend: pytest
	cd $(BACKEND) && uv run pytest -q

coverage: ## Backend: pytest with a coverage report (lines not covered are listed)
	cd $(BACKEND) && uv run pytest -q --cov=app --cov-report=term-missing

audit: ## Backend: check dependencies against known vulnerabilities (pip-audit)
	@req=$$(mktemp) && trap 'rm -f "$$req"' EXIT \
		&& cd $(BACKEND) && uv export --frozen --no-emit-project -q -o "$$req" \
		&& uvx pip-audit --disable-pip -r "$$req"

check: precommit test ## Everything CI runs: all pre-commit checks + tests

# ---- Tools -------------------------------------------------------------------
backend-shell: ## Open a shell in the running backend container
	$(COMPOSE) exec backend sh

dashboard-shell: ## Open a shell in the running dashboard container
	$(COMPOSE) exec dashboard sh

config: ## Validate the DEV and PROD compose files
	@$(COMPOSE_DEV) config -q && $(COMPOSE_PROD) config -q && echo "compose files are valid"

clean: ## Stop everything AND delete volumes (removes all stored data, asks first)
	@read -p "This deletes all Muninn data volumes. Type 'yes' to continue: " ans; \
	[ "$$ans" = "yes" ] && $(COMPOSE_DEV) down -v --remove-orphans || echo "cancelled"
