"""
Logging utilities
"""

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO"):
    """Setup application logging"""
    try:
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("logs/app.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured with level: {level}")
        
    except Exception as e:
        print(f"Failed to setup logging: {e}")
        # Fallback to basic logging
        logging.basicConfig(level=logging.INFO)
