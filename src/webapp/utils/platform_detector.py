"""
Platform detection utility for cross-platform compatibility
"""

import platform
import logging
from typing import Literal

logger = logging.getLogger(__name__)

PlatformType = Literal["windows", "linux", "macos", "unknown"]


def detect_platform() -> PlatformType:
    """
    Detect the current platform
    
    Returns:
        PlatformType: The detected platform type
    """
    system = platform.system().lower()
    
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"
    else:
        logger.warning(f"Unknown platform detected: {system}")
        return "unknown"


def is_windows() -> bool:
    """Check if running on Windows"""
    return detect_platform() == "windows"


def is_linux() -> bool:
    """Check if running on Linux"""
    return detect_platform() == "linux"


def is_macos() -> bool:
    """Check if running on macOS"""
    return detect_platform() == "macos"


def get_platform_info() -> dict:
    """Get detailed platform information"""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "platform": detect_platform()
    }
