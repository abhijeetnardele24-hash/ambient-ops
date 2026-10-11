"""Test Suite for Security Headers, Tracing, and CORS Policies."""

import pytest
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)


def test_security_headers_present_on_all_responses():
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert "X-Request-ID" in headers


def test_request_id_preservation():
    custom_id = "custom_trace_id_9999"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_cors_headers_allowed_origin():
    # CORS preflight on allowed origin
    response = client.options(
        "/api/events",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8000"


def test_runtime_endpoint():
    response = client.get("/api/runtime")
    assert response.status_code == 200
    data = response.json()
    assert "bedrock" in data
    assert "devices" in data
    assert "mcp_stats" in data
    assert data["mcp_stats"]["protocol_version"] == "2025-11-25"


def test_friction_log_endpoint():
    response = client.get("/api/friction-log")
    assert response.status_code == 200
    assert "content" in response.json()
