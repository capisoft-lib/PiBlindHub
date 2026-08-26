#!/usr/bin/env python3
"""
New Standalone Runner for Motorised Store
Simple runner for the new clean architecture
"""

import signal
import sys
import time
import logging
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from new_device_service import get_store_core, cleanup_store_core

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NewStandaloneRunner:
    """Simple standalone runner for the new architecture"""
    
    def __init__(self):
        self.store = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("New standalone runner initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Start the standalone runner"""
        try:
            print("=" * 60)
            print("PiBlindHub - New Clean Architecture")
            print("=" * 60)
            print("Physical buttons are active for manual control")
            print("Use new_cli_control.py for external control")
            print("Press Ctrl+C to quit")
            print("=" * 60)
            print()
            
            # Get store core
            self.store = get_store_core()
            self.store.start()
            self.running = True
            
            print("Store core started successfully!")
            print("Physical buttons:")
            print("  - Button on GPIO 25: Move UP (hold to move)")
            print("  - Button on GPIO 27: Move DOWN (hold to move)")
            print("  - Release button: Stop movement automatically")
            print()
            print("External control:")
            print("  python3 new_cli_control.py status")
            print("  python3 new_cli_control.py up")
            print("  python3 new_cli_control.py down")
            print("  python3 new_cli_control.py to 50")
            print("  python3 new_cli_control.py stop")
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
            
            if self.store:
                self.store.stop()
            
            cleanup_store_core()
            logger.info("Shutdown complete")


def main():
    """Main function"""
    try:
        runner = NewStandaloneRunner()
        runner.start()
    except Exception as e:
        logger.error(f"Failed to start standalone runner: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
