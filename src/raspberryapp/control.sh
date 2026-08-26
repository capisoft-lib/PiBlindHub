#!/bin/bash
# Simple control script for motorised store

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Function to show help
show_help() {
    echo "Motorised Store Control Script"
    echo "=============================="
    echo "Usage: $0 <command>"
    echo
    echo "Commands:"
    echo "  up      - Move store up (open)"
    echo "  down    - Move store down (close)"
    echo "  stop    - Stop motor"
    echo "  status  - Show current status"
    echo "  help    - Show this help"
    echo
    echo "Examples:"
    echo "  $0 up"
    echo "  $0 down"
    echo "  $0 stop"
    echo "  $0 status"
}

# Check if command is provided
if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

COMMAND=$1

# Run the command
case $COMMAND in
    "up"|"down"|"stop"|"status"|"help")
        python3 cli_control.py $COMMAND
        ;;
    *)
        echo "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
