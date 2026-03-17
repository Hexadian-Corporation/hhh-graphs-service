# hhh-graphs-service

Graph and connectivity management microservice for **H³ – Hexadian Hauling Helper**.

## Domain

Manages the travel graph connecting locations: nodes represent locations and edges represent travel routes with distances, travel types (quantum, SCM), and estimated travel times.

## Stack

- Python 3.11+ / FastAPI
- MongoDB (database: `hhh_graphs`)
- opyoid (dependency injection)
- Hexagonal architecture (Ports & Adapters)

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- MongoDB running on localhost:27017

## Setup

```bash
uv sync
```

## Run

```bash
uv run uvicorn src.main:app --reload --port 8004
```

## Test

```bash
uv run pytest
```

## Lint

```bash
uv run ruff check .
```

## Format

```bash
uv run ruff format .
```

## Run in Docker (full stack)

From the monorepo root (`hexadian-hauling-helper`):

```bash
uv run hhh up
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HHH_GRAPHS_MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `HHH_GRAPHS_MONGO_DB` | `hhh_graphs` | Database name |
| `HHH_GRAPHS_PORT` | `8004` | Service port |
| `HEXADIAN_AUTH_JWT_SECRET` | `change-me-in-production` | Shared secret for JWT signature verification |
| `HHH_GRAPHS_JWT_ALGORITHM` | `HS256` | JWT signing algorithm |

## Authentication

All endpoints (except `/health`) require a valid JWT Bearer token. Tokens are validated using [`hexadian-auth-common`](https://github.com/Hexadian-Corporation/hexadian-auth-common).

### Permissions

| Endpoint | Permission |
|---|---|
| `GET /health` | **Public** |
| `POST /graphs/` | `hhh:graphs:write` |
| `GET /graphs/` | `hhh:graphs:read` |
| `GET /graphs/{id}` | `hhh:graphs:read` |
| `DELETE /graphs/{id}` | `hhh:graphs:delete` |

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/graphs/` | Create a graph |
| `GET` | `/graphs/{id}` | Get graph by ID |
| `GET` | `/graphs/` | List all graphs |
| `DELETE` | `/graphs/{id}` | Delete a graph |
| `GET` | `/health` | Health check |
