"""
Action Plan Migration Utilities

Handles migration of legacy action plans to new unified format.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def migrate_legacy_plan(old_plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate a single legacy plan to new unified format.
    
    Handles:
    - Old "every_sweep" frequency -> "hourly"
    - Missing fields with defaults
    - Field name variations
    
    Args:
        old_plan: Legacy plan dictionary
    
    Returns:
        Migrated plan dictionary
    """
    # Ensure all required fields exist with defaults
    migrated = {
        "id": old_plan.get("id", f"migrated_{old_plan.get('name', 'unknown').replace(' ', '_')}"),
        "name": old_plan.get("name", "Unnamed Plan"),
        "task": old_plan.get("task", ""),
        "enabled": old_plan.get("enabled", True),
        
        # Schedule
        "frequency": old_plan.get("frequency", "daily"),
        "time_windows": old_plan.get("time_windows"),
        "custom_interval_hours": old_plan.get("custom_interval_hours"),
        "days_of_week": old_plan.get("days_of_week"),
        "timezone": old_plan.get("timezone", "Asia/Kolkata"),
        
        # Execution tracking
        "last_executed": old_plan.get("last_executed"),
        "next_execution": old_plan.get("next_execution"),
        "execution_count": old_plan.get("execution_count", 0),
        "failure_count": old_plan.get("failure_count", 0),
        "last_failure": old_plan.get("last_failure"),
        "last_failure_reason": old_plan.get("last_failure_reason"),
        
        # Metadata
        "created_at": old_plan.get("created_at"),
        "created_by": old_plan.get("created_by", "migration"),
        "updated_at": old_plan.get("updated_at"),
        
        # Retry configuration
        "max_retries": old_plan.get("max_retries", 3),
        "retry_delay_minutes": old_plan.get("retry_delay_minutes", 15),
        "current_retries": old_plan.get("current_retries", 0)
    }
    
    # Handle old "every_sweep" frequency (legacy autopilot format)
    if migrated["frequency"] == "every_sweep":
        migrated["frequency"] = "hourly"
        logger.info(f"Migrated legacy frequency 'every_sweep' -> 'hourly' for plan '{migrated['name']}'")
    
    # Ensure time_windows for daily/twice_daily/weekly if missing
    if migrated["frequency"] in ["daily", "twice_daily", "weekly"] and not migrated["time_windows"]:
        if migrated["frequency"] == "twice_daily":
            migrated["time_windows"] = ["09:00", "17:00"]
        else:
            migrated["time_windows"] = ["09:00"]
        logger.info(f"Added default time_windows for plan '{migrated['name']}'")
    
    return migrated


def migrate_all_plans(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate entire state including all action plans.
    
    Args:
        state: Full state dictionary with action_plans and execution_history
    
    Returns:
        Migrated state dictionary
    """
    migrated_plans = []
    migration_stats = {
        "total": 0,
        "succeeded": 0,
        "failed": 0,
        "frequency_migrations": 0
    }
    
    for plan in state.get("action_plans", []):
        migration_stats["total"] += 1
        
        try:
            # Track if frequency needs migration
            old_freq = plan.get("frequency")
            
            # Migrate the plan
            migrated = migrate_legacy_plan(plan)
            
            # Validate using model
            from .models import ActionPlan
            validated_plan = ActionPlan.from_dict(migrated)
            
            # Track frequency migrations
            if old_freq == "every_sweep":
                migration_stats["frequency_migrations"] += 1
            
            migrated_plans.append(validated_plan.to_dict())
            migration_stats["succeeded"] += 1
            
            logger.info(f"Successfully migrated plan: {migrated['id']} ({migrated['name']})")
            
        except Exception as e:
            migration_stats["failed"] += 1
            logger.error(f"Failed to migrate plan {plan.get('id', 'unknown')}: {e}")
            
            # Keep original if migration fails to prevent data loss
            migrated_plans.append(plan)
            logger.warning(f"Kept original plan data for {plan.get('id')} due to migration failure")
    
    # Log migration summary
    logger.info(
        f"Migration complete: {migration_stats['succeeded']}/{migration_stats['total']} succeeded, "
        f"{migration_stats['failed']} failed, "
        f"{migration_stats['frequency_migrations']} frequency migrations"
    )
    
    state["action_plans"] = migrated_plans
    return state


def needs_migration(state: Dict[str, Any]) -> bool:
    """
    Check if state needs migration.
    
    Args:
        state: State dictionary
    
    Returns:
        True if migration is needed
    """
    plans = state.get("action_plans", [])
    
    # Check for old frequency format
    has_old_frequency = any(
        p.get("frequency") == "every_sweep" 
        for p in plans
    )
    
    # Check for missing required fields
    has_missing_fields = any(
        not p.get("created_by")
        for p in plans
    )
    
    return has_old_frequency or has_missing_fields
