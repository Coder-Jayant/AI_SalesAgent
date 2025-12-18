#!/bin/bash
# Install Action Plan Service on Linux using systemd

echo "========================================"
echo "Action Plan Service Installer (Linux)"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVICE_FILE="action-plan-service.service"
SERVICE_NAME="action-plan-service"

echo "Project Directory: $SCRIPT_DIR"
echo "Service File: $SERVICE_FILE"
echo ""

# Check if service file exists
if [ ! -f "$SCRIPT_DIR/$SERVICE_FILE" ]; then
    echo "ERROR: Service file not found: $SERVICE_FILE"
    exit 1
fi

# Get current user (the one who ran sudo)
ACTUAL_USER="${SUDO_USER:-$USER}"
echo "Service will run as user: $ACTUAL_USER"
echo ""

# Create a temporary service file with actual paths
TEMP_SERVICE="/tmp/$SERVICE_NAME.service"
sed -e "s|your_username|$ACTUAL_USER|g" \
    -e "s|/path/to/your/project|$SCRIPT_DIR|g" \
    "$SCRIPT_DIR/$SERVICE_FILE" > "$TEMP_SERVICE"

# Copy service file to systemd directory
echo "Installing service file..."
cp "$TEMP_SERVICE" "/etc/systemd/system/$SERVICE_NAME.service"
rm "$TEMP_SERVICE"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service (auto-start on boot)
echo "Enabling service..."
systemctl enable "$SERVICE_NAME"

echo ""
echo "========================================"
echo "Service installed successfully!"
echo "========================================"
echo ""
echo "Service Name: $SERVICE_NAME"
echo "Status: Stopped (not started yet)"
echo ""
echo "To start the service:"
echo "  sudo systemctl start $SERVICE_NAME"
echo ""
echo "To stop the service:"
echo "  sudo systemctl stop $SERVICE_NAME"
echo ""
echo "To restart the service:"
echo "  sudo systemctl restart $SERVICE_NAME"
echo ""
echo "To view service status:"
echo "  sudo systemctl status $SERVICE_NAME"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo "  OR"
echo "  tail -f $SCRIPT_DIR/action_plan_service.log"
echo ""
