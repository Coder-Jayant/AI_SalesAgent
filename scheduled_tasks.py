"""
scheduled_tasks.py
Core scheduling logic for automated action plan execution
"""

import logging
from datetime import datetime, timedelta, time, timezone as dt_timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Default timezone for scheduling
DEFAULT_TIMEZONE = "Asia/Kolkata"


@dataclass
class TaskSchedule:
    """Represents a schedule configuration for an action plan"""
    frequency: str  # "once", "hourly", "daily", "weekly", "twice_daily", "custom"
    interval_minutes: Optional[int] = None  # For custom intervals
    time_windows: Optional[List[str]] = None  # e.g., ["09:00", "17:00"]
    days_of_week: Optional[List[int]] = None  # 0=Monday, 6=Sunday
    timezone: str = DEFAULT_TIMEZONE


class ScheduledTaskManager:
    """Manages scheduled task execution and state"""
    
    def __init__(self, timezone: str = DEFAULT_TIMEZONE):
        """
        Initialize the scheduler.
        
        Args:
            timezone: Timezone string (e.g., "Asia/Kolkata")
        """
        self.timezone = ZoneInfo(timezone)
        logger.info(f"[Scheduler] Initialized with timezone: {timezone}")
    
    def should_execute(self, task: Dict[str, Any], current_time: Optional[datetime] = None) -> bool:
        """
        Determine if a task should execute now based on its schedule.
        
        Args:
            task: Action plan dict with schedule configuration
            current_time: Current time (defaults to now in task's timezone)
        
        Returns:
            True if task should execute now
        """
        if not task.get("enabled", False):
            return False
        
        # Get current time in task's timezone
        task_tz = ZoneInfo(task.get("timezone", DEFAULT_TIMEZONE))
        if current_time is None:
            current_time = datetime.now(task_tz)
        elif current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=task_tz)
        else:
            current_time = current_time.astimezone(task_tz)
        
        frequency = task.get("frequency", "daily")
        last_executed = task.get("last_executed")
        
        # Parse last execution time
        last_exec_dt = None
        if last_executed:
            try:
                # ✅ CRITICAL FIX: Properly handle timezone-aware datetime
                last_exec_dt = datetime.fromisoformat(last_executed)
                
                # If naive datetime, it was stored in task's timezone - localize it properly
                if last_exec_dt.tzinfo is None:
                    # Use localize() to interpret naive datetime as being in task's timezone
                    # This is correct because datetime.now(task_tz).isoformat() produces TZ-aware strings
                    # If we get naive, it means it was stored wrongly, assume task timezone
                    last_exec_dt = last_exec_dt.replace(tzinfo=task_tz)
                    logger.warning(f"[Scheduler] Task '{task.get('name')}' had naive last_executed, assumed {task_tz}")
                else:
                    # Already timezone-aware, convert to task's timezone for comparison
                    last_exec_dt = last_exec_dt.astimezone(task_tz)
                    
            except Exception as e:
                logger.warning(f"[Scheduler] Failed to parse last_executed '{last_executed}': {e}")
        
        # Check based on frequency
        if frequency == "once":
            # Execute only if never executed before
            return last_exec_dt is None
        
        elif frequency == "hourly":
            # Execute if more than 60 minutes since last execution
            if last_exec_dt is None:
                return True
            time_since_last = (current_time - last_exec_dt).total_seconds() / 60
            return time_since_last >= 60
        
        elif frequency == "daily":
            # Execute once per day at specified time window
            time_windows = task.get("time_windows", ["09:00"])
            return self._check_time_window_match(current_time, time_windows, last_exec_dt, "daily")
        
        elif frequency == "twice_daily":
            # Execute at two specific times per day
            time_windows = task.get("time_windows", ["09:00", "17:00"])
            return self._check_time_window_match(current_time, time_windows, last_exec_dt, "twice_daily")
        
        elif frequency == "weekly":
            # Execute on specific days of week at specified time
            days_of_week = task.get("days_of_week", [0])  # Default: Monday
            time_windows = task.get("time_windows", ["09:00"])
            
            # Check if today is a scheduled day
            if current_time.weekday() not in days_of_week:
                return False
            
            return self._check_time_window_match(current_time, time_windows, last_exec_dt, "weekly")
        
        elif frequency == "custom":
            # Execute at custom interval (supports days, minutes, or hours)
            # Priority: days > minutes > hours
            interval_days = task.get("custom_interval_days")
            interval_minutes = task.get("custom_interval_minutes")
            interval_hours = task.get("custom_interval_hours", 6)
            
            # ✅ CRITICAL FIX: Check next_execution FIRST (authoritative source of truth)
            # This prevents premature execution even if last_executed appears old due to:
            # - Update failures, race conditions, or retry logic
            next_execution = task.get("next_execution")
            if next_execution:
                try:
                    next_exec_dt = datetime.fromisoformat(next_execution)
                    
                    # Handle timezone (same logic as last_executed)
                    if next_exec_dt.tzinfo is None:
                        next_exec_dt = next_exec_dt.replace(tzinfo=task_tz)
                    else:
                        next_exec_dt = next_exec_dt.astimezone(task_tz)
                    
                    # If next_execution is in the future, DON'T execute
                    if current_time < next_exec_dt:
                        time_until = (next_exec_dt - current_time).total_seconds() / 60
                        logger.debug(f"[Scheduler] Custom task '{task.get('name')}': "
                                   f"next_execution={next_exec_dt.strftime('%H:%M:%S')} is {time_until:.1f}min in future, skip")
                        return False
                    else:
                        logger.debug(f"[Scheduler] Custom task '{task.get('name')}': "
                                   f"next_execution={next_exec_dt.strftime('%H:%M:%S')} has passed, checking interval")
                        
                except Exception as e:
                    logger.warning(f"[Scheduler] Failed to parse next_execution '{next_execution}': {e}")
            
            # Fallback to last_executed-based check (for legacy plans or if next_execution is None)
            if last_exec_dt is None:
                logger.info(f"[Scheduler] Custom task '{task.get('name')}': Never executed, should run")
                return True
            
            time_since_last_seconds = (current_time - last_exec_dt).total_seconds()
            time_since_last_minutes = time_since_last_seconds / 60
            
            # Check based on interval type (priority order)
            if interval_days:
                threshold_seconds = interval_days * 86400
                should_run = time_since_last_seconds >= threshold_seconds
                logger.debug(f"[Scheduler] Custom (days) task '{task.get('name')}': "
                           f"{time_since_last_seconds:.1f}s since last (threshold: {threshold_seconds}s) = {should_run}")
                return should_run
            elif interval_minutes:
                threshold_seconds = interval_minutes * 60
                should_run = time_since_last_seconds >= threshold_seconds
                logger.info(f"[Scheduler] Custom (minutes) task '{task.get('name')}': "
                          f"Last={last_exec_dt.strftime('%H:%M:%S')}, "
                          f"Now={current_time.strftime('%H:%M:%S')}, "
                          f"Diff={time_since_last_minutes:.2f}min (need {interval_minutes}min) = {should_run}")
                return should_run
            else:
                threshold_seconds = interval_hours * 3600
                should_run = time_since_last_seconds >= threshold_seconds
                logger.debug(f"[Scheduler] Custom (hours) task '{task.get('name')}': "
                           f"{time_since_last_seconds:.1f}s since last (threshold: {threshold_seconds}s) = {should_run}")
                return should_run
        
        else:
            logger.warning(f"[Scheduler] Unknown frequency: {frequency}")
            return False
    
    def _check_time_window_match(
        self, 
        current_time: datetime, 
        time_windows: List[str],
        last_exec_dt: Optional[datetime],
        frequency_type: str
    ) -> bool:
        """
        Check if current time matches any time window and hasn't been executed recently.
        
        Args:
            current_time: Current datetime
            time_windows: List of time strings ["HH:MM", ...]
            last_exec_dt: Last execution datetime
            frequency_type: Type of frequency (for logging)
        
        Returns:
            True if should execute
        """
        current_time_str = current_time.strftime("%H:%M")
        
        for window in time_windows:
            try:
                # Parse window time
                window_hour, window_min = map(int, window.split(":"))
                window_time = time(window_hour, window_min)
                
                # Check if we're within 5 minutes of the window
                window_dt = current_time.replace(
                    hour=window_hour, 
                    minute=window_min, 
                    second=0, 
                    microsecond=0
                )
                time_diff = abs((current_time - window_dt).total_seconds() / 60)
                
                # Within 5-minute window of scheduled time
                if time_diff <= 5:
                    # Check if already executed today
                    if last_exec_dt:
                        # For daily/twice_daily: don't execute if already ran in this window today
                        if frequency_type in ["daily", "twice_daily"]:
                            if last_exec_dt.date() == current_time.date():
                                # Check if last execution was for this same time window
                                last_exec_hour = last_exec_dt.hour
                                if abs(last_exec_hour - window_hour) < 1:
                                    return False
                        
                        # For weekly: don't execute if already ran this week
                        elif frequency_type == "weekly":
                            days_since_last = (current_time.date() - last_exec_dt.date()).days
                            if days_since_last < 7:
                                return False
                    
                    logger.info(f"[Scheduler] Time window match: {window} (current: {current_time_str})")
                    return True
                    
            except Exception as e:
                logger.warning(f"[Scheduler] Failed to parse time window {window}: {e}")
        
        return False
    
    def get_next_execution_time(self, task: Dict[str, Any]) -> Optional[datetime]:
        """
        Calculate the next execution time for a task.
        
        Args:
            task: Action plan dict
        
        Returns:
            Next execution datetime in task's timezone, or None if one-time task completed
        """
        task_tz = ZoneInfo(task.get("timezone", DEFAULT_TIMEZONE))
        current_time = datetime.now(task_tz)
        frequency = task.get("frequency", "daily")
        
        if frequency == "once":
            # One-time tasks don't have a next execution if already executed
            if task.get("last_executed"):
                return None
            return current_time
        
        elif frequency == "hourly":
            # Next hour
            last_executed = task.get("last_executed")
            if last_executed:
                last_dt = datetime.fromisoformat(last_executed).astimezone(task_tz)
                return last_dt + timedelta(hours=1)
            return current_time + timedelta(hours=1)
        
        elif frequency == "daily":
            # Next occurrence of time window
            time_windows = task.get("time_windows", ["09:00"])
            return self._get_next_window_time(current_time, time_windows[0], days_offset=1)
        
        elif frequency == "twice_daily":
            # Next occurrence of either time window
            time_windows = task.get("time_windows", ["09:00", "17:00"])
            next_times = [
                self._get_next_window_time(current_time, window, days_offset=0)
                for window in time_windows
            ]
            # Return earliest future time
            future_times = [t for t in next_times if t > current_time]
            if future_times:
                return min(future_times)
            # If all times today have passed, return first window tomorrow
            return self._get_next_window_time(current_time, time_windows[0], days_offset=1)
        
        elif frequency == "weekly":
            # Next occurrence on scheduled day at time window
            days_of_week = task.get("days_of_week", [0])
            time_windows = task.get("time_windows", ["09:00"])
            window = time_windows[0]
            
            # Find next scheduled day
            current_weekday = current_time.weekday()
            days_ahead = min(
                (day - current_weekday) % 7 if (day - current_weekday) % 7 > 0 
                else 7
                for day in days_of_week
            )
            
            return self._get_next_window_time(current_time, window, days_offset=days_ahead)
        
        elif frequency == "custom":
            # Next interval (supports days, minutes, hours)
            interval_days = task.get("custom_interval_days")
            interval_minutes = task.get("custom_interval_minutes")
            interval_hours = task.get("custom_interval_hours", 6)
            
            last_executed = task.get("last_executed")
            if last_executed:
                last_dt = datetime.fromisoformat(last_executed).astimezone(task_tz)
                if interval_days:
                    return last_dt + timedelta(days=interval_days)
                elif interval_minutes:
                    return last_dt + timedelta(minutes=interval_minutes)
                else:
                    return last_dt + timedelta(hours=interval_hours)
            else:
                # Default to 6 hours if all are None
                interval_hours = interval_hours or 6
                if interval_days:
                    return current_time + timedelta(days=interval_days)
                elif interval_minutes:
                    return current_time + timedelta(minutes=interval_minutes)
                else:
                    return current_time + timedelta(hours=interval_hours)
        
        return None
    
    def _get_next_window_time(
        self, 
        current_time: datetime, 
        window: str, 
        days_offset: int = 0
    ) -> datetime:
        """
        Get next occurrence of a time window.
        
        Args:
            current_time: Current datetime
            window: Time string "HH:MM"
            days_offset: Days to add (0 for today, 1 for tomorrow, etc.)
        
        Returns:
            Next window datetime
        """
        hour, minute = map(int, window.split(":"))
        next_time = current_time.replace(
            hour=hour, 
            minute=minute, 
            second=0, 
            microsecond=0
        ) + timedelta(days=days_offset)
        
        # If days_offset is 0 and time has passed, move to next day
        if days_offset == 0 and next_time <= current_time:
            next_time += timedelta(days=1)
        
        return next_time
    
    def validate_schedule(self, schedule_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a schedule configuration.
        
        Args:
            schedule_config: Dict with frequency, time_windows, etc.
        
        Returns:
            (is_valid, error_message)
        """
        frequency = schedule_config.get("frequency")
        
        # Check frequency is valid
        valid_frequencies = ["once", "hourly", "daily", "twice_daily", "weekly", "custom"]
        if frequency not in valid_frequencies:
            return False, f"Invalid frequency. Must be one of: {', '.join(valid_frequencies)}"
        
        # Validate time windows if present
        time_windows = schedule_config.get("time_windows", [])
        if time_windows:
            for window in time_windows:
                if not self._validate_time_format(window):
                    return False, f"Invalid time format: {window}. Use HH:MM (24-hour format)"
        
        # Frequency-specific validation
        if frequency == "twice_daily":
            if not time_windows or len(time_windows) != 2:
                return False, "twice_daily requires exactly 2 time windows"
        
        elif frequency == "weekly":
            days_of_week = schedule_config.get("days_of_week", [])
            if not days_of_week:
                return False, "weekly frequency requires days_of_week (0-6, Monday-Sunday)"
            if not all(0 <= day <= 6 for day in days_of_week):
                return False, "days_of_week must be integers 0-6 (Monday-Sunday)"
        
        elif frequency == "custom":
            interval_days = schedule_config.get("custom_interval_days")
            interval_minutes = schedule_config.get("custom_interval_minutes")
            interval_hours = schedule_config.get("custom_interval_hours")
            
            # Must have at least one interval type
            if not any([interval_days, interval_minutes, interval_hours]):
                return False, "custom frequency requires at least one of: custom_interval_days, custom_interval_minutes, custom_interval_hours"
            
            # Validate intervals are positive
            if interval_days and interval_days < 1:
                return False, "custom_interval_days must be >= 1"
            if interval_minutes and interval_minutes < 1:
                return False, "custom_interval_minutes must be >= 1"
            if interval_hours and interval_hours < 1:
                return False, "custom_interval_hours must be >= 1"
        
        # Validate timezone
        timezone_str = schedule_config.get("timezone", DEFAULT_TIMEZONE)
        try:
            ZoneInfo(timezone_str)
        except Exception:
            return False, f"Invalid timezone: {timezone_str}"
        
        return True, ""
    
    def _validate_time_format(self, time_str: str) -> bool:
        """Validate time string is in HH:MM format"""
        try:
            hour, minute = map(int, time_str.split(":"))
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except:
            return False
    
    def update_last_executed(self, task_id: str, timestamp: datetime, tasks: List[Dict[str, Any]]) -> bool:
        """
        Update the last_executed timestamp for a task.
        
        Args:
            task_id: Task identifier
            timestamp: Execution timestamp
            tasks: List of all tasks (will be modified in-place)
        
        Returns:
            True if task was found and updated
        """
        for task in tasks:
            if task.get("id") == task_id:
                task["last_executed"] = timestamp.isoformat()
                task["execution_count"] = task.get("execution_count", 0) + 1
                
                # Calculate next execution
                next_exec = self.get_next_execution_time(task)
                task["next_execution"] = next_exec.isoformat() if next_exec else None
                
                logger.info(f"[Scheduler] Updated task {task_id}: last_executed={timestamp.isoformat()}")
                return True
        
        logger.warning(f"[Scheduler] Task {task_id} not found for update")
        return False
