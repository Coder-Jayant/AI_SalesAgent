"""
web_ui.py
Modern Web UI for Sales Agent with ReAct Pattern
Single file Flask server serving HTML+JS+Bootstrap interface

Run: python web_ui.py
Access: http://localhost:5000
"""

from flask import Flask, render_template_string, request, jsonify, Response
from flask_cors import CORS
import json
import os
import logging
from datetime import datetime
from pathlib import Path
import tempfile

# Import all backend logic from main_react.py
from main_react import (
    llm, ALL_TOOLS, CHATBOX_SYSTEM_PROMPT,
    get_autopilot_rules, set_autopilot_rules,
    get_autopilot_period_minutes, set_autopilot_period_minutes,
    autopilot_once, get_action_plans, set_action_plans,
    add_action_plan_execution, _load_action_plans_state,
    get_active_collection, set_active_collection,
    reload_credentials, _load_state
)

from react_agent import ReActAgent
from agent_tools import query_knowledge_base
from rag_backend import preprocess_documents, create_vector_store, QDRANT_URL, QDRANT_KEY

try:
    from qdrant_client import QdrantClient
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY, prefer_grpc=False, timeout=60)
except:
    qdrant_client = None

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# In-memory conversation store (use Redis/DB for production)
conversations = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Sales Agent - ReAct Mode</title>
    
    <!-- Bootstrap 5.3 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #64748b;
            --success-color: #10b981;
            --danger-color: #ef4444;
            --dark-bg: #1e293b;
            --light-bg: #f8fafc;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .main-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            margin: 20px auto;
            max-width: 1400px;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px 30px;
            border-bottom: 3px solid rgba(255,255,255,0.2);
        }
        
        .header h1 {
            font-size: 1.8rem;
            font-weight: 700;
            margin: 0;
        }
        
        .chat-container {
            height: calc(100vh - 300px);
            overflow-y: auto;
            padding: 20px;
            background: var(--light-bg);
        }
        
        .message {
            margin-bottom: 20px;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            text-align: right;
        }
        
        .message-bubble {
            display: inline-block;
            max-width: 80%;
            padding: 15px 20px;
            border-radius: 18px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .message.user .message-bubble {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: left;
        }
        
        .message.assistant .message-bubble {
            background: white;
            border: 1px solid #e2e8f0;
            text-align: left;
        }
        
        .react-step {
            margin: 10px 0;
            padding: 12px;
            border-radius: 8px;
            font-size: 0.9rem;
        }
        
        .step-thought {
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
        }
        
        .step-action {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
        }
        
        .step-observation {
            background: #f0fdf4;
            border-left: 4px solid #10b981;
        }
        
        .step-final {
            background: #f0fdfa;
            border-left: 4px solid #14b8a6;
            font-weight: 500;
        }
        
        .step-error {
            background: #fef2f2;
            border-left: 4px solid #ef4444;
        }
        
        .collapse-toggle {
            cursor: pointer;
            user-select: none;
            transition: all 0.2s;
        }
        
        .collapse-toggle:hover {
            opacity: 0.8;
        }
        
        .input-group {
            padding: 20px;
            background: white;
            border-top: 1px solid #e2e8f0;
        }
        
        .btn-send {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            padding: 12px 30px;
            font-weight: 600;
        }
        
        .btn-send:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .sidebar {
            background: var(--dark-bg);
            color: white;
            min-height: 100%;
        }
        
        .nav-tabs {
            border-bottom: 2px solid #e2e8f0;
        }
        
        .nav-tabs .nav-link {
            color: var(--secondary-color);
            font-weight: 600;
            padding: 12px 20px;
            border: none;
            border-bottom: 3px solid transparent;
        }
        
        .nav-tabs .nav-link.active {
            color: var(--primary-color);
            background: none;
            border-bottom: 3px solid var(--primary-color);
        }
        
        .badge-status {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .settings-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid var(--primary-color);
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            display: inline-block;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .thinking-indicator {
            display: none;
            padding: 10px;
            background: #eff6ff;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        .thinking-indicator.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container-fluid p-0">
        <div class="main-container">
            <!-- Header -->
            <div class="header">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h1><i class="bi bi-robot"></i> AI Sales Agent</h1>
                        <small>Powered by ReAct (Reasoning + Acting) Pattern</small>
                    </div>
                    <div>
                        <button class="btn btn-light btn-sm" onclick="clearChat()">
                            <i class="bi bi-trash"></i> Clear Chat
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="row g-0">
                <!-- Sidebar -->
                <div class="col-md-3 sidebar p-3">
                    <h5 class="mb-3"><i class="bi bi-gear"></i> Settings</h5>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="handsFreeToggle">
                        <label class="form-check-label" for="handsFreeToggle">
                            🚀 Hands-free Mode
                        </label>
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="autopilotToggle">
                        <label class="form-check-label" for="autopilotToggle">
                            🤖 Autopilot
                        </label>
                    </div>
                    
                    <hr class="bg-light">
                    
                    <h6 class="mb-3">📚 Knowledge Base</h6>
                    <div id="kbStatus" class="mb-3">
                        <span class="badge bg-secondary">Loading...</span>
                    </div>
                    
                    <hr class="bg-light">
                    
                    <h6 class="mb-3">📊 Recent Activity</h6>
                    <div id="activityLog" style="max-height: 200px; overflow-y: auto; font-size: 0.85rem;">
                        <small class="text-muted">No activity yet</small>
                    </div>
                </div>
                
                <!-- Main Content -->
                <div class="col-md-9">
                    <!-- Tabs -->
                    <ul class="nav nav-tabs px-3 pt-3" role="tablist">
                        <li class="nav-item">
                            <a class="nav-link active" data-bs-toggle="tab" href="#chatTab">
                                💬 Chat
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#kbTab">
                                📚 Knowledge Base
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#rulesTab">
                                ⚙️ Rules
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" data-bs-toggle="tab" href="#settingsTab">
                                🔌 Connection
                            </a>
                        </li>
                    </ul>
                    
                    <!-- Tab Content -->
                    <div class="tab-content">
                        <!-- Chat Tab -->
                        <div class="tab-pane fade show active" id="chatTab">
                            <div class="chat-container" id="chatMessages"></div>
                            
                            <div class="thinking-indicator" id="thinkingIndicator">
                                <div class="spinner"></div>
                                <span class="ms-2">Agent is thinking...</span>
                            </div>
                            
                            <div class="input-group">
                                <input type="text" class="form-control" id="userInput" 
                                       placeholder="Ask me to check emails, draft replies, query knowledge base..."
                                       onkeypress="handleKeyPress(event)">
                                <button class="btn btn-send" onclick="sendMessage()">
                                    <i class="bi bi-send"></i> Send
                                </button>
                            </div>
                        </div>
                        
                        <!-- Knowledge Base Tab -->
                        <div class="tab-pane fade p-4" id="kbTab">
                            <h4>📚 Knowledge Base Management</h4>
                            <p class="text-muted">Upload company documents to power intelligent responses</p>
                            
                            <div class="settings-card">
                                <h5>Upload Documents</h5>
                                <div class="mb-3">
                                    <label class="form-label">Collection Name</label>
                                    <input type="text" class="form-control" id="collectionName" 
                                           value="sales_knowledge_base">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Upload Files (.txt, .md, .pdf)</label>
                                    <input type="file" class="form-control" id="kbFiles" multiple 
                                           accept=".txt,.md,.pdf">
                                </div>
                                <button class="btn btn-primary" onclick="uploadKnowledgeBase()">
                                    🚀 Build Knowledge Base
                                </button>
                            </div>
                            
                            <div class="settings-card">
                                <h5>Test Knowledge Base</h5>
                                <div class="mb-3">
                                    <input type="text" class="form-control" id="kbTestQuery" 
                                           placeholder="e.g., What are our cloud hosting prices?">
                                </div>
                                <button class="btn btn-secondary" onclick="testKnowledgeBase()">
                                    🔍 Search
                                </button>
                                <div id="kbTestResults" class="mt-3"></div>
                            </div>
                        </div>
                        
                        <!-- Rules Tab -->
                        <div class="tab-pane fade p-4" id="rulesTab">
                            <h4>⚙️ Autopilot Rules</h4>
                            <div id="rulesList"></div>
                            <button class="btn btn-success mt-3" onclick="showAddRuleModal()">
                                ➕ Add Rule
                            </button>
                        </div>
                        
                        <!-- Settings Tab -->
                        <div class="tab-pane fade p-4" id="settingsTab">
                            <h4>🔌 EWS Connection Settings</h4>
                            <div class="settings-card">
                                <div class="mb-3">
                                    <label class="form-label">Email Address</label>
                                    <input type="email" class="form-control" id="ewsEmail">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Password</label>
                                    <input type="password" class="form-control" id="ewsPassword">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Exchange Host (optional)</label>
                                    <input type="text" class="form-control" id="ewsHost">
                                </div>
                                <button class="btn btn-primary" onclick="testConnection()">
                                    🧪 Test & Save
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        let conversationHistory = [];
        let handsFreeMode = false;
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            loadKnowledgeBaseStatus();
            loadRules();
            
            document.getElementById('handsFreeToggle').addEventListener('change', function() {
                handsFreeMode = this.checked;
            });
        });
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessageToChat('user', message);
            input.value = '';
            
            // Show thinking indicator
            document.getElementById('thinkingIndicator').classList.add('active');
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        hands_free: handsFreeMode,
                        history: conversationHistory
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addReActResponse(data.steps);
                    conversationHistory.push(
                        { role: 'user', content: message },
                        { role: 'assistant', content: data.final_answer }
                    );
                } else {
                    addMessageToChat('assistant', '❌ Error: ' + data.error);
                }
            } catch (error) {
                addMessageToChat('assistant', '❌ Connection error: ' + error.message);
            } finally {
                document.getElementById('thinkingIndicator').classList.remove('active');
            }
        }
        
        function addMessageToChat(role, content) {
            const container = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const bubble = document.createElement('div');
            bubble.className = 'message-bubble';
            bubble.innerHTML = escapeHtml(content);
            
            messageDiv.appendChild(bubble);
            container.appendChild(messageDiv);
            container.scrollTop = container.scrollHeight;
        }
        
        function addReActResponse(steps) {
            const container = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';
            
            const bubble = document.createElement('div');
            bubble.className = 'message-bubble';
            
            let thoughtCount = 0;
            let actionCount = 0;
            
            steps.forEach(step => {
                const stepDiv = document.createElement('div');
                
                if (step.type === 'thought') {
                    thoughtCount++;
                    stepDiv.className = 'react-step step-thought';
                    stepDiv.innerHTML = `💭 <strong>Thought ${thoughtCount}:</strong> ${escapeHtml(step.content)}`;
                } else if (step.type === 'action') {
                    actionCount++;
                    stepDiv.className = 'react-step step-action';
                    const actionId = `action-${Date.now()}-${actionCount}`;
                    stepDiv.innerHTML = `
                        <div class="collapse-toggle" data-bs-toggle="collapse" data-bs-target="#${actionId}">
                            ⚙️ <strong>Action ${actionCount}:</strong> <code>${escapeHtml(step.tool_name)}</code>
                            <i class="bi bi-chevron-down float-end"></i>
                        </div>
                        <div class="collapse mt-2" id="${actionId}">
                            <pre class="mb-0">${escapeHtml(JSON.stringify(step.tool_input, null, 2))}</pre>
                        </div>
                    `;
                } else if (step.type === 'observation') {
                    const obsId = `obs-${Date.now()}-${actionCount}`;
                    const preview = step.content.substring(0, 100);
                    stepDiv.className = 'react-step step-observation';
                    stepDiv.innerHTML = `
                        <div class="collapse-toggle" data-bs-toggle="collapse" data-bs-target="#${obsId}">
                            📊 <strong>Observation ${actionCount}:</strong> ${escapeHtml(preview)}...
                            <i class="bi bi-chevron-down float-end"></i>
                        </div>
                        <div class="collapse mt-2" id="${obsId}">
                            <textarea class="form-control" rows="8" readonly>${escapeHtml(step.content)}</textarea>
                        </div>
                    `;
                } else if (step.type === 'final_answer') {
                    stepDiv.className = 'react-step step-final';
                    stepDiv.innerHTML = `✅ <strong>Final Answer:</strong><br>${escapeHtml(step.content)}`;
                } else if (step.type === 'error') {
                    stepDiv.className = 'react-step step-error';
                    stepDiv.innerHTML = `❌ <strong>Error:</strong> ${escapeHtml(step.content)}`;
                }
                
                bubble.appendChild(stepDiv);
            });
            
            messageDiv.appendChild(bubble);
            container.appendChild(messageDiv);
            container.scrollTop = container.scrollHeight;
        }
        
        function clearChat() {
            if (confirm('Clear all chat messages?')) {
                document.getElementById('chatMessages').innerHTML = '';
                conversationHistory = [];
            }
        }
        
        async function loadKnowledgeBaseStatus() {
            try {
                const response = await fetch('/api/kb/status');
                const data = await response.json();
                
                const statusDiv = document.getElementById('kbStatus');
                if (data.active_collection) {
                    statusDiv.innerHTML = `<span class="badge bg-success">🟢 ${data.active_collection}</span>`;
                } else {
                    statusDiv.innerHTML = `<span class="badge bg-secondary">No active collection</span>`;
                }
            } catch (error) {
                console.error('Failed to load KB status:', error);
            }
        }
        
        async function uploadKnowledgeBase() {
            const files = document.getElementById('kbFiles').files;
            const collectionName = document.getElementById('collectionName').value;
            
            if (files.length === 0) {
                alert('Please select files to upload');
                return;
            }
            
            const formData = new FormData();
            formData.append('collection_name', collectionName);
            for (let file of files) {
                formData.append('files', file);
            }
            
            try {
                const response = await fetch('/api/kb/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert(`✅ Knowledge base "${collectionName}" created with ${data.chunks} chunks!`);
                    loadKnowledgeBaseStatus();
                } else {
                    alert('❌ Error: ' + data.error);
                }
            } catch (error) {
                alert('❌ Upload failed: ' + error.message);
            }
        }
        
        async function testKnowledgeBase() {
            const query = document.getElementById('kbTestQuery').value;
            const resultsDiv = document.getElementById('kbTestResults');
            
            if (!query) {
                alert('Please enter a query');
                return;
            }
            
            try {
                const response = await fetch('/api/kb/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, top_k: 3 })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    let html = '<h6>Results:</h6>';
                    data.hits.forEach((hit, i) => {
                        html += `
                            <div class="alert alert-info">
                                <strong>Result #${i+1} - Score: ${hit.score.toFixed(3)}</strong>
                                <p class="mb-0">${escapeHtml(hit.content.substring(0, 300))}...</p>
                            </div>
                        `;
                    });
                    resultsDiv.innerHTML = html;
                } else {
                    resultsDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                }
            } catch (error) {
                resultsDiv.innerHTML = `<div class="alert alert-danger">Query failed: ${error.message}</div>`;
            }
        }
        
        async function loadRules() {
            try {
                const response = await fetch('/api/rules');
                const data = await response.json();
                
                const rulesList = document.getElementById('rulesList');
                rulesList.innerHTML = '';
                
                data.rules.forEach(rule => {
                    const ruleCard = document.createElement('div');
                    ruleCard.className = 'settings-card';
                    ruleCard.innerHTML = `
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6>${rule.enabled ? '🟢' : '⚪'} ${escapeHtml(rule.name)}</h6>
                                <p class="text-muted">${escapeHtml(rule.prompt)}</p>
                            </div>
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" ${rule.enabled ? 'checked' : ''} 
                                       onchange="toggleRule('${rule.id}', this.checked)">
                            </div>
                        </div>
                    `;
                    rulesList.appendChild(ruleCard);
                });
            } catch (error) {
                console.error('Failed to load rules:', error);
            }
        }
        
        async function toggleRule(ruleId, enabled) {
            try {
                await fetch('/api/rules/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rule_id: ruleId, enabled: enabled })
                });
            } catch (error) {
                console.error('Failed to toggle rule:', error);
            }
        }
        
        async function testConnection() {
            const email = document.getElementById('ewsEmail').value;
            const password = document.getElementById('ewsPassword').value;
            const host = document.getElementById('ewsHost').value;
            
            if (!email || !password) {
                alert('Please enter email and password');
                return;
            }
            
            try {
                const response = await fetch('/api/ews/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password, host })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert('✅ ' + data.message);
                } else {
                    alert('❌ ' + data.message);
                }
            } catch (error) {
                alert('❌ Connection test failed: ' + error.message);
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""

# ============= API ENDPOINTS =============

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages with ReAct streaming"""
    try:
        data = request.json
        user_message = data.get('message', '')
        hands_free = data.get('hands_free', False)
        history = data.get('history', [])
        
        if not user_message:
            return jsonify({'success': False, 'error': 'No message provided'})
        
        # Build system prompt with policy
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
        
        # Convert history to conversation format
        conversation_history = None
        if history:
            from langchain_core.messages import HumanMessage, AIMessage
            conversation_history = []
            for msg in history[:-1]:  # Exclude current message
                if msg['role'] == 'user':
                    conversation_history.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    conversation_history.append(AIMessage(content=msg['content']))
        
        # Execute ReAct agent
        steps = []
        for step in react_agent.run_streaming(user_message, max_iterations=50, conversation_history=conversation_history):
            steps.append({
                'type': step.step_type,
                'content': step.content,
                'tool_name': step.tool_name if hasattr(step, 'tool_name') else None,
                'tool_input': step.tool_input if hasattr(step, 'tool_input') else None
            })
        
        # Extract final answer
        final_answer = next(
            (s['content'] for s in reversed(steps) if s['type'] == 'final_answer'),
            "Task completed"
        )
        
        return jsonify({
            'success': True,
            'steps': steps,
            'final_answer': final_answer
        })
        
    except Exception as e:
        logging.error(f"Chat error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/kb/status', methods=['GET'])
def kb_status():
    """Get active knowledge base collection"""
    try:
        active = get_active_collection()
        collections = []
        
        if qdrant_client:
            try:
                cols = qdrant_client.get_collections()
                collections = [col.name for col in cols.collections]
            except:
                pass
        
        return jsonify({
            'success': True,
            'active_collection': active,
            'available_collections': collections
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/kb/upload', methods=['POST'])
def kb_upload():
    """Upload and process knowledge base documents"""
    try:
        collection_name = request.form.get('collection_name', 'sales_knowledge_base')
        files = request.files.getlist('files')
        
        if not files:
            return jsonify({'success': False, 'error': 'No files provided'})
        
        # Save files temporarily
        temp_paths = []
        for file in files:
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            content = file.read().decode('utf-8')
            temp_file.write(content)
            temp_file.close()
            temp_paths.append(temp_file.name)
        
        # Process documents
        doc_splits = preprocess_documents(temp_paths)
        
        if not doc_splits:
            return jsonify({'success': False, 'error': 'Failed to process documents'})
        
        # Create vector store
        retriever = create_vector_store(doc_splits, collection_name)
        
        # Set as active collection
        set_active_collection(collection_name)
        
        # Cleanup temp files
        for path in temp_paths:
            try:
                os.remove(path)
            except:
                pass
        
        return jsonify({
            'success': True,
            'collection_name': collection_name,
            'chunks': len(doc_splits)
        })
        
    except Exception as e:
        logging.error(f"KB upload error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/kb/query', methods=['POST'])
def kb_query():
    """Query knowledge base"""
    try:
        data = request.json
        query = data.get('query', '')
        top_k = data.get('top_k', 3)
        
        if not query:
            return jsonify({'success': False, 'error': 'No query provided'})
        
        result = query_knowledge_base.invoke({
            'query': query,
            'top_k': top_k
        })
        
        result_data = json.loads(result)
        
        if 'error' in result_data:
            return jsonify({'success': False, 'error': result_data['error']})
        
        return jsonify({
            'success': True,
            'hits': result_data.get('hits', [])
        })
        
    except Exception as e:
        logging.error(f"KB query error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/rules', methods=['GET'])
def get_rules():
    """Get all autopilot rules"""
    try:
        rules = get_autopilot_rules()
        return jsonify({
            'success': True,
            'rules': rules
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/rules/toggle', methods=['POST'])
def toggle_rule():
    """Toggle rule enabled state"""
    try:
        data = request.json
        rule_id = data.get('rule_id')
        enabled = data.get('enabled', True)
        
        rules = get_autopilot_rules()
        
        for rule in rules:
            if rule.get('id') == rule_id:
                rule['enabled'] = enabled
                break
        
        set_autopilot_rules(rules)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/rules/add', methods=['POST'])
def add_rule():
    """Add new autopilot rule"""
    try:
        data = request.json
        name = data.get('name', '')
        prompt = data.get('prompt', '')
        enabled = data.get('enabled', True)
        
        if not name or not prompt:
            return jsonify({'success': False, 'error': 'Name and prompt required'})
        
        rules = get_autopilot_rules()
        
        new_rule = {
            'id': f"custom_{int(datetime.now().timestamp())}",
            'name': name,
            'enabled': enabled,
            'prompt': prompt,
            'builtin': False
        }
        
        rules.append(new_rule)
        set_autopilot_rules(rules)
        
        return jsonify({'success': True, 'rule': new_rule})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ews/test', methods=['POST'])
def test_ews():
    """Test EWS connection"""
    try:
        data = request.json
        email = data.get('email', '')
        password = data.get('password', '')
        host = data.get('host', '')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'})
        
        # Import EWS config helper
        try:
            from ews_config import save_ews_credentials, test_ews_connection
            
            # Test connection
            success, message = test_ews_connection(email, password, host or None)
            
            if success:
                # Save credentials
                save_ews_credentials(email, password, host)
                reload_credentials()
                
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'message': message})
                
        except ImportError:
            return jsonify({'success': False, 'message': 'ews_config module not available'})
        
    except Exception as e:
        logging.error(f"EWS test error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/action_plans', methods=['GET'])
def get_plans():
    """Get all action plans"""
    try:
        plans = get_action_plans()
        return jsonify({
            'success': True,
            'plans': plans
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/action_plans/add', methods=['POST'])
def add_plan():
    """Add new action plan"""
    try:
        data = request.json
        name = data.get('name', '')
        task = data.get('task', '')
        frequency = data.get('frequency', 'every_sweep')
        enabled = data.get('enabled', True)
        
        if not name or not task:
            return jsonify({'success': False, 'error': 'Name and task required'})
        
        plans = get_action_plans()
        
        new_plan = {
            'id': f"plan_{int(datetime.now().timestamp())}",
            'name': name,
            'task': task,
            'enabled': enabled,
            'frequency': frequency,
            'last_executed': None,
            'created_at': datetime.now().isoformat()
        }
        
        plans.append(new_plan)
        set_action_plans(plans)
        
        return jsonify({'success': True, 'plan': new_plan})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/autopilot/run', methods=['POST'])
def run_autopilot():
    """Manually trigger autopilot"""
    try:
        data = request.json
        hands_free = data.get('hands_free', False)
        
        logs = autopilot_once(hands_free=hands_free)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
        
    except Exception as e:
        logging.error(f"Autopilot error: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AI Sales Agent Web UI Starting...")
    print("=" * 60)
    print("📍 Access the application at: http://localhost:5000")
    print("🔧 Make sure main_react.py and all dependencies are available")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)