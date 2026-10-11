"""Test Suite for Amazon Bedrock Client Mocking & Fallback Handling."""

import json
from unittest.mock import MagicMock, patch
import pytest
from backend.bedrock_agent import BedrockAgent, TriageDecision
from backend.config import settings


def test_bedrock_live_mocked_invocation_success():
    """Validates that a live Bedrock client properly parses Claude 3.5 Sonnet JSON response."""
    agent = BedrockAgent()
    mock_boto = MagicMock()

    mock_converse_output = {
        "output": {
            "message": {
                "content": [
                    {
                        "text": json.dumps({
                            "risk_score": 75,
                            "confidence_score": 0.98,
                            "severity": "moderate",
                            "should_interrupt_user": True,
                            "decision_rationale": "Mocked live Claude 3.5 Sonnet rationale: rain approaching with package outside.",
                            "recommended_action": "unlock_storage",
                            "suggested_actions": ["unlock_storage", "log_alert"],
                            "spoken_alexa_prompt": "Hello Abhijeet, rain is imminent. Should I unlock the storage bench?",
                        })
                    }
                ]
            }
        }
    }
    mock_boto.converse.return_value = mock_converse_output
    agent.boto_client = mock_boto
    agent.provider_mode = "bedrock-live"

    decision = agent.triage_ambient_event(
        event_summary="Courier left package outside.",
        device_name="Front Porch Camera",
        detections=[{"label": "package", "confidence": 0.95}],
        ambient_conditions={"rain_prob": 0.9},
        request_id="req-test-live",
    )

    assert decision.provider_mode == "bedrock-live"
    assert decision.risk_score == 75
    assert decision.confidence_score == 0.98
    assert decision.severity == "moderate"
    assert "Mocked live Claude" in decision.decision_rationale
    assert decision.request_id == "req-test-live"
    mock_boto.converse.assert_called_once()


def test_bedrock_live_invocation_error_falls_back_to_degraded():
    """Validates that an unexpected AWS ClientError triggers degraded mode with full disclosure."""
    agent = BedrockAgent()
    mock_boto = MagicMock()
    mock_boto.converse.side_effect = RuntimeError("ThrottlingException: Rate exceeded")
    agent.boto_client = mock_boto
    agent.provider_mode = "bedrock-live"

    decision = agent.triage_ambient_event(
        event_summary="Test event with rate limit",
        device_name="Test Device",
        detections=[],
        ambient_conditions={},
    )

    assert decision.provider_mode == "degraded"
    assert "degraded" in decision.decision_rationale.lower()
    assert decision.should_interrupt_user is False


def test_bedrock_runtime_status():
    agent = BedrockAgent()
    status = agent.get_runtime_status()
    assert "provider_mode" in status
    assert "aws_region" in status
    assert "model_id" in status
    assert status["is_simulator"] is True or status["is_live_aws"] is True


def test_bedrock_initialization_with_credentials_missing():
    # When force_bedrock_simulator is set or boto3 is unavailable, agent gracefully defaults to simulator
    with patch.object(settings, "force_bedrock_simulator", True):
        agent = BedrockAgent()
        assert agent.provider_mode == "deterministic-simulator"
        assert agent.get_runtime_status()["is_simulator"] is True
