"""End-to-End Pipeline Tests for AmbientOps FastAPI & Agent Workflows."""

import pytest
from fastapi.testclient import TestClient
from backend.server import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "AmbientOps"
    assert "mcp_transport" in data


def test_mcp_streamable_http_post(client):
    payload = {
        "jsonrpc": "2.0",
        "id": "test-http-1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"},
        },
    }
    response = client.post(
        "/mcp",
        json=payload,
        headers={"Accept": "application/json, text/event-stream"},
    )
    assert response.status_code == 200
    assert "Mcp-Session-Id" in response.headers or "mcp-session-id" in response.headers


def test_ring_scenarios_and_events(client):
    scenarios_resp = client.get("/api/ring/scenarios")
    assert scenarios_resp.status_code == 200
    scenarios = scenarios_resp.json()
    assert "delivery_weather_risk" in scenarios

    events_resp = client.get("/api/ring/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert isinstance(events, list)


def test_triage_flow_stops_at_operator_approval(client):
    """Triage must strictly stop at PENDING_OPERATOR_APPROVAL without auto-executing actions."""
    response = client.post("/api/agent/triage/delivery_weather_risk")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "event" in data
    assert "decision" in data
    assert data["incident_status"] == "PENDING_OPERATOR_APPROVAL"
    # Guaranteed no auto-execution
    assert data["executed_actions"] == []

    # Explicit approval gate executes actions
    incident_id = data["incident_id"]
    approve_resp = client.post(f"/api/operator/approve/{incident_id}")
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["status"] == "success"
    assert len(approved_data["incident"]["executed_actions"]) > 0


def test_mcp_history_endpoint(client):
    # Make a triage call to populate history
    client.post("/api/agent/triage/pet_escape_risk")
    history_resp = client.get("/api/mcp/history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) > 0


def test_incidents_and_devices_endpoints(client):
    inc_resp = client.get("/api/incidents")
    assert inc_resp.status_code == 200
    assert isinstance(inc_resp.json(), list)

    dev_resp = client.get("/api/devices")
    assert dev_resp.status_code == 200
    assert len(dev_resp.json()) >= 4

    evt_resp = client.get("/api/events")
    assert evt_resp.status_code == 200
    assert isinstance(evt_resp.json(), list)

    root_resp = client.get("/")
    assert root_resp.status_code in (200, 404)
