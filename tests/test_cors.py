"""CORS behavior regression tests."""

from fastapi.testclient import TestClient

from ai_broll_autopilot.api.app import app


def test_cors_allows_configured_frontend_origin():
    client = TestClient(app)
    response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_does_not_allow_foreign_origin():
    client = TestClient(app)
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None


def test_cors_preflight_allows_configured_origin():
    client = TestClient(app)
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
