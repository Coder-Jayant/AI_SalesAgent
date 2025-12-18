"""
Action Plan Storage Backend

Handles atomic file operations with backup and recovery.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ActionPlanStorage:
    """Thread-safe storage backend for action plans with atomic writes and auto-backup"""
    
    def __init__(self, filepath: str = "action_plans_state.json"):
        self.filepath = Path(filepath)
        self.backup_dir = Path("action_plans_backups")
        self.backup_dir.mkdir(exist_ok=True)
        logger.info(f"[ActionPlanStorage] Initialized with file: {self.filepath}")
    
    def load(self) -> Dict[str, Any]:
        """
        Load state from file with error recovery.
        Falls back to backup if main file is corrupted.
        """
        try:
            if self.filepath.exists():
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    logger.debug(f"Loaded {len(state.get('action_plans', []))} action plans")
                    return state
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in action plans file: {e}")
            return self._restore_from_backup()
        except Exception as e:
            logger.error(f"Failed to load action plans: {e}")
            return self._restore_from_backup()
        
        # File doesn't exist, return empty state
        logger.info("No existing action plans file, starting fresh")
        return {"action_plans": [], "execution_history": []}
    
    def save(self, state: Dict[str, Any]):
        """
        Save state with atomic write and automatic backup.
        
        Process:
        1. Create backup of current file
        2. Write to temporary file
        3. Atomically rename temp file to main file
        4. Clean up old backups (keep last 10)
        """
        try:
            # Create backup first if file exists
            if self.filepath.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.backup_dir / f"action_plans_{timestamp}.json"
                shutil.copy2(self.filepath, backup_path)
                logger.debug(f"Created backup: {backup_path}")
                
                # Keep only last 10 backups
                backups = sorted(self.backup_dir.glob("action_plans_*.json"))
                for old_backup in backups[:-10]:
                    old_backup.unlink()
                    logger.debug(f"Removed old backup: {old_backup}")
            
            # Atomic write using temporary file
            temp_path = self.filepath.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
            
            # Atomic rename
            temp_path.replace(self.filepath)
            
            plan_count = len(state.get('action_plans', []))
            logger.info(f"[ActionPlanStorage] Saved {plan_count} action plans successfully")
            
        except Exception as e:
            logger.exception("Failed to save action plans")
            raise RuntimeError(f"Failed to save action plans: {e}")
    
    def _restore_from_backup(self) -> Dict[str, Any]:
        """
        Restore from most recent backup file.
        
        Returns:
            Restored state or empty state if no backups exist
        """
        backups = sorted(self.backup_dir.glob("action_plans_*.json"))
        if not backups:
            logger.warning("No backups available for restoration")
            return {"action_plans": [], "execution_history": []}
        
        # Try backups from newest to oldest
        for backup in reversed(backups):
            try:
                with open(backup, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    logger.info(f"Successfully restored from backup: {backup}")
                    return state
            except Exception as e:
                logger.error(f"Failed to restore from backup {backup}: {e}")
                continue
        
        logger.error("All backup restoration attempts failed")
        return {"action_plans": [], "execution_history": []}
