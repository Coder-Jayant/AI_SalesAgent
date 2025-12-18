# 🤖 SalesAgent AI

**Intelligent Email Automation System with ReAct Architecture**

An enterprise-grade AI-powered sales agent that automates email processing, customer engagement, and sales workflows using advanced reasoning and action patterns.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![LangChain](https://img.shields.io/badge/LangChain-Enabled-green.svg)
![ReAct](https://img.shields.io/badge/ReAct-Architecture-purple.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🌟 Features

### Core Capabilities
- **🤖 Intelligent Email Processing** - AI-powered email triage, drafting, and automated responses
- **🔍 RAG-Powered Knowledge** - Query company knowledge base using vector search (Qdrant)
- **⚡ Autopilot Mode** - Rule-based automatic email processing with customizable triggers
- **📅 Action Plans** - Schedule periodic tasks with natural language and stopping conditions
- **🛠️ 35+ Specialized Tools** - Comprehensive tool ecosystem for email, calendar, and knowledge operations
- **🌐 Multi-Platform Deployment** - Windows (NSSM) and Linux (systemd) service support

### Email Management
- ✅ Send, reply, forward, and draft emails with intelligent content generation
- ✅ Maintain conversation threads with CC/BCC preservation
- ✅ Smart email search with dynamic filters
- ✅ Bulk operations and batch processing
- ✅ Unresponded email tracking and automatic follow-ups

### Automation & Intelligence
- ✅ Rule-based autopilot with priority-based execution
- ✅ Scheduled tasks with custom frequencies (hourly, daily, weekly, custom)
- ✅ Natural language stopping conditions
- ✅ Context-aware responses using company knowledge
- ✅ Web search integration for market insights
- ✅ HTML email formatting with professional templates

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│              Streamlit UI  │  Web API Server                 │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                   Core Agent Layer                           │
│    ReAct Agent Engine  │  LLM  │  Tool Registry (35+)       │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│              Automation Services                             │
│  Autopilot Service  │  Action Plans  │  Scheduler           │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│            Knowledge & Storage                               │
│     RAG (Qdrant)  │  Knowledge Base  │  State Management    │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│            External Integrations                             │
│    Exchange Web Services  │  Web Search  │  Calendar         │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Exchange Web Services (EWS) access
- OpenAI API key or local LLM endpoint
- Qdrant vector database (optional for RAG)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/coder-jayant/AI_SalesAgent.git
cd AI_SalesAgent
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials:
# - EWS_EMAIL, EWS_PASSWORD, EWS_HOST
# - OPENAI_API_KEY, OPENAI_BASE_URL
# - QDRANT_URL, QDRANT_KEY (optional)
```

5. **Run the application**
```bash
streamlit run main_react.py
```

## 📋 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `EWS_EMAIL` | Exchange email address | ✅ |
| `EWS_PASSWORD` | Exchange password | ✅ |
| `EWS_HOST` | Exchange server host | ✅ |
| `OPENAI_API_KEY` | OpenAI API key | ✅ |
| `OPENAI_BASE_URL` | LLM endpoint URL | ✅ |
| `OPENAI_MODEL` | Model path/name | ✅ |
| `QDRANT_URL` | Qdrant server URL | Optional |
| `QDRANT_KEY` | Qdrant API key | Optional |
| `AGENT_USER_NAME` | Agent display name | Optional |

## 🔧 Background Services

### Windows Deployment
```bash
# Install as Windows service using NSSM
install_service.bat
install_autopilot_service.bat

# Start services
net start ActionPlanService
net start AutopilotService
```

### Linux Deployment
```bash
# Copy service files
sudo cp *.service /etc/systemd/system/

# Update paths in service files
sudo nano /etc/systemd/system/action-plan-service.service
sudo nano /etc/systemd/system/autopilot-service.service

# Enable and start services
sudo systemctl enable action-plan-service
sudo systemctl enable autopilot-service
sudo systemctl start action-plan-service
sudo systemctl start autopilot-service

# Check status
sudo systemctl status action-plan-service
sudo systemctl status autopilot-service
```

## 📚 Documentation

- **[Technical Presentation](technical_presentation.html)** - Comprehensive system overview with diagrams
- **[Tool Ecosystem](docs/tools.md)** - Complete list of 35+ available tools
- **[Action Plans Guide](docs/action_plans.md)** - How to create and manage action plans
- **[Autopilot Rules](docs/autopilot.md)** - Configuring autopilot automation

## 🎯 Use Cases

### 1. Automated Customer Support
```python
# Autopilot rule example
create_autopilot_rule(
    name="Pricing Inquiries",
    prompt="If customer asks about pricing, query knowledge base and provide detailed pricing information",
    priority=1
)
```

### 2. Scheduled Follow-ups
```python
# Action plan example
create_action_plan(
    name="Demo Follow-up",
    task="Follow up on demo request email [item_id: 'AAMk...'] every 2 days",
    frequency="custom",
    custom_interval_minutes=2880,  # 2 days
    stopping_condition="Stop when customer responds or after 3 follow-ups"
)
```

### 3. Meeting Scheduling
```python
# Agent automatically:
# 1. Checks calendar availability
# 2. Proposes 3 time slots
# 3. Sends ICS invite
# 4. Updates calendar on confirmation
```

## 🛠️ Development

### Project Structure
```
AI_SalesAgent/
├── main_react.py              # Streamlit UI entry point
├── react_agent.py             # ReAct agent implementation
├── agent_tools.py             # Tool registry (35+ tools)
├── autopilot.py               # Autopilot system
├── action_plans/
│   ├── executor.py            # Action plan executor
│   ├── manager.py             # Plan management
│   └── scheduler.py           # Task scheduling
├── rag_backend.py             # RAG/Qdrant integration
├── ews_tools2.py              # Exchange Web Services tools
├── autopilot_service.py       # Autopilot background service
├── action_plan_service.py     # Action plan background service
└── technical_presentation.html # System documentation
```

### Running Tests
```bash
python test_services_comprehensive.py
```

### Adding Custom Tools
```python
from langchain.tools import tool

@tool
def my_custom_tool(param: str) -> str:
    """Tool description for LLM"""
    # Your logic here
    return result

# Register in agent_tools.py
ALL_TOOLS.append(my_custom_tool)
```

## 📊 Performance Metrics

- **Email Processing**: ~3-5 seconds per email
- **RAG Query Latency**: ~500ms
- **Throughput**: Handles 1000+ emails/day
- **Uptime**: 99.9% with automatic restart
- **Concurrent Execution**: Protected with locking mechanisms

## 🔒 Security

- ✅ Credentials stored in `.env` (gitignored)
- ✅ Runtime credential reload without restart
- ✅ Execution lock mechanisms to prevent concurrent runs
- ✅ Graceful shutdown handling (SIGTERM)
- ✅ Automatic retry logic with exponential backoff

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangChain** - AI agent framework
- **Qdrant** - Vector database for RAG
- **Streamlit** - Web UI framework
- **Exchange Web Services** - Email integration

## 📞 Contact

**Jayant Verma** - [@coder-jayant](https://github.com/coder-jayant)

Project Link: [https://github.com/coder-jayant/AI_SalesAgent](https://github.com/coder-jayant/AI_SalesAgent)

---

⭐ **Star this repository if you find it useful!** ⭐
