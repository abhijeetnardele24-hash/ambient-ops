"""Smart Entry Event Simulator.
Simulates environmental sensor and vision events for ambient incident response testing.
All events and telemetry generated here are explicitly SIMULATED.
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    label: str
    confidence: float
    box_normalized: List[float]  # [ymin, xmin, ymax, xmax] (0.0 to 1.0)


class SmartDeviceEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    timestamp: float = Field(default_factory=time.time)
    device_id: str
    device_name: str
    event_type: str  # motion, chime_press, sound, dwell
    scenario_id: str
    summary: str
    ambient_conditions: Dict[str, Any]
    detections: List[BoundingBox]
    action_suggested: Optional[str] = None
    is_simulated: bool = True
    simulation_label: str = "SIMULATED_ENTRY_DEVICE"


class SmartEntrySimulator:
    """Deterministic event and vision simulator for smart entry testing."""

    SCENARIOS: Dict[str, Dict[str, Any]] = {
        "delivery_weather_risk": {
            "title": "Package Left in Incoming Rain",
            "device_id": "sim_entry_doorbell_01",
            "device_name": "Front Porch Smart Doorbell (Simulated)",
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
            "device_id": "sim_indoor_hallway_02",
            "device_name": "Living Hallway Motion Sensor (Simulated)",
            "event_type": "dwell",
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
            "device_id": "sim_backyard_perimeter_03",
            "device_name": "Backyard Perimeter Cam (Simulated)",
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
            "action_suggested": "Trigger chime on Alexa+ and send instant operator prompt to close yard gate.",
        },
        "nocturnal_perimeter_anomaly": {
            "title": "Unidentified Presence at 2:15 AM",
            "device_id": "sim_side_driveway_04",
            "device_name": "Driveway Spotlight Sensor (Simulated)",
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
            "device_id": "sim_entry_doorbell_01",
            "device_name": "Front Porch Smart Doorbell (Simulated)",
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
        self.history: List[SmartDeviceEvent] = []
        # Seed initial history with routine event and delivery event
        for sid in ["routine_postal_visit", "delivery_weather_risk"]:
            self.trigger_scenario(sid)

    def trigger_scenario(self, scenario_id: str) -> SmartDeviceEvent:
        if scenario_id not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario_id: '{scenario_id}'. Valid scenarios: {list(self.SCENARIOS.keys())}")

        meta = self.SCENARIOS[scenario_id]
        event = SmartDeviceEvent(
            device_id=meta["device_id"],
            device_name=meta["device_name"],
            event_type=meta["event_type"],
            scenario_id=scenario_id,
            summary=meta["summary"],
            ambient_conditions=meta["ambient_conditions"],
            detections=[BoundingBox(**d) for d in meta["detections"]],
            action_suggested=meta.get("action_suggested"),
            is_simulated=True,
        )
        self.history.insert(0, event)
        if len(self.history) > 50:
            self.history = self.history[:50]
        return event

    def get_latest_events(self, limit: int = 10) -> List[SmartDeviceEvent]:
        return self.history[:limit]

    def get_event_by_id(self, event_id: str) -> Optional[SmartDeviceEvent]:
        for e in self.history:
            if e.event_id == event_id:
                return e
        return None

    def get_device_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "device_id": "sim_entry_doorbell_01",
                "name": "Front Porch Smart Doorbell",
                "type": "simulated_doorbell",
                "status": "online",
                "mode": "SIMULATED",
                "battery": "hardwired",
                "signal_rssi": -48,
            },
            {
                "device_id": "sim_indoor_hallway_02",
                "name": "Living Hallway Motion Sensor",
                "type": "simulated_indoor_sensor",
                "status": "online",
                "mode": "SIMULATED",
                "battery": "94%",
                "signal_rssi": -52,
            },
            {
                "device_id": "sim_backyard_perimeter_03",
                "name": "Backyard Perimeter Cam",
                "type": "simulated_perimeter_cam",
                "status": "online",
                "mode": "SIMULATED",
                "battery": "hardwired",
                "signal_rssi": -61,
            },
            {
                "device_id": "sim_side_driveway_04",
                "name": "Driveway Spotlight Sensor",
                "type": "simulated_spotlight",
                "status": "online",
                "mode": "SIMULATED",
                "battery": "hardwired",
                "signal_rssi": -55,
            },
        ]


smart_entry_simulator = SmartEntrySimulator()
