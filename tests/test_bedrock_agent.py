"""Test Suite for Amazon Bedrock / AgentCore Reasoning Engine."""

import pytest
from backend.bedrock_agent import BedrockAgent


def test_bedrock_agent_delivery_scenario():
    agent = BedrockAgent()
    decision = agent.triage_ambient_event(
        event_summary="Courier deposited package on porch. Rain probability 92%.",
        device_name="Front Porch Video Doorbell Pro",
        detections=[{"label": "package_box", "confidence": 0.96}],
        ambient_conditions={"rain_probability": 0.92},
    )
    assert decision.risk_score >= 60
    assert decision.severity == "moderate"
    assert decision.should_interrupt_user is True
    assert "package" in decision.spoken_alexa_prompt.lower()
    assert "unlock_porch_storage" in decision.suggested_actions


def test_bedrock_agent_elder_alert_scenario():
    agent = BedrockAgent()
    decision = agent.triage_ambient_event(
        event_summary="Resident stationary in hallway for 52 minutes without movement.",
        device_name="Living Hallway Stick Up Cam",
        detections=[{"label": "person_stationary", "confidence": 0.94}],
        ambient_conditions={"ambient_noise_db": 18},
    )
    assert decision.risk_score >= 90
    assert decision.severity == "critical"
    assert decision.should_interrupt_user is True
    assert "wellness" in decision.spoken_alexa_prompt.lower() or "check" in decision.spoken_alexa_prompt.lower()


def test_bedrock_agent_routine_quiet_scenario():
    agent = BedrockAgent()
    decision = agent.triage_ambient_event(
        event_summary="Regular postal carrier inserted letters into mailbox and walked away.",
        device_name="Front Porch Video Doorbell Pro",
        detections=[{"label": "uniformed_carrier", "confidence": 0.92}],
        ambient_conditions={"rain_probability": 0.05},
    )
    assert decision.risk_score < 30
    assert decision.severity == "low"
    assert decision.should_interrupt_user is False
