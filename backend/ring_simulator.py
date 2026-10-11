"""Ring Developer Playground & Vision Telemetry Simulator.
Simulates Ring Video Doorbells, Stick Up Cams, and Smart Sensors with CV detections.
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    label: str
    confidence: float
    box_normalized: List[float]  # [ymin, xmin, ymax, xmax] (0.0 to 1.0)


class RingEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    timestamp: float = Field(default_factory=time.time)
    device_id: str
    device_name: str
    event_type: str  # motion, ring_press, sound, linger
    scenario_id: str
    summary: str
    ambient_conditions: Dict[str, Any]
    detections: List[BoundingBox]
    action_suggested: Optional[str] = None


class RingSimulator:
    """Simulates Ring Developer Playground with pre-configured and live events."""

    SCENARIOS = {
        "delivery_weather_risk": {
            "title": "Package Left in Incoming Rain",
            "device_id": "ring_cam_porch_01",
            "device_name": "Front Porch Video Doorbell Pro",
            "event_type": "motion",
            "summary": "Courier deposited package on exposed front steps. Local weather API indicates 92% precipitation probability within 15 minutes.",
            "ambient_conditions": {
                "rain_probability": 0.92,
                "temperature_f": 58,
                "ambient_lux": 420,
                "wind_mph": 14,
            },
            "detections": [
                {"label": "package_box", "confidence": 0.96, "box_normalized": [0.65, 0.40, 0.85, 0.60]},
                {"label": "delivery_person", "confidence": 0.91, "box_normalized": [0.20, 0.35, 0.70, 0.55]},
            ],
            "action_suggested": "Prompt user via Alexa+ to retrieve package or unlock porch enclosure.",
        },
        "elder_immobility_alert": {
            "title": "Care Recipient Prolonged Inactivity",
            "device_id": "ring_indoor_hallway_02",
            "device_name": "Living Hallway Stick Up Cam",
            "event_type": "linger",
            "summary": "Resident seated or stationary on floor for 52 minutes without movement. Scheduled medication dose overdue by 30 mins.",
            "ambient_conditions": {
                "ambient_noise_db": 18,
                "motion_duration_sec": 3120,
                "lights_on": True,
            },
            "detections": [
                {"label": "person_stationary", "confidence": 0.94, "box_normalized": [0.55, 0.30, 0.90, 0.70]},
            ],
            "action_suggested": "Initiate Alexa+ ambient voice check-in; notify emergency contact if unacknowledged.",
        },
        "pet_escape_risk": {
            "title": "Pet Approaching Open Gate",
            "device_id": "ring_backyard_floodlight_03",
            "device_name": "Backyard Floodlight Cam Plus",
            "event_type": "motion",
            "summary": "Family dog detected within 3 feet of unlatched perimeter gate with rapid heading towards sidewalk.",
            "ambient_conditions": {
                "gate_status": "unlatched",
                "ambient_lux": 850,
            },
            "detections": [
                {"label": "dog_canine", "confidence": 0.97, "box_normalized": [0.50, 0.20, 0.75, 0.45]},
                {"label": "open_gate", "confidence": 0.89, "box_normalized": [0.15, 0.10, 0.80, 0.30]},
            ],
            "action_suggested": "Trigger chime on Alexa+ and send instant smartphone nudge to close yard gate.",
        },
        "nocturnal_perimeter_anomaly": {
            "title": "Unidentified Presence at 2:15 AM",
            "device_id": "ring_side_driveway_04",
            "device_name": "Driveway Spotlight Cam Wired",
            "event_type": "motion",
            "summary": "Unregistered person loitering near vehicle driver door for over 90 seconds at 2:15 AM with infrared motion alert.",
            "ambient_conditions": {
                "time_of_night": "02:15 AM",
                "ambient_lux": 12,
                "ir_illuminator": "active",
            },
            "detections": [
                {"label": "unidentified_person", "confidence": 0.93, "box_normalized": [0.25, 0.50, 0.85, 0.75]},
                {"label": "passenger_vehicle", "confidence": 0.99, "box_normalized": [0.40, 0.10, 0.90, 0.85]},
            ],
            "action_suggested": "Activate low-level smart outdoor illumination and query resident via discrete Alexa+ whisper.",
        },
        "routine_postal_visit": {
            "title": "Routine Mail Carrier Delivery",
            "device_id": "ring_cam_porch_01",
            "device_name": "Front Porch Video Doorbell Pro",
            "event_type": "motion",
            "summary": "Regular USPS postal carrier inserted letters into mailbox and walked away normally.",
            "ambient_conditions": {
                "ambient_lux": 720,
                "rain_probability": 0.05,
            },
            "detections": [
                {"label": "uniformed_carrier", "confidence": 0.92, "box_normalized": [0.30, 0.40, 0.80, 0.60]},
            ],
            "action_suggested": "Silent log in event ledger; no proactive voice interruption needed.",
        },
    }

    def __init__(self):
        self.history: List[RingEvent] = []
        # Seed with initial simulated history
        for sid in ["routine_postal_visit", "delivery_weather_risk"]:
            self.trigger_scenario(sid)

    def trigger_scenario(self, scenario_id: str) -> RingEvent:
        if scenario_id not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario_id: {scenario_id}")

        meta = self.SCENARIOS[scenario_id]
        event = RingEvent(
            device_id=meta["device_id"],
            device_name=meta["device_name"],
            event_type=meta["event_type"],
            scenario_id=scenario_id,
            summary=meta["summary"],
            ambient_conditions=meta["ambient_conditions"],
            detections=[BoundingBox(**d) for d in meta["detections"]],
            action_suggested=meta.get("action_suggested"),
        )
        self.history.insert(0, event)
        # Keep recent 50 events
        if len(self.history) > 50:
            self.history = self.history[:50]
        return event

    def get_latest_events(self, limit: int = 10) -> List[RingEvent]:
        return self.history[:limit]

    def get_event_by_id(self, event_id: str) -> Optional[RingEvent]:
        for e in self.history:
            if e.event_id == event_id:
                return e
        return None

    def get_device_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "device_id": "ring_cam_porch_01",
                "name": "Front Porch Video Doorbell Pro",
                "type": "doorbell",
                "status": "online",
                "battery": "hardwired",
                "signal_rssi": -48,
            },
            {
                "device_id": "ring_indoor_hallway_02",
                "name": "Living Hallway Stick Up Cam",
                "type": "indoor_camera",
                "status": "online",
                "battery": "94%",
                "signal_rssi": -52,
            },
            {
                "device_id": "ring_backyard_floodlight_03",
                "name": "Backyard Floodlight Cam Plus",
                "type": "floodlight_camera",
                "status": "online",
                "battery": "hardwired",
                "signal_rssi": -61,
            },
            {
                "device_id": "ring_side_driveway_04",
                "name": "Driveway Spotlight Cam Wired",
                "type": "spotlight_camera",
                "status": "online",
                "battery": "hardwired",
                "signal_rssi": -55,
            },
        ]


# Singleton instance
ring_simulator = RingSimulator()
