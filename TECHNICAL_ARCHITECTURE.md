# SalesAgent AI - Technical Architecture Overview

## Executive Summary

**SalesAgent AI** is an enterprise-grade autonomous email management system powered by ReAct (Reasoning + Acting) agent architecture. The system provides 24/7 intelligent email processing, scheduled workflow automation, and real-time conversational AI capabilities.

---

## Core Architecture Components

### 1. ReAct Agent Engine
- **Framework**: Chain-of-Thought + Tool Execution Loop
- **LLM Backend**: GPT-4 compatible (OpenAI/Custom)
- **Temperature**: 0.2 (deterministic reasoning)
- **Max Iterations**: 50 per session
- **Token Limit**: 5000 per response
- **Tool Registry**: 35 registered tools

### 2. Service Architecture

#### Autopilot Service (`autopilot_service.py`)
```
Service Type: Background Windows/Linux Service
Check Interval: 300s (configurable)
Execution Model: Priority-based rule matching
State Management: autopilot_state.json
Control Mechanism: service_enabled flag
Credential Reload: Every iteration
Lock File: autopilot.lock (300s timeout)
```

**Key Features**:
- Custom rule engine with priority ordering
- Knowledge base integration
- EWS email processing
- Draft vs hands-free mode
- Real-time credential updates

#### Action Plan Service (`action_plan_service.py`)
```
Service Type: Background Windows/Linux Service  
Poll Interval: 30s (configurable)
Execution Model: Time-based scheduler
State Management: action_plans_state.json
Storage Backend: Atomic write with backups
Lock File: action_plans_execution.lock (300s timeout)
Retry Logic: 3 attempts with exponential backoff
```

**Key Features**:
- Flexible scheduling (daily/weekly/monthly/custom)
- Independent service execution
- Automatic retry on failure
- Execution history tracking
- Time window restrictions

### 3. Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      INPUT SOURCES                           │
├─────────────────────────────────────────────────────────────┤
│ • User Chatbox (Streamlit UI)                              │
│ • Email Inbox (EWS Protocol)                               │
│ • Scheduled Triggers (Action Plans)                        │
│ • Webhooks (Future)                                        │
└──────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              ReAct AGENT CORE ENGINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Thought] → [Action] → [Execute] → [Observe] → [Answer]  │
│      ▲                                            │          │
│      └────────────── Loop (Max 50x) ──────────────┘         │
│                                                              │
│  • LLM Reasoning Engine                                    │
│  • Tool Selection Logic                                    │
│  • Context Management                                       │
│  • Error Handling                                          │
└──────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   TOOL ECOSYSTEM (35)                       │
├─────────────────────────────────────────────────────────────┤
│ Email Tools (12)    │ Action Plans (4)  │ KB/RAG (2)      │
│ Search (3)          │ Calendar (3)      │ Automation (5)   │
│ Utility (6)                                                 │
└──────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      OUTPUT LAYER                            │
├─────────────────────────────────────────────────────────────┤
│ • Email Responses (Draft/Send)                             │
│ • Action Plan Creation                                      │
│ • Knowledge Base Updates                                   │
│ • UI Feedback                                              │
│ • Execution Logs                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Tool Ecosystem Details

### Email Management Tools (12)
1. `list_inbox_emails` - Fetch inbox with filtering
2. `search_emails_tool` - Advanced search queries
3. `get_email_thread_tool` - Retrieve conversation threads
4. `send_mail_tool` - Compose and send emails
5. `reply_to_email_tool` - Reply with CC/BCC preservation
6. `save_draft_tool` - Create draft emails
7. `get_drafts_tool` - List draft messages
8. `delete_draft_tool` - Remove drafts
9. `mark_email_as_read` - Update read status
10. `move_email_to_folder` - Organize emails
11. `create_folder_tool` - Create new folders
12. `set_email_importance` - Set priority flags

### Action Plan Tools (4)
- `create_action_plan` - Schedule new workflows
- `list_action_plans` - View all plans
- `update_action_plan` - Modify existing plans
- `delete_action_plan` - Remove plans

### Knowledge Base Tools (2)
- `query_knowledge_base` - RAG-based search
- `add_to_knowledge_base` - Insert documents

### Remaining Tools (17)
- Web search, calendar invites, EWS config, utilities

---

## State Management

### Autopilot State (`autopilot_state.json`)
```json
{
  "service_enabled": boolean,
  "service_last_run": "ISO timestamp",
  "period_minutes": integer,
  "hands_free": boolean,
  "max_actions": integer,
  "rules": [
    {
      "id": "string",
      "name": "string",
      "enabled": boolean,
      "prompt": "string",
      "priority": integer
    }
  ]
}
```

### Action Plan State (`action_plans_state.json`)
```json
{
  "plans": {
    "plan_id": {
      "id": "string",
      "name": "string",
      "task": "string",
      "schedule_type": "daily|weekly|monthly|custom",
      "schedule_time": "HH:MM",
      "enabled": boolean,
      "next_execution": "ISO timestamp",
      "execution_history": [...]
    }
  }
}
```

### Storage Features
- **Atomic Writes**: Temp file → Rename pattern
- **Auto Backups**: Keep last 10 versions
- **Error Recovery**: Restore from backup on corruption
- **Thread Safety**: File-based locking
- **Encoding**: UTF-8 with error handling

---

## Service Deployment

### Windows Deployment
```batch
# Install as Windows Service (NSSM)
install_autopilot_service.bat
install_service.bat

# Service Names
- AutopilotService
- ActionPlanService

# Control
net start AutopilotService
net stop ActionPlanService
sc query AutopilotService
```

### Linux Deployment
```bash
# Install systemd services
sudo ./install_autopilot_service_linux.sh
sudo ./install_service_linux.sh

# Service Names
- autopilot-service.service
- action-plan-service.service

# Control
sudo systemctl start autopilot-service
sudo systemctl status action-plan-service
sudo journalctl -u autopilot-service -f
```

---

## Configuration

### Environment Variables (.env)
```ini
# EWS Configuration
EWS_EMAIL=agent@company.com
EWS_PASSWORD=***
EWS_HOST=mail.company.com

# Agent Identity
AGENT_USER_NAME=Sales Agent
AGENT_EMAIL=salesagent@company.com

# LLM Configuration
OPENAI_API_KEY=***
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# Qdrant Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=***

# Service Settings
AUTOPILOT_SERVICE_INTERVAL=300
AUTOPILOT_SERVICE_HANDS_FREE=false
AUTOPILOT_SERVICE_LOG_LEVEL=INFO

ACTION_PLAN_SERVICE_INTERVAL=30
ACTION_PLAN_SERVICE_HANDS_FREE=false
ACTION_PLAN_SERVICE_LOG_LEVEL=INFO
```

---

## ReAct Execution Flow

### Phase 1: Thought Generation
```python
# LLM generates reasoning
Thought: "User wants to schedule follow-ups. I need to create an action plan."
```

### Phase 2: Action Selection
```python
# Agent selects appropriate tool
Action: create_action_plan
Input: {
    "plan_name": "Daily Follow-ups",
    "task_description": "Send follow-up emails",
    "frequency": "daily",
    "schedule_time": "09:00"
}
```

### Phase 3: Tool Execution
```python
# System executes selected tool
result = tool_registry["create_action_plan"].execute(input_params)
```

### Phase 4: Observation Processing
```python
# Agent receives execution result
Observation: "Action plan created successfully (ID: plan_abc123)"
```

### Phase 5: Answer or Continue
```python
# Agent decides: Answer user or continue loop
Answer: "I've scheduled daily follow-ups at 9 AM for you."
```

---

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Total Tools | 35 | Full tool ecosystem |
| Max Iterations | 50 | Per agent session |
| Autopilot Interval | 300s | Configurable |
| Action Plan Poll | 30s | Configurable |
| Concurrent Plans | Unlimited | No hard limit |
| Retry Attempts | 3 | Exponential backoff |
| Lock Timeout | 300s | Prevents deadlocks |
| Backup Retention | 10 | Automatic rotation |
| Service Restart | Auto | On failure |

---

## Security Features

1. **Credential Management**
   - Stored in .env (excluded from version control)
   - Runtime reload without service restart
   - No hardcoded secrets

2. **Execution Control**
   - File-based locking prevents concurrent runs
   - Draft mode for safe testing
   - Service enable/disable toggle

3. **Error Handling**
   - Automatic backup restoration
   - Retry logic with backoff
   - Comprehensive logging

4. **Isolation**
   - Separate service processes
   - Independent state files
   - No shared memory

---

## Key Differentiators

✅ **ReAct Agent Architecture** - Advanced reasoning capabilities  
✅ **35 Integrated Tools** - Comprehensive automation  
✅ **Action Plans as Tools** - Agent can schedule itself  
✅ **24/7 Service Operation** - Continuous background processing  
✅ **Dual Service Model** - Autopilot + Scheduled tasks  
✅ **Real-time Credential Reload** - No service restart needed  
✅ **Atomic State Management** - Data integrity guaranteed  
✅ **Cross-platform** - Windows & Linux support  
✅ **Production Ready** - Comprehensive testing suite  
✅ **Highly Configurable** - Environment-based settings  

---

## Use Cases

### 1. Autonomous Email Management
- Process customer inquiries 24/7
- Auto-respond to common questions
- Escalate complex issues
- Track conversation threads

### 2. Scheduled Workflows
- Daily sales reports
- Weekly follow-up reminders
- Monthly performance summaries
- Custom interval notifications

### 3. Interactive Assistance
- Real-time email composition
- Meeting scheduling
- Knowledge base queries
- Web search integration

---

## Monitoring & Logs

### Log Files
- `autopilot_service.log` - Main autopilot logs
- `autopilot_service_stderr.log` - Error logs
- `action_plan_service.log` - Action plan logs
- `action_plan_service_stderr.log` - Error logs

### Metrics to Monitor
- Service uptime
- Email processing rate
- Action plan execution success
- Error frequency
- Response latency

---

## Getting Started

1. **Install Dependencies**: `pip install -r requirements.txt`
2. **Configure .env**: Add credentials
3. **Test System**: `python test_services_comprehensive.py`
4. **Install Services**: Run install scripts
5. **Start Services**: Enable and start
6. **Monitor Logs**: Watch real-time execution

---

**For detailed deployment instructions, see**: `PRODUCTION_DEPLOYMENT_GUIDE.md`

**For architecture review, see**: `implementation_plan.md` | `walkthrough.md`
