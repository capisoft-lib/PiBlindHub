"""
Action logging service for tracking user and system actions
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
import logging
from threading import Lock
from src.webapp.config.settings import get_settings
from src.webapp.services.database_service import get_database_service, ActionLog
from src.webapp.services.logging_service import get_logging_service, LogLevel, LogCategory
from src.webapp.services.action_service import ActionType

logger = logging.getLogger(__name__)


class ActionLoggingService:
    """Service for logging and tracking user and system actions"""
    
    def __init__(self):
        self.settings = get_settings()
        self.database_service = get_database_service()
        self.logging_service = get_logging_service()
        self.lock = Lock()
        
        logger.info("Action logging service initialized")
    
    def _create_action_log(self, action_type: str, user_id: Optional[str] = None,
                          username: Optional[str] = None, device_id: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None,
                          client_ip: Optional[str] = None,
                          success: bool = True) -> ActionLog:
        """Create an action log entry"""
        return ActionLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            action_type=action_type,
            user_id=user_id,
            username=username,
            device_id=device_id,
            details=details or {},
            client_ip=client_ip,
            success=success
        )
    
    def log_user_login(self, user_id: str, username: str, 
                      client_ip: Optional[str] = None, success: bool = True):
        """Log user login attempt"""
        action_log = self._create_action_log(
            action_type=ActionType.USER_LOGIN.value,
            user_id=user_id,
            username=username,
            details={"login_attempt": "successful" if success else "failed"},
            client_ip=client_ip,
            success=success
        )
        
        self.database_service.add_action_log(action_log)
        
        # Also log to system logger
        self.logging_service.log(
            LogLevel.INFO if success else LogLevel.WARNING,
            LogCategory.AUTHENTICATION,
            f"User login: {username} ({'success' if success else 'failed'})",
            user_id=user_id,
            client_ip=client_ip
        )
    
    def log_user_logout(self, user_id: str, username: str, 
                       client_ip: Optional[str] = None):
        """Log user logout"""
        action_log = self._create_action_log(
            action_type=ActionType.USER_LOGOUT.value,
            user_id=user_id,
            username=username,
            details={"logout": "successful"},
            client_ip=client_ip,
            success=True
        )
        
        self.database_service.add_action_log(action_log)
        
        self.logging_service.log(
            LogLevel.INFO,
            LogCategory.AUTHENTICATION,
            f"User logout: {username}",
            user_id=user_id,
            client_ip=client_ip
        )
    
    def log_password_change(self, user_id: str, username: str, 
                           client_ip: Optional[str] = None, success: bool = True):
        """Log password change attempt"""
        action_log = self._create_action_log(
            action_type=ActionType.PASSWORD_CHANGE.value,
            user_id=user_id,
            username=username,
            details={"password_change": "successful" if success else "failed"},
            client_ip=client_ip,
            success=success
        )
        
        self.database_service.add_action_log(action_log)
        
        self.logging_service.log(
            LogLevel.INFO if success else LogLevel.WARNING,
            LogCategory.SECURITY,
            f"Password change: {username} ({'success' if success else 'failed'})",
            user_id=user_id,
            client_ip=client_ip
        )
    
    def log_device_action(self, device_id: str, action: str, 
                         user_id: Optional[str] = None, username: Optional[str] = None,
                         client_ip: Optional[str] = None, success: bool = True,
                         details: Optional[Dict[str, Any]] = None):
        """Log device control action"""
        action_type_map = {
            "open": ActionType.DEVICE_OPEN.value,
            "close": ActionType.DEVICE_CLOSE.value,
            "stop": ActionType.DEVICE_STOP.value,
            "calibrate": ActionType.DEVICE_CALIBRATE.value
        }
        
        action_type = action_type_map.get(action, "device_action")
        
        action_log = self._create_action_log(
            action_type=action_type,
            user_id=user_id,
            username=username,
            device_id=device_id,
            details=details or {"action": action},
            client_ip=client_ip,
            success=success
        )
        
        self.database_service.add_action_log(action_log)
        
        self.logging_service.log(
            LogLevel.INFO if success else LogLevel.WARNING,
            LogCategory.DEVICE_CONTROL,
            f"Device action: {action} on {device_id} ({'success' if success else 'failed'})",
            user_id=user_id,
            device_id=device_id,
            client_ip=client_ip
        )
    
    def log_config_change(self, config_type: str, user_id: str,
                         client_ip: Optional[str] = None, success: bool = True,
                         details: Optional[Dict[str, Any]] = None):
        """Log configuration change"""
        action_type_map = {
            "network": ActionType.NETWORK_CONFIG.value,
            "hotspot": ActionType.HOTSPOT_CONFIG.value,
            "application": ActionType.APPLICATION_CONFIG.value
        }
        
        action_type = action_type_map.get(config_type, ActionType.CONFIG_CHANGE.value)
        
        action_log = self._create_action_log(
            action_type=action_type,
            user_id=user_id,
            details=details or {"config_type": config_type},
            client_ip=client_ip,
            success=success
        )
        
        self.database_service.add_action_log(action_log)
        
        self.logging_service.log(
            LogLevel.INFO if success else LogLevel.WARNING,
            LogCategory.CONFIGURATION,
            f"Config change: {config_type} ({'success' if success else 'failed'})",
            user_id=user_id,
            client_ip=client_ip
        )
    
    def get_recent_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent action logs"""
        logs = self.database_service.get_recent_action_logs(limit=limit)
        return [asdict(log) for log in logs]
    
    def get_action_statistics(self) -> Dict[str, Any]:
        """Get action statistics"""
        return self.database_service.get_action_statistics()
    
    def get_actions_by_type(self, action_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get actions filtered by type"""
        logs = self.database_service.get_action_logs(action_type=action_type, limit=limit)
        return [asdict(log) for log in logs]
    
    def get_actions_by_user(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get actions filtered by user"""
        logs = self.database_service.get_action_logs(user_id=user_id, limit=limit)
        return [asdict(log) for log in logs]
    
    def get_actions_by_device(self, device_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get actions filtered by device"""
        logs = self.database_service.get_action_logs(device_id=device_id, limit=limit)
        return [asdict(log) for log in logs]
    
    def clear_old_logs(self, days_to_keep: int = 30) -> int:
        """Clear logs older than specified days"""
        return self.database_service.clear_old_logs(days_to_keep)


# Global instance
_action_logging_service = None


def get_action_logging_service() -> ActionLoggingService:
    """Get the global action logging service instance"""
    global _action_logging_service
    if _action_logging_service is None:
        _action_logging_service = ActionLoggingService()
    return _action_logging_service