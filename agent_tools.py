# """
# agent_tools.py
# All LangChain tool definitions for the sales agent
# """

# import os
# import json
# import logging
# from typing import Optional, List, Dict, Any
# from datetime import datetime, timezone, timedelta
# from langchain_core.tools import tool
# from langchain_core.messages import HumanMessage, SystemMessage
# from langchain_openai import ChatOpenAI

# # Import EWS functions
# from ews_tools2 import (
#     get_unread_batch,
#     read_email,
#     mark_as_read,
#     ignore_and_mark_read,
#     reply_to_email,
#     send_follow_up,
#     escalate_to_human,
#     schedule_meeting_with_check,
#     send_ical_invite,
#     set_credentials,
#     get_current_time,
#     follow_up_thread,
#     dynamic_mail_fetch,
# )

# # Import RAG functions
# from rag_backend import rag_retriever
# from rag_manager import get_active_collection

# # LLM instance
# llm = ChatOpenAI(
#     api_key=os.getenv("OPENAI_API_KEY", "token-abc123"),
#     base_url=os.getenv("OPENAI_BASE_URL", "http://49.50.117.66:8000/v1"),
#     model=os.getenv("OPENAI_MODEL", "/model"),
#     temperature=0.2,
#     max_tokens=10000,
# )

# # Helper for recording tool calls (imported from app/main)
# try:
#     from main import record_tool_call
# except ImportError:
#     def record_tool_call(tool_name: str, args: dict, result: Any):
#         logging.info(f"[tool-call] {tool_name} args={args}")


# # ============= RAG TOOL =============
# @tool
# def query_knowledge_base(query: str, top_k: int = 3) -> str:
#     """
#     Query the company knowledge base (RAG) for information about policies, pricing, products, and services.
#     Returns JSON string with hits from the active collection.
#     """
#     try:
#         logging.info(f"[query_knowledge_base] Query: {query}, top_k: {top_k}")
        
#         import rag_backend as rb
#         from qdrant_client import QdrantClient
#         import numpy as np
#         from types import SimpleNamespace
        
#         oai_client = getattr(rb, "oai_client", None)
#         EMBEDDING_MODEL = getattr(rb, "EMBEDDING_MODEL", None) or os.getenv("EMBEDDING_MODEL", "bge-m3")
#         qurl = getattr(rb, "QDRANT_URL", None) or os.getenv("QDRANT_URL")
#         qkey = getattr(rb, "QDRANT_KEY", None) or os.getenv("QDRANT_KEY")
        
#         collection_name = get_active_collection()
#         if not collection_name:
#             return json.dumps({"error": "No active collection set. Please activate a collection first."})
        
#         if not qurl:
#             return json.dumps({"error": "Qdrant URL not configured"})
        
#         if oai_client is None:
#             from openai import OpenAI
#             emb_base = getattr(rb, "EMBEDDING_BASE_URL", None) or os.getenv("EMBEDDING_BASE_URL")
#             emb_key = getattr(rb, "RAG_OPENAI_API_KEY", None) or os.getenv("RAG_OPENAI_API_KEY")
#             if not emb_key or not emb_base:
#                 return json.dumps({"error": "No embeddings client available"})
#             oai_client = OpenAI(base_url=emb_base, api_key=emb_key)
        
#         client = QdrantClient(url=qurl, api_key=qkey, prefer_grpc=False, timeout=60)
#         if not client.collection_exists(collection_name):
#             return json.dumps({
#                 "error": f"Collection '{collection_name}' not found",
#                 "hint": "Please upload documents and build the knowledge base first."
#             })
        
#         # Generate embedding
#         emb = oai_client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
#         q_vec = emb.data[0].embedding
        
#         # Search Qdrant
#         search_res = client.search(
#             collection_name=collection_name,
#             query_vector=q_vec,
#             limit=top_k,
#             with_payload=True,
#             with_vectors=False
#         )
        
#         hits = []
#         for item in search_res:
#             payload = getattr(item, "payload", None) or (item.get("payload") if isinstance(item, dict) else {})
#             if payload is None:
#                 payload = {}
            
#             content = ""
#             metadata = {}
#             if isinstance(payload, dict):
#                 content = payload.get("content") or payload.get("text") or ""
#                 metadata = payload.get("metadata") or payload.get("meta") or {}
#             else:
#                 try:
#                     content = payload.content or ""
#                     metadata = payload.metadata or {}
#                 except Exception:
#                     pass
            
#             score = getattr(item, "score", None) or (item.get("score") if isinstance(item, dict) else None)
#             item_id = getattr(item, "id", None) or (item.get("id") if isinstance(item, dict) else None)
            
#             hits.append({
#                 "id": item_id,
#                 "content": content,
#                 "metadata": metadata,
#                 "score": float(score) if score is not None else None
#             })
        
#         response = {"collection": collection_name, "query": query, "top_k": top_k, "hits": hits}
#         record_tool_call("query_knowledge_base", {"query": query, "top_k": top_k}, response)
#         logging.info(f"[query_knowledge_base] Successfully retrieved {len(hits)} hits")
#         return json.dumps(response)
        
#     except Exception as e:
#         logging.exception("[query_knowledge_base] Unexpected error")
#         return json.dumps({"error": f"Unexpected error: {str(e)}"})


# # ============= EMAIL TOOLS =============
# @tool
# def list_unread(batch_size: int = 5) -> str:
#     """Fetch a batch of unread emails from the inbox."""
#     try:
#         data = get_unread_batch(batch_size=batch_size)
#         result = json.dumps({"emails": data}, indent=2)
#         record_tool_call("list_unread", {"batch_size": batch_size}, result)
#         return result
#     except Exception as e:
#         return json.dumps({"error": str(e)})


# @tool
# def dynamic_mail_fetch_tool(
#     sender_name_match_string: Optional[str] = None,
#     sender_mail_match_string: Optional[str] = None,
#     sender_domain_match_string: Optional[str] = None,
#     recipient_name_match_string: Optional[str] = None,
#     recipient_mail_match_string: Optional[str] = None,
#     subject_match_string: Optional[str] = None,
#     body_match_string: Optional[str] = None,
#     read: Optional[bool] = None,
#     has_attachments: Optional[bool] = None,
#     date_from_iso: Optional[str] = None,
#     date_to_iso: Optional[str] = None,
#     fuzzy_threshold: float = 0.70,
#     limit: int = 10,
#     unread: bool = False,
#     batch_size: int = 10,
#     unresponded: bool = False,
#     days: int = 0,
#     only_external: bool = True,
#     params: Optional[str] = None,
# ) -> str:
#     """Flexible mail fetch tool with substring and fuzzy matching."""
#     try:
#         params_obj: Dict[str, Any] = {}
#         if params:
#             try:
#                 if isinstance(params, str):
#                     parsed = json.loads(params)
#                 else:
#                     parsed = dict(params)
#                 if isinstance(parsed, dict):
#                     params_obj.update(parsed)
#             except Exception:
#                 logging.warning("[dynamic_mail_fetch_tool] failed to parse legacy params")

#         def maybe_set(k, v):
#             if v is not None and v != "":
#                 params_obj[k] = v

#         maybe_set("sender_name_match_string", sender_name_match_string)
#         maybe_set("sender_mail_match_string", sender_mail_match_string)
#         maybe_set("sender_domain_match_string", sender_domain_match_string)
#         maybe_set("recipient_name_match_string", recipient_name_match_string)
#         maybe_set("recipient_mail_match_string", recipient_mail_match_string)
#         maybe_set("subject_match_string", subject_match_string)
#         maybe_set("body_match_string", body_match_string)

#         if read is not None:
#             params_obj["read"] = bool(read)
#         if has_attachments is not None:
#             params_obj["has_attachments"] = bool(has_attachments)
#         maybe_set("date_from_iso", date_from_iso)
#         maybe_set("date_to_iso", date_to_iso)
#         params_obj["fuzzy_threshold"] = float(fuzzy_threshold or 0.70)
#         params_obj["limit"] = int(limit or 10)

#         if unread:
#             params_obj["unread"] = True
#             params_obj["batch_size"] = int(batch_size or 10)
#         if unresponded:
#             params_obj["unresponded"] = True
#             params_obj["days"] = int(days or 0)
#             params_obj["only_external"] = bool(only_external)

#         res = dynamic_mail_fetch(strategy="filtered", params=params_obj)
#         result = json.dumps(res, indent=2, default=str)
#         record_tool_call("dynamic_mail_fetch_tool", params_obj, result)
#         return result
#     except Exception as e:
#         logging.exception("[dynamic_mail_fetch_tool] unexpected error")
#         return json.dumps({"error": str(e)})


# @tool
# def fetch_email(item_id: str, changekey: str, include_thread: bool = False) -> str:
#     """Fetch details of a specific email (include thread optionally)."""
#     try:
#         data = read_email(item_id=item_id, changekey=changekey, include_thread=bool(include_thread))
#         result = json.dumps(data, indent=2, default=str)
#         record_tool_call("fetch_email", {"item_id": item_id, "changekey": changekey, "include_thread": include_thread}, result)
#         return result
#     except Exception as e:
#         return json.dumps({"error": str(e)})


# @tool
# def reply_inline(item_id: str, changekey: str, body_html: str, attachments: Optional[List[str]] = None) -> str:
#     """Reply inline to an email with optional attachments (in-thread)."""
#     try:
#         result = reply_to_email(item_id=item_id, changekey=changekey, body_html=body_html, attachments=attachments)
#         record_tool_call("reply_inline", {"item_id": item_id, "changekey": changekey, "body_html": body_html[:200]}, result)
#         return result
#     except Exception as e:
#         return f"[Error] {e}"


# @tool
# def follow_up_thread_tool(item_id: str, changekey: str, body_html: str) -> str:
#     """Reply to the latest message in the thread (in-thread follow-up)."""
#     try:
#         result = follow_up_thread(item_id=item_id, changekey=changekey, body_html=body_html)
#         record_tool_call("follow_up_thread_tool", {"item_id": item_id, "changekey": changekey, "body_html": body_html[:200]}, result)
#         return result
#     except Exception as e:
#         return f"[Error] {e}"


# @tool
# def follow_up_email(to_email: str, subject: str, body_html: str) -> str:
#     """Send a follow-up (new mail)."""
#     try:
#         result = send_follow_up(to_email=to_email, subject=subject, body_html=body_html)
#         record_tool_call("follow_up_email", {"to_email": to_email, "subject": subject, "body_html": body_html[:200]}, result)
#         return result
#     except Exception as e:
#         return f"[Error] {e}"


# @tool
# def send_ics_invite(customer_email: str, start_iso: str, duration_minutes: int = 30, subject: str = "Cyfuture Demo Call", body_html: str = "") -> str:
#     """Send .ics invite fallback."""
#     try:
#         result = send_ical_invite(customer_email=customer_email, start_iso=start_iso, duration_minutes=duration_minutes, subject=subject, body_html=body_html)
#         record_tool_call("send_ics_invite", {"customer_email": customer_email, "start_iso": start_iso}, result)
#         return result
#     except Exception as e:
#         return f"[Error] {e}"


# @tool
# def schedule_with_check(customer_email: str, start_iso: str, duration_minutes: int = 30, notes: str = "", auto_confirm: bool = True) -> str:
#     """Schedule meeting if slot free."""
#     try:
#         result = schedule_meeting_with_check(customer_email=customer_email, start_iso=start_iso, duration_minutes=duration_minutes, notes=notes, auto_send_confirmation=auto_confirm)
#         record_tool_call("schedule_with_check", {"customer_email": customer_email, "start_iso": start_iso}, result)
#         return result
#     except Exception as e:
#         return f"[Error] {e}"


# @tool
# def escalate(item_id: str, changekey: str, reason: str) -> str:
#     """Escalate an email to a human with a given reason."""
#     try:
#         result = escalate_to_human(item_id=item_id, changekey=changekey, reason=reason)
#         record_tool_call("escalate", {"item_id": item_id, "reason": reason}, result)
#         return result
#     except Exception as e:
#         return f"[Error] {e}"


# @tool
# def mark_read(item_id: str, changekey: str, move_to: Optional[str] = None) -> str:
#     """Mark as read."""
#     try:
#         result = mark_as_read(item_id=item_id, changekey=changekey, move_to=move_to)
#         record_tool_call("mark_read", {"item_id": item_id}, result)
#         return result
#     except Exception as e:
#         return f"[Error] {e}"


# @tool
# def ignore_spam(item_id: str, changekey: str) -> str:
#     """Ignore/spam."""
#     try:
#         result = ignore_and_mark_read(item_id=item_id, changekey=changekey)
#         record_tool_call("ignore_spam", {"item_id": item_id}, result)
#         return result
#     except Exception as e:
#         return f"[Error] {e}"


# # ============= UTILITY TOOLS =============
# @tool
# def draft_html(summary_of_reply: str, extra_instructions: str = "") -> str:
#     """Generate a professional HTML email body using the LLM."""
#     prompt = (
#         "Write a professional, concise HTML email body (no <html> wrapper; just body content). "
#         "Tone: warm, helpful, consultative. 3-6 sentences max. "
#         "Add a short closing with name 'Cyfuture Sales Team' and a generic signature. "
#         f"Brief: {summary_of_reply} "
#         f"Extra: {extra_instructions}"
#     )
#     try:
#         msg = llm.invoke([
#             SystemMessage(content="You format excellent business emails in HTML."),
#             HumanMessage(content=prompt),
#         ])
#         html = msg.content.strip()
#         record_tool_call("draft_html", {"summary": summary_of_reply[:200]}, html[:200])
#         return html
#     except Exception as e:
#         return f"[Error] Failed to draft HTML: {e}"


# @tool
# def set_credentials_tool(email: str, password: str, host: str = "") -> str:
#     """Set runtime EWS credentials."""
#     try:
#         result = set_credentials(email=email, password=password, host=host or None)
#         record_tool_call("set_credentials_tool", {"email": email}, result)
#         return result
#     except Exception as e:
#         return f"[Error] {e}"


# @tool
# def current_time(tz_name: str = "Asia/Kolkata") -> str:
#     """Return current time (ISO)."""
#     try:
#         result = get_current_time(tz_name)
#         record_tool_call("current_time", {"tz_name": tz_name}, result)
#         return result
#     except Exception as e:
#         return f"[Error] {e}"


# @tool
# def reply_mail_directly(reasoning: str) -> str:
#     """Produce content intended for direct use as email body content."""
#     logging.info(f"Reply (mail) content generated: {reasoning[:160]}")
#     return reasoning


# @tool
# def inform_user(reasoning: str) -> str:
#     """Return internal reasoning or messages intended to be shown to the human operator / UI."""
#     logging.info(f"Inform user: {reasoning[:160]}")
#     return reasoning


# @tool
# def end_task(summary: str = "Task completed.") -> str:
#     """Mark the current automated task as completed."""
#     logging.info(f"End task: {summary}")
#     return f"[END_TASK] {summary}"


# @tool
# def chat_with_human(query: str, context: str = "") -> str:
#     """Request human input for queries that need manual assistance."""
#     logging.info(f"Human needed: {query}")
#     return f"[HUMAN_INPUT_REQUIRED]: {query}\nContext: {context or 'No additional context.'}\nUI: CHAT_UI"


# @tool
# def auto_handle_email(
#     item_id: str,
#     changekey: str,
#     intent: str,
#     body_html: str = "",
#     body_brief: str = "",
#     to_email: str = "",
#     followup_subject: str = "",
#     meeting_start_iso: str = "",
#     duration_minutes: int = 30,
# ) -> str:
#     """Automatically process an email based on detected intent."""
#     try:
#         from ews_tools2 import find_free_slots
#         from action_handlers import normalize_followup_subject, ensure_html_from_text
        
#         allowed = {"acknowledge", "follow_up", "propose_meeting", "mark_junk", "follow_up_thread"}
#         if intent not in allowed:
#             return f"[Error] Unknown intent: {intent}. Allowed: {allowed}"

#         def ensure_html(brief: str, html: str) -> str:
#             if html:
#                 return html
#             if brief:
#                 prompt = (
#                     "Write a short, warm, professional HTML reply (3-5 sentences). "
#                     "No <html> wrapper; just body. End with 'Cyfuture Sales Team'. "
#                     "Brief: " + brief
#                 )
#                 msg = llm.invoke([
#                     SystemMessage(content="You write crisp HTML replies."),
#                     HumanMessage(content=prompt),
#                 ])
#                 return msg.content.strip()
#             return ""

#         if intent == "mark_junk":
#             return ignore_and_mark_read(item_id=item_id, changekey=changekey)

#         if intent == "acknowledge":
#             html = ensure_html(body_brief, body_html)
#             if not html:
#                 return "[Error] No content to send. Provide body_brief or body_html."
#             return reply_to_email(item_id=item_id, changekey=changekey, body_html=html, attachments=None)

#         if intent == "follow_up" or intent == "follow_up_thread":
#             html = ensure_html(body_brief, body_html)
#             if not html:
#                 html = ensure_html(f"Following up - {body_brief or 'Do you have an update?'}", "")
#             if intent == "follow_up_thread":
#                 return follow_up_thread(item_id=item_id, changekey=changekey, body_html=html)
#             try:
#                 msg = read_email(item_id=item_id, changekey=changekey, include_thread=True)
#                 convo = msg.get("conversation_id")
#                 if convo:
#                     return follow_up_thread(item_id=item_id, changekey=changekey, body_html=html)
#             except Exception:
#                 pass
#             target_email = to_email or (msg.get("sender", {}) or {}).get("email", "") if isinstance(msg, dict) else ""
#             if not target_email:
#                 return "[Error] Missing to_email for follow_up."
#             subj = followup_subject or normalize_followup_subject(msg.get("subject","") if isinstance(msg, dict) else "Follow-up")
#             return send_follow_up(to_email=target_email, subject=subj, body_html=html)

#         if intent == "propose_meeting":
#             if not meeting_start_iso:
#                 start_iso = datetime.now(timezone.utc).isoformat()
#                 slots = find_free_slots(start_iso=start_iso, days=3)
#                 return json.dumps({"error": "No meeting_start_iso provided", "suggested_slots": slots})
#             msg = read_email(item_id=item_id, changekey=changekey, include_thread=False)
#             customer_email = (msg.get("sender", {}) or {}).get("email", "") or to_email
#             if not customer_email:
#                 return "[Error] Could not infer customer email from thread."
#             return schedule_meeting_with_check(customer_email=customer_email, start_iso=meeting_start_iso, duration_minutes=duration_minutes, notes="Cyfuture Demo Call", auto_send_confirmation=True)

#         return "[Error] Unhandled intent"
#     except Exception as e:
#         return f"[Error] auto_handle_email failed: {e}"

# # Add these @tool functions to agent_tools.py

# from ews_tools2 import send_new_email, forward_email, forward_email_with_attachments

# @tool
# def send_mail(
#     to_email: str,
#     subject: str,
#     body_html: str,
#     cc_emails: Optional[str] = None,
#     bcc_emails: Optional[str] = None,
#     attachments: Optional[str] = None,
#     importance: str = "Normal"
# ) -> str:
#     """
#     Send a new email message (not a reply).
    
#     Args:
#         to_email: Primary recipient email address
#         subject: Email subject line
#         body_html: HTML body content
#         cc_emails: Comma-separated CC email addresses (optional)
#         bcc_emails: Comma-separated BCC email addresses (optional)
#         attachments: Comma-separated file paths to attach (optional)
#         importance: Email importance - 'Low', 'Normal', or 'High' (default: Normal)
    
#     Returns:
#         Status message indicating success or failure
    
#     Example:
#         send_mail(
#             to_email="customer@example.com",
#             subject="Product Demo Invitation",
#             body_html="<p>Hello, would you like a demo?</p>",
#             cc_emails="manager@company.com",
#             importance="High"
#         )
#     """
#     try:
#         # Parse comma-separated lists
#         cc_list = [e.strip() for e in cc_emails.split(",")] if cc_emails else None
#         bcc_list = [e.strip() for e in bcc_emails.split(",")] if bcc_emails else None
#         attach_list = [p.strip() for p in attachments.split(",")] if attachments else None
        
#         result = send_new_email(
#             to_email=to_email,
#             subject=subject,
#             body_html=body_html,
#             cc_emails=cc_list,
#             bcc_emails=bcc_list,
#             attachments=attach_list,
#             importance=importance or "Normal"
#         )
        
#         record_tool_call("send_mail", {
#             "to_email": to_email,
#             "subject": subject,
#             "cc_emails": cc_emails,
#             "importance": importance
#         }, result)
        
#         return result
#     except Exception as e:
#         return f"[Error] send_mail failed: {e}"


# @tool
# def forward_mail(
#     item_id: str,
#     changekey: str,
#     to_email: str,
#     forward_comment: str = "",
#     cc_emails: Optional[str] = None,
#     bcc_emails: Optional[str] = None,
#     include_attachments: bool = True
# ) -> str:
#     """
#     Forward an existing email to one or more recipients.
    
#     Args:
#         item_id: ID of the email to forward
#         changekey: Changekey of the email (use empty string if unknown)
#         to_email: Primary recipient email address
#         forward_comment: Optional comment to add at the top (plain text)
#         cc_emails: Comma-separated CC email addresses (optional)
#         bcc_emails: Comma-separated BCC email addresses (optional)
#         include_attachments: Whether to include original attachments (default: True)
    
#     Returns:
#         Status message indicating success or failure
    
#     Example:
#         forward_mail(
#             item_id="AAMkAD...",
#             changekey="CQA...",
#             to_email="colleague@company.com",
#             forward_comment="FYI - please review this inquiry",
#             cc_emails="manager@company.com"
#         )
#     """
#     try:
#         # Parse comma-separated lists
#         cc_list = [e.strip() for e in cc_emails.split(",")] if cc_emails else None
#         bcc_list = [e.strip() for e in bcc_emails.split(",")] if bcc_emails else None
        
#         if include_attachments:
#             result = forward_email_with_attachments(
#                 item_id=item_id,
#                 changekey=changekey or "",
#                 to_email=to_email,
#                 forward_comment=forward_comment or "",
#                 cc_emails=cc_list
#             )
#         else:
#             result = forward_email(
#                 item_id=item_id,
#                 changekey=changekey or "",
#                 to_email=to_email,
#                 forward_comment=forward_comment or "",
#                 cc_emails=cc_list,
#                 bcc_emails=bcc_list
#             )
        
#         record_tool_call("forward_mail", {
#             "item_id": item_id,
#             "to_email": to_email,
#             "forward_comment": forward_comment[:100],
#             "include_attachments": include_attachments
#         }, result)
        
#         return result
#     except Exception as e:
#         return f"[Error] forward_mail failed: {e}"


# @tool
# def forward_mail_with_note(
#     item_id: str,
#     changekey: str,
#     to_email: str,
#     note: str,
#     cc_emails: Optional[str] = None
# ) -> str:
#     """
#     Forward an email with a custom note/comment. Simplified version of forward_mail.
    
#     Args:
#         item_id: ID of the email to forward
#         changekey: Changekey of the email
#         to_email: Recipient email address
#         note: Your comment/note to add at the top of the forwarded email
#         cc_emails: Optional comma-separated CC email addresses
    
#     Returns:
#         Status message
    
#     Example:
#         forward_mail_with_note(
#             item_id="AAMkAD...",
#             changekey="CQA...",
#             to_email="sales-team@company.com",
#             note="This customer is interested in our enterprise package. Please follow up.",
#             cc_emails="manager@company.com"
#         )
#     """
#     return forward_mail(
#         item_id=item_id,
#         changekey=changekey,
#         to_email=to_email,
#         forward_comment=note,
#         cc_emails=cc_emails,
#         include_attachments=True
#     )


# # Update ALL_TOOLS list at the end of agent_tools.py

"""
agent_tools.py
All LangChain tool definitions for the sales agent
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from duckduckgo_search import DDGS
# Import EWS functions
from ews_tools2 import (
    get_unread_batch,
    read_email,
    mark_as_read,
    forward_email,
    ignore_and_mark_read,
    reply_to_email,
    send_follow_up,
    escalate_to_human,
    schedule_meeting_with_check,
    send_ical_invite,
    set_credentials,
    get_current_time,
    follow_up_thread,
    dynamic_mail_fetch,
)

# Import RAG functions
from rag_backend import rag_retriever
from rag_manager import get_active_collection

# LLM instance
llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "token-abc123"),
    base_url=os.getenv("OPENAI_BASE_URL", "http://49.50.117.66:8000/v1"),
    model=os.getenv("OPENAI_MODEL", "/model"),
    temperature=0.2,
    max_tokens=2048,
)

# Helper for recording tool calls (imported from app/main)
try:
    from main import record_tool_call
except ImportError:
    def record_tool_call(tool_name: str, args: dict, result: Any):
        logging.info(f"[tool-call] {tool_name} args={args}")


# ============= RAG TOOL =============
# @tool
# def query_knowledge_base(query: str, top_k: int = 3, collection_name: Optional[str] = None) -> str:
#     """
#     Query the company knowledge base (RAG) across all active collections.
#     Returns combined results from all active collections, ranked by relevance.
    
#     Args:
#         query: The question or search query
#         top_k: Number of top relevant documents per collection (default: 3)
#         collection_name: Optional specific collection to query (otherwise queries all active)
    
#     Returns:
#         JSON string with hits from all queried collections
#     """
#     try:
#         logging.info(f"[query_knowledge_base] Query: {query}, top_k: {top_k}")
        
#         import rag_backend as rb
#         from qdrant_client import QdrantClient
#         import numpy as np
#         from types import SimpleNamespace
#         from rag_manager import get_active_collections, is_collection_active
        
#         oai_client = getattr(rb, "oai_client", None)
#         EMBEDDING_MODEL = getattr(rb, "EMBEDDING_MODEL", None) or os.getenv("EMBEDDING_MODEL", "bge-m3")
#         qurl = getattr(rb, "QDRANT_URL", None) or os.getenv("QDRANT_URL")
#         qkey = getattr(rb, "QDRANT_KEY", None) or os.getenv("QDRANT_KEY")
        
#         # Determine which collections to query
#         if collection_name:
#             # Query specific collection
#             collections_to_query = [collection_name]
#         else:
#             # Query all active collections
#             collections_to_query = get_active_collections()
#             if not collections_to_query:
#                 return json.dumps({
#                     "error": "No active collections set. Please activate at least one collection first.",
#                     "hint": "Use the collection management UI to activate collections."
#                 })
        
#         logging.info(f"[query_knowledge_base] Querying collections: {collections_to_query}")
        
#         if not qurl:
#             return json.dumps({"error": "Qdrant URL not configured"})
        
#         if oai_client is None:
#             from openai import OpenAI
#             emb_base = getattr(rb, "EMBEDDING_BASE_URL", None) or os.getenv("EMBEDDING_BASE_URL")
#             emb_key = getattr(rb, "RAG_OPENAI_API_KEY", None) or os.getenv("RAG_OPENAI_API_KEY")
#             if not emb_key or not emb_base:
#                 return json.dumps({"error": "No embeddings client available"})
#             oai_client = OpenAI(base_url=emb_base, api_key=emb_key)
        
#         client = QdrantClient(url=qurl, api_key=qkey, prefer_grpc=False, timeout=60)
        
#         # Generate embedding once for all collections
#         try:
#             emb = oai_client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
#             q_vec = emb.data[0].embedding
#         except Exception as e:
#             logging.exception("[query_knowledge_base] Embedding generation failed")
#             return json.dumps({"error": f"Embedding generation failed: {str(e)}"})
        
#         # Query each collection
#         all_hits = []
#         collections_queried = []
        
#         for coll_name in collections_to_query:
#             try:
#                 if not client.collection_exists(coll_name):
#                     logging.warning(f"[query_knowledge_base] Collection not found: {coll_name}")
#                     continue
                
#                 search_res = client.search(
#                     collection_name=coll_name,
#                     query_vector=q_vec,
#                     limit=top_k,
#                     with_payload=True,
#                     with_vectors=False
#                 )
                
#                 # Process results
#                 for item in search_res:
#                     payload = getattr(item, "payload", None) or (item.get("payload") if isinstance(item, dict) else {})
#                     if payload is None:
#                         payload = {}
                    
#                     content = ""
#                     metadata = {}
#                     if isinstance(payload, dict):
#                         content = payload.get("content") or payload.get("text") or ""
#                         metadata = payload.get("metadata") or payload.get("meta") or {}
#                     else:
#                         try:
#                             content = payload.content or ""
#                             metadata = payload.metadata or {}
#                         except Exception:
#                             pass
                    
#                     score = getattr(item, "score", None) or (item.get("score") if isinstance(item, dict) else None)
#                     item_id = getattr(item, "id", None) or (item.get("id") if isinstance(item, dict) else None)
                    
#                     all_hits.append({
#                         "id": item_id,
#                         "content": content,
#                         "metadata": metadata,
#                         "score": float(score) if score is not None else None,
#                         "collection": coll_name  # Track which collection this came from
#                     })
                
#                 collections_queried.append(coll_name)
#                 logging.info(f"[query_knowledge_base] Retrieved {len(search_res)} hits from {coll_name}")
                
#             except Exception as e:
#                 logging.exception(f"[query_knowledge_base] Error querying collection {coll_name}")
#                 continue
        
#         # Sort all results by score (highest first)
#         all_hits.sort(key=lambda x: x.get("score", 0), reverse=True)
        
#         # Limit to top results across all collections
#         max_total_results = top_k * len(collections_queried) if len(collections_queried) > 1 else top_k
#         all_hits = all_hits[:max_total_results]
        
#         response = {
#             "query": query,
#             "collections_queried": collections_queried,
#             "total_collections": len(collections_queried),
#             "total_hits": len(all_hits),
#             "top_k_per_collection": top_k,
#             "hits": all_hits
#         }
        
#         record_tool_call("query_knowledge_base", {
#             "query": query, 
#             "top_k": top_k,
#             "collections": collections_queried
#         }, response)
        
#         logging.info(f"[query_knowledge_base] Successfully retrieved {len(all_hits)} total hits from {len(collections_queried)} collections")
#         return json.dumps(response)
        
#     except Exception as e:
#         logging.exception("[query_knowledge_base] Unexpected error")
#         return json.dumps({"error": f"Unexpected error: {str(e)}"})
@tool
def query_knowledge_base(query: str, top_k: int = 3) -> str:
    """
    Query the company knowledge base (RAG) for information about policies, pricing, products, and services.
    Returns JSON string with hits from the active collection.
    """
    try:
        logging.info(f"[query_knowledge_base] Query: {query}, top_k: {top_k}")
        
        import rag_backend as rb
        from qdrant_client import QdrantClient
        import numpy as np
        from types import SimpleNamespace
        from rag_manager import get_active_collection

        oai_client = getattr(rb, "oai_client", None)
        EMBEDDING_MODEL = getattr(rb, "EMBEDDING_MODEL", None) or os.getenv("EMBEDDING_MODEL", "bge-m3")
        qurl = getattr(rb, "QDRANT_URL", None) or os.getenv("QDRANT_URL")
        qkey = getattr(rb, "QDRANT_KEY", None) or os.getenv("QDRANT_KEY")
        
        collection_name = get_active_collection()
        if not collection_name:
            return json.dumps({"error": "No active collection set. Please activate a collection first."})
        
        if not qurl:
            return json.dumps({"error": "Qdrant URL not configured"})
        
        if oai_client is None:
            from openai import OpenAI
            emb_base = getattr(rb, "EMBEDDING_BASE_URL", None) or os.getenv("EMBEDDING_BASE_URL")
            emb_key = getattr(rb, "RAG_OPENAI_API_KEY", None) or os.getenv("RAG_OPENAI_API_KEY")
            if not emb_key or not emb_base:
                return json.dumps({"error": "No embeddings client available"})
            oai_client = OpenAI(base_url=emb_base, api_key=emb_key)
        
        client = QdrantClient(url=qurl, api_key=qkey, prefer_grpc=False, timeout=60)
        if not client.collection_exists(collection_name):
            return json.dumps({
                "error": f"Collection '{collection_name}' not found",
                "hint": "Please upload documents and build the knowledge base first."
            })
        
        # Generate embedding
        emb = oai_client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
        q_vec = emb.data[0].embedding
        
        # Search Qdrant
        search_res = client.search(
            collection_name=collection_name,
            query_vector=q_vec,
            limit=top_k,
            with_payload=True,
            with_vectors=False
        )
        
        hits = []
        for item in search_res:
            payload = getattr(item, "payload", None) or (item.get("payload") if isinstance(item, dict) else {})
            if payload is None:
                payload = {}
            
            content = ""
            metadata = {}
            if isinstance(payload, dict):
                content = payload.get("content") or payload.get("text") or ""
                metadata = payload.get("metadata") or payload.get("meta") or {}
            else:
                try:
                    content = payload.content or ""
                    metadata = payload.metadata or {}
                except Exception:
                    pass
            
            score = getattr(item, "score", None) or (item.get("score") if isinstance(item, dict) else None)
            item_id = getattr(item, "id", None) or (item.get("id") if isinstance(item, dict) else None)
            
            hits.append({
                "id": item_id,
                "content": content,
                "metadata": metadata,
                "score": float(score) if score is not None else None
            })
        
        response = {"collection": collection_name, "query": query, "top_k": top_k, "hits": hits}
        record_tool_call("query_knowledge_base", {"query": query, "top_k": top_k}, response)
        logging.info(f"[query_knowledge_base] Successfully retrieved {len(hits)} hits")
        return json.dumps(response)
        
    except Exception as e:
        logging.exception("[query_knowledge_base] Unexpected error")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})


# ============= EMAIL TOOLS =============
@tool
def list_unread(batch_size: int = 5) -> str:
    """Fetch a batch of unread emails from the inbox."""
    try:
        data = get_unread_batch(batch_size=batch_size)
        result = json.dumps({"emails": data}, indent=2)
        record_tool_call("list_unread", {"batch_size": batch_size}, result)
        return result
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def dynamic_mail_fetch_tool(
    sender_name_match_string: Optional[str] = None,
    sender_mail_match_string: Optional[str] = None,
    sender_domain_match_string: Optional[str] = None,
    recipient_name_match_string: Optional[str] = None,
    recipient_mail_match_string: Optional[str] = None,
    subject_match_string: Optional[str] = None,
    body_match_string: Optional[str] = None,
    read: Optional[bool] = None,
    has_attachments: Optional[bool] = None,
    date_from_iso: Optional[str] = None,
    date_to_iso: Optional[str] = None,
    fuzzy_threshold: float = 0.70,
    limit: int = 10,
    unread: bool = False,
    batch_size: int = 10,
    unresponded: bool = False,
    days: int = 0,
    only_external: bool = True,
    params: Optional[str] = None,
) -> str:
    """Flexible mail fetch tool with substring and fuzzy matching."""
    try:
        params_obj: Dict[str, Any] = {}
        if params:
            try:
                if isinstance(params, str):
                    parsed = json.loads(params)
                else:
                    parsed = dict(params)
                if isinstance(parsed, dict):
                    params_obj.update(parsed)
            except Exception:
                logging.warning("[dynamic_mail_fetch_tool] failed to parse legacy params")

        def maybe_set(k, v):
            if v is not None and v != "":
                params_obj[k] = v

        maybe_set("sender_name_match_string", sender_name_match_string)
        maybe_set("sender_mail_match_string", sender_mail_match_string)
        maybe_set("sender_domain_match_string", sender_domain_match_string)
        maybe_set("recipient_name_match_string", recipient_name_match_string)
        maybe_set("recipient_mail_match_string", recipient_mail_match_string)
        maybe_set("subject_match_string", subject_match_string)
        maybe_set("body_match_string", body_match_string)

        if read is not None:
            params_obj["read"] = bool(read)
        if has_attachments is not None:
            params_obj["has_attachments"] = bool(has_attachments)
        maybe_set("date_from_iso", date_from_iso)
        maybe_set("date_to_iso", date_to_iso)
        params_obj["fuzzy_threshold"] = float(fuzzy_threshold or 0.70)
        params_obj["limit"] = int(limit or 10)

        if unread:
            params_obj["unread"] = True
            params_obj["batch_size"] = int(batch_size or 10)
        if unresponded:
            params_obj["unresponded"] = True
            params_obj["days"] = int(days or 0)
            params_obj["only_external"] = bool(only_external)

        res = dynamic_mail_fetch(strategy="filtered", params=params_obj)
        result = json.dumps(res, indent=2, default=str)
        record_tool_call("dynamic_mail_fetch_tool", params_obj, result)
        return result
    except Exception as e:
        logging.exception("[dynamic_mail_fetch_tool] unexpected error")
        return json.dumps({"error": str(e)})
    
@tool
def fetch_email(item_id: str, changekey: str = "", include_thread: bool = False) -> str:
    """Fetch details of a specific email (optionally include thread). 
    
    Args:
        item_id: The email ID (required)
        changekey: The email changekey (optional, can be empty string if unknown)
        include_thread: Whether to include conversation thread (default: False)
    
    Note: If you only have item_id, use empty string for changekey.
    """
    try:
        data = read_email(item_id=item_id, changekey=changekey, include_thread=bool(include_thread))
        result = json.dumps(data, indent=2, default=str)
        record_tool_call("fetch_email", {"item_id": item_id, "changekey": changekey, "include_thread": include_thread}, result)
        return result
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def reply_inline(
    item_id: str, 
    changekey: str, 
    body_html: str,
    cc_recipients: Optional[List[str]] = None,
    bcc_recipients: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    save_as_draft: bool = False
) -> str:
    """
    Reply inline to an email with optional CC/BCC recipients and attachments (in-thread).
    
    Args:
        item_id: Email item ID
        changekey: Email changekey
        body_html: HTML body for reply
        cc_recipients: Optional list of CC email addresses to include in reply
        bcc_recipients: Optional list of BCC email addresses to include in reply
        attachments: Optional file paths to attach
        save_as_draft: If True, save as draft instead of sending
    
    Examples:
        # Simple reply
        reply_inline(item_id="...", changekey="...", body_html="<p>Thank you!</p>")
        
        # Reply with CC to keep recipients in loop
        reply_inline(
            item_id="...", 
            changekey="...", 
            body_html="<p>Response</p>",
            cc_recipients=["colleague@company.com", "manager@company.com"]
        )
    """
    try:
        result = reply_to_email(
            item_id=item_id, 
            changekey=changekey, 
            body_html=body_html,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            attachments=attachments,
            save_as_draft=save_as_draft
        )
        record_tool_call("reply_inline", {
            "item_id": item_id, 
            "changekey": changekey, 
            "body_html": body_html[:200],
            "has_cc": bool(cc_recipients),
            "has_bcc": bool(bcc_recipients),
            "save_as_draft": save_as_draft
        }, result)
        return result
    except Exception as e:
        return f"[Error] {e}"

@tool
def follow_up_thread_tool(item_id: str, changekey: str, body_html: str) -> str:
    """Reply to the latest message in the thread (in-thread follow-up)."""
    try:
        result = follow_up_thread(item_id=item_id, changekey=changekey, body_html=body_html)
        record_tool_call("follow_up_thread_tool", {"item_id": item_id, "changekey": changekey, "body_html": body_html[:200]}, result)
        return result
    except Exception as e:
        return f"[Error] {e}"

@tool
def follow_up_email(
    to_email: str, 
    subject: str, 
    body_html: str,
    save_as_draft: bool = False
) -> str:
    """
    Send a follow-up (new mail) or save as draft.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        body_html: HTML body
        save_as_draft: If True, save as draft instead of sending
    """
    try:
        result = send_follow_up(
            to_email=to_email, 
            subject=subject, 
            body_html=body_html,
            save_as_draft=save_as_draft
        )
        record_tool_call("follow_up_email", {
            "to_email": to_email, 
            "subject": subject, 
            "body_html": body_html[:200],
            "save_as_draft": save_as_draft
        }, result)
        return result
    except Exception as e:
        return f"[Error] {e}"

@tool
def send_ics_invite(customer_email: str, start_iso: str, duration_minutes: int = 30, subject: str = "Cyfuture Demo Call", body_html: str = "") -> str:
    """Send .ics invite fallback."""
    try:
        result = send_ical_invite(customer_email=customer_email, start_iso=start_iso, duration_minutes=duration_minutes, subject=subject, body_html=body_html)
        record_tool_call("send_ics_invite", {"customer_email": customer_email, "start_iso": start_iso}, result)
        return result
    except Exception as e:
        return f"[Error] {e}"


@tool
def schedule_with_check(customer_email: str, start_iso: str, duration_minutes: int = 30, notes: str = "", auto_confirm: bool = True) -> str:
    """Schedule meeting if slot free."""
    try:
        result = schedule_meeting_with_check(customer_email=customer_email, start_iso=start_iso, duration_minutes=duration_minutes, notes=notes, auto_send_confirmation=auto_confirm)
        record_tool_call("schedule_with_check", {"customer_email": customer_email, "start_iso": start_iso}, result)
        return result
    except Exception as e:
        return f"[Error] {e}"


@tool
def escalate(item_id: str, changekey: str, reason: str) -> str:
    """Escalate an email to a human with a given reason."""
    try:
        result = escalate_to_human(item_id=item_id, changekey=changekey, reason=reason)
        record_tool_call("escalate", {"item_id": item_id, "reason": reason}, result)
        return result
    except Exception as e:
        return f"[Error] {e}"


@tool
def mark_read(item_id: str, changekey: str, move_to: Optional[str] = None) -> str:
    """Mark as read."""
    try:
        result = mark_as_read(item_id=item_id, changekey=changekey, move_to=move_to)
        record_tool_call("mark_read", {"item_id": item_id}, result)
        return result
    except Exception as e:
        return f"[Error] {e}"


@tool
def ignore_spam(item_id: str, changekey: str) -> str:
    """Ignore/spam."""
    try:
        result = ignore_and_mark_read(item_id=item_id, changekey=changekey)
        record_tool_call("ignore_spam", {"item_id": item_id}, result)
        return result
    except Exception as e:
        return f"[Error] {e}"


# ============= UTILITY TOOLS =============
@tool
def draft_html(summary_of_reply: str, extra_instructions: str = "") -> str:
    """Generate a professional HTML email body using the LLM."""
    prompt = (
        "Write a professional, concise HTML email body (no <html> wrapper; just body content). "
        "Tone: warm, helpful, consultative. 3-6 sentences max. "
        "Add a short closing with name 'Cyfuture Sales Team' and a generic signature. "
        f"Brief: {summary_of_reply} "
        f"Extra: {extra_instructions}"
    )
    try:
        msg = llm.invoke([
            SystemMessage(content="You format excellent business emails in HTML."),
            HumanMessage(content=prompt),
        ])
        html = msg.content.strip()
        record_tool_call("draft_html", {"summary": summary_of_reply[:200]}, html[:200])
        return html
    except Exception as e:
        return f"[Error] Failed to draft HTML: {e}"


@tool
def set_credentials_tool(email: str, password: str, host: str = "") -> str:
    """Set runtime EWS credentials."""
    try:
        result = set_credentials(email=email, password=password, host=host or None)
        record_tool_call("set_credentials_tool", {"email": email}, result)
        return result
    except Exception as e:
        return f"[Error] {e}"


@tool
def current_time(tz_name: str = "Asia/Kolkata") -> str:
    """Return current time (ISO)."""
    try:
        result = get_current_time(tz_name)
        record_tool_call("current_time", {"tz_name": tz_name}, result)
        return result
    except Exception as e:
        return f"[Error] {e}"


@tool
def reply_mail_directly(reasoning: str) -> str:
    """Produce content intended for direct use as email body content."""
    logging.info(f"Reply (mail) content generated: {reasoning[:160]}")
    return reasoning


@tool
def inform_user(reasoning: str) -> str:
    """Return internal reasoning intended to be shown to the human operator / UI."""
    logging.info(f"Inform user: {reasoning[:160]}")
    return reasoning


@tool
def end_task(summary: str = "Task completed.") -> str:
    """Mark the current automated task as completed."""
    logging.info(f"End task: {summary}")
    return f"[END_TASK] {summary}"


@tool
def chat_with_human(query: str, context: str = "") -> str:
    """Request human input for queries that need manual assistance."""
    logging.info(f"Human needed: {query}")
    return f"[HUMAN_INPUT_REQUIRED]: {query}\nContext: {context or 'No additional context.'}\nUI: CHAT_UI"


@tool
def auto_handle_email(
    item_id: str,
    changekey: str,
    intent: str,
    body_html: str = "",
    body_brief: str = "",
    to_email: str = "",
    followup_subject: str = "",
    meeting_start_iso: str = "",
    duration_minutes: int = 30,
) -> str:
    """Automatically process an email based on detected intent."""
    try:
        from ews_tools2 import find_free_slots
        from action_handlers import normalize_followup_subject, ensure_html_from_text
        
        allowed = {"acknowledge", "follow_up", "propose_meeting", "mark_junk", "follow_up_thread"}
        if intent not in allowed:
            return f"[Error] Unknown intent: {intent}. Allowed: {allowed}"

        def ensure_html(brief: str, html: str) -> str:
            if html:
                return html
            if brief:
                prompt = (
                    "Write a short, warm, professional HTML reply (3-5 sentences). "
                    "No <html> wrapper; just body. End with 'Cyfuture Sales Team'. "
                    "Brief: " + brief
                )
                msg = llm.invoke([
                    SystemMessage(content="You write crisp HTML replies."),
                    HumanMessage(content=prompt),
                ])
                return msg.content.strip()
            return ""

        if intent == "mark_junk":
            return ignore_and_mark_read(item_id=item_id, changekey=changekey)

        if intent == "acknowledge":
            html = ensure_html(body_brief, body_html)
            if not html:
                return "[Error] No content to send. Provide body_brief or body_html."
            return reply_to_email(item_id=item_id, changekey=changekey, body_html=html, attachments=None)

        if intent == "follow_up" or intent == "follow_up_thread":
            html = ensure_html(body_brief, body_html)
            if not html:
                html = ensure_html(f"Following up - {body_brief or 'Do you have an update?'}", "")
            if intent == "follow_up_thread":
                return follow_up_thread(item_id=item_id, changekey=changekey, body_html=html)
            try:
                msg = read_email(item_id=item_id, changekey=changekey, include_thread=True)
                convo = msg.get("conversation_id")
                if convo:
                    return follow_up_thread(item_id=item_id, changekey=changekey, body_html=html)
            except Exception:
                pass
            target_email = to_email or (msg.get("sender", {}) or {}).get("email", "") if isinstance(msg, dict) else ""
            if not target_email:
                return "[Error] Missing to_email for follow_up."
            subj = followup_subject or normalize_followup_subject(msg.get("subject","") if isinstance(msg, dict) else "Follow-up")
            return send_follow_up(to_email=target_email, subject=subj, body_html=html)

        if intent == "propose_meeting":
            if not meeting_start_iso:
                start_iso = datetime.now(timezone.utc).isoformat()
                slots = find_free_slots(start_iso=start_iso, days=3)
                return json.dumps({"error": "No meeting_start_iso provided", "suggested_slots": slots})
            msg = read_email(item_id=item_id, changekey=changekey, include_thread=False)
            customer_email = (msg.get("sender", {}) or {}).get("email", "") or to_email
            if not customer_email:
                return "[Error] Could not infer customer email from thread."
            return schedule_meeting_with_check(customer_email=customer_email, start_iso=meeting_start_iso, duration_minutes=duration_minutes, notes="Cyfuture Demo Call", auto_send_confirmation=True)

        return "[Error] Unhandled intent"
    except Exception as e:
        return f"[Error] auto_handle_email failed: {e}"

@tool
def list_unread_paginated(limit: int = 100, max_pages: int = 10) -> str:
    """
    Fetch all unread emails with pagination support.
    
    Args:
        limit: Total maximum emails to fetch
        max_pages: Maximum number of pages to fetch (safety limit)
    
    Returns:
        JSON with all unread emails
    """
    try:
        all_unread = []
        page_size = 50
        pages_fetched = 0
        
        while len(all_unread) < limit and pages_fetched < max_pages:
            try:
                # Fetch batch
                batch_data = get_unread_batch(batch_size=page_size)
                if not batch_data:
                    break
                
                # Add to results
                all_unread.extend(batch_data)
                pages_fetched += 1
                
                # If we got fewer than page_size, we've reached the end
                if len(batch_data) < page_size:
                    break
                    
            except Exception as e:
                logging.error(f"[list_unread_paginated] Page {pages_fetched} failed: {e}")
                break
        
        # Trim to limit
        all_unread = all_unread[:limit]
        
        result = json.dumps({
            "total_fetched": len(all_unread),
            "pages": pages_fetched,
            "emails": all_unread
        }, indent=2)
        
        record_tool_call("list_unread_paginated", {"limit": limit, "max_pages": max_pages}, result)
        return result
        
    except Exception as e:
        return json.dumps({"error": str(e)})

# # Export all tools as a list
# ALL_TOOLS = [
#     query_knowledge_base,
#     # list_unread,
#     list_unread_paginated,
#     dynamic_mail_fetch_tool,
#     fetch_email,
#     reply_inline,
#     follow_up_thread_tool,
#     follow_up_email,
#     send_ics_invite,
#     schedule_with_check,
#     draft_html,
#     auto_handle_email,
#     reply_mail_directly,
#     inform_user,
#     set_credentials_tool,
#     current_time,
#     end_task,
#     chat_with_human,
#     escalate,
#     mark_read,
#     ignore_spam,
# ]

# ADD THIS TO agent_tools.py (in EMAIL TOOLS section, after follow_up_email)

from ews_tools2 import send_mail

@tool
def send_mail_tool(
    to_email: str,
    subject: str,
    body_html: str,
    cc_recipients: Optional[List[str]] = None,
    bcc_recipients: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    importance: str = "Normal"
) -> str:
    """
    Send a new standalone email (not in-thread).
    
    Args:
        to_email: Recipient email (required)
        subject: Subject line (required)
        body_html: HTML body content (required)
        cc_recipients: List of CC emails
        bcc_recipients: List of BCC emails
        attachments: List of file paths to attach
        importance: Normal, High, or Low
    
    Returns:
        Success or error message
    """
    try:
        result = send_mail(
            to_email=to_email,
            subject=subject,
            body_html=body_html,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            attachments=attachments,
            importance=importance
        )
        record_tool_call("send_mail_tool", {
            "to_email": to_email,
            "subject": subject,
            "importance": importance,
            "has_cc": bool(cc_recipients),
            "has_bcc": bool(bcc_recipients),
            "has_attachments": bool(attachments)
        }, result)
        return result
    except Exception as e:
        return f"[Error] {e}"


@tool
def forward_mail_with_note(
    item_id: str,
    changekey: str,
    to_email: str,
    note: str,
    cc_emails: Optional[str] = None
) -> str:
    """Forward an email with a custom note/comment."""
    # Parse CC emails
    cc_list = [e.strip() for e in cc_emails.split(",")] if cc_emails else None
    
    try:
        result = forward_email(
            item_id=item_id,
            changekey=changekey or "",
            to_email=to_email,
            forward_comment=note,
            cc_emails=cc_list
            # ❌ REMOVE: include_attachments=True (not in function signature)
        )
        
        record_tool_call("forward_mail_with_note", {
            "item_id": item_id,
            "to_email": to_email,
            "note": note[:100]
        }, result)
        
        return result
    except Exception as e:
        return f"[Error] forward_mail_with_note failed: {e}"
@tool
def web_search(query: str) -> str:
    """
    Search the web for the latest articles and commands related to a certain task or query using DuckDuckGo.

    Args:
        query (str): The search query (e.g., "latest nmap commands for pentesting site:github.com").

    Returns:
        str: A JSON string containing the top search results with titles, links, and snippets.
    """
    logging.info(f"Performing web search for: {query}")
    try:
        results = []
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region='us-en', max_results=5))  # Changed to list() for explicit conversion
        if not results:
            broadened_query = re.sub(r'\b\d{4}\b', '', query).strip() + " OR tutorial OR guide"
            logging.info(f"No results for '{query}'. Retrying with broadened query: '{broadened_query}'")
            results = list(ddgs.text(broadened_query, region='us-en', max_results=5))
        if results:
            formatted_results = [
                {"title": r['title'], "link": r['href'], "snippet": r['body']}
                for r in results
            ]
            logging.info(f"Web search results: {formatted_results}")  # Added logging for results
            return json.dumps(formatted_results, indent=2)
        else:
            logging.warning(f"No results found even after broadening query for '{query}'")
            return json.dumps({"warning": "No search results found. Try refining the query."})
    except Exception as e:
        logging.error(f"Web search failed: {str(e)}")
        return json.dumps({"error": f"Failed to perform web search for '{query}': {str(e)}. Try a different query."})
@tool
def batch_fetch_emails(
    item_ids: str,
    changekeys: Optional[str] = None,
    include_threads: bool = True,
    max_emails: int = 50
) -> str:
    """
    Fetch multiple emails with their full body content and conversation threads in one operation.
    
    Args:
        item_ids: Comma-separated list of email IDs to fetch
        changekeys: Optional comma-separated list of changekeys (must match item_ids)
        include_threads: Include full conversation threads for each email (default: True)
        max_emails: Maximum number of emails to fetch (safety limit, default: 50)
    
    Returns:
        JSON string with all fetched emails and their content
    
    Example:
        batch_fetch_emails(
            item_ids="AAMkAD...,AAMkAE...,AAMkAF...",
            include_threads=True,
            max_emails=10
        )
    """
    try:
        from ews_tools2 import fetch_multiple_emails_with_threads
        
        # Parse item IDs
        id_list = [id.strip() for id in item_ids.split(",") if id.strip()]
        if not id_list:
            return json.dumps({"error": "No item_ids provided"})
        
        # Parse changekeys if provided
        ck_list = None
        if changekeys:
            ck_list = [ck.strip() for ck in changekeys.split(",") if ck.strip()]
            if len(ck_list) != len(id_list):
                logging.warning("[batch_fetch_emails] Changekeys length mismatch, ignoring")
                ck_list = None
        
        # Fetch emails
        results = fetch_multiple_emails_with_threads(
            item_ids=id_list,
            changekeys=ck_list,
            include_threads=bool(include_threads),
            max_emails=int(max_emails)
        )
        
        # Prepare response
        successful = [r for r in results if not r.get("skipped")]
        failed = [r for r in results if r.get("skipped")]
        
        response = {
            "total_requested": len(id_list),
            "successful": len(successful),
            "failed": len(failed),
            "emails": results
        }
        
        result_json = json.dumps(response, indent=2, default=str)
        record_tool_call("batch_fetch_emails", {
            "count": len(id_list),
            "include_threads": include_threads
        }, f"Fetched {len(successful)}/{len(id_list)} emails")
        
        return result_json
        
    except Exception as e:
        logging.exception("[batch_fetch_emails] Failed")
        return json.dumps({"error": str(e)})


@tool
def search_and_fetch_emails(
    sender_name: Optional[str] = None,
    sender_email: Optional[str] = None,
    sender_domain: Optional[str] = None,
    subject_contains: Optional[str] = None,
    read: Optional[bool] = None,
    has_attachments: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 5,
    include_threads: bool = True,
    include_body: bool = True
) -> str:
    """
    Search for emails by criteria and fetch their complete content with threads in one operation.
    This is more efficient than searching and then fetching individually.
    
    Args:
        sender_name: Partial sender name to match (e.g., "John", "Smith")
        sender_email: Partial sender email to match (e.g., "john", "example.com")
        sender_domain: Sender domain to filter by (e.g., "gmail.com")
        subject_contains: Text to find in subject line
        read: Filter by read status (True/False/None for all)
        has_attachments: Filter by attachment presence (True/False/None for all)
        date_from: Start date in ISO format (e.g., "2024-01-01T00:00:00")
        date_to: End date in ISO format
        limit: Maximum emails to fetch (default: 5, max: 50)
        include_threads: Include full conversation threads (default: True)
        include_body: Include email body content (default: True)
    
    Returns:
        JSON with matched emails, their full content, and conversation threads
    
    Example:
        # Find all unread emails from a specific sender with full threads
        search_and_fetch_emails(
            sender_email="customer@example.com",
            read=False,
            include_threads=True,
            limit=10
        )
        
        # Find emails about pricing with attachments
        search_and_fetch_emails(
            subject_contains="pricing",
            has_attachments=True,
            include_threads=True
        )
    """
    try:
        from ews_tools2 import fetch_emails_by_criteria_with_content
        
        # Call the combined search + fetch function
        results = fetch_emails_by_criteria_with_content(
            sender_name_match_string=sender_name,
            sender_mail_match_string=sender_email,
            sender_domain_match_string=sender_domain,
            subject_match_string=subject_contains,
            read=read,
            has_attachments=has_attachments,
            date_from_iso=date_from,
            date_to_iso=date_to,
            limit=min(int(limit), 50),  # Cap at 50 for safety
            include_threads=bool(include_threads),
            include_body=bool(include_body)
        )
        
        result_json = json.dumps(results, indent=2, default=str)
        
        record_tool_call("search_and_fetch_emails", {
            "sender_email": sender_email,
            "subject": subject_contains,
            "limit": limit,
            "include_threads": include_threads
        }, f"Found and fetched {results.get('total_fetched', 0)} emails")
        
        return result_json
        
    except Exception as e:
        logging.exception("[search_and_fetch_emails] Failed")
        return json.dumps({"error": str(e)})
# ADD send_mail_tool TO ALL_TOOLS LIST AT END:
ALL_TOOLS = [
    query_knowledge_base,
    dynamic_mail_fetch_tool,
    fetch_email,
    batch_fetch_emails,          # NEW - Fetch multiple emails by IDs
    # search_and_fetch_emails,      # NEW - Search and fetch in one operation
    reply_inline,
    web_search,
    forward_mail_with_note,
    follow_up_thread_tool,
    follow_up_email,
    send_mail_tool,
    send_ics_invite,
    schedule_with_check,
    draft_html,
    auto_handle_email,
    reply_mail_directly,
    inform_user,
    set_credentials_tool,
    current_time,
    # send_ical_invite,
    end_task,
    chat_with_human,
    escalate,
    mark_read,
    ignore_spam,
]

# ============= ACTION PLAN MANAGEMENT TOOLS =============
@tool
def create_action_plan(
    plan_name: str,
    task_description: str,
    frequency: str = "daily",
    time_windows: Optional[List[str]] = None,
    custom_interval_hours: Optional[int] = None,
    custom_interval_minutes: Optional[int] = None,
    custom_interval_days: Optional[int] = None,
    days_of_week: Optional[List[int]] = None,
    stopping_condition: Optional[str] = None,
    auto_delete_on_stop: bool = False,
    enabled: bool = True
) -> str:
    """
    Create a scheduled action plan that executes automatically on a defined schedule via autopilot.
    
    **IMPORTANT**: This tool SCHEDULES a task to run later automatically. DO NOT execute the task yourself!
    After creating the plan, call end_task immediately. The autopilot will execute it at the scheduled time.
    
    Use this tool when the user wants to set up recurring email automation tasks.
    
    Args:
        plan_name: Human-readable name for the action plan
        task_description: Natural language task description for the ReAct agent to execute (autopilot will run this)
        frequency: How often to run - "once", "hourly", "daily", "twice_daily", "weekly", or "custom"
        time_windows: Specific times to run in 24h format (e.g., ["09:00", "17:00"] for twice_daily)
        custom_interval_hours: For "custom" frequency, interval in whole hours (e.g., 6 for every 6 hours)
        custom_interval_minutes: For "custom" frequency, interval in minutes (e.g., 30 for every 30 minutes)
        custom_interval_days: For "custom" frequency, interval in days (e.g., 3 for every 3 days)
                               NOTE: Priority order is days > minutes > hours (only one will be used)
        days_of_week: For "weekly" frequency only, list of weekdays (0=Monday, 6=Sunday, e.g., [0,2,4] for Mon/Wed/Fri)
        stopping_condition: Natural language condition for when to stop (optional)
                          Examples: "Stop after 5 executions", "Stop when customer replies", "Stop after 3 days"
        auto_delete_on_stop: If True, delete plan when stopped; if False, disable it (default: False)
        enabled: Whether to activate the plan immediately (default: True)
    
    Returns:
        JSON with created plan details and next execution time
    
    Example:
        create_action_plan(
            plan_name="VIP Follow-ups",
            task_description="Find unreplied emails from VIP customers older than 2 days and draft polite follow-up emails",
            frequency="twice_daily", 
            time_windows=["09:00", "17:00"],
            stopping_condition="Stop after 5 executions OR when customer replies",
            auto_delete_on_stop=True,
            enabled=True
        )
        # Then immediately call: end_task("Action plan created successfully, will run twice daily at 9 AM and 5 PM")
        # DO NOT: Start fetching emails or executing the task yourself!
    """
    try:
        # Use action_plans module instead of importing main_react (which triggers Streamlit UI)
        from action_plans import get_manager
        
        manager = get_manager()
        plan = manager.create_plan(
            name=plan_name,
            task=task_description,
            frequency=frequency,
            time_windows=time_windows,
            custom_interval_hours=custom_interval_hours,
            custom_interval_minutes=custom_interval_minutes,
            custom_interval_days=custom_interval_days,
            days_of_week=days_of_week,
            stopping_condition=stopping_condition,
            auto_delete_on_stop=auto_delete_on_stop,
            enabled=enabled,
            created_by="agent"
        )
        
        result = {
            "success": True,
            "plan_id": plan.id,
            "name": plan.name,
            "frequency": plan.frequency,
            "next_execution": plan.next_execution,
            "enabled": plan.enabled,
            "stopping_condition": plan.stopping_condition,
            "message": f"Action plan '{plan.name}' created successfully"
        }
        
        record_tool_call("create_action_plan", {
            "plan_name": plan_name,
            "frequency": frequency,
            "has_stopping_condition": bool(stopping_condition)
        }, result)
        
        return json.dumps(result, indent=2)
        
    except ValueError as e:
        # Validation error from manager
        return json.dumps({"error": str(e)})
    except Exception as e:
        logging.exception("[create_action_plan] Failed")
        return json.dumps({"error": f"Failed to create action plan: {str(e)}"})


@tool
def list_action_plans(status_filter: Optional[str] = None) -> str:
    """
    List all scheduled action plans with their execution details.
    
    Args:
        status_filter: Optional filter - "enabled", "disabled", or "all" (default: "all")
    
    Returns:
        JSON with all action plans, their schedules, and execution status
    
    Example:
        list_action_plans(status_filter="enabled")
    """
    try:
        from action_plans import get_manager
        
        manager = get_manager()
        plans = manager.list_plans(status_filter=status_filter or None)
        
        # Format plan summaries
        plan_summaries = []
        for p in plans:
            plan_summaries.append({
                "id": p.id,
                "name": p.name,
                "task": p.task[:100] + "..." if len(p.task) > 100 else p.task,
                "enabled": p.enabled,
                "frequency": p.frequency,
                "next_execution": p.next_execution,
                "last_executed": p.last_executed,
                "execution_count": p.execution_count,
                "created_by": p.created_by
            })
        
        all_plans = manager.list_plans()
        enabled_count = sum(1 for p in all_plans if p.enabled)
        
        result = {
            "success": True,
            "total_plans": len(all_plans),
            "enabled": enabled_count,
            "disabled": len(all_plans) - enabled_count,
            "filtered_count": len(plans),
            "plans": plan_summaries
        }
        
        logging.info(f"[list_action_plans] Retrieved {len(plans)} plans (filter: {status_filter or 'all'})")
        
        record_tool_call("list_action_plans", {"status_filter": status_filter}, result)
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logging.exception("[list_action_plans] Failed")
        return json.dumps({"error": str(e)})


@tool
def update_autopilot_rule(
    rule_id: str,
    name: Optional[str] = None,
    prompt: Optional[str] = None,
    priority: Optional[int] = None,
    enabled: Optional[bool] = None
) -> str:
    """
    Update an existing autopilot rule. Only specified fields will be updated.
    
    Args:
        rule_id: ID of the rule to update (required)
        name: New name for the rule (optional)
        prompt: New prompt/instruction text (optional)
        priority: New priority number 1-999, lower = higher priority (optional)
        enabled: Enable (True) or disable (False) the rule (optional)
    
    Returns:
        JSON with update status
    
    Example:
        # Disable a specific rule
        update_autopilot_rule(rule_id="rule_followups", enabled=False)
        
        # Change priority and prompt
        update_autopilot_rule(
            rule_id="rule_vip_customers",
            priority=10,
            prompt="Reply to VIP customers within 1 hour with personalized response"
        )
    """
    try:
        from autopilot import update_autopilot_rule_by_id
        
        # Build updates dictionary with only provided values
        updates = {}
        if name is not None:
            updates["name"] = name
        if prompt is not None:
            updates["prompt"] = prompt
        if priority is not None:
            if not (1 <= priority <= 999):
                return json.dumps({"error": "Priority must be between 1 and 999"})
            updates["priority"] = priority
        if enabled is not None:
            updates["enabled"] = enabled
        
        if not updates:
            return json.dumps({"error": "No fields provided to update. Specify at least one: name, prompt, priority, or enabled"})
        
        # Perform update
        success = update_autopilot_rule_by_id(rule_id, updates)
        
        if success:
            result = {
                "success": True,
                "rule_id": rule_id,
                "updated_fields": list(updates.keys()),
                "message": f"Rule '{rule_id}' updated successfully"
            }
            record_tool_call("update_autopilot_rule", {"rule_id": rule_id, **updates}, result)
            return json.dumps(result, indent=2)
        else:
            return json.dumps({
                "error": f"Rule '{rule_id}' not found",
                "hint": "Use list_autopilot_rules tool to see all available rule IDs"
            })
    
    except Exception as e:
        logging.exception("[update_autopilot_rule] Failed")
        return json.dumps({"error": str(e)})


@tool
def update_action_plan(
    plan_id: str,
    name: Optional[str] = None,
    task_description: Optional[str] = None,
    frequency: Optional[str] = None,
    time_windows: Optional[List[str]] = None,
    custom_interval_hours: Optional[int] = None,
    custom_interval_minutes: Optional[int] = None,
    custom_interval_days: Optional[int] = None,
    days_of_week: Optional[List[int]] = None,
    stopping_condition: Optional[str] = None,
    auto_delete_on_stop: Optional[bool] = None,
    enabled: Optional[bool] = None
) -> str:
    """
    Update an existing action plan. Only specified fields will be updated.
    
    Args:
        plan_id: ID of the plan to update (required)
        name: New name for the plan (optional)
        task_description: New task description (optional)
        frequency: New frequency - "once", "hourly", "daily", "twice_daily", "weekly", or "custom" (optional)
        time_windows: New execution times in 24h format, e.g., ["09:00", "17:00"] (optional)
        custom_interval_hours: For "custom" frequency, interval in hours (optional)
        custom_interval_minutes: For "custom" frequency, interval in minutes (optional)
        custom_interval_days: For "custom" frequency, interval in days (optional)
        days_of_week: For "weekly" frequency, list of weekdays 0-6 (0=Monday, 6=Sunday) (optional)
        stopping_condition: Natural language stopping condition (optional)
        auto_delete_on_stop: Whether to delete (True) or disable (False) when stopped (optional)
        enabled: Enable (True) or disable (False) the plan (optional)
    
    Returns:
        JSON with update status
    
    Example:
        # Disable a plan
        update_action_plan(plan_id="plan_12345", enabled=False)
        
        # Change schedule to run every 3 hours
        update_action_plan(
            plan_id="plan_12345",
            frequency="custom",
            custom_interval_hours=3
        )
        
        # Add stopping condition
        update_action_plan(
            plan_id="plan_12345",
            stopping_condition="Stop after 5 executions OR when customer replies"
        )
    """
    try:
        from action_plans import get_manager
        
        manager = get_manager()
        
        # Build updates dictionary with only provided values
        updates = {}
        if name is not None:
            updates["name"] = name
        if task_description is not None:
            updates["task"] = task_description
        if frequency is not None:
            updates["frequency"] = frequency
        if time_windows is not None:
            updates["time_windows"] = time_windows
        if custom_interval_hours is not None:
            updates["custom_interval_hours"] = custom_interval_hours
        if custom_interval_minutes is not None:
            updates["custom_interval_minutes"] = custom_interval_minutes
        if custom_interval_days is not None:
            updates["custom_interval_days"] = custom_interval_days
        if days_of_week is not None:
            updates["days_of_week"] = days_of_week
        if stopping_condition is not None:
            updates["stopping_condition"] = stopping_condition
        if auto_delete_on_stop is not None:
            updates["auto_delete_on_stop"] = auto_delete_on_stop
        if enabled is not None:
            updates["enabled"] = enabled
        
        if not updates:
            return json.dumps({"error": "No fields provided to update"})
        
        # Perform update
        updated_plan = manager.update_plan(plan_id, **updates)
        
        result = {
            "success": True,
            "plan_id": updated_plan.id,
            "name": updated_plan.name,
            "updated_fields": list(updates.keys()),
            "enabled": updated_plan.enabled,
            "next_execution": updated_plan.next_execution,
            "message": f"Action plan '{updated_plan.name}' updated successfully"
        }
        
        record_tool_call("update_action_plan", {"plan_id": plan_id, **updates}, result)
        return json.dumps(result, indent=2)
        
    except ValueError as e:
        # Plan not found or validation error
        return json.dumps({"error": str(e)})
    except Exception as e:
        logging.exception("[update_action_plan] Failed")
        return json.dumps({"error": f"Failed to update action plan: {str(e)}"})


# ALL_TOOLS = [
#     query_knowledge_base,
#     list_unread,
#     dynamic_mail_fetch_tool,
#     fetch_email,
#     reply_inline,
#     follow_up_thread_tool,
#     follow_up_email,
#     send_ics_invite,
#     schedule_with_check,
#     draft_html,
#     auto_handle_email,
#     reply_mail_directly,
#     inform_user,
#     set_credentials_tool,
#     current_time,
#     end_task,
#     chat_with_human,
#     escalate,
#     mark_read,
#     ignore_spam,
#     send_mail,              # NEW
#     forward_mail,           # NEW
#     forward_mail_with_note, # NEW
# ]

# ============= AUTOPILOT RULE MANAGEMENT TOOLS =============

@tool
def create_autopilot_rule(
    rule_name: str,
    rule_prompt: str,
    priority: int = 3,
    enabled: bool = True
) -> str:
    """
    Create a new autopilot rule that defines how the agent should handle certain types of emails.
    
    Args:
        rule_name: Human-readable name for the rule
        rule_prompt: Natural language instruction for the agent (e.g., "If email is from VIP customer, reply within 1 hour")
        priority: Priority level 1-3 (1=Critical/High, 2=Medium, 3=Low, default: 3)
        enabled: Whether to activate the rule immediately (default: True)
    
    Returns:
        JSON with created rule details
    
    Example:
        create_autopilot_rule(
            rule_name="VIP Customer Priority",
            rule_prompt="If email is from a customer with @bigcorp.com domain, immediately escalate to human and send acknowledgment within 15 minutes",
            priority=1,
            enabled=True
        )
    """
    try:
        from autopilot import get_autopilot_rules, set_autopilot_rules
        from datetime import datetime, timezone
        
        # Validate priority
        if not (1 <= priority <= 3):
            return json.dumps({"error": "Priority must be between 1 and 3 (1=Critical, 2=Medium, 3=Low)"})
        
        # Get existing rules
        current_rules = get_autopilot_rules()
        
        # Generate unique ID
        rule_id = f"custom_{int(datetime.now(timezone.utc).timestamp())}"
        
        # Create new rule
        new_rule = {
            "id": rule_id,
            "name": rule_name.strip(),
            "prompt": rule_prompt.strip(),
            "priority": priority,
            "enabled": bool(enabled),
            "builtin": False
        }
        
        # Add to rules and save
        current_rules.append(new_rule)
        set_autopilot_rules(current_rules)
        
        result = {
            "success": True,
            "rule_id": rule_id,
            "name": new_rule["name"],
            "priority": priority,
            "enabled": enabled,
            "message": f"Autopilot rule '{rule_name}' created successfully"
        }
        
        record_tool_call("create_autopilot_rule", {
            "rule_name": rule_name,
            "priority": priority
        }, result)
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logging.exception("[create_autopilot_rule] Failed")
        return json.dumps({"error": str(e)})


@tool
def list_autopilot_rules(status_filter: Optional[str] = None) -> str:
    """
    List all autopilot rules with their configuration details.
    
    Args:
        status_filter: Optional filter - "enabled", "disabled", or "all" (default: "all")
    
    Returns:
        JSON with all autopilot rules and their details
    
    Example:
        list_autopilot_rules(status_filter="enabled")
    """
    try:
        from autopilot import get_autopilot_rules
        
        rules = get_autopilot_rules()
        
        # Filter by status
        if status_filter == "enabled":
            filtered_rules = [r for r in rules if r.get("enabled", True)]
        elif status_filter == "disabled":
            filtered_rules = [r for r in rules if not r.get("enabled", True)]
        else:
            filtered_rules = rules
        
        # Sort by priority
        filtered_rules = sorted(filtered_rules, key=lambda r: r.get("priority", 999))
        
        # Format rule summaries
        rule_summaries = []
        for r in filtered_rules:
            rule_summaries.append({
                "id": r["id"],
                "name": r["name"],
                "prompt": r["prompt"][:100] + "..." if len(r.get("prompt", "")) > 100 else r.get("prompt", ""),
                "priority": r.get("priority", 999),
                "enabled": r.get("enabled", True),
                "builtin": r.get("builtin", False)
            })
        
        enabled_count = sum(1 for r in rules if r.get("enabled", True))
        
        result = {
            "success": True,
            "total_rules": len(rules),
            "enabled": enabled_count,
            "disabled": len(rules) - enabled_count,
            "filtered_count": len(filtered_rules),
            "rules": rule_summaries
        }
        
        record_tool_call("list_autopilot_rules", {"status_filter": status_filter}, result)
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logging.exception("[list_autopilot_rules] Failed")
        return json.dumps({"error": str(e)})


@tool
def delete_autopilot_rule(rule_id: str) -> str:
    """
    Delete an autopilot rule by its ID. Built-in rules cannot be deleted.
    
    Args:
        rule_id: ID of the rule to delete (required)
    
    Returns:
        JSON with deletion status
    
    Example:
        delete_autopilot_rule(rule_id="custom_1703267891")
    """
    try:
        from autopilot import get_autopilot_rules, set_autopilot_rules
        
        rules = get_autopilot_rules()
        
        # Find the rule
        rule_to_delete = None
        for r in rules:
            if r["id"] == rule_id:
                rule_to_delete = r
                break
        
        if not rule_to_delete:
            return json.dumps({
                "error": f"Rule '{rule_id}' not found",
                "hint": "Use list_autopilot_rules tool to see all available rule IDs"
            })
        
        # Check if built-in
        if rule_to_delete.get("builtin", False):
            return json.dumps({
                "error": f"Cannot delete built-in rule '{rule_to_delete['name']}'",
                "hint": "You can disable it using update_autopilot_rule instead"
            })
        
        # Remove the rule
        updated_rules = [r for r in rules if r["id"] != rule_id]
        set_autopilot_rules(updated_rules)
        
        result = {
            "success": True,
            "rule_id": rule_id,
            "rule_name": rule_to_delete["name"],
            "message": f"Autopilot rule '{rule_to_delete['name']}' deleted successfully"
        }
        
        record_tool_call("delete_autopilot_rule", {"rule_id": rule_id}, result)
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logging.exception("[delete_autopilot_rule] Failed")
        return json.dumps({"error": str(e)})


@tool
def delete_action_plan(plan_id: str) -> str:
    """
    Delete an action plan by its ID.
    
    Args:
        plan_id: ID of the action plan to delete (required)
    
    Returns:
        JSON with deletion status
    
    Example:
        delete_action_plan(plan_id="plan_1703267891")
    """
    try:
        from action_plans import get_manager
        
        manager = get_manager()
        success = manager.delete_plan(plan_id)
        
        if success:
            result = {
                "success": True,
                "plan_id": plan_id,
                "message": f"Action plan '{plan_id}' deleted successfully"
            }
            record_tool_call("delete_action_plan", {"plan_id": plan_id}, result)
            return json.dumps(result, indent=2)
        else:
            return json.dumps({
                "error": f"Action plan '{plan_id}' not found",
                "hint": "Use list_action_plans tool to see all available plan IDs"
            })
    
    except Exception as e:
        logging.exception("[delete_action_plan] Failed")
        return json.dumps({"error": str(e)})



# ============= TOOL CATEGORIZATION =============
# Split tools into categories for different agent contexts

# EXECUTION_TOOLS: Tools for executing tasks (action plan service agents)
# These tools allow the agent to perform work but NOT manage plans/autopilot
EXECUTION_TOOLS = [
    query_knowledge_base,
    dynamic_mail_fetch_tool,
    fetch_email,
    batch_fetch_emails,
    reply_inline,
    web_search,
    forward_mail_with_note,
    follow_up_thread_tool,
    follow_up_email,
    send_mail_tool,
    send_ics_invite,
    schedule_with_check,
    draft_html,
    auto_handle_email,
    reply_mail_directly,
    inform_user,
    set_credentials_tool,
    current_time,
    end_task,
    chat_with_human,
    escalate,
    mark_read,
    ignore_spam,
]

#MANAGEMENT_TOOLS: Tools for managing action plans and autopilot rules
# EXCLUDED from action plan service to prevent duplicate creation/modification
MANAGEMENT_TOOLS = [
    create_action_plan,
    list_action_plans,
    update_action_plan,
    delete_action_plan,
    create_autopilot_rule,
    list_autopilot_rules,
    update_autopilot_rule,
    delete_autopilot_rule
]

# ALL_TOOLS: Complete tool set for UI/chatbox agents (backward compatible)
ALL_TOOLS = EXECUTION_TOOLS + MANAGEMENT_TOOLS


