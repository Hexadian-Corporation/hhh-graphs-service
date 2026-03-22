> **© 2026 Hexadian Corporation** — Licensed under [PolyForm Noncommercial 1.0.0 (Modified)](./LICENSE). No commercial use, no public deployment, no plagiarism. See [LICENSE](./LICENSE) for full terms.

# hhh-graphs-service

Graph and connectivity management microservice for **H³ – Hexadian Hauling Helper**.

## Domain

Manages the travel graph connecting locations: nodes represent locations and edges represent travel routes with distances, travel types (quantum, SCM, wormhole), and estimated travel times.

### Graph Generation — Pairwise Composition

The `POST /graphs/generate` endpoint builds a distance graph from a set of location IDs using a **pairwise composition algorithm** with **two-level hash caching**:

1. **Level 1 — Full-request hash**: `hash(sorted(location_ids))` is checked first. If a merged graph already exists for that exact set of locations, it is returned immediately.
2. **Level 2 — Pairwise hash**: For each pair `(A, B)` from the input, `hash(sorted([A, B]))` is checked. Cached pairwise graphs are reused; only missing pairs are generated.
3. **Tree building**: For each pair, `tree(A)` and `tree(B)` ancestor chains are fetched (excluding the star/system root), and their union forms the node set for the pair.
4. **Cross-system BFS**: If two locations are in different systems, a BFS over wormhole gateway connections discovers all non-cyclic paths between the systems, adding gateway nodes to the graph.
5. **Merge**: All pairwise graphs are merged (union of nodes, edges deduplicated by `(source_id, target_id)`) into the final graph, which is persisted with the full-request hash.

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
| `HHH_GRAPHS_HOST` | `0.0.0.0` | Host address the service binds to |
| `HHH_GRAPHS_PORT` | `8004` | Service port |
| `HHH_GRAPHS_MAPS_SERVICE_URL` | `http://localhost:8003` | Base URL of the maps-service |
| `HHH_GRAPHS_CORS_ALLOW_ORIGINS` | `["http://localhost:3000","http://localhost:3001"]` | JSON array of allowed CORS origins |
| `HEXADIAN_AUTH_JWT_SECRET` | `change-me-in-production` | Shared secret for JWT signature verification |
| `HHH_GRAPHS_JWT_ALGORITHM` | `HS256` | JWT signing algorithm |

## Authentication

All endpoints (except `/health`) require a valid JWT Bearer token. Tokens are validated using [`hexadian-auth-common`](https://github.com/Hexadian-Corporation/hexadian-auth-common).

### Permissions

| Endpoint | Permission |
|---|---|
| `GET /health` | **Public** |
| `POST /graphs/` | `hhh:graphs:write` |
| `POST /graphs/generate` | `hhh:graphs:write` |
| `GET /graphs/` | `hhh:graphs:read` |
| `GET /graphs/{id}` | `hhh:graphs:read` |
| `DELETE /graphs/{id}` | `hhh:graphs:delete` |

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/graphs/` | Create a graph |
| `POST` | `/graphs/generate` | Generate a graph from location IDs (pairwise composition) |
| `GET` | `/graphs/{id}` | Get graph by ID |
| `GET` | `/graphs/` | List all graphs |
| `DELETE` | `/graphs/{id}` | Delete a graph |
| `GET` | `/health` | Health check |
