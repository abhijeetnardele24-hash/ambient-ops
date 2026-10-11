"""End-to-End Pipeline Tests for AmbientOps FastAPI & Agent Workflows."""

import pytest
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "AmbientOps"


def test_mcp_jsonrpc_http_post():
    payload = {
        "jsonrpc": "2.0",
        "id": "test-http-1",
        "method": "tools/list",
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["jsonrpc"] == "2.0"
    assert "tools" in body["result"]


def test_ring_scenarios_and_events():
    scenarios_resp = client.get("/api/ring/scenarios")
    assert scenarios_resp.status_code == 200
    scenarios = scenarios_resp.json()
    assert "delivery_weather_risk" in scenarios

    events_resp = client.get("/api/ring/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert isinstance(events, list)


def test_autonomous_triage_flow():
    response = client.post("/api/agent/triage/delivery_weather_risk")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "event" in data
    assert "decision" in data
    assert "executed_actions" in data
    decision = data["decision"]
    assert decision["risk_score"] > 50
    assert len(data["executed_actions"]) > 0


def test_mcp_history_endpoint():
    # Make a triage call to populate history
    client.post("/api/agent/triage/pet_escape_risk")
    history_resp = client.get("/api/mcp/history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) > 0
