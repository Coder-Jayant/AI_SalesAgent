# Action Plan Service Setup Guide

## Overview
The Action Plan Service is a standalone background service that executes scheduled action plans automatically, independent of the Streamlit UI and autopilot mode.

## Features
- ✅ Runs 24/7 in the background
- ✅ Independent of Streamlit UI (works even when UI is closed)
- ✅ Independent of autopilot mode  
- ✅ Auto-starts with Windows
- ✅ Graceful shutdown handling
- ✅ Comprehensive logging
- ✅ Automatic restart on failure

## Prerequisites

### 1. Download NSSM (Non-Sucking Service Manager)
1. Go to https://nssm.cc/download
2. Download the latest version (e.g., `nssm-2.24.zip`)
3. Extract the ZIP file
4. Copy `nssm.exe` from the `win64` folder to your project directory
   - OR add it to your system PATH

### 2. Verify Python Installation
```powershell
python --version
```

Should show Python 3.10 or later.

---

## Installation

### Step 1: Test Manual Execution (Recommended)
Before installing as a service, test it manually:

```powershell
# Run in foreground mode
.\start_service_manually.bat
```

You should see log output like:
```
2025-12-10 12:30:00 - Action Plan Service Starting
2025-12-10 12:30:00 - Check Interval: 30 seconds
2025-12-10 12:30:00 - Hands-Free Mode: False
...
[Iteration 1] Checking scheduled plans at 2025-12-10 12:30:00
```

Press `Ctrl+C` to stop. If it works correctly, proceed to install as a service.

### Step 2: Install as Windows Service
```powershell
# Run as Administrator
.\install_service.bat
```

This will:
- Install the service as "ActionPlanService"
- Configure it to start automatically with Windows
- Set up logging
- Configure restart on failure

### Step 3: Start the Service
```powershell
# Start the service
net start ActionPlanService

# OR
nssm start ActionPlanService
```

---

## Service Management

### Check Service Status
```powershell
# Using Windows service command
sc query ActionPlanService

# Using NSSM
nssm status ActionPlanService
```

### Stop the Service
```powershell
# Using Windows service command
net stop ActionPlanService

# Using NSSM
nssm stop ActionPlanService
```

### Restart the Service
```powershell
# Using Windows service command
net stop ActionPlanService
net start ActionPlanService

# Using NSSM
nssm restart ActionPlanService
```

### View Service Logs
Logs are written to the project directory:
- `action_plan_service.log` - Main application log (rotates daily, keeps 7 days)
- `action_plan_service_stdout.log` - Standard output
- `action_plan_service_stderr.log` - Standard error

```powershell
# View main log (PowerShell)
Get-Content -Path action_plan_service.log -Tail 50 -Wait

# View main log (Command Prompt)
tail -f action_plan_service.log
```

### Uninstall the Service
```powershell
.\uninstall_service.bat
```

---

## Configuration

### Environment Variables
Create or edit `.env` file in the project directory:

```env
# Check interval in seconds (default: 30)
ACTION_PLAN_SERVICE_INTERVAL=30

# Enable hands-free mode - send emails automatically (default: false)
ACTION_PLAN_SERVICE_HANDS_FREE=false

# Log level (default: INFO)
# Options: DEBUG, INFO, WARNING, ERROR
ACTION_PLAN_SERVICE_LOG_LEVEL=INFO
```

### Applying Configuration Changes
After changing environment variables:
1. Stop the service: `net stop ActionPlanService`
2. Start the service: `net start ActionPlanService`

---

## How It Works

```
┌─────────────────────────────────────┐
│   Action Plan Service (Background)  │
│                                     │
│   Every 30 seconds:                 │
│   1. Check all enabled action plans │
│   2. Execute plans that are due     │
│   3. Update execution status        │
│   4. Log results                    │
└─────────────────────────────────────┘
          │
          ├─ Uses: action_plans/executor.py
          ├─ Uses: scheduled_tasks.py
          └─ Uses: ReAct agent for execution
```

### Execution Flow
1. Service starts automatically with Windows
2. Every 30 seconds, checks for scheduled plans
3. For each enabled plan:
   - Checks if it's due (using `ScheduledTaskManager`)
   - If due, executes using ReAct agent
   - Updates `last_executed`, `next_execution`, `execution_count`
   - Records result in execution history
4. Logs all activity to `action_plan_service.log`

---

## Troubleshooting

### Service won't start
1. Check if Python is in PATH:
   ```powershell
   python --version
   ```
2. Check service logs:
   ```powershell
   Get-Content action_plan_service_stderr.log
   ```
3. Try running manually first:
   ```powershell
   .\start_service_manually.bat
   ```

### Plans not executing
1. Check if service is running:
   ```powershell
   nssm status ActionPlanService
   ```
2. Check the main log for errors:
   ```powershell
   Get-Content -Tail 100 action_plan_service.log
   ```
3. Verify plans are enabled in the UI (Tab 5: Action Plans)
4. Check `next_execution` time in the UI

### High CPU usage
- Increase `ACTION_PLAN_SERVICE_INTERVAL` (e.g., 60 seconds)
- This reduces check frequency

### Service crashes/restarts frequently
1. Check `action_plan_service_stderr.log` for errors
2. Check `action_plan_service.log` for exceptions
3. Verify all dependencies are installed
4. Test manually: `.\start_service_manually.bat`

---

## Best Practices

### 1. Start with Manual Testing
Always test with `start_service_manually.bat` before installing as a service.

### 2. Monitor Logs Initially
For the first few hours after installation, monitor logs to ensure proper execution:
```powershell
Get-Content -Path action_plan_service.log -Tail 50 -Wait
```

### 3. Hands-Free Mode
- Start with `hands_free=false` (default) to review drafts
- Once confident, switch to `hands_free=true` for automatic sending

### 4. Check Interval
- 30 seconds is recommended for most use cases
- For high-frequency plans (every minute), keep at 30s
- For low-frequency plans (hourly/daily), can increase to 60s

### 5. Regular Monitoring
Check service status and logs periodically to ensure smooth operation.

---

## Example Usage

### Create a Plan That Runs Every Minute
1. Use the chatbot to create a plan:
   ```
   Create an action plan to send a test email every minute
   ```
2. Agent creates plan with `custom_interval_minutes=1`
3. Service automatically executes it every minute (no UI or autopilot needed!)

### View Execution History
1. Open Streamlit UI
2. Go to Tab 5 (Action Plans)
3. Scroll to "Execution History" section
4. See all past executions with timestamps and results

---

## Uninstalling

To completely remove the service:

1. Stop and uninstall the service:
   ```powershell
   .\uninstall_service.bat
   ```

2. Delete service files (optional):
   ```powershell
   del action_plan_service.py
   del install_service.bat
   del uninstall_service.bat
   del start_service_manually.bat
   del action_plan_service*.log
   ```

---

## Notes

- The service runs under the SYSTEM account by default
- Logs rotate daily and keep 7 days of history
- The service automatically restarts on failure (5-second delay)
- Works independently - Streamlit UI can be closed
- Works independently - Autopilot can be OFF

**Service is now running 24/7, executing your scheduled action plans!** 🎉
