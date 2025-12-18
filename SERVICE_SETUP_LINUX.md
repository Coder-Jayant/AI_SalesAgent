# Action Plan Service - Linux Setup Guide

## Overview
Instructions for installing and running the Action Plan Service on Linux (Ubuntu/Debian/CentOS/RHEL) using systemd.

## Prerequisites

### Python 3
```bash
python3 --version
# Should show Python 3.8 or later
```

### Required Python packages
```bash
# Install required packages
pip3 install -r requirements.txt
```

---

## Installation

### Step 1: Make scripts executable
```bash
chmod +x install_service_linux.sh
chmod +x uninstall_service_linux.sh
chmod +x start_service_manually_linux.sh
```

### Step 2: Test Manual Execution (Recommended)
Before installing as a service, test it manually:

```bash
./start_service_manually_linux.sh
```

You should see log output. Press `Ctrl+C` to stop.

### Step 3: Install as Systemd Service
```bash
# Run as root
sudo ./install_service_linux.sh
```

This will:
- Install the service as "action-plan-service"
- Configure it to start automatically on boot
- Set up logging
- Configure restart on failure

### Step 4: Start the Service
```bash
sudo systemctl start action-plan-service
```

---

## Service Management

### Check Service Status
```bash
sudo systemctl status action-plan-service
```

### Stop the Service
```bash
sudo systemctl stop action-plan-service
```

### Restart the Service
```bash
sudo systemctl restart action-plan-service
```

### View Logs (Real-time)
```bash
# Using journalctl (systemd logs)
sudo journalctl -u action-plan-service -f

# Using log file
tail -f action_plan_service.log
```

### View Recent Logs
```bash
# Last 100 lines
sudo journalctl -u action-plan-service -n 100

# OR from log file
tail -n 100 action_plan_service.log
```

### Enable/Disable Auto-Start
```bash
# Enable (start on boot)
sudo systemctl enable action-plan-service

# Disable (don't start on boot)
sudo systemctl disable action-plan-service
```

### Uninstall the Service
```bash
sudo ./uninstall_service_linux.sh
```

---

## Configuration

### Environment Variables
Edit the service file directly or create a `.env` file:

```bash
# Edit service file
sudo nano /etc/systemd/system/action-plan-service.service

# Add/modify environment variables in the [Service] section:
Environment="ACTION_PLAN_SERVICE_INTERVAL=30"
Environment="ACTION_PLAN_SERVICE_HANDS_FREE=false"
Environment="ACTION_PLAN_SERVICE_LOG_LEVEL=INFO"

# Reload and restart after changes
sudo systemctl daemon-reload
sudo systemctl restart action-plan-service
```

---

## Troubleshooting

### Service won't start
```bash
# Check status and logs
sudo systemctl status action-plan-service
sudo journalctl -u action-plan-service -n 50

# Test manually
./start_service_manually_linux.sh
```

### Permission denied errors
```bash
# Make sure service runs as the correct user
# Check the User= line in /etc/systemd/system/action-plan-service.service
sudo nano /etc/systemd/system/action-plan-service.service
```

### Python not found
```bash
# Check Python path
which python3

# Update ExecStart in service file if needed
sudo nano /etc/systemd/system/action-plan-service.service
```

---

## System Service File Location

The systemd service file is installed at:
```
/etc/systemd/system/action-plan-service.service
```

---

## Logs Location

Logs are written to:
- `action_plan_service.log` (main log, in project directory)
- `action_plan_service_stdout.log` (stdout)
- `action_plan_service_stderr.log` (stderr)
- journalctl (systemd logs)

---

## Notes

- The service runs as the user who executed the install script (or USER specified in service file)
- Logs rotate daily and keep 7 days of history
- The service automatically restarts on failure (5-second delay)
- Works independently of Streamlit UI and autopilot mode

**Service is now running 24/7 on Linux!** 🐧
