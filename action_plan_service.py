"""
Action Plan Background Service

Standalone Python service that runs continuously in the background,
checking and executing scheduled action plans independent of the
Streamlit UI and autopilot mode.

Usage:
    python action_plan_service.py

Configuration via environment variables:
    ACTION_PLAN_SERVICE_INTERVAL: Check interval in seconds (default: 30)
    ACTION_PLAN_SERVICE_HANDS_FREE: Enable hands-free mode (default: false)
    ACTION_PLAN_SERVICE_LOG_LEVEL: Logging level (default: INFO)
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
CHECK_INTERVAL = int(os.getenv("ACTION_PLAN_SERVICE_INTERVAL", "30"))  # seconds
HANDS_FREE = os.getenv("ACTION_PLAN_SERVICE_HANDS_FREE", "false").lower() == "true"
LOG_LEVEL = os.getenv("ACTION_PLAN_SERVICE_LOG_LEVEL", "INFO")
LOG_FILE = "action_plan_service.log"

# Global flag for graceful shutdown
shutdown_requested = False


def setup_logging():
    """Configure logging for the service."""
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.stream = open(console_handler.stream.fileno(), 'w', encoding='utf-8', errors='replace')
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)
    
    # File handler (rotating daily) with UTF-8 encoding
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=7,  # Keep 7 days of logs
        encoding='utf-8',
        errors='replace'
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)
    
    return logger


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def run_service():
    """Main service loop"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Action Plan Service Starting")
    logger.info(f"Check Interval: {CHECK_INTERVAL} seconds")
    logger.info(f"Hands-Free Mode: {HANDS_FREE}")
    logger.info(f"Log Level: {LOG_LEVEL}")
    logger.info("=" * 60)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    iteration = 0
    last_execution_time = None
    
    try:
        while not shutdown_requested:
            iteration += 1
            current_time = datetime.now(ZoneInfo("Asia/Kolkata"))
            
            logger.info(f"[Iteration {iteration}] Checking scheduled plans at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            try:
                # Reload environment variables to get fresh credentials
                load_dotenv(override=True)
                
                # Force reload of ews_tools2 module to pick up new credentials
                import sys
                if 'ews_tools2' in sys.modules:
                    import importlib
                    import ews_tools2
                    importlib.reload(ews_tools2)
                    logger.debug(f"[Iteration {iteration}] Reloaded EWS credentials")
                    
                    # Update ews_tools2 globals with fresh credentials from .env
                    import os
                    ews_tools2.EWS_EMAIL = os.getenv('EWS_EMAIL')
                    ews_tools2.EWS_PASSWORD = os.getenv('EWS_PASSWORD')
                    ews_tools2.EWS_HOST = os.getenv('EWS_HOST')
                    
                    # Clear the account config to force reconnection with new credentials
                    if hasattr(ews_tools2, '_account_config'):
                        ews_tools2._account_config = None
                    logger.debug(f"[Iteration {iteration}] Updated EWS credentials: {ews_tools2.EWS_EMAIL}")
                
                # Import here to avoid issues if modules aren't ready at startup
                from action_plans.executor import execute_scheduled_plans
                
                # Execute scheduled plans
                results = execute_scheduled_plans(hands_free=HANDS_FREE)
                
                if results:
                    logger.info(f"[Iteration {iteration}] Executed {len(results)} action plan(s)")
                    
                    for result in results:
                        plan_name = result.get("plan_name", "Unknown")
                        status = result.get("status", "unknown")
                        
                        if status == "success":
                            logger.info(f"  [OK] {plan_name} - Success")
                        else:
                            error = result.get("error", "Unknown error")
                            logger.warning(f"  [FAIL] {plan_name} - Failed: {error}")
                    
                    last_execution_time = current_time
                else:
                    logger.debug(f"[Iteration {iteration}] No plans due for execution")
                
            except Exception as e:
                logger.exception(f"[Iteration {iteration}] Error executing scheduled plans: {e}")
            
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
        logger.info("Action Plan Service Stopped")
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
