"""Amazon Bedrock & AgentCore Reasoning Engine.
Fulfills the AWS Builder Mini-Challenge by providing generative triage,
risk scoring, and proactive voice synthesis via Bedrock Converse API / Claude 3.5 Sonnet.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .config import settings

logger = logging.getLogger("ambient_ops.bedrock")


class TriageDecision(BaseModel):
    risk_score: int = Field(ge=0, le=100)  # 0 to 100
    severity: str  # low, moderate, critical
    should_interrupt_user: bool
    reasoning_summary: str
    spoken_alexa_prompt: str
    suggested_actions: List[str]
    model_used: str
    latency_ms: float


class BedrockAgent:
    """Manages reasoning pipelines using Amazon Bedrock or high-fidelity emulator."""

    def __init__(self):
        self.use_mock = settings.use_bedrock_mock
        self.boto_client = None

        if not self.use_mock and settings.aws_access_key_id:
            try:
                import boto3

                self.boto_client = boto3.client(
                    "bedrock-runtime",
                    region_name=settings.aws_region,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                )
                logger.info("Initialized live AWS Bedrock client.")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize live Bedrock client ({e}). Falling back to emulator."
                )
                self.use_mock = True

    def triage_ambient_event(
        self,
        event_summary: str,
        device_name: str,
        detections: List[Dict[str, Any]],
        ambient_conditions: Dict[str, Any],
        resident_context: Optional[Dict[str, Any]] = None,
    ) -> TriageDecision:
        """Evaluates an ambient event and determines proactive Alexa+ response."""
        start_time = 1000.0 * 0.05  # baseline simulation

        # Default context
        if resident_context is None:
            resident_context = {
                "household_name": "Nardele Residence",
                "quiet_hours_active": False,
                "current_mode": "home_relaxed",
            }

        if not self.use_mock and self.boto_client:
            try:
                return self._invoke_live_bedrock(
                    event_summary,
                    device_name,
                    detections,
                    ambient_conditions,
                    resident_context,
                )
            except Exception as e:
                logger.error(f"Live Bedrock invocation failed ({e}). Using emulator.")

        return self._invoke_mock_bedrock(
            event_summary,
            device_name,
            detections,
            ambient_conditions,
            resident_context,
        )

    def _invoke_live_bedrock(
        self,
        event_summary: str,
        device_name: str,
        detections: List[Dict[str, Any]],
        ambient_conditions: Dict[str, Any],
        resident_context: Dict[str, Any],
    ) -> TriageDecision:
        import time

        t0 = time.time()
        prompt = f"""
You are AmbientOps, an intelligent autonomous agent running on Alexa+ and connected to Ring smart home vision cameras.
Analyze this smart home ambient event and respond strictly in valid JSON.

Event Summary: {event_summary}
Device: {device_name}
Detections: {json.dumps(detections)}
Ambient Conditions: {json.dumps(ambient_conditions)}
Resident Context: {json.dumps(resident_context)}

Respond strictly in this JSON format:
{{
  "risk_score": <int 0-100>,
  "severity": "<low|moderate|critical>",
  "should_interrupt_user": <true|false>,
  "reasoning_summary": "<brief technical rationale>",
  "spoken_alexa_prompt": "<conversational natural spoken message for Alexa+ voice device>",
  "suggested_actions": ["<action1>", "<action2>"]
}}
"""
        response = self.boto_client.converse(
            modelId=settings.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0.2, "maxTokens": 450},
        )
        latency = round((time.time() - t0) * 1000, 2)
        raw_text = response["output"]["message"]["content"][0]["text"]
        
        # Clean potential markdown fences
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        parsed = json.loads(cleaned.strip())

        return TriageDecision(
            risk_score=parsed["risk_score"],
            severity=parsed["severity"],
            should_interrupt_user=parsed["should_interrupt_user"],
            reasoning_summary=parsed["reasoning_summary"],
            spoken_alexa_prompt=parsed["spoken_alexa_prompt"],
            suggested_actions=parsed["suggested_actions"],
            model_used=settings.bedrock_model_id,
            latency_ms=latency,
        )

    def _invoke_mock_bedrock(
        self,
        event_summary: str,
        device_name: str,
        detections: List[Dict[str, Any]],
        ambient_conditions: Dict[str, Any],
        resident_context: Dict[str, Any],
    ) -> TriageDecision:
        """High-fidelity local deterministic emulator for testing and offline demos."""
        summary_lower = event_summary.lower()

        detection_labels = [d.get("label", "").lower() for d in detections]
        has_stationary = any("stationary" in lbl or "fall" in lbl for lbl in detection_labels)

        if "package" in summary_lower or "rain" in summary_lower or any("package" in lbl for lbl in detection_labels):
            return TriageDecision(
                risk_score=68,
                severity="moderate",
                should_interrupt_user=True,
                reasoning_summary="Package left exposed with >90% precipitation probability within 15 minutes. High likelihood of water damage without quick retrieval.",
                spoken_alexa_prompt="Excuse me, Abhijeet. Your Ring Porch camera detected a package delivery, and rain is forecast in 15 minutes. Would you like me to unlock the porch storage bench or alert you when you head downstairs?",
                suggested_actions=[
                    "unlock_porch_storage",
                    "log_delivery_ledger",
                    "remind_in_10_minutes",
                ],
                model_used=f"{settings.bedrock_model_id} (Emulated Bedrock Converse)",
                latency_ms=184.5,
            )
        elif (
            "elder" in summary_lower
            or "immobility" in summary_lower
            or "inactivity" in summary_lower
            or "stationary" in summary_lower
            or has_stationary
        ):
            return TriageDecision(
                risk_score=94,
                severity="critical",
                should_interrupt_user=True,
                reasoning_summary="Prolonged lack of motion (52 min) detected in hallway coupled with overdue medication schedule. Exceeds wellness risk threshold.",
                spoken_alexa_prompt="Hello Abhijeet, this is an ambient wellness check. I noticed you haven't moved from the hallway for a while and your scheduled medication was due 30 minutes ago. Are you feeling alright?",
                suggested_actions=[
                    "initiate_voice_dialogue",
                    "prepare_emergency_contact_sms",
                    "illuminate_hallway_safety_path",
                ],
                model_used=f"{settings.bedrock_model_id} (Emulated Bedrock Converse)",
                latency_ms=210.2,
            )
        elif "gate" in summary_lower or "pet" in summary_lower or "dog" in summary_lower:
            return TriageDecision(
                risk_score=78,
                severity="moderate",
                should_interrupt_user=True,
                reasoning_summary="Canine detected within 3 feet of unlatched backyard perimeter gate with outward heading.",
                spoken_alexa_prompt="Quick alert: The backyard floodlight cam shows your dog is heading toward the open side gate. Would you like me to sound a chime and secure the perimeter?",
                suggested_actions=[
                    "sound_backyard_chime",
                    "notify_mobile_push",
                    "trigger_smart_lock_latch",
                ],
                model_used=f"{settings.bedrock_model_id} (Emulated Bedrock Converse)",
                latency_ms=165.8,
            )
        elif "unidentified" in summary_lower or "loitering" in summary_lower or "2:15" in summary_lower:
            return TriageDecision(
                risk_score=86,
                severity="critical",
                should_interrupt_user=True,
                reasoning_summary="Unrecognized individual lingering near driveway vehicles during quiet hours (2:15 AM) exceeding 90-second threshold.",
                spoken_alexa_prompt="Abhijeet, sorry to disturb you. Your Driveway Spotlight Cam noticed an unrecognized person loitering near your car for over a minute. I have switched on the perimeter lighting. Would you like me to sound the exterior siren?",
                suggested_actions=[
                    "illuminate_driveway_spotlight_100pct",
                    "record_cloud_evidence_clip",
                    "prompt_siren_confirmation",
                ],
                model_used=f"{settings.bedrock_model_id} (Emulated Bedrock Converse)",
                latency_ms=195.4,
            )
        else:
            return TriageDecision(
                risk_score=15,
                severity="low",
                should_interrupt_user=False,
                reasoning_summary="Standard routine postal activity detected under clear daylight conditions. No anomalous factors identified.",
                spoken_alexa_prompt="Routine postal delivery observed at front porch. Logged silently to your timeline.",
                suggested_actions=["log_silent_timeline_event"],
                model_used=f"{settings.bedrock_model_id} (Emulated Bedrock Converse)",
                latency_ms=132.1,
            )


# Singleton instance
bedrock_agent = BedrockAgent()
