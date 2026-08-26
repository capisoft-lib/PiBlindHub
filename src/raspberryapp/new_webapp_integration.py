#!/usr/bin/env python3
"""
New Webapp Integration for Motorised Store
Direct integration with the new store core (same process)
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from new_device_service import get_store_core, StoreStatus

logger = logging.getLogger(__name__)


class NewWebappIntegration:
    """Direct integration with the new store core"""
    
    def __init__(self, username: str = "webapp_user"):
        self.username = username
        self.store = get_store_core()
        
        # Ensure store is running
        if not hasattr(self.store, 'main_thread') or not self.store.main_thread.is_alive():
            self.store.start()
        
        logger.info(f"Webapp integration initialized for user: {username}")
    
    async def open_device(self, user_id: str = "webapp") -> Dict[str, Any]:
        """Open device (move up)"""
        try:
            logger.info(f"Opening device by user {user_id}")
            
            # Use callback to get result
            result = {}
            
            def callback(status: StoreStatus):
                result.update({
                    "success": True,
                    "username": self.username,
                    "action": "open",
                    "state": status.state.value,
                    "position": status.position,
                    "user_id": user_id
                })
            
            self.store.move_up(callback)
            
            # Wait a moment for the callback
            await asyncio.sleep(0.1)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to open device: {e}")
            return {
                "success": False,
                "username": self.username,
                "action": "open",
                "error": str(e),
                "user_id": user_id
            }
    
    async def close_device(self, user_id: str = "webapp") -> Dict[str, Any]:
        """Close device (move down)"""
        try:
            logger.info(f"Closing device by user {user_id}")
            
            # Use callback to get result
            result = {}
            
            def callback(status: StoreStatus):
                result.update({
                    "success": True,
                    "username": self.username,
                    "action": "close",
                    "state": status.state.value,
                    "position": status.position,
                    "user_id": user_id
                })
            
            self.store.move_down(callback)
            
            # Wait a moment for the callback
            await asyncio.sleep(0.1)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to close device: {e}")
            return {
                "success": False,
                "username": self.username,
                "action": "close",
                "error": str(e),
                "user_id": user_id
            }
    
    async def stop_device(self, user_id: str = "webapp") -> Dict[str, Any]:
        """Stop device"""
        try:
            logger.info(f"Stopping device by user {user_id}")
            
            # Use callback to get result
            result = {}
            
            def callback(status: StoreStatus):
                result.update({
                    "success": True,
                    "username": self.username,
                    "action": "stop",
                    "state": status.state.value,
                    "position": status.position,
                    "user_id": user_id
                })
            
            self.store.stop_movement(callback)
            
            # Wait a moment for the callback
            await asyncio.sleep(0.1)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to stop device: {e}")
            return {
                "success": False,
                "username": self.username,
                "action": "stop",
                "error": str(e),
                "user_id": user_id
            }
    
    async def get_device_status(self) -> Dict[str, Any]:
        """Get device status"""
        try:
            logger.info(f"Getting status for user {self.username}")
            
            # Use callback to get result
            result = {}
            
            def callback(status: StoreStatus):
                result.update({
                    "success": True,
                    "username": self.username,
                    "state": status.state.value,
                    "position": status.position,
                    "is_moving": status.is_moving,
                    "target_position": status.target_position,
                    "calibration_in_progress": status.calibration_in_progress,
                    "last_updated": status.last_updated.isoformat()
                })
            
            self.store.get_status(callback)
            
            # Wait a moment for the callback
            await asyncio.sleep(0.1)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get device status: {e}")
            return {
                "success": False,
                "username": self.username,
                "state": "error",
                "error": str(e)
            }
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Webapp integration cleanup completed")


# Global integration instance
_webapp_integration: Optional[NewWebappIntegration] = None


def get_webapp_integration(username: str = "webapp_user") -> NewWebappIntegration:
    """Get or create the global webapp integration instance"""
    global _webapp_integration
    if _webapp_integration is None:
        _webapp_integration = NewWebappIntegration(username)
    return _webapp_integration


def cleanup_webapp_integration():
    """Cleanup the global webapp integration"""
    global _webapp_integration
    if _webapp_integration:
        _webapp_integration.cleanup()
        _webapp_integration = None


if __name__ == "__main__":
    # Test the webapp integration
    async def test_integration():
        integration = get_webapp_integration()
        
        print("Testing webapp integration...")
        
        # Get status
        status = await integration.get_device_status()
        print(f"Status: {status}")
        
        # Move up
        result = await integration.open_device("test_user")
        print(f"Open result: {result}")
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Stop
        result = await integration.stop_device("test_user")
        print(f"Stop result: {result}")
        
        # Get final status
        status = await integration.get_device_status()
        print(f"Final status: {status}")
    
    asyncio.run(test_integration())
