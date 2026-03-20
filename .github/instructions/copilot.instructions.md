<critical>Note: This is a living document and will be updated as we refine our processes. Always refer back to this for the latest guidelines. Update whenever necessary.</critical>

<critical>**Development Workflow:** All changes go through a branch + PR — no direct commits to `main` unless explicitly instructed. See `.github/instructions/development-workflow.instructions.md`.</critical>

<critical>**PR and Issue linkage:** When creating a pull request from an issue, always mention the issue number in the PR description using `Fixes #N`, `Closes #N`, or `Resolves #N`. This is required for GitHub to auto-close the issue on merge.</critical>

<critical>**Before starting implementation:** Read ALL instruction files in `.github/instructions/` of this repository. Also read the organization-level instructions from the `Hexadian-Corporation/.github` repository (`.github/instructions/` directory). These contain essential rules for workflow, bug history, domain models, and GitHub procedures that you MUST follow.</critical>

<critical>**PR title:** The PR title MUST be identical to the originating issue title. Set the final PR title (remove the `[WIP]` prefix) before beginning implementation, not after.</critical>

# Copilot Instructions — hhh-graphs-service

## Project Context

**H³ (Hexadian Hauling Helper)** is a Star Citizen companion app for managing hauling contracts, owned by **Hexadian Corporation** (GitHub org: `Hexadian-Corporation`).

This service manages **navigation graphs** — nodes (locations) and edges (travel connections) used by the route optimizer.

- **Repo:** `Hexadian-Corporation/hhh-graphs-service`
- **Port:** 8004
- **Stack:** Python · FastAPI · MongoDB · pymongo · opyoid (DI) · pydantic-settings

## Architecture — Hexagonal (Ports & Adapters)

```
src/
├── main.py                          # FastAPI app factory + uvicorn
├── domain/
│   ├── models/                      # Pure dataclasses (no framework deps)
│   └── exceptions/                  # Domain-specific exceptions
├── application/
│   ├── ports/
│   │   ├── inbound/                 # Service interfaces (ABC)
│   │   └── outbound/               # Repository interfaces (ABC)
│   └── services/                    # Implementations of inbound ports
└── infrastructure/
    ├── config/
    │   ├── settings.py              # pydantic-settings (env prefix: HHH_GRAPHS_)
    │   └── dependencies.py          # opyoid DI Module
    └── adapters/
        ├── inbound/api/             # FastAPI router, DTOs (Pydantic), API mappers
        └── outbound/persistence/    # MongoDB repository, persistence mappers
```

**Key conventions:**
- Domain models are **pure Python dataclasses** — no Pydantic, no ORM
- DTOs at the API boundary are **Pydantic BaseModel** subclasses
- Mappers are **static classes** (`to_domain`, `to_dto`, `to_document`)
- DI uses **opyoid** (`Module`, `Injector`, `SingletonScope`)
- Repositories use **pymongo** directly (no ODM)
- Router pattern: **`init_router(service)` + module-level `router`** (standard pattern)

## Domain Model

- **Graph** — `id`, `name`, `nodes` (list[Node]), `edges` (list[Edge])
- **Node** — `location_id` (references maps-service Location.id), `label`
- **Edge** — `source_id`, `target_id`, `distance`, `travel_type` (quantum/scm/on_foot), `travel_time_seconds`

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HHH_GRAPHS_MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `HHH_GRAPHS_MONGO_DB` | `hhh_graphs` | Database name |
| `HHH_GRAPHS_HOST` | `0.0.0.0` | Host address the service binds to |
| `HHH_GRAPHS_PORT` | `8004` | Service port |
| `HHH_GRAPHS_MAPS_SERVICE_URL` | `http://localhost:8003` | Base URL of the maps-service |
| `HHH_GRAPHS_CORS_ALLOW_ORIGINS` | `["http://localhost:3000","http://localhost:3001"]` | JSON array of allowed CORS origins |
| `HEXADIAN_AUTH_JWT_SECRET` | `change-me-in-production` | Shared secret for JWT signature verification |
| `HHH_GRAPHS_JWT_ALGORITHM` | `HS256` | JWT signing algorithm |

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/graphs/` | Create a graph |
| `GET` | `/graphs/{id}` | Get graph by ID |
| `GET` | `/graphs/` | List all graphs |
| `DELETE` | `/graphs/{id}` | Delete a graph |
| `GET` | `/health` | Health check |

## Issue & PR Title Format

**Format:** `<type>(graphs): description`

- Example: `feat(graphs): add graph model`
- Example: `fix(graphs): correct edge distance calculation`

**Allowed types:** `chore`, `fix`, `ci`, `docs`, `feat`, `refactor`, `test`, `build`, `perf`, `style`, `revert`

The issue title and PR title must be **identical**. PR body must include `Fixes #N`.

## Quality Standards

- `ruff check .` + `ruff format --check .` must pass
- `pytest --cov=src` with ≥90% coverage on changed lines (`diff-cover`)
- Type hints on all functions
- Squash merge only — PR title becomes the commit message

## CI & Branch Protection

**Required status checks** (all with `app_id: 15368` — GitHub Actions):
- `Lint & Format` — `ruff check .` + `ruff format --check .`
- `Tests & Coverage` — `pytest` + `diff-cover` (≥90% on changed lines)
- `Validate PR Title` — conventional commit format
- `Secret Scan` — gitleaks

> **Critical:** Required status checks must always use `app_id: 15368` (GitHub Actions). Using `app_id: null` causes checks to freeze as "Expected — Waiting for status" for any check name not previously reported on `main`. See BUG-011.

## Tooling

| Action | Command |
|--------|---------|
| Setup | `uv sync` |
| Run (dev) | `uv run uvicorn src.main:app --reload --port 8004` |
| Run in Docker | `uv run hhh up` (from monorepo root) |
| Test | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |

## Maintenance Rules

- **Keep the README up to date.** When you add, remove, or change commands, environment variables, API endpoints, domain models, or architecture — update `README.md`. The README is the source of truth for developers.
- **Keep the monorepo CLI service registry up to date.** When adding or removing a service, update `SERVICES`, `FRONTENDS`, `COMPOSE_SERVICE_MAP`, and `SERVICE_ALIASES` in `hexadian-hauling-helper/hhh_cli/__init__.py`, plus the `docker-compose.yml` entry.

<critical>**Configuration externalization:** Any new configuration value that could vary between environments (URLs, secrets, ports, feature flags, timeouts, etc.) MUST be externalized as a Docker environment variable with a sensible default for local development. Add the field to `Settings` in `src/infrastructure/config/settings.py`, document it in `README.md` and in `.github/instructions/copilot.instructions.md`, and create a task in `hexadian-hauling-helper` to wire it in `docker-compose.yml`.</critical>

## Organization Profile Maintenance

- **Keep the org profile README up to date.** When repositories, ports, architecture, workflows, security policy, or ownership change, update Hexadian-Corporation/.github/profile/README.md in the public .github repo.
- **Treat the org profile as canonical org summary.** Ensure descriptions in this repo remain consistent with the organization profile README.

Remember, before finishing: resolve any merge conflict and merge source (PR origin and destination) branch into current one.