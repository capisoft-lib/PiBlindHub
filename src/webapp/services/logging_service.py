"""
Simplified logging service
"""

import logging
from enum import Enum
from typing import Optional


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Log categories"""
    AUTHENTICATION = "authentication"
    DEVICE_CONTROL = "device_control"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    NETWORK = "network"
    SECURITY = "security"


class LoggingService:
    """Simplified logging service"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log(self, level: LogLevel, category: LogCategory, message: str, **kwargs):
        """Log a message with specified level and category"""
        log_message = f"[{category.value}] {message}"
        
        if level == LogLevel.DEBUG:
            self.logger.debug(log_message, extra=kwargs)
        elif level == LogLevel.INFO:
            self.logger.info(log_message, extra=kwargs)
        elif level == LogLevel.WARNING:
            self.logger.warning(log_message, extra=kwargs)
        elif level == LogLevel.ERROR:
            self.logger.error(log_message, extra=kwargs)
        elif level == LogLevel.CRITICAL:
            self.logger.critical(log_message, extra=kwargs)


# Global instance
_logging_service = None


def get_logging_service() -> LoggingService:
    """Get the global logging service instance"""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service
