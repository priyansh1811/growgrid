"""Canonical enums shared across all GrowGrid agents."""

from __future__ import annotations

from enum import Enum


class WaterLevel(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class LabourLevel(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class Goal(str, Enum):
    MAXIMIZE_PROFIT = "MAXIMIZE_PROFIT"
    STABLE_INCOME = "STABLE_INCOME"
    WATER_SAVING = "WATER_SAVING"
    FAST_ROI = "FAST_ROI"


class IrrigationSource(str, Enum):
    NONE = "NONE"
    CANAL = "CANAL"
    BOREWELL = "BOREWELL"
    DRIP = "DRIP"
    MIXED = "MIXED"


class ProfitPotential(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class Compatibility(str, Enum):
    GOOD = "GOOD"
    MED = "MED"
    POOR = "POOR"


class ConflictLevel(str, Enum):
    NO_ISSUE = "NO_ISSUE"
    MINOR_VARIATION = "MINOR_VARIATION"
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"
    MAJOR_CONFLICT = "MAJOR_CONFLICT"
