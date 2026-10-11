"""Test Suite for Ring Simulator & Computer Vision Telemetry."""

import pytest
from backend.ring_simulator import RingSimulator


def test_ring_simulator_catalog():
    sim = RingSimulator()
    devices = sim.get_device_catalog()
    assert len(devices) >= 4
    device_types = [d["type"] for d in devices]
    assert "doorbell" in device_types
    assert "indoor_camera" in device_types


def test_ring_simulator_trigger_scenario():
    sim = RingSimulator()
    event = sim.trigger_scenario("elder_immobility_alert")
    assert event.scenario_id == "elder_immobility_alert"
    assert event.device_id == "ring_indoor_hallway_02"
    assert len(event.detections) > 0
    box = event.detections[0]
    assert box.label == "person_stationary"
    assert box.confidence > 0.90
    assert len(box.box_normalized) == 4


def test_ring_simulator_invalid_scenario():
    sim = RingSimulator()
    with pytest.raises(ValueError):
        sim.trigger_scenario("fake_scenario_xyz")


def test_ring_simulator_history_limit():
    sim = RingSimulator()
    for _ in range(60):
        sim.trigger_scenario("routine_postal_visit")
    assert len(sim.history) <= 50
