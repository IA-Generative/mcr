# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCR (Meeting Capture & Report) — a microservices platform that captures meeting audio, transcribes it, and generates reports using LLMs. Documentation and commits are in French; code is in English.

## Commands

### Full Stack

```bash
make start                      # Start all services (docker compose --watch)
make start service=mcr-frontend # Start a single service
make stop                       # Stop all services
make restart service=...        # Restart specific service
make rebuild service=...        # Rebuild and restart a service
```

### Per-Package (run from package directory, e.g. `cd mcr-core`)

```bash
make pre-commit     # Run format + type-check + lint + test (all at once)
make test           # uv run pytest .
make type-check     # uv run mypy -p <package>
make lint           # uv run ruff check
make format         # uv run ruff format && ruff check --select I . --fix
make deps-check     # uv run deptry -v .
make test-coverage  # pytest with --cov
```

### Single test

```bash
cd mcr-core && uv run pytest tests/unit/test_foo.py::test_bar -v
```

### Database Migrations (mcr-core only)

```bash
make db-migration m='add users table'   # Create migration
make db-upgrade                          # Apply migrations
make db-downgrade                        # Revert last migration
```

### Frontend (`cd mcr-frontend`)

```bash
pnpm dev            # Dev server
pnpm build          # Production build
pnpm test:unit      # Vitest
pnpm lint           # ESLint
```

### Root-Level Quality Checks (all Python packages)

```bash
make type-check     # mypy across all packages
make lint           # ruff across all packages
make format         # ruff format across all packages
make pre-commit     # all three above
make coverage       # test coverage across all packages
```

## Architecture

```
Frontend (Vue 3) → mcr-gateway (FastAPI, auth/routing) → mcr-core (FastAPI, CRUD + Celery tasks)
                                                        → mcr-generation (Celery worker, LLM reports)

mcr-capture-worker (Playwright bot) — joins meetings, records audio, uploads to S3, reports to mcr-core
```

- **mcr-gateway**: Auth via Keycloak, proxies requests to backend services
- **mcr-core**: Meeting CRUD, transcription scheduling, Alembic migrations. Dual role: FastAPI API + Celery worker
- **mcr-generation**: Celery-only worker for LLM report generation (LangChain, OpenAI, Instructor)
- **mcr-capture-worker**: Playwright bot that joins video meetings (Visio, Webex, Webconf), records audio, uploads to Minio/S3
- **mcr-frontend**: Vue 3 + TypeScript, DSFR design system, Pinia state, TanStack Query

### Infrastructure

- **PostgreSQL 17** — main database (port 5433)
- **Redis** — Celery broker + cache
- **Minio** — S3-compatible object storage for audio files
- **Keycloak** — authentication
- **Alembic** — database migrations (mcr-core)

## Code Conventions

- **Python**: `uv` for package management, `ruff` for formatting/linting, `mypy --strict` for type checking, `pydantic-settings` for config
- **Frontend**: `pnpm`, ESLint + Prettier, `vue-tsc`
- **Logging**: `loguru` (not stdlib logging)
- **DB access**: SQLAlchemy 2.0 with repository pattern
- **Architecture layers**: API routers → Services → Repositories → DB
- **Commits**: Gitmoji convention — e.g. `:sparkles: (317): add webex url validator`
- **PRs**: Target the `dev` branch (not `main`)

## Environment Files

- `.env` — secrets (not committed)
- `.env.local.docker` — docker compose dev config
- `.env.local.host` — host-based local dev
- `.env.local.testing` — test overrides

## Testing

- **Python**: pytest with `pytest-asyncio`, `factory-boy` (mcr-core), `pytest-httpx` (mcr-gateway)
- **Frontend**: Vitest + @testing-library/vue
- Tests use a temporary SQLite database with transaction rollback per test
