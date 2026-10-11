"""Compatibility layer mapping legacy imports to SmartEntrySimulator.
Explicitly marks all items as simulated smart entry devices.
"""

from .smart_entry_simulator import (
    BoundingBox,
    SmartDeviceEvent as RingEvent,
    SmartEntrySimulator as RingSimulator,
    smart_entry_simulator as ring_simulator,
)

__all__ = ["BoundingBox", "RingEvent", "RingSimulator", "ring_simulator"]
