"""
Autopilot Stop Flag Control

NOTE: These stop flags are only used for MANUAL autopilot runs triggered from the UI
(e.g., "Run Now" button). The background autopilot SERVICE ignores these flags and 
uses the service_enabled state in autopilot_state.json instead.

Creates a stop flag file that manual autopilot runs can check on each iteration.
When user manually stops autopilot via UI, flag is set to stop the sweep immediately.
"""

import json
from pathlib import Path

AUTOPILOT_STOP_FLAG = "autopilot_stop.flag"

def set_autopilot_stop_flag():
    """Signal autopilot to stop immediately"""
    Path(AUTOPILOT_STOP_FLAG).write_text(json.dumps({
        "stop": True,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }))

def clear_autopilot_stop_flag():
    """Clear the stop flag when autopilot is enabled"""
    try:
        Path(AUTOPILOT_STOP_FLAG).unlink(missing_ok=True)
    except:
        pass

def should_autopilot_stop() -> bool:
    """Check if autopilot should stop"""
    try:
        if Path(AUTOPILOT_STOP_FLAG).exists():
            return True
    except:
        pass
    return False
