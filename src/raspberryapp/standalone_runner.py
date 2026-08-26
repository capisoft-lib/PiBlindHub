#!/usr/bin/env python3
"""
Simple Standalone Runner for Motorised Store
Minimalistic replacement for original run.py
"""

import signal
import sys
import time
import logging
from device_service import get_device_service, cleanup_device_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleStandaloneRunner:
    """Simple standalone runner"""
    
    def __init__(self):
        self.device_service = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Simple standalone runner initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Start the standalone runner"""
        try:
            print("=" * 60)
            print("PiBlindHub - Simple Standalone Mode")
            print("=" * 60)
            print("Physical buttons are active for manual control")
            print("Press Ctrl+C to quit")
            print("=" * 60)
            print()
            
            # Get device service
            self.device_service = get_device_service()
            self.device_service.start()
            self.running = True
            
            print("Device service started. Press Ctrl+C to quit.")
            print("Physical buttons:")
            print("  - Button on GPIO 25: Open/Stop")
            print("  - Button on GPIO 27: Close/Stop")
            print()
            
            # Main loop
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Error in standalone runner: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the standalone runner"""
        if self.running:
            logger.info("Stopping standalone runner...")
            self.running = False
            
            if self.device_service:
                self.device_service.stop()
            
            cleanup_device_service()
            logger.info("Shutdown complete")

def main():
    """Main function"""
    try:
        runner = SimpleStandaloneRunner()
        runner.start()
    except Exception as e:
        logger.error(f"Failed to start standalone runner: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
