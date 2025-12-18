#!/bin/bash
# Start Action Plan Service manually (foreground mode for testing)

echo "========================================"
echo "Action Plan Service - Manual Start"
echo "========================================"
echo ""
echo "Running service in foreground mode..."
echo "Press Ctrl+C to stop"
echo ""
echo "========================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to script directory
cd "$SCRIPT_DIR"

# Try to find venv Python first
VENV_PYTHON="$(dirname $(dirname $SCRIPT_DIR))/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Virtual environment not found, using system Python..."
    VENV_PYTHON="python3"
fi

# Run the service
"$VENV_PYTHON" action_plan_service.py

echo ""
echo "Service stopped."
