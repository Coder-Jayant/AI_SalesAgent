"""
action_handlers.py
Action handling and LLM decision generation
"""

import os
import json
import logging
import html as _html
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# LLM instance
llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "token-abc123"),
    base_url=os.getenv("OPENAI_BASE_URL", "http://49.50.117.66:8000/v1"),
    model=os.getenv("OPENAI_MODEL", "/model"),
    temperature=0.2,
    max_tokens=2048,
)


# ============= HELPER FUNCTIONS =============
def summarize_for_llm(mail: Dict[str, Any], max_body_chars: int = 800) -> str:
    """Compact summary for LLM decision prompts."""
    subject = mail.get("subject", "No subject")
    sender = mail.get("sender_email") or (mail.get("sender", {}) or {}).get("email") or mail.get("from") or "Unknown"
    received = mail.get("received") or mail.get("datetime_received") or ""
    body = (mail.get("body") or mail.get("body_text") or "")[:max_body_chars]
    attachments = mail.get("has_attachments", False)
    convo = mail.get("conversation_id") or ""
    summary = f"From: {sender}\nSubject: {subject}\nReceived: {received}\nConversation: {convo}\nHas attachments: {attachments}\nBody snippet:\n{body}"
    return summary


def normalize_followup_subject(subject: str, prefix: str = "Follow-up regarding ") -> str:
    """Normalize subject used for follow-up messages to avoid repeated prefixes."""
    if not subject:
        return prefix.strip()
    s = subject.strip()
    while s.startswith(prefix):
        s = s[len(prefix):].strip()
    for p in ("Re: ", "Fwd: ", "FW: "):
        if s.startswith(p):
            s = s[len(p):].strip()
    return prefix + s


def ensure_html_from_text(text: str) -> str:
    """Convert plain text into simple HTML body (paragraphs)."""
    if not text:
        return ""
    if "<" in text and ">" in text and "\n" not in text:
        return text
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if paragraphs:
        parts = []
        for p in paragraphs:
            safe = _html.escape(p).replace("\n", "<br/>")
            parts.append(f"<p>{safe}</p>")
        return "\n".join(parts)
    return "<p>" + _html.escape(text).replace("\n", "<br/>") + "</p>"


# ============= LLM ACTION GENERATION =============
def generate_action_from_llm(prompt: str) -> dict | str:
    """
    Ask the LLM to return a JSON object action (or text fallback).
    Now includes RAG awareness in system prompt.
    """
    try:
        sys_msg = SystemMessage(content=(
            "You are Cyfuture's Sales Representative AI Agent that decides actions on incoming emails. "
            "Return a JSON object (no extra text) with keys: action, reason, and optional fields.\n\n"
            
            "**IMPORTANT: You have access to web search and knowledge base with company information.**\n"
            "Before making decisions about pricing, products, or policies, or any critical information you should:\n"
            "1. Use 'query_kb' for company-specific information (pricing, products, policies)\n"
            "2. Use 'web_search' for company-specific information (pricing, products, policies), industry trends, competitor info, or general knowledge\n"
            
            "Please use both query_kb and web_search to get the most accurate information.\n"
            "Available actions:\n"
            "- query_kb: Query knowledge base (include kb_query field)\n"
            "- web_search: Search the web (include query field)\n"
            "- reply: Send a reply (include reply_html or reply_body)\n"
            "- follow_up: Send follow-up message\n"
            "- follow_up_thread: Reply in-thread\n"
            "- escalate: Forward to human (include reason)\n"
            "- mark_spam: Mark as junk\n"
            "- mark_read: Mark as read\n"
            "- schedule_meeting: Propose meeting (include meeting_start_iso, meeting_duration_minutes)\n"
            "- no_action: Do nothing\n\n"
            "Examples:\n"
            '{"action": "query_kb", "kb_query": "What is our pricing for cloud hosting?", "reason": "Need pricing info before replying"}\n'
            '{"action": "web_search", "query": "Latest cloud computing trends 2024", "reason": "Need industry context"}\n'
            '{"action": "reply", "reply_html": "<p>Thanks for your interest...</p>", "reason": "Acknowledge inquiry"}\n'
            '{"action": "escalate", "reason": "Complex legal question requiring human review"}\n'
        ))
        user_msg = HumanMessage(content=prompt)
        resp = llm.invoke([sys_msg, user_msg])
        text = resp.content.strip()
        
        # Try to parse JSON
        if text.startswith("{"):
            try:
                return json.loads(text)
            except Exception:
                pass
        
        # Extract JSON from text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end+1]
            try:
                return json.loads(candidate)
            except Exception:
                pass
        
        return text
    except Exception as e:
        return f"[LLM error] {e}"


# ============= ACTION HANDLER =============
def handle_action(mail: dict, action_desc: dict | str) -> dict:
    """
    Execute action described by action_desc on the given mail-like dict.
    Supports querying knowledge base before taking action.
    """
    from agent_tools import (
        fetch_email, reply_inline, follow_up_thread_tool, 
        follow_up_email, escalate, ignore_spam, mark_read,
        schedule_with_check, query_knowledge_base
    )
    
    def _safe_get_id(m: dict) -> tuple[Optional[str], Optional[str]]:
        mid = m.get("id") or m.get("uid") or m.get("message_id")
        mck = m.get("changekey") or m.get("changekey_id") or m.get("etag") or m.get("id")
        return (str(mid) if mid is not None else None, str(mck) if mck is not None else None)

    try:
        # Parse action if string
        if isinstance(action_desc, str):
            text = action_desc.lower()
            if "no action" in text or text.strip() == "" or "noaction" in text:
                return {"result": "No action taken (LLM returned 'No action').", "outgoing": ""}
            if "reply" in text:
                action = {"action": "reply", "reason": "LLM instructed to reply", "reply_html": action_desc}
            elif "escalate" in text:
                action = {"action": "escalate", "reason": "LLM requested escalation"}
            elif "spam" in text or "junk" in text:
                action = {"action": "mark_spam", "reason": "LLM flagged as spam"}
            else:
                return {"result": f"No actionable instruction parsed from LLM text: {action_desc[:200]}", "outgoing": ""}
        else:
            action = action_desc

        act = (action.get("action") or "").lower()
        reason = action.get("reason", "")

        # ========================================
        # Handle knowledge base query action
        # ========================================
        if act == "query_kb":
            kb_query = action.get("kb_query") or action.get("query") or reason
            if not kb_query:
                return {"result": "KB query requested but no query provided", "outgoing": ""}
            
            logger.info(f"[autopilot] Querying KB: {kb_query}")
            try:
                # Query the knowledge base
                kb_result = query_knowledge_base.invoke({"query": kb_query, "top_k": 3})
                logger.info(f"[autopilot] KB raw result: {kb_result[:500]}")
                
                kb_data = json.loads(kb_result)
                
                # Check for errors
                if "error" in kb_data:
                    logger.error(f"[autopilot] KB query failed: {kb_data['error']}")
                    return {"result": f"KB query failed: {kb_data['error']}", "outgoing": ""}
                
                # Check if we got actual results
                hits = kb_data.get("hits", [])
                if not hits:
                    logger.warning(f"[autopilot] KB returned empty results for: {kb_query}")
                    return {
                        "result": "KB returned no relevant information", 
                        "outgoing": "<p>Thank you for your inquiry. We'll get back to you shortly with detailed information.</p>"
                    }
                
                # Format KB results with detail
                kb_context_parts = []
                for i, r in enumerate(hits[:3], 1):
                    content = r.get('content', '')
                    score = r.get('score', 0)
                    
                    if not content:
                        continue
                        
                    kb_context_parts.append(
                        f"=== Knowledge Base Source {i} (Relevance: {score:.1%}) ===\n{content}\n"
                    )
                
                if not kb_context_parts:
                    logger.warning("[autopilot] KB results had no content")
                    return {
                        "result": "KB results contained no usable content",
                        "outgoing": "<p>Thank you for your inquiry. We'll get back to you shortly with detailed information.</p>"
                    }
                
                kb_context = "\n\n".join(kb_context_parts)
                logger.info(f"[autopilot] KB context length: {len(kb_context)} chars")
                
                # Get email details
                subject = mail.get("subject", "inquiry")
                sender = mail.get("sender_email") or mail.get("from") or "customer"
                
                # Get the original email body
                email_body = ""
                item_id, changekey = _safe_get_id(mail)
                if item_id:
                    try:
                        full_mail_json = fetch_email.invoke({
                            "item_id": item_id, 
                            "changekey": changekey or "", 
                            "include_thread": False
                        })
                        full_mail_data = json.loads(full_mail_json)
                        email_body = full_mail_data.get("body_text", "") or full_mail_data.get("body_html", "")
                        email_body = email_body[:1000]
                    except Exception as e:
                        logger.warning(f"[autopilot] Could not fetch email body: {e}")
                
                # Create detailed prompt for LLM
                reply_prompt = f"""You are Cyfuture's sales representative. Generate a professional email reply using the knowledge base information below.

        
CUSTOMER EMAIL:
Subject: {subject}
From: {sender}
Body: {email_body or "Not available"}

KNOWLEDGE BASE INFORMATION (USE THIS TO ANSWER):
{kb_context}

INSTRUCTIONS:
1. Write a professional great HTML email reply (body only, no <html> wrapper)
2. Directly answer the customer's question using SPECIFIC information from the knowledge base and web search above
3. Include actual pricing numbers, specifications, or details mentioned in the knowledge base and web search
4. Be concise but informative 
5. If pricing is mentioned in KB or web search include it in your response
6. Use a warm, consultative tone
7. Provide helpful links to users if available
8. Make tables and other better ways of data representations whenever possible
9. Sign off as "Best regards,\\nCyfuture Sales Team"

IMPORTANT: Use the actual data from the knowledge base sources above. Don't be generic - cite specific details, numbers, and features.
"""

                # Generate reply using the KB context
                reply_msg = llm.invoke([
                    SystemMessage(content=(
                        "You are an expert sales representative. Your replies must be based ONLY on the "
                        "knowledge base and web search information provided. Include specific details, pricing, and features "
                        "from the knowledge base and web search. Never make up information."
                    )),
                    HumanMessage(content=reply_prompt)
                ])
                
                reply_html = reply_msg.content.strip()
                logger.info(f"[autopilot] Generated reply preview: {reply_html[:300]}")
                
                # Send the reply
                if item_id:
                    try:
                        res = reply_inline.invoke({
                            "item_id": item_id,
                            "changekey": changekey,
                            "body_html": reply_html,
                            "attachments": None
                        })
                        logger.info(f"[autopilot] Reply sent successfully: {res}")
                        return {
                            "result": f"Queried KB and replied: {res}",
                            "outgoing": reply_html,
                            "kb_used": True,
                            "kb_sources": len(hits)
                        }
                    except Exception as e:
                        logger.exception("[autopilot] Reply send failed")
                        return {
                            "result": f"KB query succeeded but reply failed: {e}", 
                            "outgoing": reply_html,
                            "kb_used": True
                        }
                else:
                    return {
                        "result": "KB queried but no item_id to reply to", 
                        "outgoing": reply_html,
                        "kb_used": True
                    }
                    
            except json.JSONDecodeError as e:
                logger.exception(f"[autopilot] KB result JSON parse error")
                return {"result": f"KB query returned invalid JSON: {e}", "outgoing": ""}
            except Exception as e:
                logger.exception("[autopilot] KB query in autopilot failed")
                return {"result": f"KB query error: {e}", "outgoing": ""}
                # ========================================
        # Handle web search action
        # ========================================
        if act == "web_search":
            from agent_tools import web_search
            
            search_query = action.get("query") or action.get("search_query") or reason
            if not search_query:
                return {"result": "Web search requested but no query provided", "outgoing": ""}
            
            logger.info(f"[autopilot] Performing web search: {search_query}")
            try:
                # Perform web search
                search_result = web_search.invoke({"query": search_query})
                logger.info(f"[autopilot] Web search raw result: {search_result[:500]}")
                
                search_data = json.loads(search_result)
                
                # Check for errors
                if "error" in search_data:
                    logger.error(f"[autopilot] Web search failed: {search_data['error']}")
                    return {"result": f"Web search failed: {search_data['error']}", "outgoing": ""}
                
                # Check for warning (no results)
                if "warning" in search_data:
                    logger.warning(f"[autopilot] Web search returned no results: {search_data['warning']}")
                    return {
                        "result": "Web search returned no results", 
                        "outgoing": "<p>Thank you for your inquiry. We'll get back to you shortly with detailed information.</p>"
                    }
                
                # Format web search results
                if isinstance(search_data, list) and len(search_data) > 0:
                    web_context_parts = []
                    for i, result in enumerate(search_data[:3], 1):
                        title = result.get('title', 'No title')
                        snippet = result.get('snippet', '')
                        link = result.get('link', '')
                        
                        if not snippet:
                            continue
                            
                        web_context_parts.append(
                            f"=== Web Search Result {i} ===\n"
                            f"Title: {title}\n"
                            f"Source: {link}\n"
                            f"Content: {snippet}\n"
                        )
                    
                    if not web_context_parts:
                        logger.warning("[autopilot] Web search results had no content")
                        return {
                            "result": "Web search results contained no usable content",
                            "outgoing": "<p>Thank you for your inquiry. We'll get back to you shortly with detailed information.</p>"
                        }
                    
                    web_context = "\n\n".join(web_context_parts)
                    logger.info(f"[autopilot] Web search context length: {len(web_context)} chars")
                    
                    # Get email details
                    subject = mail.get("subject", "inquiry")
                    sender = mail.get("sender_email") or mail.get("from") or "customer"
                    
                    # Get the original email body
                    email_body = ""
                    item_id, changekey = _safe_get_id(mail)
                    if item_id:
                        try:
                            full_mail_json = fetch_email.invoke({
                                "item_id": item_id, 
                                "changekey": changekey or "", 
                                "include_thread": False
                            })
                            full_mail_data = json.loads(full_mail_json)
                            email_body = full_mail_data.get("body_text", "") or full_mail_data.get("body_html", "")
                            email_body = email_body[:1000]
                        except Exception as e:
                            logger.warning(f"[autopilot] Could not fetch email body: {e}")
                    
                    # Create detailed prompt for LLM
                    reply_prompt = f"""You are Cyfuture's sales representative. Generate a professional email reply using the web search information below.
CUSTOMER EMAIL:
Subject: {subject}
From: {sender}
Body: {email_body or "Not available"}

WEB SEARCH INFORMATION (USE THIS TO ANSWER):
{web_context}

INSTRUCTIONS:
1. Write a professional great HTML email reply (body only, no <html> wrapper)
2. Answer the customer's question using information from the knowledge base and web search results above
3. Cite sources by mentioning the website/source naturally in your response
4. Be concise but informative
5. Use a warm, consultative tone
6. Provide helpful links to users if available
7. Make tables and other better ways of data representations whenever possible
8. Sign off as "Best regards,\\nCyfuture Sales Team"

IMPORTANT: Use the actual data from the web search results above. Include source attribution where appropriate.
"""
                    
                    # Generate reply using the web search context
                    reply_msg = llm.invoke([
                        SystemMessage(content=(
                            "You are an expert sales representative. Your replies must be based on the "
                            "web search information provided. Include specific details from the search results "
                            "and cite sources naturally. Never make up information."
                        )),
                        HumanMessage(content=reply_prompt)
                    ])
                    
                    reply_html = reply_msg.content.strip()
                    logger.info(f"[autopilot] Generated reply with web search: {reply_html[:300]}")
                    
                    # Send the reply
                    if item_id:
                        try:
                            res = reply_inline.invoke({
                                "item_id": item_id,
                                "changekey": changekey,
                                "body_html": reply_html,
                                "attachments": None
                            })
                            logger.info(f"[autopilot] Reply sent successfully: {res}")
                            return {
                                "result": f"Performed web search and replied: {res}",
                                "outgoing": reply_html,
                                "web_search_used": True,
                                "sources": len(search_data)
                            }
                        except Exception as e:
                            logger.exception("[autopilot] Reply send failed")
                            return {
                                "result": f"Web search succeeded but reply failed: {e}", 
                                "outgoing": reply_html,
                                "web_search_used": True
                            }
                    else:
                        return {
                            "result": "Web search completed but no item_id to reply to", 
                            "outgoing": reply_html,
                            "web_search_used": True
                        }
                else:
                    return {"result": "Web search returned unexpected format", "outgoing": ""}
                    
            except json.JSONDecodeError as e:
                logger.exception(f"[autopilot] Web search result JSON parse error")
                return {"result": f"Web search returned invalid JSON: {e}", "outgoing": ""}
            except Exception as e:
                logger.exception("[autopilot] Web search in autopilot failed")
                return {"result": f"Web search error: {e}", "outgoing": ""}
        # Rest of existing handle_action code for other actions...
        item_id, changekey = _safe_get_id(mail)

        full_msg = None
        if act in {"reply", "escalate", "mark_read", "follow_up_thread", "schedule_meeting"} and item_id:
            try:
                fetched_json = fetch_email.invoke({"item_id": item_id, "changekey": changekey or "", "include_thread": True})
                full_msg = json.loads(fetched_json)
            except Exception:
                full_msg = None

        if act == "no_action":
            return {"result": "No action (as decided by LLM).", "outgoing": ""}

        if act == "reply":
            reply_source = (action.get("reply_html") or action.get("body_html") or 
                          action.get("reply_body") or action.get("body") or 
                          action.get("response") or "")

            if not item_id:
                return {"result": "Reply skipped: missing item id.", "outgoing": ""}

            if not reply_source:
                reply_text = reason or "Thanks - we'll get back shortly."
                reply_html = ensure_html_from_text(reply_text)
            else:
                if "<" in reply_source and ">" in reply_source:
                    reply_html = reply_source
                else:
                    reply_html = ensure_html_from_text(str(reply_source))

            try:
                res = reply_inline.invoke({"item_id": item_id, "changekey": changekey, "body_html": reply_html, "attachments": None})
                return {"result": f"Replied (item={item_id}): {res}", "outgoing": reply_html}
            except Exception as e:
                return {"result": f"Reply failed: {e}", "outgoing": ""}

        if act == "follow_up":
            body_html = action.get("reply_html") or action.get("body_html") or action.get("followup_body") or ""
            if not body_html and reason:
                body_html = ensure_html_from_text(reason)
            if not body_html:
                body_html = ensure_html_from_text(action.get("body_brief") or "Following up - any update?")

            if item_id:
                try:
                    msg = full_msg or (json.loads(fetch_email.invoke({"item_id": item_id, "changekey": changekey or "", "include_thread": True})) if item_id else {})
                    convo = (msg.get("conversation_id") if isinstance(msg, dict) else None)
                    if convo:
                        res = follow_up_thread_tool.invoke({"item_id": item_id, "changekey": changekey, "body_html": body_html})
                        return {"result": f"In-thread follow-up: {res}", "outgoing": body_html}
                except Exception:
                    pass

            to_email = action.get("followup_email") or action.get("to_email") or (mail.get("sender_email") or mail.get("from") or "")
            if not to_email:
                return {"result": "Follow-up skipped: missing recipient email.", "outgoing": ""}
            raw_subj = action.get("followup_subject") or (full_msg.get("subject") if isinstance(full_msg, dict) else mail.get("subject") or "")
            subj = normalize_followup_subject(raw_subj)
            try:
                res = follow_up_email.invoke({"to_email": to_email, "subject": subj, "body_html": body_html})
                return {"result": f"Follow-up sent to {to_email}: {res}", "outgoing": body_html}
            except Exception as e:
                return {"result": f"Follow-up failed: {e}", "outgoing": ""}

        if act == "follow_up_thread":
            if item_id:
                body_html = action.get("reply_html") or action.get("body_html") or ensure_html_from_text(reason or "Following up in-thread.")
                try:
                    res = follow_up_thread_tool.invoke({"item_id": item_id, "changekey": changekey, "body_html": body_html})
                    return {"result": f"In-thread follow-up: {res}", "outgoing": body_html}
                except Exception as e:
                    return {"result": f"In-thread follow-up failed: {e}", "outgoing": ""}
            return {"result": "Follow-up thread skipped: missing item id.", "outgoing": ""}

        if act == "escalate":
            if not item_id:
                try:
                    res = follow_up_email.invoke({
                        "to_email": os.getenv("HUMAN_SALES_EMAIL"),
                        "subject": f"Escalation: {mail.get('subject','')}",
                        "body_html": f"<p>{reason}</p><pre>{json.dumps(mail)[:1000]}</pre>"
                    })
                    return {"result": f"Escalation (fallback via follow_up) triggered: {res}", "outgoing": ""}
                except Exception as e:
                    return {"result": f"Escalation fallback failed: {e}", "outgoing": ""}
            try:
                res = escalate.invoke({"item_id": item_id, "changekey": changekey, "reason": reason})
                return {"result": f"Escalated item {item_id}: {res}", "outgoing": ""}
            except Exception as e:
                return {"result": f"Escalation failed: {e}", "outgoing": ""}

        if act == "mark_spam":
            if item_id:
                try:
                    res = ignore_spam.invoke({"item_id": item_id, "changekey": changekey})
                    return {"result": f"Marked spam (item={item_id}): {res}", "outgoing": ""}
                except Exception as e:
                    return {"result": f"Mark spam failed: {e}", "outgoing": ""}
            return {"result": "Mark spam skipped: missing item id.", "outgoing": ""}

        if act == "mark_read":
            if item_id:
                try:
                    res = mark_read.invoke({"item_id": item_id, "changekey": changekey, "move_to": action.get("move_to")})
                    return {"result": f"Marked read (item={item_id}): {res}", "outgoing": ""}
                except Exception as e:
                    return {"result": f"Mark read failed: {e}", "outgoing": ""}
            return {"result": "Mark read skipped: missing item id.", "outgoing": ""}

        if act == "schedule_meeting":
            customer = action.get("meeting_email") or (mail.get("sender_email") or mail.get("from") or "")
            start_iso = action.get("meeting_start_iso")
            duration = int(action.get("meeting_duration_minutes", 30))
            if not customer or not start_iso:
                return {"result": "Schedule meeting skipped: missing customer or start time.", "outgoing": ""}
            try:
                res = schedule_with_check.invoke({
                    "customer_email": customer,
                    "start_iso": start_iso,
                    "duration_minutes": duration,
                    "notes": action.get("reason",""),
                    "auto_confirm": True
                })
                return {"result": f"Scheduled meeting for {customer} at {start_iso}: {res}", "outgoing": ""}
            except Exception as e:
                return {"result": f"Schedule meeting failed: {e}", "outgoing": ""}

        return {"result": f"Unhandled action type: {act}", "outgoing": ""}

    except Exception as e:
        return {"result": f"[handle_action error] {e}", "outgoing": ""}