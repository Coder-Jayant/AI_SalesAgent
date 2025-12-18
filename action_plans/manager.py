"""
Action Plan Manager

Centralized management for action plans with unified interface.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import uuid4

from .models import ActionPlan
from .storage import ActionPlanStorage

logger = logging.getLogger(__name__)


class ActionPlanManager:
    """Centralized action plan management for both agent and UI"""
    
    def __init__(self, storage_path: str = "action_plans_state.json"):
        self.storage = ActionPlanStorage(storage_path)
        
        # Import scheduler here to avoid circular imports
        from scheduled_tasks import ScheduledTaskManager
        self.scheduler = ScheduledTaskManager()
        
        # Auto-migrate legacy plans on initialization
        self._auto_migrate()
        
        logger.info("[ActionPlanManager] Initialized")
    
    def _auto_migrate(self):
        """Automatically migrate legacy plans if needed"""
        try:
            from .migration import migrate_all_plans
            
            state = self.storage.load()
            plans = state.get("action_plans", [])
            
            # Check if migration needed (look for old frequency format)
            needs_migration = any(
                p.get("frequency") == "every_sweep" 
                for p in plans
            )
            
            if needs_migration:
                logger.info("[ActionPlanManager] Detected legacy plans, starting migration...")
                state = migrate_all_plans(state)
                self.storage.save(state)
                logger.info("[ActionPlanManager] Migration complete")
        except Exception as e:
            logger.error(f"[ActionPlanManager] Auto-migration failed: {e}")
    
    def create_plan(
        self,
        name: str,
        task: str,
        frequency: str = "daily",
        time_windows: Optional[List[str]] = None,
        custom_interval_hours: Optional[int] = None,
        custom_interval_minutes: Optional[int] = None,
        custom_interval_days: Optional[int] = None,
        days_of_week: Optional[List[int]] = None,
        stopping_condition: Optional[str] = None,
        auto_delete_on_stop: bool = False,
        enabled: bool = True,
        created_by: str = "unknown"
    ) -> ActionPlan:
        """
        Create a new action plan.
        
        Args:
            name: Human-readable plan name
            task: Natural language task description
            frequency: Schedule type
            time_windows: Execution times ["09:00", "17:00"]
            custom_interval_hours: For custom frequency
            custom_interval_minutes: For custom frequency (minutes)
            custom_interval_days: For custom frequency (days)
            days_of_week: For weekly frequency [0-6]
            stopping_condition: Natural language stopping condition (optional)
            auto_delete_on_stop: If True, delete when stopped; if False, disable
            enabled: Active status
            created_by: Source - "agent", "user", or "migration"
        
        Returns:
            Created ActionPlan object
        
        Raises:
            ValueError: If validation fails
        """
        # Create plan object
        plan = ActionPlan(
            id=f"plan_{uuid4().hex[:12]}",
            name=name.strip(),
            task=task.strip(),
            enabled=enabled,
            frequency=frequency,
            time_windows=time_windows or (["09:00"] if frequency in ["daily", "twice_daily", "weekly"] else None),
            custom_interval_hours=custom_interval_hours,
            custom_interval_minutes=custom_interval_minutes,
            custom_interval_days=custom_interval_days,
            days_of_week=days_of_week,
            stopping_condition=stopping_condition,
            auto_delete_on_stop=auto_delete_on_stop,
            created_by=created_by,
            created_at=datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        )
        
        # Validate
        is_valid, error_msg = plan.validate()
        if not is_valid:
            raise ValueError(f"Invalid plan configuration: {error_msg}")
        
        # Calculate next execution
        next_exec = self.scheduler.get_next_execution_time(plan.to_dict())
        plan.next_execution = next_exec.isoformat() if next_exec else None
        
        # Save
        state = self.storage.load()
        state["action_plans"].append(plan.to_dict())
        self.storage.save(state)
        
        logger.info(f"[ActionPlanManager] Created plan '{plan.name}' (ID: {plan.id}) by {created_by}")
        return plan
    
    def list_plans(self, status_filter: Optional[str] = None) -> List[ActionPlan]:
        """
        List all action plans with optional filtering.
        
        Args:
            status_filter: "enabled", "disabled", or None for all
        
        Returns:
            List of ActionPlan objects
        """
        state = self.storage.load()
        plans = [ActionPlan.from_dict(p) for p in state["action_plans"]]
        
        if status_filter == "enabled":
            plans = [p for p in plans if p.enabled]
        elif status_filter == "disabled":
            plans = [p for p in plans if not p.enabled]
        
        return plans
    
    def get_plan(self, plan_id: str) -> Optional[ActionPlan]:
        """
        Get a single plan by ID.
        
        Args:
            plan_id: Plan identifier
        
        Returns:
            ActionPlan object or None if not found
        """
        plans = self.list_plans()
        for plan in plans:
            if plan.id == plan_id:
                return plan
        return None
    
    def update_plan(self, plan_id: str, **updates) -> ActionPlan:
        """
        Update an existing plan.
        
        Args:
            plan_id: Plan identifier
            **updates: Fields to update (enabled, frequency, time_windows, etc.)
        
        Returns:
            Updated ActionPlan object
        
        Raises:
            ValueError: If plan not found or validation fails
        """
        state = self.storage.load()
        plans = state["action_plans"]
        
        # Find plan
        plan_dict = None
        for p in plans:
            if p["id"] == plan_id:
                plan_dict = p
                break
        
        if not plan_dict:
            raise ValueError(f"Action plan not found: {plan_id}")
        
        # Apply updates
        for key, value in updates.items():
            if value is not None and key in ActionPlan.__dataclass_fields__:
                plan_dict[key] = value
        
        # Update timestamp
        plan_dict["updated_at"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        
        # Recalculate next execution if schedule changed
        schedule_fields = ["frequency", "time_windows", "custom_interval_hours", "custom_interval_minutes", "custom_interval_days", "enabled", "days_of_week"]
        if any(k in updates for k in schedule_fields):
            next_exec = self.scheduler.get_next_execution_time(plan_dict)
            plan_dict["next_execution"] = next_exec.isoformat() if next_exec else None
        
        # Validate and save
        plan = ActionPlan.from_dict(plan_dict)
        is_valid, error_msg = plan.validate()
        if not is_valid:
            raise ValueError(f"Invalid update: {error_msg}")
        
        self.storage.save(state)
        logger.info(f"[ActionPlanManager] Updated plan {plan_id}: {list(updates.keys())}")
        return plan
    
    def delete_plan(self, plan_id: str) -> bool:
        """
        Delete a plan.
        
        Args:
            plan_id: Plan identifier
        
        Returns:
            True if deleted, False if not found
        """
        state = self.storage.load()
        plans = state["action_plans"]
        
        initial_count = len(plans)
        state["action_plans"] = [p for p in plans if p["id"] != plan_id]
        
        if len(state["action_plans"]) < initial_count:
            self.storage.save(state)
            logger.info(f"[ActionPlanManager] Deleted plan {plan_id}")
            return True
        
        logger.warning(f"[ActionPlanManager] Plan {plan_id} not found for deletion")
        return False
    
    def add_execution_record(self, plan_id: str, result: Dict[str, Any]):
        """
        Record execution history for a plan.
        
        Args:
            plan_id: Plan identifier
            result: Execution  result dict with status, error, etc.
        """
        state = self.storage.load()
        history = state.get("execution_history", [])
        
        history.insert(0, {
            "plan_id": plan_id,
            "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
            **result
        })
        
        # Keep last 100 records
        state["execution_history"] = history[:100]
        self.storage.save(state)
        
        logger.debug(f"[ActionPlanManager] Added execution record for {plan_id}")
    
    def get_execution_history(self, plan_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get execution history.
        
        Args:
            plan_id: Optional plan ID to filter by
            limit: Maximum records to return
        
        Returns:
            List of execution records
        """
        state = self.storage.load()
        history = state.get("execution_history", [])
        
        if plan_id:
            history = [h for h in history if h.get("plan_id") == plan_id]
        
        return history[:limit]
