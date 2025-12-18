# Autopilot Service Setup Guide

## Overview

The Autopilot Service is a Windows background service that continuously monitors and processes emails based on configured autopilot rules. It runs independently of the Streamlit UI and persists across system reboots.

## Architecture

- **Service Name**: `AutopilotService`
- **Display Name**: Autopilot Email Processing Service  
- **Service Type**: Windows Service (via NSSM)
- **Auto-Start**: Yes (when `service_enabled: true` in state)
- **Hands-Free Mode**: Configurable via environment variable

## Prerequisites

1. **NSSM (Non-Sucking Service Manager)**
   - Download from: https://nssm.cc/download
   - Extract `nssm.exe` to the project directory or add to PATH

2. **Python Virtual Environment**
   - Ensure Python venv is set up at: `C:\Users\JayantVerma\AA\SSH_AGENT\SOLO_AGENTS\SalesAgent\venv`

3. **Environment Configuration**
   - `.env` file with autopilot service settings configured

## Installation

### Windows Installation

1. **Install Service**
   ```cmd
   .\install_autopilot_service.bat
   ```

2. **Verify Installation**
   ```cmd
   sc query AutopilotService
   ```

3. **Start Service** (via UI toggle or manually)
   ```cmd
   net start AutopilotService
   ```

### Service Management Commands

**Check Status:**
```cmd
sc query AutopilotService
# OR
nssm status AutopilotService
```

**Start Service:**
```cmd
net start AutopilotService
# OR
nssm start AutopilotService
```

**Stop Service:**
```cmd
net stop AutopilotService
# OR
nssm stop AutopilotService
```

**Restart Service:**
```cmd
net stop AutopilotService
timeout /t 2
net start AutopilotService
```

**Uninstall Service:**
```cmd
.\uninstall_autopilot_service.bat
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Autopilot Service Configuration
AUTOPILOT_SERVICE_INTERVAL=300        # Check interval in seconds (default: 300 = 5 minutes)
AUTOPILOT_SERVICE_HANDS_FREE=false    # Enable hands-free mode (true/false)
AUTOPILOT_SERVICE_LOG_LEVEL=INFO      # Logging level (DEBUG, INFO, WARNING, ERROR)
```

### State File

The service reads `autopilot_state.json` to determine if it should run:

```json
{
  "service_enabled": true,
  "autohandle_period_minutes": 5,
  "service_last_run": "2025-12-14T00:30:00+05:30",
  "autopilot_rules": [...]
}
```

### UI Control

The Streamlit UI provides a toggle to enable/disable the service:

1. Open UI: `streamlit run main_react.py`
2. Navigate to sidebar → Autopilot Service section
3. Toggle "Enable Autopilot Service" ON/OFF
4. The toggle will start/stop the Windows service automatically

**Features:**
- ✅ Service status indicator (Running/Stopped/Not Installed)
- ⚙️ Configure check interval (minutes)
- 🔄 Restart service button
- ⏱️ Last run timestamp display
- ▶️ Manual run button

## How It Works

### Service Loop

```
1. Check if service_enabled == true in autopilot_state.json
2. If disabled, sleep for 30 seconds and check again
3. If enabled:
   a. Call autopilot_once() to process emails
   b. Update service_last_run timestamp
   c. Log activity
   d. Sleep for configured interval
4. Repeat
```

### Email Processing

When enabled, the service:
1. Fetches unread emails from EWS
2. Applies autopilot rules (priority-ordered)
3. Uses ReAct agent for intelligent processing
4. Executes actions (reply, mark read, escalate, etc.)
5. Saves processed email IDs to avoid duplicates
6. Logs all activities

## Logging

### Log Files

- `autopilot_service.log` - Main rotating log (daily rotation, 7 days retention)
- `autopilot_service_stdout.log` - Standard output
- `autopilot_service_stderr.log` - Error output

### Log Location

All log files are in the project directory:
```
c:\Users\JayantVerma\AA\SSH_AGENT\SOLO_AGENTS\SalesAgent\SalesAgent15_\required_files_project\
```

### View Logs

```cmd
# Real-time log monitoring
Get-Content autopilot_service.log -Wait -Tail 50

# View last 100 lines
Get-Content autopilot_service.log -Tail 100
```

## Troubleshooting

### Service Won't Start

**Check 1: Service Enabled in State?**
```json
// autopilot_state.json
{
  "service_enabled": true  // Must be true
}
```

**Check 2: Python Path Correct?**
- Verify venv exists: `C:\Users\JayantVerma\AA\SSH_AGENT\SOLO_AGENTS\SalesAgent\venv\Scripts\python.exe`

**Check 3: Check Error Logs**
```cmd
Get-Content autopilot_service_stderr.log -Tail 50
```

### Service Installed But Not Running

1. Check service status:
   ```cmd
   sc query AutopilotService
   ```

2. Try manual start:
   ```cmd
   .\start_autopilot_service_manually.bat
   ```
   This runs in foreground for debugging.

3. Check Windows Event Viewer:
   - Open Event Viewer
   - Navigate to: Windows Logs → Application
   - Look for errors from "AutopilotService"

### Emails Not Being Processed

**Check 1: Service Running?**
- Verify status indicator in UI shows "Running"

**Check 2: Rules Enabled?**
- Check Autopilot Rules tab in UI
- Ensure at least one rule is enabled

**Check 3: EWS Credentials Valid?**
- Test credentials in Connection Settings tab

**Check 4: Check Processed IDs**
- Emails already in `processed_mails.json` will be skipped

### Service Crashes on Startup

1. Check `.env` file exists and is valid
2. Verify all required Python packages installed in venv
3. Check `autopilot_service_stderr.log` for stack trace
4. Run manually to see full error:
   ```cmd
   .\start_autopilot_service_manually.bat
   ```

### Configuration Changes Not Applied

After changing `.env` or interval settings:
1. Click "Restart" button in UI, OR
2. Manually restart:
   ```cmd
   net stop AutopilotService
   net start AutopilotService
   ```

## Testing

### Test Service Installation

```cmd
# 1. Install service
.\install_autopilot_service.bat

# 2. Check status
sc query AutopilotService
# Should show STATE: STOPPED

# 3. Enable via UI toggle
# Open Streamlit UI, toggle ON

# 4. Verify service started
sc query AutopilotService
# Should show STATE: RUNNING

# 5. Check logs
Get-Content autopilot_service.log -Wait -Tail 20
```

### Test Email Processing

1. Send test email to configured EWS account
2. Wait for check interval (default 5 minutes)
3. Check logs for processing activity:
   ```cmd
   Get-Content autopilot_service.log -Tail 50 | Select-String "processed"
   ```
4. Verify email in `processed_mails.json`

### Test Service Persistence (Reboot)

1. Enable autopilot service via UI
2. Verify service running
3. Reboot system
4. After reboot, check service status:
   ```cmd
   sc query AutopilotService
   ```
   Should auto-start if `service_enabled: true`

## Migration from UI-Only Autopilot

If previously using the UI toggle (old version without service):

1. **Install Service**: Run `install_autopilot_service.bat`
2. **Enable via UI**: Toggle "Enable Autopilot Service" ON
3. **Verify**: Check service status in UI sidebar
4. **Test**: Close UI completely, service should keep running

**Key Differences:**
- **Old**: Autopilot only ran when UI was open
- **New**: Service runs independently, survives UI close and reboot

## Advanced Configuration

### Change Check Interval

**Via UI:**
1. Enter desired minutes in "Check interval" field
2. Click "Save" button  
3. Click "Restart" button to apply

**Via .env:**
```env
# Example: Check every 10 minutes (600 seconds)
AUTOPILOT_SERVICE_INTERVAL=600
```
Then restart service.

### Enable Hands-Free Mode

**Warning**: Hands-free mode auto-sends emails without drafting.

```env
AUTOPILOT_SERVICE_HANDS_FREE=true
```

Restart service after changing.

### Adjust Logging Level

For more verbose logging:
```env
AUTOPILOT_SERVICE_LOG_LEVEL=DEBUG
```

Restart service after changing.

## Security Considerations

1. **Credentials**: EWS credentials are in `.env` - protect this file
2. **Service Runs as**: Current user account (via NSSM)
3. **Auto-Start**: Service starts automatically on boot if enabled
4. **Hands-Free Mode**: Use with caution - emails sent automatically

## Uninstallation

1. Stop and disable service via UI toggle
2. Run uninstaller:
   ```cmd
   .\uninstall_autopilot_service.bat
   ```
3. Verify removal:
   ```cmd
   sc query AutopilotService
   # Should return "The specified service does not exist"
   ```

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review log files for errors
3. Test with manual run: `.\start_autopilot_service_manually.bat`
4. Verify configuration in `.env` and `autopilot_state.json`
