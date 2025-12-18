"""
Action Plan Data Models

Defines the unified ActionPlan dataclass with validation.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo


@dataclass
class ActionPlan:
    """Unified action plan model for both agent and UI creation"""
    
    # Core fields
    id: str
    name: str
    task: str
    enabled: bool = True
    
    # Schedule configuration
    frequency: str = "daily"  # once, hourly, daily, twice_daily, weekly, custom
    time_windows: Optional[List[str]] = None
    custom_interval_hours: Optional[int] = None  # For "custom" frequency
    custom_interval_minutes: Optional[int] = None  # For "custom" frequency (takes precedence over hours)
    custom_interval_days: Optional[int] = None  # For "custom" frequency (takes precedence over hours/minutes)
    days_of_week: Optional[List[int]] = None
    timezone: str = "Asia/Kolkata"
    
    # Execution tracking
    last_executed: Optional[str] = None
    next_execution: Optional[str] = None
    execution_count: int = 0
    failure_count: int = 0
    last_failure: Optional[str] = None
    last_failure_reason: Optional[str] = None
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(ZoneInfo("Asia/Kolkata")).isoformat())
    created_by: str = "unknown"  # "agent", "user", or "migration"
    updated_at: Optional[str] = None
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_minutes: int = 15
    current_retries: int = 0
    
    # Stopping conditions (NEW)
    stopping_condition: Optional[str] = None  # Natural language stopping condition
    auto_delete_on_stop: bool = False  # If True, delete; if False, disable when stopped

    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionPlan':
        """
        Create ActionPlan from dictionary with validation.
        Handles missing fields with defaults.
        """
        # Only include fields that exist in the dataclass
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate plan configuration using scheduler.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            from scheduled_tasks import ScheduledTaskManager
            scheduler = ScheduledTaskManager()
            return scheduler.validate_schedule({
                "frequency": self.frequency,
                "time_windows": self.time_windows,
                "custom_interval_hours": self.custom_interval_hours,
                "custom_interval_minutes": self.custom_interval_minutes,
                "custom_interval_days": self.custom_interval_days,
                "days_of_week": self.days_of_week,
                "timezone": self.timezone
            })
        except Exception as e:
            return False, f"Validation error: {str(e)}"
