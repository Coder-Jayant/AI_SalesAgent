#!/bin/bash
# Uninstall Autopilot Service on Linux

set -e

echo "========================================"
echo "Autopilot Service Uninstaller (Linux)"
echo "========================================"
echo

SERVICE_NAME="autopilot-service"
SYSTEMD_DIR="/etc/systemd/system"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Check if service exists
if [ ! -f "$SYSTEMD_DIR/$SERVICE_NAME.service" ]; then
    echo "Service not installed"
    exit 0
fi

# Stop service
echo "Stopping service..."
systemctl stop "$SERVICE_NAME" || true

# Disable service
echo "Disabling service..."
systemctl disable "$SERVICE_NAME"

# Remove service file
echo "Removing service file..."
rm -f "$SYSTEMD_DIR/$SERVICE_NAME.service"

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

echo
echo "========================================"
echo "Service uninstalled successfully!"
echo "========================================"
echo
