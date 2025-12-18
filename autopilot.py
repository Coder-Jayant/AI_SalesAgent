"""
autopilot.py
Autopilot logic: state management, rules, and auto-sweep functionality
"""

import os
import json
import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone as pytz_timezone
from pathlib import Path
from react_agent import ReActAgent
import autopilot_control

logger = logging.getLogger(__name__)

# Constants
STATE_FILE = os.getenv("AUTOPILOT_STATE_FILE", "autopilot_state.json")
_PROCESSED_MAIL_IDS_FILE = "processed_mails.json"
AUTOPILOT_MAX_ACTIONS = int(os.getenv("AUTOPILOT_MAX_ACTIONS", "3"))
LOCK_FILE = "autopilot.lock"  # Execution lock file

# Default autopilot rules
_DEFAULT_RULES = [
    {
        "id": "internal_greet",
        "name": "Internal greetings handler",
        "enabled": True,
        "prompt": "If the email is just greetings, wishes, or thanks, acknowledge politely and no action needed.",
        "builtin": True
    },
    {
        "id": "external_interest",
        "name": "Handle external interest or sales inquiries",
        "enabled": True,
        "prompt": (
            "If the email is from an external sender asking for demos, pricing, meetings, or collaborations - "
            "FIRST query the knowledge base and use web search  for relevant information (pricing, products, services, offerings, and any company specific information.), "
            "THEN prepare a polite, informative sales reply using the accurate information from the knowledge base."
        ),
        "builtin": True
    },
    {
        "id": "pricing_queries",
        "name": "Pricing and product information queries",
        "enabled": True,
        "prompt": (
            "If customer asks about pricing, product details, or technical specifications, or anything that you don't know about cyfuture - "
            "ALWAYS query the knowledge base and web search first using action: query_kb and use web search using action: web_search with appropriate query, "
            "then provide accurate information based on the knowledge base and web search results. "
            "NEVER guess pricing or product details or anything that you don't know about cyfuture."
        ),
        "builtin": True
    },
    {
        "id": "spam_filter",
        "name": "Spam or newsletters",
        "enabled": True,
        "prompt": "Ignore or archive messages that appear to be newsletters, spam, or automated notifications.",
        "builtin": True
    },
    {
        "id": "followups",
        "name": "Follow-ups",
        "enabled": True,
        "prompt": (
            "If the sender has already been replied to but there is no reply from the customer, "
            "follow up in-thread politely. If the original inquiry was about pricing/products, "
            "query the knowledge base and web search first to include updated or additional information."
        ),
        "builtin": True
    },
]


# Autopilot system prompt for ReAct agent
AUTOPILOT_SYSTEM_PROMPT = """
**CURRENT CONTEXT:**
Current Date/Time: {current_time_context}

You are Cyfuture's AI Sales Agent in AUTOPILOT MODE.

Your goal: Process emails autonomously based on rules, using multiple tools as needed.

CRITICAL AUTOPILOT BEHAVIORS:
1. ALWAYS use query_knowledge_base AND web_search before answering pricing/product questions
2. Chain tools together (e.g., query_knowledge_base → web_search → reply_inline)
3. Mark emails as read after processing using mark_read tool
4. Escalate complex legal/security issues using escalate            
**Behaviour & Principles:**
1. **NEVER use placeholders** in emails (e.g., [Your Name], [list services], [phone number])
2. **ALWAYS use real information:** You are {user_name} ({user_email})
3. **For company introductions:** MUST query knowledge base FIRST to get real Cyfuture service details
4. Write comprehensive, informative emails with strong sales perspective
5. Include specific company information, product benefits, technical details
6. Add links to services (e.g., https://www.cyfuture.com)
7. Use HTML formatting (tables, headings, lists) for professional appearance
8. When customer asks for demo: propose 2-3 specific time slots
9. For pricing inquiries: query KB first, then provide detailed response
10. Escalate high-risk emails (legal, security, compliance issues)
11. Respect opt-outs: mark read, don't follow up
12. Cite sources when using KB or web search
9. **BUSINESS CRITICAL: If KB lacks info about a product/service inquiry:**
   - NEVER recommend external/competitor/open-source alternatives
   - Express interest in the customer's needs
   - Offer to connect them with specialized sales team
   - Use escalate tool OR draft reply offering human consultation
   - Goal: CAPTURE the business opportunity, not deflect it

WORKFLOW FOR COMPLEX EMAILS (pricing, demos, technical questions):
1. Analyze email intent and sender
2. Use query_knowledge_base to get company-specific information
3. Use web_search to get additional context or industry information
4. IF KB/web search have sufficient info: Craft response with available information
5. IF KB/web search DON'T have info: 
   - Acknowledge the inquiry professionally
   - State "Cyfuture can discuss custom solutions for your needs"
   - Offer to escalate or schedule a meeting: use escalate tool OR mention scheduling
   - NEVER recommend competitors or open-source alternatives
6. Use reply_inline to send the response **ONLY ONCE**
7. Use mark_read to mark email as read
8. Call end_task immediately with summary of actions taken

WORKFLOW FOR SIMPLE EMAILS (greetings, spam, acknowledgments):
1. Analyze email intent
2. Take appropriate action (mark_read, ignore_spam, or simple reply - **ONE TIME ONLY**)
3. Call end_task with summary

AVAILABLE TOOLS - Use these as needed:
- Information: query_knowledge_base, web_search, current_time
- Email Reply: reply_inline (USE ONLY ONCE), follow_up_email, follow_up_thread_tool
- Email Management: mark_read, ignore_spam, escalate
- Scheduling: schedule_with_check
- Utility: chat_with_human (for human intervention), end_task (MUST call when done)

IMPORTANT: 
- You MUST call end_task when finished with a brief summary of actions taken
- **NEVER send multiple replies to the same email - reply_inline should be called ONLY ONCE**
- For pricing/product queries, ALWAYS query both knowledge base and web search
- Include source citations and links in customer-facing emails
- Never guess or make up information about pricing or products
- After sending a reply with reply_inline, immediately mark as read and call end_task

CRITICAL BUSINESS RULES:
- **NEVER recommend competitor products, open-source alternatives, or external solutions**
- If information is NOT in knowledge base: acknowledge professionally and offer to escalate or schedule a call
- For unfamiliar products/services: Say "Cyfuture can potentially help with custom solutions" and escalate
- ALWAYS capture business opportunities - never send customers away
- Use escalate tool for queries outside your knowledge scope

**BUSINESS HANDLING RULES:**
- **DO NOT recommend competitors, external tools, or open-source alternatives**
- If specific product/service not in KB: offer human consultation, not external solutions
- Your role is BUSINESS CAPTURE - connect interested customers to human sales team
- When uncertain about offerings: "Let me connect you with our specialist" NOT "Try external source X"
"""

# Cached ReAct agent instance
_cached_autopilot_react_agent = None


# ============= STATE MANAGEMENT =============
def _init_state_file_if_missing():
    """Initialize autopilot state file if it doesn't exist."""
    p = Path(STATE_FILE)
    if not p.exists():
        default = {
            "pending_followups": [],
            "processed_ids": [],
            "autohandle_period_minutes": int(os.getenv("AUTOPILOT_PERIOD_MINUTES", "1")),
            "autopilot_rules": _DEFAULT_RULES.copy(),
            "autopilot_summaries": [],
        }
        p.write_text(json.dumps(default, indent=2), encoding="utf-8")


def _load_state() -> Dict[str, Any]:
    """Load autopilot state from file."""
    try:
        p = Path(STATE_FILE)
        if not p.exists():
            _init_state_file_if_missing()
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
        data.setdefault("pending_followups", [])
        data.setdefault("processed_ids", [])
        data.setdefault("autohandle_period_minutes", int(os.getenv("AUTOPILOT_PERIOD_MINUTES", "1")))
        data.setdefault("autopilot_rules", _DEFAULT_RULES.copy())
        data.setdefault("autopilot_summaries", [])
        return data
    except Exception:
        return {
            "pending_followups": [],
            "processed_ids": [],
            "autohandle_period_minutes": int(os.getenv("AUTOPILOT_PERIOD_MINUTES", "1")),
            "autopilot_rules": _DEFAULT_RULES.copy(),
            "autopilot_summaries": []
        }


def _save_state(state: Dict[str, Any]) -> None:
    """Save autopilot state to file."""
    try:
        Path(STATE_FILE).write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"[autopilot] failed to persist state: {e}")


# ============= PROCESSED IDS MANAGEMENT =============
def _load_processed_ids() -> set:
    """Load set of processed email IDs."""
    try:
        with open(_PROCESSED_MAIL_IDS_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
    except Exception:
        return set()


def _save_processed_ids(ids: set):
    """Save set of processed email IDs."""
    try:
        with open(_PROCESSED_MAIL_IDS_FILE, "w") as f:
            json.dump(list(ids), f, indent=2)
    except Exception as e:
        logger.warning(f"[autopilot] Failed to save processed mail IDs: {e}")


# ============= RULES MANAGEMENT =============
def get_autopilot_rules() -> List[Dict[str, Any]]:
    """Get current autopilot rules."""
    st_data = _load_state()
    return st_data.get("autopilot_rules", _DEFAULT_RULES.copy())


def set_autopilot_rules(rules: List[Dict[str, Any]]):
    """Set autopilot rules."""
    st_data = _load_state()
    st_data["autopilot_rules"] = rules
    _save_state(st_data)


def update_autopilot_rule_by_id(rule_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update a specific autopilot rule by ID.
    
    Args:
        rule_id: ID of the rule to update
        updates: Dictionary of fields to update (name, prompt, priority, enabled)
    
    Returns:
        True if updated successfully, False if rule not found
    """
    rules = get_autopilot_rules()
    
    for rule in rules:
        if rule.get("id") == rule_id:
            # Update allowed fields
            if "name" in updates:
                rule["name"] = updates["name"]
            if "prompt" in updates:
                rule["prompt"] = updates["prompt"]
            if "priority" in updates:
                rule["priority"] = int(updates["priority"])
            if "enabled" in updates:
                rule["enabled"] = bool(updates["enabled"])
            
            # Save updated rules
            set_autopilot_rules(rules)
            logger.info(f"[AutopilotRules] Updated rule {rule_id}: {list(updates.keys())}")
            return True
    
    logger.warning(f"[AutopilotRules] Rule {rule_id} not found")
    return False


def get_autopilot_period_minutes() -> int:
    """Get autopilot period in minutes."""
    st_data = _load_state()
    return int(st_data.get("autohandle_period_minutes", 1))


def set_autopilot_period_minutes(minutes: int):
    """Set autopilot period in minutes."""
    st_data = _load_state()
    st_data["autohandle_period_minutes"] = int(minutes)
    _save_state(st_data)


def get_autopilot_service_enabled() -> bool:
    """Get whether autopilot service is enabled."""
    st_data = _load_state()
    return st_data.get("service_enabled", False)


def set_autopilot_service_enabled(enabled: bool):
    """Set autopilot service enabled state."""
    st_data = _load_state()
    st_data["service_enabled"] = bool(enabled)
    _save_state(st_data)

def get_hands_free_mode() -> bool:
    """Get hands-free mode state."""
    st_data = _load_state()
    return st_data.get("hands_free_mode", False)


def set_hands_free_mode(enabled: bool):
    """Set hands-free mode state."""
    st_data = _load_state()
    st_data["hands_free_mode"] = bool(enabled)
    _save_state(st_data)

def get_autopilot_react_agent(tools=None):
    """
    Get or create ReAct agent for autopilot mode.
    
    Args:
        tools: Optional list of tools to use. If None, uses ALL_TOOLS (default).
               Action plan service should pass EXECUTION_TOOLS to prevent plan management.
    """
    global _cached_autopilot_react_agent
    
    # Get current time for context
    from datetime import datetime
    from zoneinfo import ZoneInfo
    current_time = datetime.now(ZoneInfo("Asia/Kolkata"))
    time_str = current_time.strftime('%A, %B %d, %Y at %I:%M %p %Z')
    
    # Always create a fresh agent with updated timestamp
    # (Don't cache to ensure current time is always fresh)
    from react_agent import ReActAgent
    from agent_tools import ALL_TOOLS
    
    # Use provided tools or default to ALL_TOOLS
    agent_tools = tools if tools is not None else ALL_TOOLS
    from langchain_openai import ChatOpenAI
    
    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "token-abc123"),
        base_url=os.getenv("OPENAI_BASE_URL", "http://49.50.117.66:8000/v1"),
        model=os.getenv("OPENAI_MODEL", "/model"),
        temperature=0.2,
        max_tokens=3000,
    )
    
    # Get user identity from environment
    user_name = os.getenv("AGENT_USER_NAME", "Sales Team Cyfuture")
    user_email = os.getenv("EWS_EMAIL", "sales-ai-agent@cyfuture.com")
    
    # Format system prompt with current time and user identity
    formatted_prompt = AUTOPILOT_SYSTEM_PROMPT.format(
        current_time_context=time_str,
        user_name=user_name,
        user_email=user_email
    )
    
    agent = ReActAgent(
        llm=llm,
        tools=agent_tools,  # Use filtered tools if provided
        system_prompt=formatted_prompt
    )
    logger.debug(f"[autopilot] Created ReAct agent with current time: {time_str}")
    
    return agent


# ============= AUTOPILOT SWEEP =============
def autopilot_once(max_actions: int = AUTOPILOT_MAX_ACTIONS, hands_free: bool = False, ignore_stop_flag: bool = False) -> List[str]:
    """
    Perform one autopilot sweep: fetch emails, apply rules, execute actions.
    
    Args:
        max_actions: Maximum number of emails to process
        hands_free: If True, can auto-send; if False, save as drafts
        ignore_stop_flag: If True, ignore autopilot_stop.flag (for background service)
    
    Returns:
        List of log strings
    """
    from agent_tools import dynamic_mail_fetch_tool, fetch_email, mark_read
    from action_handlers import handle_action, generate_action_from_llm, summarize_for_llm

    logs = []
    
    # CRITICAL FIX: Execution lock to prevent concurrent runs
    instance_id = str(uuid.uuid4())
    lock_path = Path(LOCK_FILE)
    
    try:
        # Check if another autopilot is already running
        if lock_path.exists():
            # Check if lock is stale (older than 10 minutes)
            age = time.time() - lock_path.stat().st_mtime
            if age < 600:  # 10 minutes
                logger.warning(f"[autopilot] Another sweep is running (lock age: {age:.0f}s), skipping")
                return ["[SKIPPED] Another autopilot sweep in progress"]
            else:
                # Stale lock, remove it
                logger.warning(f"[autopilot] Removing stale lock (age: {age:.0f}s)")
                lock_path.unlink()
        
        # Create new lock with our instance ID
        lock_path.write_text(instance_id)
        
        # Verify we got the lock (race condition check)
        time.sleep(0.1)
        if lock_path.read_text() != instance_id:
            logger.warning("[autopilot] Lock acquired by another process, skipping")
            return ["[SKIPPED] Lock acquired by another process"]
        
        logger.info(f"[autopilot] Acquired execution lock: {instance_id}")
    except Exception as e:
        logger.error(f"[autopilot] Failed to acquire lock: {e}")
        return ["[ERROR] Failed to acquire execution lock"]
    
    try:
        logs = []
        state = _load_state()
        rules = [r for r in state.get("autopilot_rules", _DEFAULT_RULES.copy()) if r.get("enabled")]
        # Sort rules by priority (1 = highest priority)
        rules = sorted(rules, key=lambda r: r.get('priority', 999))
        
        if not rules:
            logs.append("No rules enabled.")
            return logs

        # ============= PROCESS EMAILS =============
        processed_ids = _load_processed_ids()
        logger.info(f"[autopilot] Loaded {len(processed_ids)} already-processed email IDs")

        # Fetch unread emails
        try:
            unread_resp = dynamic_mail_fetch_tool.invoke({"unread": True, "batch_size": 10})
            unread_data = json.loads(unread_resp)
            unread = unread_data.get("unread", []) or []
            logger.info(f"[autopilot] Fetched {len(unread)} unread emails")
        except Exception as e:
            logs.append(f"[error] Failed to fetch unread emails: {e}")
            unread = []

        new_mails = [m for m in unread if m.get("id") not in processed_ids]
        logger.info(f"[autopilot] After filtering: {len(new_mails)} new emails to process")

        # Determine additional strategies from rule keywords
        keyword_map = {
            "follow": "unresponded",
            "unresponded": "unresponded",
            "follow-up": "unresponded",
            "filter": "filtered",
            "search": "filtered",
        }
        strategies_needed = set()
        for r in rules:
            prompt = (r.get("prompt") or "").lower()
            for kw, strat in keyword_map.items():
                if kw in prompt:
                    strategies_needed.add(strat)
        strategies_needed.discard("unread")

        # Fetch additional mails based on strategies
        for strat in strategies_needed:
            try:
                if strat == "unresponded":
                    resp = dynamic_mail_fetch_tool.invoke({"unresponded": True, "days": 0, "limit": 10, "only_external": True})
                    data = json.loads(resp)
                    threads = data.get("unresponded_threads", []) or []
                    for t in threads:
                        mid = t.get("last_message_id")
                        mck = t.get("last_changekey")
                        subj = t.get("subject") or ""
                        if mid and mid not in processed_ids:
                            synthetic = {
                                "id": mid,
                                "changekey": mck or "",
                                "subject": subj,
                                "sender_email": t.get("customer_email") or "",
                                "received": t.get("last_message_time") or "",
                                "conversation_id": t.get("conversation_id") or "",
                                "from_unresponded": True,
                            }
                            if not any(x.get("id") == synthetic["id"] for x in new_mails):
                                new_mails.append(synthetic)
                elif strat == "filtered":
                    resp = dynamic_mail_fetch_tool.invoke({"limit": 50})
                    data = json.loads(resp)
                    filtered = data.get("filtered", []) or []
                    for m in filtered:
                        if m.get("id") and m.get("id") not in processed_ids and not any(x.get("id") == m.get("id") for x in new_mails):
                            new_mails.append(m)
            except Exception as e:
                logs.append(f"[warn] Strategy '{strat}' failed: {e}")

        if not new_mails:
            logs.append("No new unread emails or unresponded threads to process.")
            return logs

        # Build rules context for LLM
        rules_context = "\n".join([f"- {r['prompt']}" for r in rules if r.get("prompt")])
        logs.append("[rules/context] Active natural-language rules:")
        logs.extend([f"  → {r['prompt']}" for r in rules if r.get("prompt")])

        # Process emails
        actions_taken = 0
        for mail in new_mails[:max_actions]:
            # CRITICAL: Check for stop flag at start of each iteration (unless ignored by service)
            if not ignore_stop_flag:
                from autopilot_control import should_autopilot_stop
                if should_autopilot_stop():
                    logger.info("[autopilot] Stop flag detected - terminating immediately")
                    logs.append("[STOPPED] Autopilot stopped by user")
                    break
            
            if actions_taken >= max_actions:
                break

            mail_id = mail.get("id")
            
            # CRITICAL: Double-check email hasn't been processed (safety net)
            if mail_id in processed_ids:
                logger.warning(f"[autopilot] Skipping already processed email: {mail_id}")
                logs.append(f"[SKIP] Already processed: {mail.get('subject', 'No Subject')}")
                continue

            sender = (mail.get("from") or mail.get("sender") or 
                     (mail.get("from", {}).get("email") if isinstance(mail.get("from"), dict) else None) or 
                     mail.get("sender_email") or "Unknown Sender")
            subject = mail.get("subject", "No Subject")
            changekey = mail.get("changekey")

            # Fetch full email with thread
            body = "[No body text]"
            full_mail = None
            try:
                if mail_id:
                    full_mail_json = fetch_email.invoke({"item_id": mail_id, "changekey": changekey or "", "include_thread": True})
                    full_mail = json.loads(full_mail_json)
                    if isinstance(full_mail, dict) and full_mail.get("thread"):
                        parts = []
                        for t in full_mail.get("thread", [])[:6]:
                            who = t.get("sender_email") or t.get("sender_name") or "Unknown"
                            when = t.get("received") or ""
                            txt = t.get("body_text") or t.get("body_html") or ""
                            snippet = (txt or "")
                            parts.append(f"{who} @ {when}:\n{snippet}\n---")
                        body = "\n".join(parts)
                    else:
                        body = (full_mail.get("body") or full_mail.get("body_text") or "")[:1500] if isinstance(full_mail, dict) else "[No body text]"
                    mail_summary = summarize_for_llm(full_mail or mail)
                else:
                    mail_summary = summarize_for_llm(mail)
            except Exception as fe:
                logger.warning(f"[autopilot] Failed to fetch full email for {subject}: {fe}")
                mail_summary = summarize_for_llm(mail)
                body = mail_summary

            read_snippet = (body or "")[:2000]
            logs.append(f"[read] {subject} -> {read_snippet[:300]}")

            # Build hands-free instruction
            if hands_free:
                hands_free_instruction = """
    **HANDS-FREE MODE: ON**
    - You CAN send emails directly
    - Set save_as_draft=False (or omit parameter, as False is default)
    """
            else:
                hands_free_instruction = """
    **HANDS-FREE MODE: OFF - DRAFT MODE ACTIVE**  
    - You MUST save all replies as drafts
    - Set save_as_draft=True for ALL email tools
    - Examples:
      * reply_inline(item_id="...", changekey="...", body_html="...", save_as_draft=True)
      * follow_up_email(to_email="...", subject="...", body_html="...", save_as_draft=True)
    - NEVER send emails directly - always save as draft
    """

            # Extract TO, CC, BCC from email for context
            to_recipients = full_mail.get("to", []) if full_mail else []
            cc_recipients = full_mail.get("cc", []) if full_mail else []
            bcc_recipients = full_mail.get("bcc", []) if full_mail else []
            
            # Get user identity from ENV
            user_name = os.getenv("AGENT_USER_NAME", "Sales Agent")
            user_email = os.getenv("EWS_EMAIL", "")
            # Extract recipient info
            to_recipients = full_mail.get("to", []) if full_mail else []
            cc_recipients = full_mail.get("cc", []) if full_mail else []
            
            # Filter out None values and convert to strings
            to_list_str = ", ".join([str(r) for r in to_recipients if r is not None]) if to_recipients else "N/A"
            cc_list_str = ", ".join([str(r) for r in cc_recipients if r is not None]) if cc_recipients else "N/A"
            
            # Get current time for context
            from datetime import datetime
            from zoneinfo import ZoneInfo
            current_time = datetime.now(ZoneInfo("Asia/Kolkata"))
            time_str = current_time.strftime('%A, %B %d, %Y at %I:%M %p %Z')
            
            # Use ReAct agent for intelligent multi-step processing
            agent_instruction = f"""
    AUTOPILOT MODE - Process this email by evaluating ALL rules below.
    
    **CURRENT TIME:** {time_str}
    
    **YOUR IDENTITY:**
    - You are acting on behalf of: {user_name} ({user_email})
    - You represent {user_name} in all communications
    - Check if this email is addressed to {user_email} (in TO or CC)
    - If email is NOT addressed to {user_email}, consider if you should respond based on rules
    
    {hands_free_instruction}
    
    RULES (with priority for conflict resolution):
    {rules_context}
    
    **CRITICAL RULE APPLICATION:**
    - Evaluate ALL rules above
    - Follow ALL rules that apply to this email
    - If rules contradict each other, use PRIORITY to decide:
      * Priority 1 (Critical) - Security, escalation, urgent matters
      * Priority 2 (Medium) - Standard operations, replies, acknowledgments  
      * Priority 3 (Low) - General guidelines, catch-all behaviors
    - In case of conflict, follow the rule with LOWER priority number (1 beats 2, 2 beats 3)
    - If no conflicts, apply ALL applicable rules together

    EMAIL DETAILS:
    Subject: {subject}
    From: {sender}
    To: {to_list_str}
    CC: {cc_list_str}
    ID: {mail_id}
    Changekey: {changekey}

    EMAIL CONTENT:
    {mail_summary}

    CRITICAL INSTRUCTIONS:
    1. Analyze the email based on the rules above
    2. For pricing/product queries: use query_knowledge_base AND web_search tools
    3. Craft your response carefully based on gathered information
    4. **MAINTAIN CC/BCC RECIPIENTS:**
       - If original email has CC recipients, preserve them in your reply
       - Extract CC list from EMAIL DETAILS above
       - Pass cc_recipients parameter to reply_inline
       - Example: reply_inline(..., cc_recipients={cc_recipients})
    5. **ADD EMAIL SIGNATURE:**
       - End ALL email replies with this signature:
         
         Best regards,
         {user_name}
         {user_email}
    6. Send **ONLY ONE reply** using reply_inline tool with these EXACT parameters:
       - item_id: "{mail_id}"
       - changekey: "{changekey}"
       - body_html: "<your HTML formatted reply with signature>"
       - cc_recipients: {cc_recipients} (if original email had CC)
    7. After sending ONE reply, immediately use mark_read tool
    8. Call end_task with a summary

    **TOOL USAGE EXAMPLE FOR reply_inline WITH CC:**
    ```
    reply_inline(
        item_id="{mail_id}", 
        changekey="{changekey}", 
        body_html="<p>Your reply</p><br><p>Best regards,<br>{user_name}<br>{user_email}</p>",
        cc_recipients={cc_recipients}
    )
    ```

    **CRITICAL RULES:**
    - Send ONLY ONE reply per email - DO NOT call reply_inline twice
    - MUST use item_id, changekey, and body_html parameters (NOT just 'body')
    - After calling reply_inline ONCE, proceed directly to mark_read then end_task
    - NEVER attempt a second reply

    Execute the workflow now.
    """

            try:
                # Get cached ReAct agent
                react_agent = get_autopilot_react_agent()
            
                # Run agent with max 15 iterations to prevent infinite loops
                logs.append(f"[react-agent] Processing '{subject[:60]}'...")
                final_answer = react_agent.run(
                    user_input=agent_instruction,
                    max_iterations=15
                )
            
                logs.append(f"[react-completed] {subject}: {final_answer[:200]}")
            
                # Extract result info from final answer
                outgoing = ""
                if "replied" in final_answer.lower() or "sent" in final_answer.lower():
                    outgoing = final_answer[:300]
                    logs.append(f"[sent] {subject} -> {outgoing}")
                else:
                    logs.append(f"[action-result] {final_answer[:200]}")

                # Save summary
                try:
                    from datetime import datetime
                    from zoneinfo import ZoneInfo
                    st_data = _load_state()
                    summ_list = st_data.get("autopilot_summaries", [])
                    summary_record = {
                        "time": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
                        "subject": subject,
                        "from": sender,
                        "action": "react-processed",
                        "read_snippet": read_snippet,
                        "outgoing_snippet": (outgoing or ""),
                    }
                    summ_list.insert(0, summary_record)
                    st_data["autopilot_summaries"] = summ_list[:200]
                    _save_state(st_data)
                except Exception as se:
                    logger.warning(f"[autopilot] failed to persist summary: {se}")

                actions_taken += 1

                # Mark as read
                try:
                    if changekey and mail_id:
                        mark_read.invoke({"item_id": mail_id, "changekey": changekey})
                        logs.append(f"[marked-read] {subject}")
                except Exception as mark_err:
                    logs.append(f"[warn] Failed to mark as read: {mark_err}")

                # CRITICAL FIX: Save processed ID IMMEDIATELY after processing each email
                if mail_id:
                    processed_ids.add(mail_id)
                    _save_processed_ids(processed_ids)  # Save NOW, not at end
                    logger.info(f"[autopilot] Marked {mail_id} as processed and saved")

            except Exception as e:
                logs.append(f"[error] {e}")

        time.sleep(1.0)

        # Final save (redundant but safe)
        _save_processed_ids(processed_ids)
        return logs
    
    finally:
        # Always release lock
        try:
            if lock_path.exists() and lock_path.read_text() == instance_id:
                lock_path.unlink()
                logger.info(f"[autopilot] Released execution lock: {instance_id}")
        except Exception as unlock_err:
            logger.error(f"[autopilot] Failed to release lock: {unlock_err}")