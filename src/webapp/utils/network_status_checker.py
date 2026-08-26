"""
Unified network status checker that automatically detects platform and uses appropriate implementation
"""

import logging
from typing import Dict, Any

from src.webapp.utils.platform_detector import detect_platform
from src.webapp.utils.status_checker_linux import get_linux_status_checker
from src.webapp.utils.status_checker_windows import get_windows_status_checker

logger = logging.getLogger(__name__)


class NetworkStatusChecker:
    """Unified network status checker with platform-specific implementations"""
    
    def __init__(self):
        self.platform = detect_platform()
        self.logger = logging.getLogger(__name__)
        
        # Initialize platform-specific checker
        if self.platform == "linux":
            self._checker = get_linux_status_checker()
        elif self.platform == "windows":
            self._checker = get_windows_status_checker()
        else:
            self.logger.warning(f"Unsupported platform: {self.platform}")
            self._checker = None
    
    async def get_all_status(self) -> Dict[str, Any]:
        """Get status of all network components"""
        if not self._checker:
            return {
                "wifi": {"status": "unsupported_platform", "connected": False},
                "lan": {"status": "unsupported_platform", "connected": False},
                "hotspot": {"status": "Unsupported Platform", "active": False},
                "platform": self.platform
            }
        
        try:
            # Get all statuses in parallel
            import asyncio
            wifi_task = asyncio.create_task(self._checker.get_wifi_status())
            lan_task = asyncio.create_task(self._checker.get_lan_status())
            hotspot_task = asyncio.create_task(self._checker.get_hotspot_status())
            
            wifi_status = await wifi_task
            lan_status = await lan_task
            hotspot_status = await hotspot_task
            
            return {
                "wifi": wifi_status,
                "lan": lan_status,
                "hotspot": hotspot_status,
                "platform": self.platform
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get network status: {e}")
            return {
                "wifi": {"status": "error", "connected": False, "error": str(e)},
                "lan": {"status": "error", "connected": False, "error": str(e)},
                "hotspot": {"status": "Error", "active": False, "error": str(e)},
                "platform": self.platform
            }
    
    async def get_wifi_status(self) -> Dict[str, Any]:
        """Get WiFi status only"""
        if not self._checker:
            return {"status": "unsupported_platform", "connected": False}
        
        try:
            return await self._checker.get_wifi_status()
        except Exception as e:
            self.logger.error(f"Failed to get WiFi status: {e}")
            return {"status": "error", "connected": False, "error": str(e)}
    
    async def get_lan_status(self) -> Dict[str, Any]:
        """Get LAN status only"""
        if not self._checker:
            return {"status": "unsupported_platform", "connected": False}
        
        try:
            return await self._checker.get_lan_status()
        except Exception as e:
            self.logger.error(f"Failed to get LAN status: {e}")
            return {"status": "error", "connected": False, "error": str(e)}
    
    async def get_hotspot_status(self) -> Dict[str, Any]:
        """Get hotspot status only"""
        if not self._checker:
            return {"status": "Unsupported Platform", "active": False}
        
        try:
            return await self._checker.get_hotspot_status()
        except Exception as e:
            self.logger.error(f"Failed to get hotspot status: {e}")
            return {"status": "Error", "active": False, "error": str(e)}
    
    def get_platform(self) -> str:
        """Get current platform"""
        return self.platform


# Global instance
_network_status_checker = None


def get_network_status_checker() -> NetworkStatusChecker:
    """Get network status checker singleton"""
    global _network_status_checker
    if _network_status_checker is None:
        _network_status_checker = NetworkStatusChecker()
    return _network_status_checker
