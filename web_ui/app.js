// ==========================================
// SALES AGENT WEB UI - JAVASCRIPT
// Main application logic and API integration
// ==========================================

// ========== CONFIGURATION ==========
const API_BASE_URL = 'http://localhost:5000';

// ========== STATE MANAGEMENT ==========
const state = {
    handsFree: false,
    activeTab: 'chatbox',
    chatHistory: [],
    collections: [],
    activeCollection: null,
    autopilotRules: [],
    actionPlans: [],
    autopilotLogs: [],
    serviceStatus: null
};

// ========== UTILITY FUNCTIONS ==========
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function showLoading(show = true, text = 'Processing...') {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = overlay.querySelector('.loading-text');
    loadingText.textContent = text;

    if (show) {
        overlay.classList.remove('hidden');
    } else {
        overlay.classList.add('hidden');
    }
}

function formatTimestamp(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString();
}

// ========== API CLIENT ==========
const api = {
    async get(endpoint) {
        const response = await fetch(`${API_BASE_URL}${endpoint}`);
        if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
        return response.json();
    },

    async post(endpoint, data) {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
        return response.json();
    },

    async put(endpoint, data) {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
        return response.json();
    },

    async delete(endpoint) {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
        return response.json();
    }
};

// ========== TAB MANAGEMENT ==========
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;

            // Update active tab
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Show corresponding pane
            tabPanes.forEach(pane => pane.classList.remove('active'));
            document.getElementById(`${tabName}-tab`).classList.add('active');

            state.activeTab = tabName;

            // Load data for specific tabs
            if (tabName === 'knowledge') loadKnowledgeBase();
            if (tabName === 'rules') loadAutopilotRules();
            if (tabName === 'activity') loadAutopilotActivity();
            if (tabName === 'plans') loadActionPlans();
            if (tabName === 'connection') loadConnectionInfo();
        });
    });
}

// ========== CHAT FUNCTIONALITY ==========
function initChat() {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');

    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
    });

    // Send on Enter (Shift+Enter for new line)
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);
}

async function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();

    if (!message) return;

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Add user message to UI
    addChatMessage(message, 'user');

    // Create assistant message placeholder
    const assistantBubble = addChatMessage('', 'assistant', true);

    try {
        // Stream response from API
        const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                hands_free: state.handsFree
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let thoughts = [];
        let actions = [];
        let observations = [];
        let finalAnswer = '';
        let actionCounter = 0;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));

                    if (data.type === 'thought') {
                        thoughts.push(data.content);
                        updateAssistantMessage(assistantBubble, { thoughts, actions, observations, finalAnswer });
                    } else if (data.type === 'action') {
                        actionCounter++;
                        actions.push({
                            name: data.tool_name,
                            input: data.tool_input,
                            counter: actionCounter
                        });
                        updateAssistantMessage(assistantBubble, { thoughts, actions, observations, finalAnswer });
                    } else if (data.type === 'observation') {
                        observations.push({
                            content: data.content,
                            counter: actionCounter
                        });
                        updateAssistantMessage(assistantBubble, { thoughts, actions, observations, finalAnswer });
                    } else if (data.type === 'final_answer') {
                        finalAnswer = data.content;
                        updateAssistantMessage(assistantBubble, { thoughts, actions, observations, finalAnswer });
                    } else if (data.type === 'error') {
                        assistantBubble.innerHTML += `<div class="error-message">❌ Error: ${data.content}</div>`;
                    }
                }
            }
        }

        // Scroll to bottom
        scrollChatToBottom();

    } catch (error) {
        assistantBubble.innerHTML = `<div class="error-message">❌ Error: ${error.message}</div>`;
    }
}

function addChatMessage(content, role = 'user', isPlaceholder = false) {
    const messagesContainer = document.getElementById('chatMessages');

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';

    if (isPlaceholder) {
        bubble.innerHTML = '<div class="typing-indicator">●●●</div>';
    } else {
        bubble.textContent = content;
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(bubble);
    messagesContainer.appendChild(messageDiv);

    scrollChatToBottom();

    return bubble;
}

function updateAssistantMessage(bubble, data) {
    let html = '';

    // Thoughts
    data.thoughts.forEach((thought, i) => {
        html += `<div class="react-thought">💭 <strong>Thought ${i + 1}:</strong> ${escapeHtml(thought)}</div>`;
    });

    // Actions with expandable observations
    data.actions.forEach((action, i) => {
        const obs = data.observations.find(o => o.counter === action.counter);
        const isExpanded = i === data.actions.length - 1; // Expand latest

        html += `
            <div class="expander ${isExpanded ? 'expanded' : ''}" data-idx="${i}">
                <div class="expander-header" onclick="toggleExpander(${i})">
                    <span>⚙️ <strong>Action ${action.counter}:</strong> <code>${escapeHtml(action.name)}</code></span>
                    <span>${isExpanded ? '▼' : '▶'}</span>
                </div>
                <div class="expander-content">
                    <p><strong>Input:</strong></p>
                    <pre class="code-block">${JSON.stringify(action.input, null, 2).substring(0, 500)}</pre>
                    ${obs ? `
                        <p><strong>📊 Observation:</strong></p>
                        <pre class="code-block">${escapeHtml(obs.content.substring(0, 800))}</pre>
                    ` : ''}
                </div>
            </div>
        `;
    });

    // Final answer
    if (data.finalAnswer) {
        html += `<div class="success-message">✅ <strong>Final Answer:</strong><br>${escapeHtml(data.finalAnswer)}</div>`;
    }

    bubble.innerHTML = html;
}

function toggleExpander(idx) {
    const expander = document.querySelector(`.expander[data-idx="${idx}"]`);
    expander.classList.toggle('expanded');

    const arrow = expander.querySelector('.expander-header span:last-child');
    arrow.textContent = expander.classList.contains('expanded') ? '▼' : '▶';
}

function scrollChatToBottom() {
    const container = document.getElementById('chatMessages');
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== KNOWLEDGE BASE ==========
async function loadKnowledgeBase() {
    try {
        // Load collections
        const collections = await api.get('/api/knowledge/collections');
        state.collections = collections;

        const select = document.getElementById('activeCollectionSelect');
        select.innerHTML = '<option value="None">None</option>';
        collections.forEach(col => {
            const option = document.createElement('option');
            option.value = col;
            option.textContent = col;
            select.appendChild(option);
        });

        // Load active collection
        const { active } = await api.get('/api/knowledge/active');
        state.activeCollection = active;

        if (active) {
            select.value = active;
            showKBTestForm(true, active);
        } else {
            showKBTestForm(false);
        }

        // Update collections list
        updateCollectionsList();

    } catch (error) {
        showToast(`Error loading knowledge base: ${error.message}`, 'error');
    }
}

function showKBTestForm(show, collectionName = '') {
    const noActive = document.getElementById('kbNoActive');
    const testForm = document.getElementById('kbTestForm');
    const activeInfo = document.getElementById('kbActiveInfo');

    if (show) {
        noActive.classList.add('hidden');
        testForm.classList.remove('hidden');
        activeInfo.textContent = `📚 Querying: ${collectionName}`;
    } else {
        noActive.classList.remove('hidden');
        testForm.classList.add('hidden');
    }
}

function updateCollectionsList() {
    const container = document.getElementById('collectionsList');

    if (state.collections.length === 0) {
        container.innerHTML = '<p class="no-collections">No collections yet. Upload documents to create one.</p>';
        return;
    }

    container.innerHTML = '';
    state.collections.forEach(col => {
        const isActive = col === state.activeCollection;
        const item = document.createElement('div');
        item.className = 'collection-item';
        item.innerHTML = `
            <div class="collection-info">
                <span>${isActive ? '🟢 ACTIVE' : '⚪'}</span>
                <strong>${col}</strong>
            </div>
            <div class="collection-actions">
                <button class="btn btn-sm btn-secondary" onclick="deleteCollection('${col}')">🗑️ Delete</button>
            </div>
        `;
        container.appendChild(item);
    });
}

async function deleteCollection(name) {
    if (!confirm(`Delete collection "${name}"?`)) return;

    try {
        await api.delete(`/api/knowledge/collection/${name}`);
        showToast('Collection deleted successfully', 'success');
        loadKnowledgeBase();
    } catch (error) {
        showToast(`Error deleting collection: ${error.message}`, 'error');
    }
}

function initKnowledgeBase() {
    // File upload zone
    const uploadZone = document.getElementById('fileUploadZone');
    const fileInput = document.getElementById('fileInput');
    const fileList = document.getElementById('fileList');

    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--accent-purple)';
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.style.borderColor = 'var(--border-glass)';
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--border-glass)';
        fileInput.files = e.dataTransfer.files;
        updateFileList();
    });

    fileInput.addEventListener('change', updateFileList);

    function updateFileList() {
        const files = Array.from(fileInput.files);
        if (files.length === 0) {
            fileList.classList.add('hidden');
            return;
        }

        fileList.classList.remove('hidden');
        fileList.innerHTML = `<p><strong>Selected files (${files.length}):</strong></p>`;
        files.forEach(f => {
            fileList.innerHTML += `<p style="font-size: 0.875rem; color: var(--text-secondary);">• ${f.name} (${(f.size / 1024).toFixed(1)} KB)</p>`;
        });
    }

    // Build KB button
    document.getElementById('buildKBBtn').addEventListener('click', async () => {
        const files = fileInput.files;
        if (files.length === 0) {
            showToast('Please select files to upload', 'warning');
            return;
        }

        const collectionName = document.getElementById('collectionName').value.trim();
        if (!collectionName) {
            showToast('Please enter a collection name', 'warning');
            return;
        }

        const formData = new FormData();
        for (const file of files) {
            formData.append('files', file);
        }
        formData.append('collection_name', collectionName);

        showLoading(true, 'Building knowledge base...');

        try {
            const response = await fetch(`${API_BASE_URL}/api/knowledge/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Upload failed');

            const result = await response.json();
            showToast(`Knowledge base built with ${result.chunks} chunks!`, 'success');

            // Reset form
            fileInput.value = '';
            updateFileList();

            // Reload collections
            loadKnowledgeBase();

        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            showLoading(false);
        }
    });

    // Set active button
    document.getElementById('setActiveBtn').addEventListener('click', async () => {
        const selected = document.getElementById('activeCollectionSelect').value;

        try {
            await api.post('/api/knowledge/active', { collection: selected });
            showToast(`Active collection set: ${selected}`, 'success');
            loadKnowledgeBase();
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    });

    // Refresh button
    document.getElementById('refreshCollectionsBtn').addEventListener('click', () => {
        loadKnowledgeBase();
    });

    // Test query slider
    const testK = document.getElementById('testK');
    const testKValue = document.getElementById('testKValue');
    testK.addEventListener('input', () => {
        testKValue.textContent = testK.value;
    });

    // Search button
    document.getElementById('searchKBBtn').addEventListener('click', async () => {
        const query = document.getElementById('testQuery').value.trim();
        if (!query) {
            showToast('Please enter a query', 'warning');
            return;
        }

        const topK = parseInt(document.getElementById('testK').value);

        showLoading(true, 'Searching...');

        try {
            const result = await api.post('/api/knowledge/query', { query, top_k: topK });

            const resultsContainer = document.getElementById('searchResults');
            resultsContainer.classList.remove('hidden');

            if (result.error) {
                resultsContainer.innerHTML = `<div class="error-message">❌ ${result.error}</div>`;
            } else {
                const hits = result.hits || [];
                resultsContainer.innerHTML = `<p><strong>✅ Found ${hits.length} results</strong></p>`;

                hits.forEach((hit, i) => {
                    resultsContainer.innerHTML += `
                        <div class="expander expanded" style="margin: 1rem 0;">
                            <div class="expander-header">
                                <span><strong>Result #${i + 1}</strong> - Score: ${hit.score.toFixed(3)}</span>
                            </div>
                            <div class="expander-content">
                                <pre class="code-block">${escapeHtml(hit.content.substring(0, 500))}</pre>
                                ${hit.metadata ? `<p style="margin-top: 0.5rem;"><strong>Metadata:</strong> <code>${JSON.stringify(hit.metadata)}</code></p>` : ''}
                            </div>
                        </div>
                    `;
                });
            }
        } catch (error) {
            showToast(`Search failed: ${error.message}`, 'error');
        } finally {
            showLoading(false);
        }
    });
}

// ========== AUTOPILOT RULES ==========
async function loadAutopilotRules() {
    try {
        const rules = await api.get('/api/autopilot/rules');
        state.autopilotRules = rules.sort((a, b) => (a.priority || 999) - (b.priority || 999));

        const container = document.getElementById('rulesList');
        container.innerHTML = '';

        state.autopilotRules.forEach((rule, idx) => {
            const ruleDiv = document.createElement('div');
            ruleDiv.className = 'rule-item';
            ruleDiv.style.cssText = 'background: var(--bg-glass); border: 1px solid var(--border-glass); border-radius: var(--border-radius); padding: 1rem; margin-bottom: 1rem;';

            ruleDiv.innerHTML = `
                <div style="display: flex; gap: 1rem; align-items: flex-start;">
                    <label class="toggle-label">
                        <input type="checkbox" class="toggle-input" ${rule.enabled ? 'checked' : ''} onchange="toggleRule(${idx})">
                    </label>
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-secondary);">${rule.enabled ? '🟢' : '⚪'}</span>
                            <span style="padding: 0.25rem 0.5rem; background: var(--bg-glass-hover); border-radius: 4px; font-size: 0.75rem; font-weight: 600;">#${rule.priority}</span>
                            <strong>${escapeHtml(rule.name)}</strong>
                            ${rule.builtin ? '<span style="font-size: 0.75rem; color: var(--text-tertiary);">(Built-in)</span>' : ''}
                        </div>
                        <p style="font-size: 0.875rem; color: var(--text-secondary);">${escapeHtml(rule.prompt)}</p>
                    </div>
                    <select class="select-field" style="width: 120px;" onchange="updateRulePriority(${idx}, this.value)">
                        <option value="1" ${rule.priority === 1 ? 'selected' : ''}>1-Critical</option>
                        <option value="2" ${rule.priority === 2 ? 'selected' : ''}>2-Medium</option>
                        <option value="3" ${rule.priority === 3 ? 'selected' : ''}>3-Low</option>
                    </select>
                    ${!rule.builtin ? `<button class="btn btn-sm btn-danger" onclick="deleteRule(${idx})">🗑️</button>` : ''}
                </div>
            `;

            container.appendChild(ruleDiv);
        });

    } catch (error) {
        showToast(`Error loading rules: ${error.message}`, 'error');
    }
}

function toggleRule(idx) {
    state.autopilotRules[idx].enabled = !state.autopilotRules[idx].enabled;
}

function updateRulePriority(idx, priority) {
    state.autopilotRules[idx].priority = parseInt(priority);
}

async function deleteRule(idx) {
    const rule = state.autopilotRules[idx];
    if (!confirm(`Delete rule "${rule.name}"?`)) return;

    try {
        await api.delete(`/api/autopilot/rules/${rule.id}`);
        showToast('Rule deleted successfully', 'success');
        loadAutopilotRules();
    } catch (error) {
        showToast(`Error deleting rule: ${error.message}`, 'error');
    }
}

function initAutopilotRules() {
    // Save rules button
    document.getElementById('saveRulesBtn').addEventListener('click', async () => {
        try {
            await api.put('/api/autopilot/rules', { rules: state.autopilotRules });
            showToast('Rules saved successfully!', 'success');
        } catch (error) {
            showToast(`Error saving rules: ${error.message}`, 'error');
        }
    });

    // Add rule button
    document.getElementById('addRuleBtn').addEventListener('click', async () => {
        const name = document.getElementById('newRuleName').value.trim();
        const prompt = document.getElementById('newRulePrompt').value.trim();
        const enabled = document.getElementById('newRuleEnabled').checked;
        const priority = parseInt(document.getElementById('newRulePriority').value) || 3;

        if (!name || !prompt) {
            showToast('Please provide both name and instruction', 'warning');
            return;
        }

        try {
            await api.post('/api/autopilot/rules', { name, prompt, enabled, priority });
            showToast('Rule added successfully!', 'success');

            // Clear form
            document.getElementById('newRuleName').value = '';
            document.getElementById('newRulePrompt').value = '';
            document.getElementById('newRuleEnabled').checked = true;
            document.getElementById('newRulePriority').value = '3';  // Reset to default

            loadAutopilotRules();
        } catch (error) {
            showToast(`Error adding rule: ${error.message}`, 'error');
        }
    });
}

// ========== AUTOPILOT ACTIVITY ==========
async function loadAutopilotActivity() {
    try {
        const summaries = await api.get('/api/autopilot/activity');

        const container = document.getElementById('activitySummaries');
        container.innerHTML = '';

        if (summaries.length === 0) {
            container.innerHTML = '<p class="info-message">No autopilot actions recorded yet</p>';
            return;
        }

        summaries.forEach(summary => {
            const item = document.createElement('div');
            item.className = 'expander';
            item.innerHTML = `
                <div class="expander-header" onclick="this.parentElement.classList.toggle('expanded')">
                    <span>⏰ ${summary.time || ''} — ${escapeHtml(summary.subject || '')}</span>
                    <span>▶</span>
                </div>
                <div class="expander-content">
                    <p><strong>From:</strong> ${escapeHtml(summary.from || '')}</p>
                    <p><strong>Action:</strong> <code>${summary.action || ''}</code></p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                        <div>
                            <p><strong>Email Content:</strong></p>
                            <pre class="code-block">${escapeHtml((summary.read_snippet || '').substring(0, 500))}</pre>
                        </div>
                        <div>
                            <p><strong>Agent Response:</strong></p>
                            <pre class="code-block">${escapeHtml((summary.outgoing_snippet || '').substring(0, 500))}</pre>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(item);
        });

    } catch (error) {
        showToast(`Error loading activity: ${error.message}`, 'error');
    }
}

// ========== ACTION PLANS ==========
async function loadActionPlans() {
    try {
        const plans = await api.get('/api/action-plans');
        state.actionPlans = plans;

        const container = document.getElementById('plansList');
        const saveBtn = document.getElementById('savePlansBtn');

        if (plans.length === 0) {
            container.innerHTML = '<p class="info-message">📝 No action plans yet. Create one below!</p>';
            saveBtn.classList.add('hidden');
            return;
        }

        saveBtn.classList.remove('hidden');
        container.innerHTML = '';

        plans.forEach((plan, idx) => {
            const freqDisplay = {
                'every_sweep': 'Every Autopilot Sweep',
                'hourly': 'Once per Hour',
                'daily': 'Once per Day'
            }[plan.frequency] || plan.frequency;

            const planDiv = document.createElement('div');
            planDiv.className = 'plan-item';
            planDiv.style.cssText = 'background: var(--bg-glass); border: 1px solid var(--border-glass); border-radius: var(--border-radius); padding: 1rem; margin-bottom: 1rem;';

            planDiv.innerHTML = `
                <div style="display: flex; gap: 1rem; align-items: flex-start;">
                    <label class="toggle-label">
                        <input type="checkbox" class="toggle-input" ${plan.enabled ? 'checked' : ''} onchange="togglePlan(${idx})">
                    </label>
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <span style="color: var(--text-secondary);">${plan.enabled ? '🟢' : '⚪'}</span>
                            <strong>${escapeHtml(plan.name)}</strong>
                        </div>
                        <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 0.5rem;">${escapeHtml(plan.task)}</p>
                        <p style="font-size: 0.75rem; color: var(--text-tertiary);">📅 ${freqDisplay}</p>
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="deletePlan(${idx})">🗑️</button>
                </div>
            `;

            container.appendChild(planDiv);
        });

        // Load execution history
        const history = await api.get('/api/action-plans/history');
        const historyContainer = document.getElementById('executionHistory');

        if (history.length === 0) {
            historyContainer.innerHTML = '<p class="info-message">No execution history yet. Enable action plans and autopilot to start.</p>';
            return;
        }

        historyContainer.innerHTML = '';
        history.forEach(entry => {
            const planName = plans.find(p => p.id === entry.plan_id)?.name || 'Unknown';
            const statusEmoji = entry.success ? '✅' : '❌';

            const item = document.createElement('div');
            item.className = 'expander';
            item.innerHTML = `
                <div class="expander-header" onclick="this.parentElement.classList.toggle('expanded')">
                    <span>${statusEmoji} ${planName} - ${entry.timestamp || ''}</span>
                    <span>▶</span>
                </div>
                <div class="expander-content">
                    <p><strong>Plan:</strong> ${planName}</p>
                    <p><strong>Timestamp:</strong> ${entry.timestamp}</p>
                    <p><strong>Status:</strong> ${entry.success ? 'Success' : 'Failed'}</p>
                    ${entry.final_answer ? `<div class="success-message"><strong>Final Answer:</strong> ${escapeHtml(entry.final_answer)}</div>` : ''}
                    ${entry.error ? `<div class="error-message"><strong>Error:</strong> ${escapeHtml(entry.error)}</div>` : ''}
                </div>
            `;
            historyContainer.appendChild(item);
        });

    } catch (error) {
        showToast(`Error loading action plans: ${error.message}`, 'error');
    }
}

function togglePlan(idx) {
    state.actionPlans[idx].enabled = !state.actionPlans[idx].enabled;
}

async function deletePlan(idx) {
    const plan = state.actionPlans[idx];
    if (!confirm(`Delete action plan "${plan.name}"?`)) return;

    try {
        await api.delete(`/api/action-plans/${plan.id}`);
        showToast('Action plan deleted successfully', 'success');
        loadActionPlans();
    } catch (error) {
        showToast(`Error deleting plan: ${error.message}`, 'error');
    }
}

function initActionPlans() {
    // Save plans button
    document.getElementById('savePlansBtn').addEventListener('click', async () => {
        try {
            await api.put('/api/action-plans', { plans: state.actionPlans });
            showToast('Action plans saved!', 'success');
        } catch (error) {
            showToast(`Error saving plans: ${error.message}`, 'error');
        }
    });

    // Add plan button
    document.getElementById('addPlanBtn').addEventListener('click', async () => {
        const name = document.getElementById('newPlanName').value.trim();
        const task = document.getElementById('newPlanTask').value.trim();
        const frequency = document.getElementById('newPlanFrequency').value;
        const enabled = document.getElementById('newPlanEnabled').checked;

        if (!name || !task) {
            showToast('Please provide both name and task', 'warning');
            return;
        }

        try {
            await api.post('/api/action-plans', { name, task, frequency, enabled });
            showToast('Action plan added successfully!', 'success success');

            // Clear form
            document.getElementById('newPlanName').value = '';
            document.getElementById('newPlanTask').value = '';
            document.getElementById('newPlanEnabled').checked = true;

            loadActionPlans();
        } catch (error) {
            showToast(`Error adding plan: ${error.message}`, 'error');
        }
    });
}

// ========== CONNECTION SETTINGS ==========
async function loadConnectionInfo() {
    try {
        const info = await api.get('/api/connection/status');

        document.getElementById('ewsEmail').value = info.email || '';
        document.getElementById('ewsHost').value = info.host || '';
        document.getElementById('agentName').value = info.agent_name || '';

        const infoContainer = document.getElementById('connectionInfo');
        infoContainer.innerHTML = `
            <div class="info-item">
                <span class="info-label">Email:</span>
                <span class="info-value">${info.email || 'Not set'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Host:</span>
                <span class="info-value">${info.host || 'Auto-detect'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Password:</span>
                <span class="info-value">${info.has_password ? '●●●●●●' : 'Not set'}</span>
            </div>
        `;
    } catch (error) {
        showToast(`Error loading connection info: ${error.message}`, 'error');
    }
}

function initConnectionSettings() {
    // Password toggle
    document.getElementById('togglePassword').addEventListener('click', () => {
        const pwdField = document.getElementById('ewsPassword');
        const btn = document.getElementById('togglePassword');

        if (pwdField.type === 'password') {
            pwdField.type = 'text';
            btn.textContent = '🙈';
        } else {
            pwdField.type = 'password';
            btn.textContent = '👁️';
        }
    });

    // Test connection
    document.getElementById('testConnectionBtn').addEventListener('click', async () => {
        const email = document.getElementById('ewsEmail').value.trim();
        const password = document.getElementById('ewsPassword').value;
        const host = document.getElementById('ewsHost').value.trim();
        const agentName = document.getElementById('agentName').value.trim();

        if (!email || !password) {
            showToast('Please provide both email and password', 'warning');
            return;
        }

        showLoading(true, 'Testing connection...');

        try {
            const testResult = await api.post('/api/connection/test', { email, password, host });

            if (testResult.success) {
                showToast('✅ Connection successful!', 'success');

                // Auto-save
                const saveResult = await api.post('/api/connection/save', { email, password, host, agent_name: agentName });

                if (saveResult.success) {
                    showToast('✅ Credentials saved and applied!', 'success');
                    loadConnectionInfo();
                } else {
                    showToast('⚠️ Connection succeeded but failed to save credentials', 'warning');
                }
            } else {
                showToast(`❌ ${testResult.message}`, 'error');
            }
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            showLoading(false);
        }
    });

    // Save without testing
    document.getElementById('saveWithoutTestBtn').addEventListener('click', async () => {
        const email = document.getElementById('ewsEmail').value.trim();
        const password = document.getElementById('ewsPassword').value;
        const host = document.getElementById('ewsHost').value.trim();
        const agentName = document.getElementById('agentName').value.trim();

        if (!email) {
            showToast('Email address is required', 'warning');
            return;
        }

        showLoading(true, 'Saving...');

        try {
            const result = await api.post('/api/connection/save', { email, password, host, agent_name: agentName });

            if (result.success) {
                showToast('✅ Settings saved and applied!', 'success');
                showToast('⚠️ Credentials not tested - verify connection before use', 'warning');
                loadConnectionInfo();
            } else {
                showToast('❌ Failed to save settings', 'error');
            }
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            showLoading(false);
        }
    });

    // Fetch test
    document.getElementById('fetchTestBtn').addEventListener('click', async () => {
        showLoading(true, 'Fetching emails...');

        try {
            const result = await api.post('/api/connection/fetch-test');

            const resultsContainer = document.getElementById('fetchResults');
            resultsContainer.classList.remove('hidden');

            if (result.success && result.emails.length > 0) {
                resultsContainer.innerHTML = `<p class="success-message">✅ Found ${result.emails.length} unread emails</p>`;
                result.emails.forEach((email, i) => {
                    resultsContainer.innerHTML += `<p style="font-size: 0.875rem; margin-top: 0.5rem;">${i + 1}. ${escapeHtml(email.subject)} - From: ${escapeHtml(email.from)}</p>`;
                });
            } else if (result.success) {
                resultsContainer.innerHTML = '<p class="info-message">📭 No unread emails found</p>';
            } else {
                resultsContainer.innerHTML = `<p class="error-message">❌ Error: ${result.error}</p>`;
            }
        } catch (error) {
            showToast(`Error fetching emails: ${error.message}`, 'error');
        } finally {
            showLoading(false);
        }
    });
}

// ========== SIDEBAR SERVICE STATUS ==========
async function loadServiceStatus() {
    try {
        const status = await api.get('/api/autopilot/service/status');
        state.serviceStatus = status;

        const statusIndicator = document.querySelector('#serviceStatus .status-indicator');
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');

        // Update status display
        statusDot.className = 'status-dot';
        if (status.status === 'running') {
            statusDot.classList.add('running');
            statusText.textContent = '✅ Service Running';
        } else if (status.status === 'stopped') {
            statusDot.classList.add('stopped');
            statusText.textContent = '⏸️ Service Stopped';
        } else if (status.status === 'not_installed') {
            statusDot.classList.add('error');
            statusText.textContent = '⚠️ Service Not Installed';
            document.getElementById('serviceNotInstalled').classList.remove('hidden');
            document.getElementById('autopilotConfig').classList.add('hidden');
            return;
        }

        // Update toggle
        document.getElementById('autopilotServiceToggle').checked = status.enabled;

        // Show/hide config
        if (status.enabled || status.status === 'running') {
            document.getElementById('autopilotConfig').classList.remove('hidden');
            document.getElementById('serviceNotInstalled').classList.add('hidden');

            // Update period
            document.getElementById('autopilotPeriod').value = status.period_minutes || 5;

            // Update last run
            if (status.last_run) {
                document.getElementById('lastRunTime').textContent = `⏱️ Last run: ${formatTimestamp(status.last_run)}`;
            }
        } else {
            document.getElementById('autopilotConfig').classList.add('hidden');
        }
    } catch (error) {
        console.error('Error loading service status:', error);
    }
}

function initSidebar() {
    // Hands-free toggle
    document.getElementById('handsFreeToggle').addEventListener('change', (e) => {
        state.handsFree = e.target.checked;
    });

    // Autopilot service toggle
    document.getElementById('autopilotServiceToggle').addEventListener('change', async (e) => {
        const enable = e.target.checked;

        try {
            const result = await api.post('/api/autopilot/service/toggle', { enable });

            if (result.success) {
                showToast(enable ? '✅ Service started' : '✅ Service stopped', 'success');
                setTimeout(loadServiceStatus, 1000);
            } else {
                showToast(`❌ ${result.message}`, 'error');
                e.target.checked = !enable; // Revert
            }
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
            e.target.checked = !enable; // Revert
        }
    });

    // Save period
    document.getElementById('savePeriodBtn').addEventListener('click', async () => {
        const period = parseInt(document.getElementById('autopilotPeriod').value);

        try {
            await api.post('/api/autopilot/period', { period });
            showToast('✅ Saved - restart service for changes', 'success');
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    });

    // Restart service
    document.getElementById('restartServiceBtn').addEventListener('click', async () => {
        showLoading(true, 'Restarting service...');

        try {
            await api.post('/api/autopilot/service/toggle', { enable: false });
            await new Promise(resolve => setTimeout(resolve, 2000));
            await api.post('/api/autopilot/service/toggle', { enable: true });

            showToast('✅ Service restarted', 'success');
            setTimeout(loadServiceStatus, 1000);
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            showLoading(false);
        }
    });

    // Run manual
    document.getElementById('runManualBtn').addEventListener('click', async () => {
        showLoading(true, 'Running autopilot...');

        try {
            const result = await api.post('/api/autopilot/run-manual');
            showToast(`✅ Processed ${result.logs.length} items`, 'success');

            // Update activity logs in sidebar
            const logsContainer = document.getElementById('activityLogs');
            logsContainer.innerHTML = '';
            result.logs.slice(-10).forEach(log => {
                const p = document.createElement('p');
                p.style.fontSize = '0.75rem';
                p.style.color = 'var(--text-tertiary)';
                p.textContent = log;
                logsContainer.appendChild(p);
            });
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            showLoading(false);
        }
    });

    // Clear chat
    document.getElementById('clearChatBtn').addEventListener('click', async () => {
        if (!confirm('Clear all chat history?')) return;

        try {
            await api.delete('/api/chat/clear');
            document.getElementById('chatMessages').innerHTML = '';
            showToast('Chat cleared', 'success');
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    });

    // Load service status periodically
    setInterval(loadServiceStatus, 10000); // Every 10 seconds
}

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Sales Agent Web UI Initialized');

    // Initialize all modules
    initTabs();
    initChat();
    initKnowledgeBase();
    initAutopilotRules();
    initActionPlans();
    initConnectionSettings();
    initSidebar();

    // Load initial data
    loadServiceStatus();

    showToast('Welcome to Sales Agent Web UI! 🎉', 'success');
});

// ========== GLOBAL FUNCTION DECLARATIONS ==========
// These functions are called from inline onclick handlers in dynamically generated HTML
// They must be available in the global scope

window.toggleExpander = toggleExpander;
window.deleteCollection = deleteCollection;
window.toggleRule = toggleRule;
window.updateRulePriority = updateRulePriority;
window.deleteRule = deleteRule;
window.togglePlan = togglePlan;
window.deletePlan = deletePlan;
