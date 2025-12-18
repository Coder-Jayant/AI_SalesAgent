"""
Flask API Server for Sales Agent Web UI
Provides REST API and Server-Sent Events for the standalone HTML/CSS/JS frontend
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all necessary modules from main project
from react_agent import ReActAgent
from agent_tools import ALL_TOOLS
from autopilot import (
    get_autopilot_rules, set_autopilot_rules,
    get_autopilot_period_minutes, set_autopilot_period_minutes,
    autopilot_once, _load_state, _save_state,
    get_autopilot_service_enabled, set_autopilot_service_enabled
)
from rag_manager import (
    get_active_collection, set_active_collection
)
from rag_backend import (
    preprocess_documents, create_vector_store
)
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='.')
CORS(app)

# Initialize LLM (same as main_react.py)
llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "token-abc123"),
    base_url=os.getenv("OPENAI_BASE_URL", "http://49.50.117.66:8000/v1"),
    model=os.getenv("OPENAI_MODEL", "/model"),
    temperature=0.2,
    max_tokens=5000,
)

# Try to import Qdrant client
try:
    from qdrant_client import QdrantClient
    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )
except Exception as e:
    logger.warning(f"Qdrant client not available: {e}")
    qdrant_client = None

# Conversation history storage
conversation_history = []

# System prompts (from main_react.py)
user_name = os.getenv("AGENT_USER_NAME", "Sales Agent")
user_email = os.getenv("EWS_EMAIL", "")

CHATBOX_SYSTEM_PROMPT = f"""
You are {user_name}, an AI sales representative assistant with access to email, calendar, and knowledge base tools.

**YOUR IDENTITY:**
- Name: {user_name}
- Email: {user_email}

**EMAIL SIGNATURES:**
- End ALL email replies with:
  
  Best regards,
  {user_name}
  {user_email}

**IMPORTANT RULES:**
1) Query knowledge base when you need company info
2) Use web_search for external information
3) DRAFT emails by default unless hands-free mode is ON
4) Always keep professional tone
5) Be concise and helpful
"""

# ============= STATIC FILE SERVING =============
@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """Serve static files (CSS, JS, images)"""
    return send_from_directory('.', path)

# ============= CHAT ENDPOINTS =============
@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """Stream chat response using Server-Sent Events"""
    data = request.json
    user_message = data.get('message', '')
    hands_free = data.get('hands_free', False)
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    def generate():
        try:
            # Add user message to history
            conversation_history.append(HumanMessage(content=user_message))
            
            # Create policy message
            policy_msg = (
                f"[POLICY] HANDS_FREE={'ON' if hands_free else 'OFF'}; "
                "If ON, you may auto-send routine items. "
                "If OFF or content is sensitive, DRAFT first and ask via inform_user."
            )
            
            # Create ReAct agent
            react_agent = ReActAgent(
                llm=llm,
                tools=ALL_TOOLS,
                system_prompt=CHATBOX_SYSTEM_PROMPT + "\n" + policy_msg
            )
            
            # Stream steps
            react_steps = []
            for step in react_agent.run_streaming(
                user_message,
                max_iterations=50,
                conversation_history=conversation_history[:-1] if len(conversation_history) > 1 else None
            ):
                react_steps.append(step)
                
                # Send step as SSE
                step_data = {
                    "type": step.step_type,
                    "content": step.content,
                    "tool_name": step.tool_name if hasattr(step, 'tool_name') else None,
                    "tool_input": step.tool_input if hasattr(step, 'tool_input') else None
                }
                yield f"data: {json.dumps(step_data)}\n\n"
            
            # Build full response for history
            serialized_parts = []
            for step in react_steps:
                if step.step_type == "thought":
                    serialized_parts.append(f"💭 Thought: {step.content}")
                elif step.step_type == "action":
                    serialized_parts.append(f"⚙️ Action: {step.tool_name}")
                elif step.step_type == "observation":
                    serialized_parts.append(f"📊 Observation: {step.content}")
                elif step.step_type == "final_answer":
                    serialized_parts.append(f"✅ Final Answer: {step.content}")
            
            full_response = "\n\n".join(serialized_parts)
            conversation_history.append(AIMessage(content=full_response))
            
            # Send completion signal
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """Get conversation history"""
    history = []
    for msg in conversation_history:
        if isinstance(msg, HumanMessage):
            history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            history.append({"role": "assistant", "content": msg.content})
    return jsonify(history)

@app.route('/api/chat/clear', methods=['DELETE'])
def clear_chat():
    """Clear conversation history"""
    global conversation_history
    conversation_history = []
    return jsonify({"success": True})

# ============= KNOWLEDGE BASE ENDPOINTS =============
@app.route('/api/knowledge/collections', methods=['GET'])
def get_collections():
    """List all knowledge base collections"""
    try:
        if not qdrant_client:
            logger.warning("Qdrant client not available")
            return jsonify([])  # Return empty array instead of error
        
        collections = qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]
        return jsonify(collection_names)
    except Exception as e:
        logger.error(f"Error fetching collections: {e}")
        # Return empty array on error to prevent frontend crash
        return jsonify([])

@app.route('/api/knowledge/active', methods=['GET'])
def get_active():
    """Get active collection"""
    active = get_active_collection()
    return jsonify({"active": active})

@app.route('/api/knowledge/active', methods=['POST'])
def set_active():
    """Set active collection"""
    data = request.json
    collection_name = data.get('collection')
    set_active_collection(collection_name if collection_name != "None" else None)
    return jsonify({"success": True, "active": collection_name})

@app.route('/api/knowledge/upload', methods=['POST'])
def upload_documents():
    """Upload documents to knowledge base"""
    try:
        if 'files' not in request.files:
            return jsonify({"error": "No files provided"}), 400
        
        files = request.files.getlist('files')
        collection_name = request.form.get('collection_name', 'sales_knowledge_base')
        
        # Save files temporarily with correct extensions
        import tempfile
        temp_paths = []
        for file in files:
            # Get file extension
            filename = file.filename
            ext = filename.rsplit('.', 1)[1] if '.' in filename else 'txt'
            
            # Write as binary to support PDFs and other formats
            with tempfile.NamedTemporaryFile(mode='wb', suffix=f'.{ext}', delete=False) as tmp:
                tmp.write(file.read())
                temp_paths.append(tmp.name)
        
        # Process documents
        doc_splits = preprocess_documents(temp_paths)
        
        if doc_splits:
            # Create vector store
            retriever = create_vector_store(doc_splits, collection_name)
            set_active_collection(collection_name)
            
            # Cleanup
            for path in temp_paths:
                try:
                    os.remove(path)
                except:
                    pass
            
            return jsonify({
                "success": True,
                "collection": collection_name,
                "chunks": len(doc_splits)
            })
        else:
            return jsonify({"error": "Failed to process documents"}), 500
            
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/knowledge/query', methods=['POST'])
def query_knowledge():
    """Query knowledge base"""
    try:
        from agent_tools import query_knowledge_base
        
        data = request.json
        query = data.get('query', '')
        top_k = data.get('top_k', 3)
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        result = query_knowledge_base.invoke({"query": query, "top_k": top_k})
        result_data = json.loads(result)
        
        return jsonify(result_data)
    except Exception as e:
        logger.error(f"Query error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/knowledge/collection/<collection_name>', methods=['DELETE'])
def delete_collection(collection_name):
    """Delete a collection"""
    try:
        if not qdrant_client:
            return jsonify({"error": "Qdrant not available"}), 503
        
        qdrant_client.delete_collection(collection_name)
        
        # Clear active if deleted
        if collection_name == get_active_collection():
            set_active_collection(None)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============= AUTOPILOT RULES ENDPOINTS =============
@app.route('/api/autopilot/rules', methods=['GET'])
def get_rules():
    """Get all autopilot rules"""
    rules = get_autopilot_rules()
    return jsonify(rules)

@app.route('/api/autopilot/rules', methods=['PUT'])
def update_rules():
    """Update autopilot rules"""
    data = request.json
    rules = data.get('rules', [])
    set_autopilot_rules(rules)
    return jsonify({"success": True})

@app.route('/api/autopilot/rules', methods=['POST'])
def add_rule():
    """Add new autopilot rule"""
    data = request.json
    rules = get_autopilot_rules()
    
    new_rule = {
        "id": f"custom_{int(datetime.now(timezone.utc).timestamp())}",
        "name": data.get("name", ""),
        "enabled": data.get("enabled", True),
        "prompt": data.get("prompt", ""),
        "builtin": False,
        "priority": data.get("priority", 2)
    }
    
    rules.append(new_rule)
    set_autopilot_rules(rules)
    return jsonify({"success": True, "rule": new_rule})

@app.route('/api/autopilot/rules/<rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    """Delete autopilot rule"""
    rules = get_autopilot_rules()
    rules = [r for r in rules if r['id'] != rule_id]
    set_autopilot_rules(rules)
    return jsonify({"success": True})

@app.route('/api/autopilot/activity', methods=['GET'])
def get_activity():
    """Get autopilot activity logs"""
    state = _load_state()
    summaries = state.get("autopilot_summaries", [])[:20]
    return jsonify(summaries)

@app.route('/api/autopilot/service/status', methods=['GET'])
def service_status():
    """Get autopilot service status"""
    try:
        import subprocess
        result = subprocess.run(
            ["sc", "query", "AutopilotService"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            if "RUNNING" in result.stdout:
                status = "running"
            elif "STOPPED" in result.stdout:
                status = "stopped"
            else:
                status = "unknown"
        else:
            status = "not_installed"
        
        enabled = get_autopilot_service_enabled()
        period = get_autopilot_period_minutes()
        
        # Get last run time
        state = _load_state()
        last_run = state.get("service_last_run")
        
        return jsonify({
            "status": status,
            "enabled": enabled,
            "period_minutes": period,
            "last_run": last_run
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/autopilot/service/toggle', methods=['POST'])
def toggle_service():
    """Start or stop autopilot service"""
    data = request.json
    enable = data.get('enable', False)
    
    try:
        import subprocess
        set_autopilot_service_enabled(enable)
        
        if enable:
            result = subprocess.run(
                ["net", "start", "AutopilotService"],
                capture_output=True,
                text=True,
                timeout=10
            )
        else:
            result = subprocess.run(
                ["net", "stop", "AutopilotService"],
                capture_output=True,
                text=True,
                timeout=10
            )
        
        success = result.returncode == 0
        return jsonify({
            "success": success,
            "message": result.stdout if success else result.stderr
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/autopilot/run-manual', methods=['POST'])
def run_manual():
    """Manually trigger autopilot"""
    try:
        logs = autopilot_once()
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/autopilot/period', methods=['POST'])
def set_period():
    """Set autopilot check period"""
    data = request.json
    period = data.get('period', 5)
    set_autopilot_period_minutes(period)
    
    # Update .env file
    from pathlib import Path
    import re
    env_path = Path(".env")
    if env_path.exists():
        content = env_path.read_text()
        interval_seconds = period * 60
        new_content = re.sub(
            r'AUTOPILOT_SERVICE_INTERVAL=\d+',
            f'AUTOPILOT_SERVICE_INTERVAL={interval_seconds}',
            content
        )
        env_path.write_text(new_content)
    
    return jsonify({"success": True})

# ============= ACTION PLANS ENDPOINTS =============
# Import action plan functions
sys.path.insert(0, str(Path(__file__).parent.parent))
from main_react import (
    get_action_plans, set_action_plans,
    add_action_plan_execution, _load_action_plans_state
)

@app.route('/api/action-plans', methods=['GET'])
def get_plans():
    """Get all action plans"""
    plans = get_action_plans()
    return jsonify(plans)

@app.route('/api/action-plans', methods=['PUT'])
def update_plans():
    """Update action plans"""
    data = request.json
    plans = data.get('plans', [])
    set_action_plans(plans)
    return jsonify({"success": True})

@app.route('/api/action-plans', methods=['POST'])
def add_plan():
    """Add new action plan"""
    data = request.json
    plans = get_action_plans()
    
    new_plan = {
        "id": f"plan_{int(datetime.now(timezone.utc).timestamp())}",
        "name": data.get("name", ""),
        "task": data.get("task", ""),
        "enabled": data.get("enabled", True),
        "frequency": data.get("frequency", "every_sweep"),
        "last_executed": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    plans.append(new_plan)
    set_action_plans(plans)
    return jsonify({"success": True, "plan": new_plan})

@app.route('/api/action-plans/<plan_id>', methods=['DELETE'])
def delete_plan(plan_id):
    """Delete action plan"""
    plans = get_action_plans()
    plans = [p for p in plans if p['id'] != plan_id]
    set_action_plans(plans)
    return jsonify({"success": True})

@app.route('/api/action-plans/history', methods=['GET'])
def get_plan_history():
    """Get action plan execution history"""
    state = _load_action_plans_state()
    history = state.get("execution_history", [])[:20]
    return jsonify(history)

# ============= CONNECTION SETTINGS ENDPOINTS =============
@app.route('/api/connection/status', methods=['GET'])
def connection_status():
    """Get current connection info"""
    return jsonify({
        "email": os.getenv("EWS_EMAIL", ""),
        "host": os.getenv("EWS_HOST", ""),
        "has_password": bool(os.getenv("EWS_PASSWORD")),
        "agent_name": os.getenv("AGENT_USER_NAME", "")
    })

@app.route('/api/connection/test', methods=['POST'])
def test_connection():
    """Test EWS connection"""
    try:
        from ews_config import test_ews_connection
        
        data = request.json
        email = data.get('email', '')
        password = data.get('password', '')
        host = data.get('host', None)
        
        success, message = test_ews_connection(email, password, host)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/connection/save', methods=['POST'])
def save_connection():
    """Save EWS credentials"""
    try:
        from ews_config import save_ews_credentials
        from main_react import reload_credentials
        
        data = request.json
        email = data.get('email', '')
        password = data.get('password', '')
        host = data.get('host', '')
        agent_name = data.get('agent_name', '')
        
        success = save_ews_credentials(email, password, host, agent_name)
        
        if success:
            # Reload credentials
            reload_credentials()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/connection/fetch-test', methods=['POST'])
def fetch_test():
    """Quick email fetch test"""
    try:
        from ews_tools2 import get_unread_batch
        
        emails = get_unread_batch(batch_size=5)
        
        email_list = []
        for email in emails:
            email_list.append({
                "subject": email.get('subject', 'No Subject'),
                "from": email.get('from', 'Unknown')
            })
        
        return jsonify({"success": True, "emails": email_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============= START SERVER =============
if __name__ == '__main__':
    logger.info("Starting Sales Agent API Server...")
    logger.info("Access the UI at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
