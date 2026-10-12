"""Amazon Bedrock & AgentCore Cognitive Triage Engine.
Fulfills the AWS Builder Mini-Challenge using Bedrock Converse API / Claude 3.5 Sonnet,
with explicit provider mode telemetry (bedrock-live, deterministic-simulator, degraded).
"""

import json
import logging
import time
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from .config import settings

logger = logging.getLogger("ambient_ops.bedrock")


class TriageDecision(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    confidence_score: float = Field(ge=0.0, le=1.0)
    severity: Literal["low", "moderate", "critical"]
    should_interrupt_user: bool
    decision_rationale: str = Field(max_length=500)
    recommended_action: str = Field(max_length=100)
    suggested_actions: List[str] = Field(default_factory=list)
    spoken_alexa_prompt: str = Field(max_length=500)
    provider_mode: Literal["bedrock-live", "deterministic-simulator", "degraded"]
    model_used: str = Field(max_length=120)
    measured_latency_ms: float = Field(ge=0.0)
    request_id: Optional[str] = None


class BedrockAgent:
    """Evaluates smart entry incidents using Amazon Bedrock or deterministic simulation."""

    def __init__(self):
        self.provider_mode: Literal["bedrock-live", "deterministic-simulator", "degraded"] = "deterministic-simulator"
        self.boto_client = None
        self._initialize_client()

    def _initialize_client(self):
        """Attempts to initialize boto3 bedrock-runtime via standard credential chain only if explicitly enabled."""
        if settings.force_bedrock_simulator or not settings.enable_live_bedrock:
            self.provider_mode = "deterministic-simulator"
            logger.info("Bedrock agent configured for deterministic simulator mode (safe demo default).")
            return

        try:
            import boto3
            from botocore.config import Config

            session = boto3.Session(region_name=settings.aws_region)
            credentials = session.get_credentials()

            if credentials and credentials.access_key:
                bedrock_cfg = Config(
                    connect_timeout=settings.bedrock_connect_timeout,
                    read_timeout=settings.bedrock_read_timeout,
                    retries={"max_attempts": settings.bedrock_max_retries, "mode": "standard"},
                )
                self.boto_client = session.client(
                    "bedrock-runtime",
                    region_name=settings.aws_region,
                    config=bedrock_cfg,
                )
                self.provider_mode = "bedrock-live"
                logger.info(
                    "Initialized live AWS Bedrock client in region %s",
                    settings.aws_region,
                )
            else:
                self.provider_mode = "deterministic-simulator"
                logger.info(
                    "No AWS credentials detected in environment. Using deterministic simulator."
                )
        except Exception as e:
            logger.warning(
                "Could not initialize live Bedrock client (%s). Using deterministic simulator.",
                type(e).__name__,
            )
            self.provider_mode = "deterministic-simulator"

    def get_runtime_status(self) -> Dict[str, Any]:
        """Returns the honest runtime configuration and active provider mode."""
        return {
            "provider_mode": self.provider_mode,
            "aws_region": settings.aws_region,
            "model_id": settings.bedrock_model_id,
            "is_live_aws": self.provider_mode == "bedrock-live",
            "is_simulator": self.provider_mode == "deterministic-simulator",
        }

    def triage_ambient_event(
        self,
        event_summary: str,
        device_name: str,
        detections: List[Dict[str, Any]],
        ambient_conditions: Dict[str, Any],
        resident_context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> TriageDecision:
        """Evaluates an ambient smart entry event and generates structured decision rationale."""
        if resident_context is None:
            resident_context = {
                "household_name": settings.household_name,
                "resident_display_name": settings.resident_display_name,
                "quiet_hours_active": False,
                "current_mode": "home_normal",
            }

        # Attempt live Bedrock call if configured
        if self.provider_mode == "bedrock-live" and self.boto_client:
            try:
                return self._invoke_live_bedrock(
                    event_summary,
                    device_name,
                    detections,
                    ambient_conditions,
                    resident_context,
                    request_id,
                )
            except Exception as e:
                logger.error(
                    "Live Bedrock invocation failed (%s). Transitioning to degraded mode.",
                    type(e).__name__,
                )
                return self._invoke_fallback_degraded(
                    event_summary,
                    device_name,
                    detections,
                    ambient_conditions,
                    error_message=f"Bedrock service error: {type(e).__name__}",
                    request_id=request_id,
                )

        # Standard deterministic simulator mode
        return self._invoke_deterministic_simulator(
            event_summary,
            device_name,
            detections,
            ambient_conditions,
            resident_context,
            request_id,
        )

    def _invoke_live_bedrock(
        self,
        event_summary: str,
        device_name: str,
        detections: List[Dict[str, Any]],
        ambient_conditions: Dict[str, Any],
        resident_context: Dict[str, Any],
        request_id: Optional[str],
    ) -> TriageDecision:
        t0 = time.perf_counter()
        prompt = f"""
You are AmbientOps, an incident-response AI agent running on Alexa+ connected to smart home sensors.
Analyze this incident evidence and provide a structured JSON response.

Incident Summary: {event_summary}
Sensor Device: {device_name}
Detections: {json.dumps(detections)}
Ambient Conditions: {json.dumps(ambient_conditions)}
Resident Context: {json.dumps(resident_context)}

Respond strictly in valid JSON with this exact schema:
{{
  "risk_score": <int 0-100>,
  "confidence_score": <float 0.0-1.0>,
  "severity": "<low|moderate|critical>",
  "should_interrupt_user": <true|false>,
  "decision_rationale": "<concise explanation of why this risk was assessed>",
  "recommended_action": "<primary operational recommendation>",
  "suggested_actions": ["<action1>", "<action2>"],
  "spoken_alexa_prompt": "<conversational natural spoken message for Alexa+ voice device>"
}}
"""
        response = self.boto_client.converse(
            modelId=settings.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0.1, "maxTokens": 450},
        )
        latency = round((time.perf_counter() - t0) * 1000, 2)
        raw_text = response["output"]["message"]["content"][0]["text"].strip()

        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        parsed = json.loads(raw_text.strip())

        sev = str(parsed["severity"]).lower()
        if sev not in ("low", "moderate", "critical"):
            sev = "moderate"

        return TriageDecision(
            risk_score=int(parsed["risk_score"]),
            confidence_score=float(parsed.get("confidence_score", 0.95)),
            severity=sev,  # type: ignore
            should_interrupt_user=bool(parsed["should_interrupt_user"]),
            decision_rationale=str(parsed["decision_rationale"])[:500],
            recommended_action=str(parsed.get("recommended_action", "log_timeline"))[:100],
            suggested_actions=[str(a)[:100] for a in parsed.get("suggested_actions", [])[:10]],
            spoken_alexa_prompt=str(parsed["spoken_alexa_prompt"])[:500],
            provider_mode="bedrock-live",
            model_used=settings.bedrock_model_id,
            measured_latency_ms=latency,
            request_id=request_id,
        )

    def _invoke_deterministic_simulator(
        self,
        event_summary: str,
        device_name: str,
        detections: List[Dict[str, Any]],
        ambient_conditions: Dict[str, Any],
        resident_context: Dict[str, Any],
        request_id: Optional[str],
    ) -> TriageDecision:
        """Deterministic simulation reproducing verified model outputs for offline evaluation."""
        t0 = time.perf_counter()
        summary_lower = event_summary.lower()
        detection_labels = [d.get("label", "").lower() for d in detections]
        has_stationary = any("stationary" in lbl or "fall" in lbl for lbl in detection_labels)

        time.sleep(0.015)  # Realistic simulation elapsed time
        latency = round((time.perf_counter() - t0) * 1000, 2)
        resident_name = settings.resident_display_name

        if "package" in summary_lower or "rain" in summary_lower or any("package" in lbl for lbl in detection_labels):
            return TriageDecision(
                risk_score=68,
                confidence_score=0.96,
                severity="moderate",
                should_interrupt_user=True,
                decision_rationale="Package detected on exposed porch steps with 92% forecasted precipitation within 15 minutes. Moderate risk of moisture damage without timely shelter.",
                recommended_action="unlock_porch_storage",
                suggested_actions=[
                    "unlock_porch_storage",
                    "log_delivery_ledger",
                    "remind_in_10_minutes",
                ],
                spoken_alexa_prompt=f"Excuse me, {resident_name}. Your front porch camera observed a package delivery, and rain is forecast in 15 minutes. Would you like me to unlock the porch storage bench?",
                provider_mode="deterministic-simulator",
                model_used=f"{settings.bedrock_model_id} (Deterministic Simulator)",
                measured_latency_ms=latency,
                request_id=request_id,
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
                confidence_score=0.94,
                severity="critical",
                should_interrupt_user=True,
                decision_rationale="Prolonged stationary dwell of 52 minutes detected in hallway with medication schedule overdue by 30 minutes. Exceeds wellness risk safety threshold.",
                recommended_action="initiate_voice_dialogue",
                suggested_actions=[
                    "initiate_voice_dialogue",
                    "prepare_emergency_contact_sms",
                    "illuminate_hallway_safety_path",
                ],
                spoken_alexa_prompt=f"Hello {resident_name}, this is an ambient wellness check. I noticed you haven't moved from the hallway for a while and your scheduled medication was due 30 minutes ago. Are you feeling alright?",
                provider_mode="deterministic-simulator",
                model_used=f"{settings.bedrock_model_id} (Deterministic Simulator)",
                measured_latency_ms=latency,
                request_id=request_id,
            )
        elif "gate" in summary_lower or "pet" in summary_lower or "dog" in summary_lower:
            return TriageDecision(
                risk_score=78,
                confidence_score=0.97,
                severity="moderate",
                should_interrupt_user=True,
                decision_rationale="Canine detected within 3 feet of unlatched backyard perimeter gate with outward trajectory. Immediate containment recommended.",
                recommended_action="sound_backyard_chime",
                suggested_actions=[
                    "sound_backyard_chime",
                    "notify_mobile_push",
                    "trigger_smart_lock_latch",
                ],
                spoken_alexa_prompt="Quick alert: The backyard camera shows your pet is heading toward the open side gate. Would you like me to sound a chime and secure the latch?",
                provider_mode="deterministic-simulator",
                model_used=f"{settings.bedrock_model_id} (Deterministic Simulator)",
                measured_latency_ms=latency,
                request_id=request_id,
            )
        elif "unidentified" in summary_lower or "loitering" in summary_lower or "2:15" in summary_lower:
            return TriageDecision(
                risk_score=86,
                confidence_score=0.93,
                severity="critical",
                should_interrupt_user=True,
                decision_rationale="Unrecognized person loitering near vehicle driver door during quiet hours (2:15 AM) exceeding the 90-second dwell baseline.",
                recommended_action="illuminate_driveway_spotlight_100pct",
                suggested_actions=[
                    "illuminate_driveway_spotlight_100pct",
                    "record_cloud_evidence_clip",
                    "prompt_siren_confirmation",
                ],
                spoken_alexa_prompt=f"{resident_name}, sorry to disturb you. Your driveway camera noticed an unrecognized person loitering near your car for over a minute. I have switched on exterior lighting. Would you like to sound the perimeter chime?",
                provider_mode="deterministic-simulator",
                model_used=f"{settings.bedrock_model_id} (Deterministic Simulator)",
                measured_latency_ms=latency,
                request_id=request_id,
            )
        else:
            return TriageDecision(
                risk_score=15,
                confidence_score=0.92,
                severity="low",
                should_interrupt_user=False,
                decision_rationale="Routine postal delivery observed in clear daylight conditions. No anomalous factors or security threats detected.",
                recommended_action="log_silent_timeline_event",
                suggested_actions=["log_silent_timeline_event"],
                spoken_alexa_prompt="Routine postal delivery observed at front porch. Logged silently to your timeline.",
                provider_mode="deterministic-simulator",
                model_used=f"{settings.bedrock_model_id} (Deterministic Simulator)",
                measured_latency_ms=latency,
                request_id=request_id,
            )

    def _invoke_fallback_degraded(
        self,
        event_summary: str,
        device_name: str,
        detections: List[Dict[str, Any]],
        ambient_conditions: Dict[str, Any],
        error_message: str,
        request_id: Optional[str],
    ) -> TriageDecision:
        """Explicit degraded mode when live cloud service fails. Sanitizes external error."""
        # Sanitize error: never return raw AWS traceback or exception to clients
        sanitized_summary = "Service unavailable or timeout"
        if "Timeout" in error_message:
            sanitized_summary = "Inference timeout exceeded"
        elif "Credentials" in error_message or "AccessDenied" in error_message:
            sanitized_summary = "Authentication check required"

        return TriageDecision(
            risk_score=50,
            confidence_score=0.50,
            severity="moderate",
            should_interrupt_user=False,
            decision_rationale=f"Cloud Bedrock invocation degraded ({sanitized_summary}). Operating in safe contingency mode without autonomous escalation.",
            recommended_action="log_degraded_warning",
            suggested_actions=["log_degraded_warning"],
            spoken_alexa_prompt="AmbientOps alert: Service is operating in offline contingency mode. Sensor event logged.",
            provider_mode="degraded",
            model_used="bedrock-contingency-fallback",
            measured_latency_ms=0.0,
            request_id=request_id,
        )


bedrock_agent = BedrockAgent()
