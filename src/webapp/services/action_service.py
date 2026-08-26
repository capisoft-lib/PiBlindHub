"""
Simplified action service
"""

from enum import Enum
from typing import Dict, Any, Optional


class ActionType(Enum):
    """Action types for change tracking"""
    # Authentication & Security
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    PASSWORD_CHANGE = "password_change"
    SESSION_CREATE = "session_create"
    SESSION_INVALIDATE = "session_invalidate"
    
    # Device Control
    DEVICE_OPEN = "device_open"
    DEVICE_CLOSE = "device_close"
    DEVICE_STOP = "device_stop"
    DEVICE_CALIBRATE = "device_calibrate"
    DEVICE_STATUS_CHANGE = "device_status_change"
    
    # Configuration
    CONFIG_CHANGE = "config_change"
    NETWORK_CONFIG = "network_config"
    NETWORK_CONFIG_UPDATE = "network_config_update"
    HOTSPOT_CONFIG = "hotspot_config"
    HOTSPOT_START = "hotspot_start"
    HOTSPOT_STOP = "hotspot_stop"
    APPLICATION_CONFIG = "application_config"
    SYSTEM_CONFIG_UPDATE = "system_config_update"
    
    # API Calls
    API_CALL = "api_call"


class ActionStatus(Enum):
    """Action status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionService:
    """Simplified action service"""
    
    def __init__(self):
        pass
    
    def create_action(self, action_type: ActionType, details: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new action"""
        return {
            "action_type": action_type.value,
            "details": details,
            "status": ActionStatus.PENDING.value
        }


# Global instance
_action_service = None


def get_action_service() -> ActionService:
    """Get the global action service instance"""
    global _action_service
    if _action_service is None:
        _action_service = ActionService()
    return _action_service
