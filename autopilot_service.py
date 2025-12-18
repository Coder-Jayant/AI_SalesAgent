"""
Autopilot Background Service

Standalone Python service that runs continuously in the background,
monitoring and processing emails based on autopilot rules independent
of the Streamlit UI.

Usage:
    python autopilot_service.py

Configuration via environment variables:
    AUTOPILOT_SERVICE_INTERVAL: Check interval in seconds (default: 300)
    AUTOPILOT_SERVICE_HANDS_FREE: Enable hands-free mode (default: false)
    AUTOPILOT_SERVICE_LOG_LEVEL: Logging level (default: INFO)
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configuration
CHECK_INTERVAL = int(os.getenv("AUTOPILOT_SERVICE_INTERVAL", "200"))  # seconds (5 minutes default)
HANDS_FREE = os.getenv("AUTOPILOT_SERVICE_HANDS_FREE", "false").lower() == "true"
LOG_LEVEL = os.getenv("AUTOPILOT_SERVICE_LOG_LEVEL", "INFO")
LOG_FILE = "autopilot_service.log"

# Global flag for graceful shutdown
shutdown_requested = False


def setup_logging():
    """Configure logging with file and console output"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    # File handler (rotating daily)
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=7,  # Keep 7 days of logs
        encoding='utf-8'  # Use UTF-8 encoding for file
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)
    
    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Set UTF-8 encoding for console on Windows
    try:
        import io
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # If this fails, continue with default encoding
    
    logger.addHandler(console_handler)
    
    return logger


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def is_service_enabled() -> bool:
    """Check if autopilot service is enabled in state file"""
    try:
        from autopilot import _load_state
        state = _load_state()
        return state.get("service_enabled", False)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error checking service state: {e}")
        return False


def update_last_run_timestamp():
    """Update the last run timestamp in state file"""
    try:
        from autopilot import _load_state, _save_state
        state = _load_state()
        state["service_last_run"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        _save_state(state)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to update last run timestamp: {e}")


def run_service():
    """Main service loop"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Autopilot Service Starting")
    logger.info(f"Check Interval: {CHECK_INTERVAL} seconds")
    logger.info(f"Hands-Free Mode: {HANDS_FREE}")
    logger.info(f"Log Level: {LOG_LEVEL}")
    logger.info("=" * 60)
    
    # Clear any stale stop flags on startup
    try:
        from autopilot_control import clear_autopilot_stop_flag
        clear_autopilot_stop_flag()
        logger.info("Cleared any stale autopilot stop flags")
    except Exception as e:
        logger.warning(f"Could not clear stop flag: {e}")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    iteration = 0
    last_execution_time = None
    
    try:
        while not shutdown_requested:
            iteration += 1
            current_time = datetime.now(ZoneInfo("Asia/Kolkata"))
            
            # Check if service is enabled in state
            if not is_service_enabled():
                logger.info(f"[Iteration {iteration}] Service disabled in state file, skipping execution")
                # Still sleep but check again
                time.sleep(min(30, CHECK_INTERVAL))  # Check every 30 seconds if disabled
                continue
            
            # CRITICAL: Clear any stop flags before execution
            # This prevents false stops from UI toggles or stale flags
            try:
                from autopilot_control import clear_autopilot_stop_flag
                clear_autopilot_stop_flag()
                logger.debug(f"[Iteration {iteration}] Cleared autopilot stop flag before execution")
            except Exception as clear_err:
                logger.warning(f"[Iteration {iteration}] Could not clear stop flag: {clear_err}")
            
            logger.info(f"[Iteration {iteration}] Checking for emails at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            try:
                # Reload environment variables to get fresh credentials
                load_dotenv(override=True)
                
                # Log credential info (not the actual password)
                ews_email = os.getenv("EWS_EMAIL", "")
                ews_host = os.getenv("EWS_HOST", "")
                if ews_email and ews_host:
                    logger.debug(f"[Iteration {iteration}] Using EWS credentials: {ews_email}@{ews_host}")
                else:
                    logger.warning(f"[Iteration {iteration}] EWS credentials not found in .env")
                
                # Update ews_tools2 runtime globals with fresh credentials
                try:
                    import ews_tools2
                    ews_tools2.EMAIL = os.getenv("EWS_EMAIL", "")
                    ews_tools2.PASSWORD = os.getenv("EWS_PASSWORD", "")
                    ews_tools2.EXCHANGE_HOST = os.getenv("EWS_HOST", "")
                    
                    # Clear cached account to force reconnection with new credentials
                    ews_tools2._account = None
                    ews_tools2._account_config = None
                    
                    logger.debug(f"[Iteration {iteration}] EWS credentials reloaded from .env")
                except Exception as cred_err:
                    logger.warning(f"[Iteration {iteration}] Failed to update EWS runtime globals: {cred_err}")
                
                # Import here to avoid issues if modules aren't ready at startup
                from autopilot import autopilot_once, AUTOPILOT_MAX_ACTIONS
                
                # Execute autopilot sweep (ignore stop flag - service has its own control)
                max_actions = AUTOPILOT_MAX_ACTIONS
                logs = autopilot_once(max_actions=max_actions, hands_free=HANDS_FREE, ignore_stop_flag=True)
                
                if logs:
                    logger.info(f"[Iteration {iteration}] Autopilot processed {len(logs)} item(s)")
                    
                    for log_entry in logs:
                        logger.info(f"  {log_entry}")
                    
                    last_execution_time = current_time
                    update_last_run_timestamp()
                else:
                    logger.debug(f"[Iteration {iteration}] No emails to process")
                
            except Exception as e:
                logger.exception(f"[Iteration {iteration}] Error executing autopilot: {e}")
            
            # Sleep for the configured interval (unless shutdown requested)
            if not shutdown_requested:
                logger.debug(f"[Iteration {iteration}] Sleeping for {CHECK_INTERVAL} seconds...")
                
                # Sleep in small chunks to allow faster shutdown response
                sleep_chunk = 1  # 1 second chunks
                remaining = CHECK_INTERVAL
                
                while remaining > 0 and not shutdown_requested:
                    time.sleep(min(sleep_chunk, remaining))
                    remaining -= sleep_chunk
    
    except Exception as e:
        logger.exception(f"Fatal error in service main loop: {e}")
        return 1
    
    finally:
        logger.info("=" * 60)
        logger.info("Autopilot Service Stopped")
        if last_execution_time:
            logger.info(f"Last execution: {last_execution_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Total iterations: {iteration}")
        logger.info("=" * 60)
    
    return 0


def main():
    """Entry point for the service"""
    # Setup logging first
    logger = setup_logging()
    
    try:
        # Run the service
        exit_code = run_service()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Service interrupted by user (Ctrl+C)")
        sys.exit(0)
    
    except Exception as e:
        logger.exception(f"Unexpected error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
