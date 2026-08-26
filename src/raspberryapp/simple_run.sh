#!/bin/bash
# Simple run script for motorised store

echo "Starting PiBlindHub - Simple Mode"
echo "=============================================="
echo "Ultra-simple replacement for original run.py"
echo "Physical buttons are active for manual control"
echo "Press Ctrl+C to quit"
echo "=============================================="
echo

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run the simple standalone runner
python3 standalone_runner.py
