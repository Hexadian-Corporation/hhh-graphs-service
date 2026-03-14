# hhh-graphs-service

Graph and connectivity management microservice for **H³ – Hexadian Hauling Helper**.

## Domain

Manages the travel graph connecting locations: nodes represent locations and edges represent travel routes with distances, travel types (quantum, SCM), and estimated travel times.

## Stack

- Python 3.11+ / FastAPI
- MongoDB (database: `hhh_graphs`)
- opyoid (dependency injection)
- Hexagonal architecture (Ports & Adapters)

## Quick Start

```bash
uv sync
uv run uvicorn src.main:app --reload --port 8004
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HHH_GRAPHS_MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `HHH_GRAPHS_MONGO_DB` | `hhh_graphs` | Database name |
| `HHH_GRAPHS_PORT` | `8004` | Service port |

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/graphs/` | Create a graph |
| `GET` | `/graphs/{id}` | Get graph by ID |
| `GET` | `/graphs/` | List all graphs |
| `DELETE` | `/graphs/{id}` | Delete a graph |
| `GET` | `/health` | Health check |
