#!/usr/bin/env python3
"""
Device models for PiBlindHub
Contains data models and enums used by the device service
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


class DeviceState(Enum):
    """Device state enumeration"""
    STOPPED = "stopped"
    OPENING = "opening"
    CLOSING = "closing"
    ERROR = "error"


class MotorDirection(Enum):
    """Motor direction enumeration"""
    UP = "up"
    DOWN = "down"
    STOP = "stop"


# CLI Response Models (REST API style)
@dataclass
class CLIResponse:
    """Base CLI response structure"""
    success: bool
    message: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class StatusData:
    """Status response data structure"""
    state: str
    position: Optional[float]
    is_moving: bool
    target_position: Optional[float]
    calibration_in_progress: bool
    power_loss_recovery: Optional[Dict[str, Any]] = None


@dataclass
class MovementData:
    """Movement response data structure"""
    action: str
    target_position: Optional[float]
    estimated_duration: Optional[float]
    current_position: Optional[float]


@dataclass
class CalibrationData:
    """Calibration response data structure"""
    action: str
    estimated_duration: float
    current_position: Optional[float]


@dataclass
class PowerLossRecoveryData:
    """Power loss recovery data structure"""
    recovery_needed: bool
    last_direction: Optional[str]
    estimated_position: Optional[float]
    recommendation: str
