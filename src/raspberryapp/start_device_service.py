#!/usr/bin/env python3
"""
Device Service Startup Script
Initializes the device service for webapp integration
"""

import sys
import logging
import signal
import time
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent))

from device_service import get_device_service, cleanup_device_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeviceServiceManager:
    """Manages the device service for webapp integration"""
    
    def __init__(self, device_id: str = "webapp_store"):
        self.device_id = device_id
        self.device_service = None
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"Device service manager initialized for device: {device_id}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def start(self):
        """Start the device service"""
        try:
            # Initialize device service
            self.device_service = get_device_service(self.device_id)
            
            # Note: Webapp integration removed - using cli_control.py for all control
            
            logger.info("Device service started - use cli_control.py for external control")
            logger.info("Physical buttons are active for manual control")
            
            # Keep running until shutdown signal
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to start device service: {e}")
            raise
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the device service"""
        logger.info("Shutting down device service...")
        
        
        if self.device_service:
            cleanup_device_service()
        
        logger.info("Device service shutdown complete")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Start device service")
    parser.add_argument("--device-id", default="webapp_store",
                       help="Device identifier")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("=" * 60)
    print("Motorised Store Device Service")
    print("=" * 60)
    print(f"Device ID: {args.device_id}")
    print("Physical buttons are active for manual control")
    print("Use cli_control.py for external control")
    print("Press Ctrl+C to quit")
    print("=" * 60)
    
    manager = DeviceServiceManager(args.device_id)
    manager.start()


if __name__ == "__main__":
    main()
