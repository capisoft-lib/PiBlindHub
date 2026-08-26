#!/usr/bin/env python3
"""
Webapp runner script for PiBlindHub
Run this from the project root directory
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and run the webapp
if __name__ == "__main__":
    from src.webapp.main import main
    main()
