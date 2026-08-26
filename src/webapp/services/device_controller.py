"""
Device controller service for interfacing with the Raspberry Pi device app
Updated to use the new webapp integration architecture
"""

import logging
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.webapp.config.settings import get_settings

logger = logging.getLogger(__name__)


class DeviceController:
    """Controller for managing the motorised store device using new webapp integration"""
    
    def __init__(self, username: str = None):
        self.settings = get_settings()
        self.device_id = self.settings.device_default_id
        self.username = username or "default_user"
        self.integration = None
        self.mock_controller = None
        
        # Import the new webapp integration
        try:
            sys.path.append(str(Path(__file__).parent.parent.parent / "raspberryapp"))
            from new_webapp_integration import get_webapp_integration
            self.integration = get_webapp_integration(self.username)
            logger.info(f"Using new webapp integration for user: {self.username}")
        except ImportError as e:
            logger.error(f"Failed to import new webapp integration: {e}")
            self.integration = None
            
            # Fallback to mock controller for development
            try:
                from .mock.mock_device_controller import MockDeviceController
                self.mock_controller = MockDeviceController()
                logger.info("Using mock device controller for development")
            except Exception as mock_e:
                logger.error(f"Failed to initialize mock controller: {mock_e}")
                self.mock_controller = None
        
    async def open_device(self, device_id: str = None, timeout: int = None) -> Dict[str, Any]:
        """
        Open the motorised store device
        
        Args:
            device_id: Device identifier (optional, uses default if not provided)
            timeout: Operation timeout in seconds (optional, uses default if not provided)
            
        Returns:
            Dict containing operation result
        """
        device_id = device_id or self.device_id
        
        if not self.integration:
            return {
                "success": False,
                "device_id": device_id,
                "action": "open",
                "error": "Device integration not available",
                "timestamp": self._get_timestamp()
            }
        
        try:
            logger.info(f"Opening device {device_id}")
            
            # Use new webapp integration
            result = await self.integration.open_device(device_id)
            return result
            
        except Exception as e:
            logger.error(f"Failed to open device {device_id}: {str(e)}")
            return {
                "success": False,
                "device_id": device_id,
                "action": "open",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def close_device(self, device_id: str = None, timeout: int = None) -> Dict[str, Any]:
        """
        Close the motorised store device
        
        Args:
            device_id: Device identifier (optional, uses default if not provided)
            timeout: Operation timeout in seconds (optional, uses default if not provided)
            
        Returns:
            Dict containing operation result
        """
        device_id = device_id or self.device_id
        
        if not self.integration:
            return {
                "success": False,
                "device_id": device_id,
                "action": "close",
                "error": "Device integration not available",
                "timestamp": self._get_timestamp()
            }
        
        try:
            logger.info(f"Closing device {device_id}")
            
            # Use new webapp integration
            result = await self.integration.close_device(device_id)
            return result
            
        except Exception as e:
            logger.error(f"Failed to close device {device_id}: {str(e)}")
            return {
                "success": False,
                "device_id": device_id,
                "action": "close",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def stop_device(self, device_id: str = None) -> Dict[str, Any]:
        """
        Stop the motorised store device (emergency stop)
        
        Args:
            device_id: Device identifier (optional, uses default if not provided)
            
        Returns:
            Dict containing operation result
        """
        device_id = device_id or self.device_id
        
        if not self.integration:
            return {
                "success": False,
                "device_id": device_id,
                "action": "stop",
                "error": "Device integration not available",
                "timestamp": self._get_timestamp()
            }
        
        try:
            logger.info(f"Stopping device {device_id}")
            
            # Use new webapp integration
            result = await self.integration.stop_device(device_id)
            return result
            
        except Exception as e:
            logger.error(f"Failed to stop device {device_id}: {str(e)}")
            return {
                "success": False,
                "device_id": device_id,
                "action": "stop",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def get_device_status(self, device_id: str = None) -> Dict[str, Any]:
        """
        Get the current status of the motorised store device
        
        Args:
            device_id: Device identifier (optional, uses default if not provided)
            
        Returns:
            Dict containing device status
        """
        device_id = device_id or self.device_id
        
        if not self.integration:
            return {
                "success": False,
                "device_id": device_id,
                "status": "error",
                "is_online": False,
                "error": "Device integration not available",
                "last_updated": self._get_timestamp()
            }
        
        try:
            logger.info(f"Getting status for device {device_id}")
            
            # Use new webapp integration
            result = await self.integration.get_device_status()
            return result
            
        except Exception as e:
            logger.error(f"Failed to get status for device {device_id}: {str(e)}")
            return {
                "success": False,
                "device_id": device_id,
                "status": "error",
                "is_online": False,
                "error": str(e),
                "last_updated": self._get_timestamp()
            }
    
    async def calibrate_device(self, device_id: str = None) -> Dict[str, Any]:
        """
        Calibrate the motorised store device
        
        Args:
            device_id: Device identifier (optional, uses default if not provided)
            
        Returns:
            Dict containing operation result
        """
        device_id = device_id or self.device_id
        
        if not self.integration:
            return {
                "success": False,
                "device_id": device_id,
                "action": "calibrate",
                "error": "Device integration not available",
                "timestamp": self._get_timestamp()
            }
        
        try:
            logger.info(f"Calibrating device {device_id}")
            
            # Use new webapp integration - we need to add this method
            # For now, we'll use the store core directly
            sys.path.append(str(Path(__file__).parent.parent.parent / "raspberryapp"))
            from new_device_service import get_store_core
            store = get_store_core()
            store.calibrate()
            
            return {
                "success": True,
                "device_id": device_id,
                "action": "calibrate",
                "message": "Calibration started",
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Failed to calibrate device {device_id}: {str(e)}")
            return {
                "success": False,
                "device_id": device_id,
                "action": "calibrate",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    # Synchronous wrapper methods for API endpoints
    def open_device_sync(self) -> Dict[str, Any]:
        """Synchronous wrapper for open_device"""
        if self.mock_controller:
            return self.mock_controller.open_device()
        
        # For real integration, we'd need to handle async properly
        return {
            "success": False,
            "error": "Real device integration requires async handling"
        }
    
    def close_device_sync(self) -> Dict[str, Any]:
        """Synchronous wrapper for close_device"""
        if self.mock_controller:
            return self.mock_controller.close_device()
        
        return {
            "success": False,
            "error": "Real device integration requires async handling"
        }
    
    def stop_device_sync(self) -> Dict[str, Any]:
        """Synchronous wrapper for stop_device"""
        if self.mock_controller:
            return self.mock_controller.stop_device()
        
        return {
            "success": False,
            "error": "Real device integration requires async handling"
        }
    
    def get_device_status_sync(self) -> Dict[str, Any]:
        """Synchronous wrapper for get_device_status"""
        if self.mock_controller:
            return self.mock_controller.get_device_status()
        
        return {
            "success": False,
            "error": "Real device integration requires async handling"
        }
    
    def calibrate_device_sync(self) -> Dict[str, Any]:
        """Synchronous wrapper for calibrate_device"""
        if self.mock_controller:
            return self.mock_controller.calibrate_device()
        
        return {
            "success": False,
            "error": "Real device integration requires async handling"
        }




# Factory function to create the appropriate controller
def create_device_controller() -> DeviceController:
    """Create a device controller instance"""
    return DeviceController()


# For backward compatibility
DeviceService = DeviceController
