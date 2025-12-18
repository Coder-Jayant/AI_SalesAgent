def format_frequency_display(plan: dict) -> str:
    """
    Format frequency for user-friendly display.
    
    Args:
        plan: Action plan dictionary
    
    Returns:
        Human-readable frequency string
    """
    freq = plan.get("frequency", "daily")
    
    if freq == "once":
        return "Once"
    elif freq == "hourly":
        return "Every hour"
    elif freq == "daily":
        return "Daily"
    elif freq == "twice_daily":
        return "Twice daily"
    elif freq == "weekly":
        days_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        days = plan.get("days_of_week", [0])
        day_names = [days_map.get(d, str(d)) for d in days]
        return f"Weekly ({', '.join(day_names)})"
    elif freq == "custom":
        # Show the actual interval
        interval_days = plan.get("custom_interval_days")
        interval_minutes = plan.get("custom_interval_minutes")
        interval_hours = plan.get("custom_interval_hours")
        
        if interval_days:
            return f"Every {interval_days} day{'s' if interval_days > 1 else ''}"
        elif interval_minutes:
            if interval_minutes == 1:
                return "Every minute"
            elif interval_minutes == 60:
                return "Every hour"
            else:
                return f"Every {interval_minutes} minute{'s' if interval_minutes > 1 else ''}"
        elif interval_hours:
            return f"Every {interval_hours} hour{'s' if interval_hours > 1 else ''}"
        else:
            return "Custom"
    else:
        return freq.replace("_", " ").title()
