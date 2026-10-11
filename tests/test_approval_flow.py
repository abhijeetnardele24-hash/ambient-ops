"""Test Suite for Operator Sequence & Human Approval Boundary.
Tests: Trigger -> Observe Evidence -> Analyze -> Review -> Operator Approval -> Outcome Verification.
"""

import pytest
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)


def test_complete_operator_approval_workflow():
    # 1. Trigger Scenario
    trig_resp = client.post("/api/events/trigger/delivery_weather_risk")
    assert trig_resp.status_code == 200
    event_data = trig_resp.json()["event"]
    event_id = event_data["event_id"]
    assert event_data["is_simulated"] is True

    # 2. Observe Evidence
    events_resp = client.get("/api/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert any(e["event_id"] == event_id for e in events)

    # 3. Analyze Event via MCP & Bedrock
    analyze_resp = client.post(f"/api/agent/analyze/{event_id}")
    assert analyze_resp.status_code == 200
    incident = analyze_resp.json()["incident"]
    incident_id = incident["incident_id"]
    assert incident["status"] == "PENDING_OPERATOR_APPROVAL"
    assert incident["outcome_verified"] is False
    assert "decision_rationale" in incident["triage_decision"]

    # 4. Operator Approves Simulation
    approve_resp = client.post(
        f"/api/operator/approve/{incident_id}",
        json={"operator_notes": "Operator verified porch weather radar and approved unlocked bench."},
    )
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["status"] == "success"
    updated_incident = approved_data["incident"]
    assert updated_incident["status"] == "SIMULATION_APPROVED"
    assert updated_incident["outcome_verified"] is True
    assert updated_incident["verified_at"] is not None
    assert len(updated_incident["executed_actions"]) > 0

    # 5. Subsequent approval is idempotent
    second_approve = client.post(f"/api/operator/approve/{incident_id}")
    assert second_approve.status_code == 200
    assert second_approve.json()["status"] == "already_processed"


def test_operator_rejection_workflow():
    # Trigger and analyze
    trig_resp = client.post("/api/events/trigger/routine_postal_visit")
    event_id = trig_resp.json()["event"]["event_id"]

    analyze_resp = client.post(f"/api/agent/analyze/{event_id}")
    incident_id = analyze_resp.json()["incident_id"]

    # Operator rejects recommendation
    reject_resp = client.post(f"/api/operator/reject/{incident_id}")
    assert reject_resp.status_code == 200
    rejected_data = reject_resp.json()
    assert rejected_data["status"] == "success"
    assert rejected_data["incident"]["status"] == "OPERATOR_REJECTED"
    assert rejected_data["incident"]["outcome_verified"] is False


def test_operator_invalid_incident_lookups():
    # Analyze non-existent event
    bad_analyze = client.post("/api/agent/analyze/non_existent_evt_999")
    assert bad_analyze.status_code == 404

    # Approve non-existent incident
    bad_approve = client.post("/api/operator/approve/non_existent_inc_999")
    assert bad_approve.status_code == 404

    # Reject non-existent incident
    bad_reject = client.post("/api/operator/reject/non_existent_inc_999")
    assert bad_reject.status_code == 404
