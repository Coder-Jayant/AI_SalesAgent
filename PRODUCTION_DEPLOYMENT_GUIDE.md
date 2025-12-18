# Production Deployment Guide

Complete guide for deploying the SalesAgent system to production.

## Pre-Deployment Checklist

### 1. System Requirements

- **Operating System**: Windows Server 2016+ or Linux (Ubuntu 20.04+, CentOS 8+)
- **Python**: 3.9 or higher
- **Memory**: Minimum 4GB RAM
- **Disk Space**: 10GB free space
- **Network**: Stable internet connection for EWS and API access

### 2. Required Credentials

Ensure you have the following before deployment:

- **EWS (Exchange) Credentials**:
  - Email address
  - Password
  - Exchange server host

- **OpenAI API** (or compatible endpoint):
  - API key
  - Base URL
  - Model name

- **Qdrant Vector Database** (for RAG):
  - URL
  - API key

- **Optional - ElevenLabs** (for voice):
  - API key

## Deployment Steps

### Step 1: Extract Deployment Package

```bash
# Extract the zip file
unzip SalesAgent_deployment_YYYYMMDD_HHMMSS.zip -d /opt/salesagent

# Navigate to project directory
cd /opt/salesagent
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Copy the template
cp .env.template .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required .env variables**:
```ini
# EWS Configuration
EWS_EMAIL=your_email@company.com
EWS_PASSWORD=your_password
EWS_HOST=mail.company.com

# Agent Identity
AGENT_USER_NAME=Sales Agent
AGENT_EMAIL=salesagent@company.com

# OpenAI/LLM Configuration
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_key

# Service Configuration
AUTOPILOT_SERVICE_INTERVAL=300  # 5 minutes
AUTOPILOT_SERVICE_HANDS_FREE=false
ACTION_PLAN_SERVICE_INTERVAL=30  # 30 seconds
ACTION_PLAN_SERVICE_HANDS_FREE=false
```

### Step 4: Run Comprehensive Tests

```bash
# Make sure virtual environment is activated
python test_services_comprehensive.py
```

**Expected output**:
```
========================================
     COMPREHENSIVE SERVICE TESTING
========================================

Pre-flight Checks
✓ .env file found
✓ autopilot_state.json found
...

FINAL TEST REPORT
Total Tests: XX
Passed: XX
Failed: 0
Warnings: X

✓ ALL TESTS PASSED! System is ready for production deployment.
```

### Step 5: Install Services

#### On Windows

```batch
REM Install Autopilot Service
install_autopilot_service.bat

REM Install Action Plan Service
install_service.bat
```

#### On Linux

```bash
# Make scripts executable
chmod +x install_autopilot_service_linux.sh
chmod +x install_service_linux.sh

# Install services
sudo ./install_autopilot_service_linux.sh
sudo ./install_service_linux.sh
```

### Step 6: Start Services

#### On Windows

```batch
REM Start services
net start AutopilotService
net start ActionPlanService

REM Check service status
sc query AutopilotService
sc query ActionPlanService
```

#### On Linux

```bash
# Start services
sudo systemctl start autopilot-service
sudo systemctl start action-plan-service

# Enable auto-start on boot
sudo systemctl enable autopilot-service
sudo systemctl enable action-plan-service

# Check status
sudo systemctl status autopilot-service
sudo systemctl status action-plan-service
```

### Step 7: Monitor Services

#### View Logs

**Windows**:
```batch
REM View autopilot logs
type autopilot_service.log

REM View action plan logs
type action_plan_service.log
```

**Linux**:
```bash
# Real-time autopilot logs
sudo journalctl -u autopilot-service -f

# Real-time action plan logs
sudo journalctl -u action-plan-service -f

# OR use log files directly
tail -f autopilot_service.log
tail -f action_plan_service.log
```

#### Check Service Health

```python
# Run this Python snippet to check service status
from autopilot import _load_state, get_autopilot_service_enabled
from action_plans import get_manager

# Check autopilot state
state = _load_state()
print(f"Autopilot enabled: {get_autopilot_service_enabled()}")
print(f"Last run: {state.get('service_last_run', 'Never')}")

# Check action plans
manager = get_manager()
plans = manager.list_plans(status_filter='enabled')
print(f"Active action plans: {len(plans)}")
```

### Step 8: Access UI

#### Streamlit UI (main interface)

```bash
# Activate venv and start Streamlit
source venv/bin/activate  # On Linux
# venv\Scripts\activate  # On Windows

streamlit run main_react.py --server.port 8501
```

Access at: `http://your-server-ip:8501`

#### Web UI (optional)

```bash
# Navigate to web_ui directory
cd web_ui

# Start the API server
python api_server.py
```

Access at: `http://your-server-ip:5000`

## Production Configuration

### Recommended Settings

#### For High-Volume Email Processing

```ini
# .env settings
AUTOPILOT_SERVICE_INTERVAL=180  # 3 minutes
AUTOPILOT_MAX_ACTIONS=5  # Process up to 5 emails per run
```

#### For Testing/Staging

```ini
AUTOPILOT_SERVICE_HANDS_FREE=false  # All emails saved as drafts
ACTION_PLAN_SERVICE_HANDS_FREE=false
```

#### For Production

```ini
AUTOPILOT_SERVICE_HANDS_FREE=true  # Auto-send routine emails
ACTION_PLAN_SERVICE_HANDS_FREE=true
```

### Security Best Practices

1. **Protect .env file**:
   ```bash
   chmod 600 .env  # Linux only
   ```

2. **Use firewall rules**:
   - Block external access to ports 8501, 5000
   - Allow only internal network or VPN access

3. **Regular credential rotation**:
   - Rotate EWS password every 90 days
   - Rotate API keys quarterly

4. **Monitor logs for suspicious activity**:
   ```bash
   # Set up log rotation
   # Linux: Configure in /etc/logrotate.d/
   ```

## Troubleshooting

### Services Won't Start

**Check logs**:
```bash
# Windows
type autopilot_service_stderr.log

# Linux
sudo journalctl -xe -u autopilot-service
```

**Common issues**:
- Invalid credentials in .env
- Port conflicts
- Missing Python dependencies
- Insufficient permissions

**Solutions**:
```bash
# Verify credentials
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(f'Email: {os.getenv(\"EWS_EMAIL\")}')"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check service user permissions (Linux)
sudo chown -R salesagent:salesagent /opt/salesagent
```

### Email Processing Issues

**Test EWS connection**:
```python
python -c "from ews_tools2 import list_inbox_emails; print(list_inbox_emails(top=1))"
```

**Check autopilot rules**:
```python
from autopilot import get_autopilot_rules
rules = get_autopilot_rules()
for rule in rules:
    print(f"{rule['name']}: {'enabled' if rule['enabled'] else 'disabled'}")
```

### Action Plans Not Executing

**Debug action plan service**:
```bash
# Stop service
sudo systemctl stop action-plan-service  # Linux
net stop ActionPlanService  # Windows

# Run manually in foreground
python action_plan_service.py
# Watch for errors in output

# Ctrl+C to stop, then restart service
```

**Check plan schedules**:
```python
from action_plans import get_manager
from datetime import datetime
from zoneinfo import ZoneInfo

manager = get_manager()
plans = manager.list_plans(status_filter='enabled')

now = datetime.now(ZoneInfo("Asia/Kolkata"))
for plan in plans:
    print(f"{plan.name}:")
    print(f"  Next execution: {plan.next_execution}")
    print(f"  Should run: {plan.next_execution <= now.isoformat() if plan.next_execution else 'No schedule'}")
```

## Maintenance

### Daily Tasks

- Check service status
- Review error logs
- Monitor email processing volume

### Weekly Tasks

- Review and clean old logs
- Check disk space usage
- Verify credential validity

### Monthly Tasks

- Update autopilot rules as needed
- Review action plan effectiveness
- Update Python dependencies (test first)
- Backup configuration files

### Backup Strategy

```bash
# Backup critical files
tar -czf salesagent_backup_$(date +%Y%m%d).tar.gz \
    .env \
    autopilot_state.json \
    action_plans_state.json \
    ews_accounts.json \
    rag_state.json
```

## Scaling Considerations

### For High Email Volume

1. **Increase autopilot frequency**:
   ```ini
   AUTOPILOT_SERVICE_INTERVAL=60  # Check every minute
   ```

2. **Process more emails per run**:
   ```ini
   AUTOPILOT_MAX_ACTIONS=10
   ```

3. **Add monitoring**:
   - Set up alerting for service failures
   - Monitor queue depth
   - Track response times

### For Multiple Agents

Deploy separate instances with different `.env` configurations:
```bash
/opt/salesagent-team1/
/opt/salesagent-team2/
/opt/salesagent-support/
```

## Rollback Procedure

If issues arise after deployment:

1. **Stop services**:
   ```bash
   sudo systemctl stop autopilot-service action-plan-service
   ```

2. **Restore configuration**:
   ```bash
   tar -xzf salesagent_backup_YYYYMMDD.tar.gz
   ```

3. **Restart services**:
   ```bash
   sudo systemctl start autopilot-service action-plan-service
   ```

## Support

### Log Files Location

- `autopilot_service.log` - Autopilot execution logs
- `action_plan_service.log` - Action plan execution logs
- `autopilot_service_stderr.log` - Autopilot errors
- `action_plan_service_stderr.log` - Action plan errors
- `test_report.json` - Latest test results

### Debug Mode

Run services in foreground for detailed debugging:

```bash
# Linux
./start_autopilot_service_manually_linux.sh
./start_service_manually_linux.sh

# Windows
start_autopilot_service_manually.bat
start_service_manually.bat
```

## Post-Deployment Verification

After 24 hours, verify:

- [x] Both services running
- [x] Emails being processed
- [x] Action plans executing on schedule
- [x] No critical errors in logs
- [x] Resource usage acceptable (CPU < 50%, Memory < 80%)

---

**Congratulations! Your SalesAgent system is now in production.** 🚀
