#!/bin/bash
# Install Autopilot Service on Linux (systemd)

set -e

echo "========================================"
echo "Autopilot Service Installer (Linux)"
echo "========================================"
echo

SERVICE_NAME="autopilot-service"
SERVICE_FILE="autopilot-service.service"
SYSTEMD_DIR="/etc/systemd/system"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if service file exists
if [ ! -f "$SCRIPT_DIR/$SERVICE_FILE" ]; then
    echo "ERROR: Service file not found: $SERVICE_FILE"
    exit 1
fi

# Update paths in service file
echo "Updating service file with correct paths..."
VENV_PYTHON="$(dirname $(dirname $SCRIPT_DIR))/venv/bin/python"
sed -i "s|/path/to/SalesAgent/venv/bin|$(dirname $VENV_PYTHON)|g" "$SCRIPT_DIR/$SERVICE_FILE"
sed -i "s|/path/to/SalesAgent/SalesAgent15_/required_files_project|$SCRIPT_DIR|g" "$SCRIPT_DIR/$SERVICE_FILE"
sed -i "s|User=%i|User=$SUDO_USER|g" "$SCRIPT_DIR/$SERVICE_FILE"

# Copy service file to systemd directory
echo "Installing service file..."
cp "$SCRIPT_DIR/$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_NAME.service"

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable service (auto-start on boot)
echo "Enabling service..."
systemctl enable "$SERVICE_NAME"

echo
echo "========================================"
echo "Service installed successfully!"
echo "========================================"
echo
echo "Service Name: $SERVICE_NAME"
echo "Status: Stopped (not started yet)"
echo
echo "To start the service:"
echo "  sudo systemctl start $SERVICE_NAME"
echo
echo "To stop the service:"
echo "  sudo systemctl stop $SERVICE_NAME"
echo
echo "To check status:"
echo "  sudo systemctl status $SERVICE_NAME"
echo
echo "To view logs:"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo
