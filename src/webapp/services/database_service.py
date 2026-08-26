"""
Simplified database service for action logging
Uses JSON file storage for simplicity
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class ActionLog:
    """Action log entry"""
    id: str
    timestamp: str
    action_type: str
    user_id: Optional[str]
    username: Optional[str]
    device_id: Optional[str]
    details: Dict[str, Any]
    client_ip: Optional[str] = None
    success: bool = True


class DatabaseService:
    """Simplified database service using JSON file storage"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.action_logs_file = self.data_dir / "action_logs.json"
        self.lock = Lock()
        
        # Initialize files if they don't exist
        self._initialize_files()
        
        logger.info(f"Database service initialized with data directory: {self.data_dir}")
    
    def _initialize_files(self):
        """Initialize JSON files if they don't exist"""
        if not self.action_logs_file.exists():
            with open(self.action_logs_file, 'w') as f:
                json.dump([], f)
            logger.info("Created action_logs.json file")
    
    def _load_action_logs(self) -> List[Dict[str, Any]]:
        """Load action logs from JSON file"""
        try:
            with open(self.action_logs_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading action logs: {e}")
            return []
    
    def _save_action_logs(self, logs: List[Dict[str, Any]]):
        """Save action logs to JSON file"""
        try:
            with open(self.action_logs_file, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving action logs: {e}")
    
    def add_action_log(self, action_log: ActionLog) -> bool:
        """Add a new action log entry"""
        with self.lock:
            try:
                logs = self._load_action_logs()
                logs.append(asdict(action_log))
                self._save_action_logs(logs)
                logger.debug(f"Added action log: {action_log.id}")
                return True
            except Exception as e:
                logger.error(f"Error adding action log: {e}")
                return False
    
    def get_action_logs(self, limit: Optional[int] = None, 
                       action_type: Optional[str] = None,
                       user_id: Optional[str] = None,
                       device_id: Optional[str] = None) -> List[ActionLog]:
        """Get action logs with optional filtering"""
        try:
            logs_data = self._load_action_logs()
            
            # Convert to ActionLog objects
            logs = [ActionLog(**log_data) for log_data in logs_data]
            
            # Apply filters
            if action_type:
                logs = [log for log in logs if log.action_type == action_type]
            if user_id:
                logs = [log for log in logs if log.user_id == user_id]
            if device_id:
                logs = [log for log in logs if log.device_id == device_id]
            
            # Sort by timestamp (newest first)
            logs.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            if limit:
                logs = logs[:limit]
            
            return logs
        except Exception as e:
            logger.error(f"Error getting action logs: {e}")
            return []
    
    def get_recent_action_logs(self, limit: int = 50) -> List[ActionLog]:
        """Get recent action logs"""
        return self.get_action_logs(limit=limit)
    
    def get_action_statistics(self) -> Dict[str, Any]:
        """Get action statistics"""
        try:
            logs = self.get_action_logs()
            
            # Count by action type
            action_counts = {}
            success_count = 0
            failure_count = 0
            
            for log in logs:
                action_counts[log.action_type] = action_counts.get(log.action_type, 0) + 1
                if log.success:
                    success_count += 1
                else:
                    failure_count += 1
            
            return {
                "total_actions": len(logs),
                "successful_actions": success_count,
                "failed_actions": failure_count,
                "action_type_counts": action_counts,
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting action statistics: {e}")
            return {
                "total_actions": 0,
                "successful_actions": 0,
                "failed_actions": 0,
                "action_type_counts": {},
                "last_updated": datetime.now().isoformat()
            }
    
    def clear_old_logs(self, days_to_keep: int = 30) -> int:
        """Clear logs older than specified days"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            logs = self.get_action_logs()
            
            # Filter out old logs
            recent_logs = []
            removed_count = 0
            
            for log in logs:
                try:
                    log_timestamp = datetime.fromisoformat(log.timestamp).timestamp()
                    if log_timestamp >= cutoff_date:
                        recent_logs.append(log)
                    else:
                        removed_count += 1
                except ValueError:
                    # Keep logs with invalid timestamps
                    recent_logs.append(log)
            
            # Save filtered logs
            with self.lock:
                self._save_action_logs([asdict(log) for log in recent_logs])
            
            logger.info(f"Cleared {removed_count} old action logs")
            return removed_count
        except Exception as e:
            logger.error(f"Error clearing old logs: {e}")
            return 0


# Global instance
_database_service = None


def get_database_service() -> DatabaseService:
    """Get the global database service instance"""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service
