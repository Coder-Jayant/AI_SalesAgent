#!/bin/bash
# Uninstall Action Plan Service from Linux

echo "========================================"
echo "Action Plan Service Uninstaller (Linux)"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

SERVICE_NAME="action-plan-service"

# Check if service exists
if ! systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
    echo "Service '$SERVICE_NAME' does not exist."
    echo "Nothing to uninstall."
    exit 0
fi

# Stop service if running
echo "Stopping service..."
systemctl stop "$SERVICE_NAME" 2>/dev/null

# Disable service
echo "Disabling service..."
systemctl disable "$SERVICE_NAME" 2>/dev/null

# Remove service file
echo "Removing service file..."
rm -f "/etc/systemd/system/$SERVICE_NAME.service"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload
systemctl reset-failed

echo ""
echo "========================================"
echo "Service uninstalled successfully!"
echo "========================================"
echo ""
