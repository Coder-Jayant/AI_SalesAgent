"""
Unified Action Plan Management Module

Provides centralized management for scheduled action plans
created by both agent tools and UI.

This module ensures perfect sync between all sources and provides
a clean interface for CRUD operations.
"""

from .manager import ActionPlanManager
from .models import ActionPlan
from .migration import migrate_all_plans, needs_migration

# Singleton manager instance
_manager_instance = None


def get_manager() -> ActionPlanManager:
    """
    Get singleton manager instance.
    
    Returns:
        ActionPlanManager singleton
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ActionPlanManager()
    return _manager_instance


# Backward compatibility functions for existing code
def get_action_plans():
    """
    Get all action plans as list of dicts (backward compatible).
    
    Legacy function - new code should use get_manager().list_plans()
    
    Returns:
        List of action plan dictionaries
    """
    return [p.to_dict() for p in get_manager().list_plans()]


def set_action_plans(plans):
    """
    Set action plans directly (backward compatible but not recommended).
    
    Legacy function - new code should use manager methods.
    This bypasses validation and should be avoided.
    
    Args:
        plans: List of plan dictionaries
    """
    manager = get_manager()
    state = manager.storage.load()
    state["action_plans"] = plans
    manager.storage.save(state)


def add_action_plan_execution(plan_id, result):
    """
    Add execution record (backward compatible).
    
    Args:
        plan_id: Plan identifier
        result: Execution result dictionary
    """
    get_manager().add_execution_record(plan_id, result)


__all__ = [
    # Main classes
    "ActionPlanManager",
    "ActionPlan",
    
    # Manager access
    "get_manager",
    
    # Backward compatibility
    "get_action_plans",
    "set_action_plans",
    "add_action_plan_execution",
    
    # Migration utilities
    "migrate_all_plans",
    "needs_migration"
]
