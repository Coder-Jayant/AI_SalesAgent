"""
Scheduled Action Plans Execution Module

Standalone execution of scheduled action plans, independent of autopilot.
"""

import os
import time
import logging
from typing import List, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

logger = logging.getLogger(__name__)

# Execution lock to prevent concurrent runs
EXECUTION_LOCK_FILE = "action_plans_execution.lock"



def execute_scheduled_plans(hands_free: bool = False) -> List[Dict[str, Any]]:
    """
    Check and execute all action plans that are due for execution.
    
    This function is called by the independent action plan service.
    Uses execution locking to prevent concurrent runs.
    
    Args:
        hands_free: If True, allows actual email sending; if False, saves as drafts
    
    Returns:
        List of execution results with status, plan details, and any errors
    """
    # Acquire execution lock to prevent concurrent runs
    lock_path = Path(EXECUTION_LOCK_FILE)
    
    try:
        # Check if another execution is already running
        if lock_path.exists():
            age = time.time() - lock_path.stat().st_mtime
            if age < 300:  # 5 minutes
                logger.debug(f"[ScheduledPlans] Another execution in progress (lock age: {age:.0f}s), skipping")
                return []
            else:
                # Stale lock, remove it
                logger.warning(f"[ScheduledPlans] Removing stale lock (age: {age:.0f}s)")
                lock_path.unlink()
        
        # Create lock file
        lock_path.write_text(str(os.getpid()))
        logger.debug("[ScheduledPlans] Execution lock acquired")
        
    except Exception as e:
        logger.error(f"[ScheduledPlans] Failed to acquire lock: {e}")
        return []
    
    try:
        from action_plans import get_manager
        from scheduled_tasks import ScheduledTaskManager
        
        manager = get_manager()
        scheduler = ScheduledTaskManager()
        
        # Get all enabled plans
        plans = manager.list_plans(status_filter="enabled")
        
        if not plans:
            logger.debug("[ScheduledPlans] No enabled action plans")
            return []
        
        # Get current time in Indian timezone
        current_time = datetime.now(ZoneInfo("Asia/Kolkata"))
        logger.info(f"[ScheduledPlans] Checking {len(plans)} enabled plans at {current_time.strftime('%H:%M:%S')}")
        
        results = []
        
        for plan in plans:
            try:
                # Convert plan to dict for scheduler
                plan_dict = plan.to_dict()
                
                # Check if this plan should execute now
                should_run = scheduler.should_execute(plan_dict, current_time)
                
                # ✅ Enhanced logging for debugging timing issues
                logger.debug(f"[ScheduledPlans] Plan '{plan.name}' timing check: "
                           f"last_executed={plan.last_executed[-8:] if plan.last_executed else 'Never'}, "
                           f"next_execution={plan.next_execution[-8:] if plan.next_execution else 'None'}, "
                           f"should_run={should_run}")
                
                if not should_run:
                    logger.debug(f"[ScheduledPlans] Plan '{plan.name}' not due (next: {plan.next_execution})")
                    continue
                
                logger.info(f"[ScheduledPlans] Executing plan: {plan.name} (ID: {plan.id})")
                
                # Execute the plan using ReAct agent
                execution_result = _execute_single_plan(plan, hands_free)
                
                # Update execution tracking based on result
                if execution_result["status"] == "success":
                    # ✅ CRITICAL FIX: Update plan_dict with new values BEFORE calculating next execution
                    # Otherwise get_next_execution_time() uses the OLD last_executed value!
                    plan_dict['last_executed'] = current_time.isoformat()
                    plan_dict['execution_count'] = plan.execution_count + 1
                    plan_dict['current_retries'] = 0
                    
                    # Calculate next execution time with updated values
                    next_exec = scheduler.get_next_execution_time(plan_dict)
                    
                    # ✅ Single atomic update with ALL fields (eliminates race condition)
                    manager.update_plan(
                        plan.id,
                        last_executed=current_time.isoformat(),
                        execution_count=plan.execution_count + 1,
                        current_retries=0,
                        next_execution=next_exec.isoformat() if next_exec else None
                    )
                    
                    logger.info(f"[ScheduledPlans] SUCCESS: Plan '{plan.name}' executed successfully "
                               f"(next: {next_exec.strftime('%H:%M:%S') if next_exec else 'never'})")

                    
                else:
                    # Handle failure with retry logic
                    current_retries = plan.current_retries + 1
                    
                    if current_retries < plan.max_retries:
                        # Schedule retry
                        from datetime import timedelta
                        retry_time = current_time + timedelta(minutes=plan.retry_delay_minutes)
                        
                        manager.update_plan(
                            plan.id,
                            failure_count=plan.failure_count + 1,
                            last_failure=current_time.isoformat(),
                            last_failure_reason=execution_result.get("error", "Unknown error"),
                            current_retries=current_retries,
                            next_execution=retry_time.isoformat()
                        )
                        
                        logger.warning(
                            f"[ScheduledPlans] FAILED: Plan '{plan.name}' failed (retry {current_retries}/{plan.max_retries}), "
                            f"retrying at {retry_time.strftime('%H:%M:%S')}"
                        )
                    else:
                        # Max retries reached, schedule next regular execution
                        next_exec = scheduler.get_next_execution_time(plan_dict)
                        
                        manager.update_plan(
                            plan.id,
                            failure_count=plan.failure_count + 1,
                            last_failure=current_time.isoformat(),
                            last_failure_reason=execution_result.get("error", "Unknown error"),
                            current_retries=0,  # Reset for next scheduled run
                            next_execution=next_exec.isoformat() if next_exec else None
                        )
                        
                        logger.error(
                            f"[ScheduledPlans] FAILED: Plan '{plan.name}' failed after {plan.max_retries} retries, "
                            f"next attempt: {next_exec.strftime('%Y-%m-%d %H:%M') if next_exec else 'never'}"
                        )
                
                # Record execution in history
                manager.add_execution_record(plan.id, execution_result)
                
                results.append({
                    "plan_id": plan.id,
                    "plan_name": plan.name,
                    **execution_result
                })
                
            except Exception as e:
                logger.exception(f"[ScheduledPlans] Error processing plan '{plan.name}': {e}")
                results.append({
                    "plan_id": plan.id,
                    "plan_name": plan.name,
                    "status": "error",
                    "error": str(e),
                    "timestamp": current_time.isoformat()
                })
        
        if results:
            logger.info(f"[ScheduledPlans] Completed: {len(results)} plans executed")
        
        return results
        
    except Exception as e:
        logger.exception(f"[ScheduledPlans] Fatal error in execute_scheduled_plans: {e}")
        return [{
            "status": "error",
            "error": f"Fatal error: {str(e)}",
            "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        }]
    
    finally:
        # Always release the execution lock
        try:
            if lock_path.exists():
                lock_path.unlink()
                logger.debug("[ScheduledPlans] Execution lock released")
        except Exception as unlock_err:
            logger.error(f"[ScheduledPlans] Failed to release lock: {unlock_err}")



def _execute_single_plan(plan, hands_free: bool) -> Dict[str, Any]:
    """
    Execute a single action plan using the ReAct agent.
    
    Args:
        plan: ActionPlan object
        hands_free: Whether to allow actual sending
    
    Returns:
        Execution result dict
    """
    try:
        from autopilot import get_autopilot_react_agent
        from datetime import datetime
        from zoneinfo import ZoneInfo
        import os
        
        # Get current time for context
        current_time = datetime.now(ZoneInfo("Asia/Kolkata"))
        time_str = current_time.strftime('%A, %B %d, %Y at %I:%M %p %Z')
        
        # Get user identity from ENV for signatures
        user_name = os.getenv("AGENT_USER_NAME", "Sales Agent")
        user_email = os.getenv("EWS_EMAIL", "")
        
        # Build instruction for ReAct agent
        hands_free_mode = "ON - Can send emails directly" if hands_free else "OFF - Save all as drafts"
        
        # Format execution metadata
        exec_metadata = f"""
**PLAN METADATA:**
- Plan ID: {plan.id}
- Executions: {plan.execution_count} times
- Created: {plan.created_at[:10] if plan.created_at else 'Unknown'}
- Last Run: {plan.last_executed[:16] if plan.last_executed else 'Never'}
- Failures: {plan.failure_count}"""
        
        # Get and format recent execution history (last 2-3 runs)
        recent_history = ""
        try:
            from action_plans import get_manager
            manager = get_manager()
            history = manager.get_execution_history(plan.id, limit=3)
            
            if history:
                history_lines = []
                for i, record in enumerate(history[:3], 1):
                    ts = record.get("timestamp", "")[:16] if record.get("timestamp") else "Unknown"
                    status = record.get("status", "unknown")
                    result = record.get("result", record.get("final_answer", ""))[:80]
                    history_lines.append(f"{i}. {ts} | {status} | {result}...")
                
                recent_history = f"""
**RECENT HISTORY (last {len(history)} runs):**
{chr(10).join(history_lines)}"""
        except Exception as e:
            logger.warning(f"[ScheduledPlans] Could not fetch execution history: {e}")
            recent_history = ""
        
        # Build stopping condition section if present
        stopping_section = ""
        if plan.stopping_condition:  # ActionPlan is a dataclass, use attribute access
            auto_action = "delete" if plan.auto_delete_on_stop else "disable"
            stopping_section = f"""
**STOPPING CONDITION:** {plan.stopping_condition}

**CRITICAL**: Evaluate if stopping condition is met BEFORE executing task:
- Use plan metadata above to check counts, dates, durations
- Use tools to check email/customer responses if needed
- If condition IS MET:
  * Call {'delete_action_plan' if auto_action == 'delete' else 'update_action_plan'}(plan_id="{plan.id}"{'' if auto_action == 'delete' else ', enabled=False'})
  * Call end_task("Stopping condition met: {plan.stopping_condition}")
  * DO NOT execute the task
- If condition NOT MET: proceed with task execution
"""
        
        instruction = f"""
SCHEDULED ACTION PLAN EXECUTION

**TIME:** {time_str}
**IDENTITY:** {user_name} ({user_email})
**HANDS-FREE:** {hands_free_mode}
{exec_metadata}{recent_history}

**TASK:** {plan.task}
{stopping_section}
**CRITICAL EMAIL WRITING INSTRUCTIONS:**
⚠️ **NEVER USE PLACEHOLDER EMAIL ADDRESSES OR TEMPLATE TEXT**
- ❌ FORBIDDEN: customer_email@example.com, user@example.com, [recipient email], [customer name]
- ✅ REQUIRED: Use ACTUAL email addresses from the task description/metadata
- If task references a specific email (with item_id/changekey in metadata), extract recipient info from that email
- If task says "send to john@company.com", use EXACTLY that address, NOT placeholders
- If task mentions a customer but no email provided, you MUST use dynamic_mail_fetch_tool to find their email first
- **Every email MUST have a REAL, valid recipient address - NO EXCEPTIONS**

**EXAMPLE - CORRECT vs WRONG:**
❌ WRONG: send_mail_tool(to_email="customer_email@example.com", ...)
✅ CORRECT: Use email from task metadata OR fetch_email to get real recipient

**CRITICAL INSTRUCTIONS:**
1. {'Check stopping condition first (if present)' if stopping_section else 'Read task carefully'}
2. **Extract REAL email addresses** from task metadata/description (look for [Subject: '...' | From/To: '...' | item_id: '...'])
3. If no email address found in task, use dynamic_mail_fetch_tool or fetch_email to get recipient info
4. Execute task using appropriate tools with REAL email addresses, NOT placeholders
5. DO NOT create new action plans (this plan already exists)
6. Use {'save_as_draft=False' if hands_free else 'save_as_draft=True'} for emails
7. **For follow-ups: ALWAYS use reply_inline (threaded reply), NEVER send independent emails**
8. **IMMEDIATELY call end_task(summary) after completing the task - DO NOT repeat the task**

**⚠️ IMPORTANT:** 
- Once you complete the task (e.g., send an email), you MUST call end_task immediately.
- DO NOT send the same email multiple times. DO NOT repeat the task. Call end_task RIGHT AWAY.
- For follow-up emails: Use reply_inline tool to maintain conversation thread, NOT send_mail_tool
- VERIFY recipient email is REAL before sending (not example.com, not placeholder text)

Execute now.
"""
        
        # Get ReAct agent with EXECUTION TOOLS ONLY (no plan management)
        # This prevents the agent from creating/modifying plans during execution
        from agent_tools import EXECUTION_TOOLS
        agent = get_autopilot_react_agent(tools=EXECUTION_TOOLS)
        
        logger.info(f"[ScheduledPlans] Running ReAct agent for plan '{plan.name}'...")
        final_answer = agent.run(
            user_input=instruction,
            max_iterations=20  # Allow more iterations for complex tasks
        )
        
        logger.info(f"[ScheduledPlans] Plan '{plan.name}' completed: {final_answer[:150]}...")
        
        return {
            "status": "success",
            "result": final_answer,
            "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
            "hands_free": hands_free
        }
        
    except Exception as e:
        logger.exception(f"[ScheduledPlans] Execution failed for plan '{plan.name}': {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        }
