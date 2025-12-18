# Sales Agent - Required Files

This folder contains all essential files for the Sales Agent project with ReAct agent and Autopilot integration.

## Core Application Files

### Main Entry Point
- **main_react.py** - Streamlit UI application with ReAct agent integration

### Agent Components  
- **react_agent.py** - ReAct (Reasoning + Acting) agent implementation
- **agent_tools.py** - All LangChain tool definitions (email, RAG, scheduling, etc.)
- **autopilot.py** - Autopilot logic with ReAct agent integration for autonomous email processing
- **action_handlers.py** - LLM decision generation and action execution handlers

### Email & EWS Integration
- **ews_tools2.py** - Exchange Web Services (EWS) integration functions
- **ews_config.py** - EWS configuration management
- **ews_accounts.json** - EWS account credentials (encrypted)

### RAG & Knowledge Base
- **rag_backend.py** - RAG (Retrieval Augmented Generation) backend with Qdrant
- **rag_manager.py** - RAG collection management
- **TAB2_KNOWLEDGE_BASE.py** - Knowledge base UI tab

### Configuration
- **.env** - Environment variables (API keys, URLs, etc.)
- **TAB6_CONNECTION_SETTINGS.py** - Connection settings UI tab
- **package.json** - Node.js dependencies (if any)

### State Files
- **autopilot_state.json** - Autopilot rules and state persistence
- **rag_state.json** - RAG active collection state
- **processed_mails.json** - Tracking of processed email IDs

## Key Features

### ReAct Agent Integration
- Multi-step reasoning with Thought → Action → Observation loops
- Real-time streaming of agent steps in UI
- Tool chaining capabilities (query KB → web search → reply)

### Autopilot Mode
- **NEW**: ReAct agent-based decision making (replaced single-action pattern)
- Multi-step intelligent email processing
- Business opportunity capture (prevents deflecting to competitors)
- Autonomous handling with proper escalation

### Recent Improvements
1. ✅ ReAct agent integrated into autopilot mode
2. ✅ Fixed duplicate reply issue with explicit tool parameter guidance
3. ✅ Added business handling rules to prevent recommending external solutions
4. ✅ Proper tool chaining for complex queries

## Setup Requirements

### Python Dependencies
- streamlit
- langchain
- langchain-openai
- langchain-community
- exchangelib
- qdrant-client
- openai
- ddgs (DuckDuckGo Search)

### External Services
- OpenAI-compatible LLM endpoint
- Qdrant vector database
- Exchange Web Services (EWS) server
- BGE-M3 embedding service

## Usage

```bash
# Run the Streamlit application
streamlit run main_react.py
```

## Important Notes

- All backup and corrupted files are excluded from this folder
- State JSON files contain runtime data and will be updated during execution
- .env file contains sensitive credentials - keep secure
- Autopilot now uses ReAct agent for intelligent multi-step processing
