#!/bin/bash
# Manually start Autopilot Service for testing
# This runs the service in the foreground (not as systemd service)

echo "========================================"
echo "Starting Autopilot Service Manually"
echo "========================================"
echo
echo "Press Ctrl+C to stop"
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Navigate to script directory
cd "$SCRIPT_DIR"

# Find Python executable
VENV_PYTHON="$(dirname $(dirname $SCRIPT_DIR))/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    # Try alternative path
    VENV_PYTHON="python3"
fi

# Check if Python exists
if ! command -v "$VENV_PYTHON" &> /dev/null; then
    echo "ERROR: Python not found"
    echo "Please ensure Python 3 is installed or venv is set up"
    exit 1
fi

# Run the service
"$VENV_PYTHON" autopilot_service.py
