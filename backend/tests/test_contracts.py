"""API contract conformance: the standard error envelope, status codes, public
endpoints, and key response shapes (contracts/api.md)."""

from __future__ import annotations

from tests.conftest import auth_headers


def test_health_is_public_and_reports_storage(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "registry" in body["storage"] and "vectors" in body["storage"]


def test_unknown_route_uses_error_envelope(client):
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert set(r.json()["error"]) == {"code", "message"}


def test_validation_error_uses_envelope(client):
    r = client.post("/api/auth/signup", json={})  # missing required `email`
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_unauthorized_envelope_on_data_route(client):
    r = client.get("/api/courses")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_create_course_response_shape(client, register):
    token = register("c@x.com")["session_token"]
    r = client.post("/api/courses", json={"name": "Bio"}, headers=auth_headers(token))
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id", "name", "created_at"}
    assert body["name"] == "Bio"
