"""
Webapp services package
Provides centralized access to all application services
"""

# Import real services
from src.webapp.services.security_service import SecurityService, get_security_service as get_real_security_service
from src.webapp.services.action_logging_service import get_action_logging_service as get_real_action_logging_service
from src.webapp.services.database_service import get_database_service as get_real_database_service
from src.webapp.services.logging_service import get_logging_service as get_real_logging_service
from src.webapp.services.action_service import get_action_service as get_real_action_service

# Service getter functions - these provide the main interface
def get_security_service():
    """Get the security service instance"""
    return get_real_security_service()

def get_action_logging_service():
    """Get the action logging service instance"""
    return get_real_action_logging_service()

def get_database_service():
    """Get the database service instance"""
    return get_real_database_service()

def get_logging_service():
    """Get the logging service instance"""
    return get_real_logging_service()

def get_action_service():
    """Get the action service instance"""
    return get_real_action_service()

def get_device_controller():
    """Get the device controller instance"""
    from src.webapp.services.device_controller import get_device_controller as get_real_device_controller
    return get_real_device_controller()

# Import enums and types from their respective services for convenience
from src.webapp.services.security_service import UserRole
from src.webapp.services.action_service import ActionType, ActionStatus
from src.webapp.services.logging_service import LogLevel, LogCategory

# Export the main service getters
__all__ = [
    'get_security_service', 'get_action_logging_service', 'get_database_service',
    'get_logging_service', 'get_action_service', 'get_device_controller',
    'UserRole', 'ActionType', 'ActionStatus', 'LogLevel', 'LogCategory'
]