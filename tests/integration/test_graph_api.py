"""Integration tests for Graph CRUD endpoints (real MongoDB via testcontainers)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.auth_helpers import make_auth_header

_READ = make_auth_header("hhh:graphs:read")
_WRITE = make_auth_header("hhh:graphs:write")
_DELETE = make_auth_header("hhh:graphs:delete")


def _full_graph_payload() -> dict:
    """Graph payload with all fields populated."""
    return {
        "name": "StantonGraph",
        "hash": "abc123hash",
        "nodes": [
            {"location_id": "loc-1", "label": "Lorville"},
            {"location_id": "loc-2", "label": "Area18"},
        ],
        "edges": [
            {
                "source_id": "loc-1",
                "target_id": "loc-2",
                "distance": 42.5,
                "travel_type": "quantum",
                "travel_time_seconds": 120.0,
            },
        ],
    }


def _minimal_graph_payload() -> dict:
    """Graph payload with only the required ``name`` field."""
    return {"name": "MinimalGraph"}


# ---------------------------------------------------------------------------
# POST /graphs/
# ---------------------------------------------------------------------------
class TestPostGraph:
    def test_create_graph_with_all_fields(self, client: TestClient) -> None:
        payload = _full_graph_payload()
        resp = client.post("/graphs/", json=payload, headers=_WRITE)

        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == payload["name"]
        assert body["hash"] == payload["hash"]
        assert len(body["nodes"]) == 2
        assert body["nodes"][0]["location_id"] == "loc-1"
        assert body["nodes"][0]["label"] == "Lorville"
        assert len(body["edges"]) == 1
        edge = body["edges"][0]
        assert edge["source_id"] == "loc-1"
        assert edge["target_id"] == "loc-2"
        assert edge["distance"] == 42.5
        assert edge["travel_type"] == "quantum"
        assert edge["travel_time_seconds"] == 120.0

    def test_create_graph_with_minimal_fields(self, client: TestClient) -> None:
        resp = client.post("/graphs/", json=_minimal_graph_payload(), headers=_WRITE)

        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "MinimalGraph"
        assert body["nodes"] == []
        assert body["edges"] == []
        assert body["stale"] is False
        assert body["stale_reason"] is None
        assert body["stale_since"] is None

    def test_create_multiple_graphs(self, client: TestClient) -> None:
        for i in range(3):
            resp = client.post("/graphs/", json={"name": f"Graph-{i}"}, headers=_WRITE)
            assert resp.status_code == 201

        all_resp = client.get("/graphs/", headers=_READ)
        assert len(all_resp.json()) == 3

    def test_id_is_auto_generated(self, client: TestClient) -> None:
        resp = client.post("/graphs/", json=_minimal_graph_payload(), headers=_WRITE)
        body = resp.json()

        assert body["id"] is not None
        assert isinstance(body["id"], str)
        assert len(body["id"]) == 24  # ObjectId hex string

    def test_returns_201(self, client: TestClient) -> None:
        resp = client.post("/graphs/", json=_minimal_graph_payload(), headers=_WRITE)
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# GET /graphs/
# ---------------------------------------------------------------------------
class TestGetGraphs:
    def test_empty_list(self, client: TestClient) -> None:
        resp = client.get("/graphs/", headers=_READ)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_multiple_graphs(self, client: TestClient) -> None:
        names = ["Alpha", "Beta", "Gamma"]
        for n in names:
            client.post("/graphs/", json={"name": n}, headers=_WRITE)

        resp = client.get("/graphs/", headers=_READ)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        returned_names = {g["name"] for g in body}
        assert returned_names == set(names)

    def test_response_contains_expected_fields(self, client: TestClient) -> None:
        client.post("/graphs/", json=_full_graph_payload(), headers=_WRITE)

        resp = client.get("/graphs/", headers=_READ)
        graph = resp.json()[0]

        assert "id" in graph
        assert "name" in graph
        assert "hash" in graph
        assert "nodes" in graph
        assert "edges" in graph
        assert "stale" in graph
        assert "stale_reason" in graph
        assert "stale_since" in graph


# ---------------------------------------------------------------------------
# GET /graphs/{id}
# ---------------------------------------------------------------------------
class TestGetGraphById:
    def test_get_existing_graph(self, client: TestClient) -> None:
        created = client.post("/graphs/", json=_full_graph_payload(), headers=_WRITE).json()
        graph_id = created["id"]

        resp = client.get(f"/graphs/{graph_id}", headers=_READ)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == graph_id
        assert body["name"] == "StantonGraph"
        assert len(body["nodes"]) == 2
        assert len(body["edges"]) == 1

    def test_get_nonexistent_graph_returns_404(self, client: TestClient) -> None:
        fake_id = "000000000000000000000000"
        resp = client.get(f"/graphs/{fake_id}", headers=_READ)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /graphs/{id}
# ---------------------------------------------------------------------------
class TestDeleteGraph:
    def test_delete_existing_graph(self, client: TestClient) -> None:
        created = client.post("/graphs/", json=_minimal_graph_payload(), headers=_WRITE).json()
        graph_id = created["id"]

        resp = client.delete(f"/graphs/{graph_id}", headers=_DELETE)
        assert resp.status_code == 204

    def test_delete_nonexistent_graph_returns_404(self, client: TestClient) -> None:
        fake_id = "000000000000000000000000"
        resp = client.delete(f"/graphs/{fake_id}", headers=_DELETE)
        assert resp.status_code == 404

    def test_get_after_delete_returns_404(self, client: TestClient) -> None:
        created = client.post("/graphs/", json=_minimal_graph_payload(), headers=_WRITE).json()
        graph_id = created["id"]

        del_resp = client.delete(f"/graphs/{graph_id}", headers=_DELETE)
        assert del_resp.status_code == 204

        get_resp = client.get(f"/graphs/{graph_id}", headers=_READ)
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Cache-Control headers
# ---------------------------------------------------------------------------
class TestCacheControlHeaders:
    def test_get_graph_by_id_has_cache_control(self, client: TestClient) -> None:
        created = client.post("/graphs/", json=_minimal_graph_payload(), headers=_WRITE).json()
        graph_id = created["id"]

        resp = client.get(f"/graphs/{graph_id}", headers=_READ)
        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "max-age=3600"

    def test_list_graphs_has_cache_control(self, client: TestClient) -> None:
        resp = client.get("/graphs/", headers=_READ)
        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "max-age=3600"
