"""
Scheduler module for SynthetIA - Automated synthesis tasks.
Uses APScheduler for background job scheduling.
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class ScheduledTask:
    """Represents a scheduled synthesis task."""
    id: str
    name: str
    search_query: str
    schedule_type: str  # "daily", "weekly", "interval"
    schedule_time: str  # "HH:MM" for daily/weekly, "Xh" for interval
    summary_type: str
    project_id: int
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: str = ""


class SchedulerManager:
    """
    Manages scheduled synthesis tasks.
    Note: Full APScheduler integration requires running a separate process.
    This implementation stores task configs that can be executed by an external scheduler.
    """
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            config_path = os.path.join(data_dir, "scheduler_config.json")
        
        self.config_path = config_path
        self._load_config()
    
    def _load_config(self):
        """Load scheduler configuration from JSON file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = [ScheduledTask(**t) for t in data.get('tasks', [])]
            except Exception as e:
                print(f"Error loading scheduler config: {e}")
                self.tasks = []
        else:
            self.tasks = []
    
    def _save_config(self):
        """Save scheduler configuration to JSON file."""
        data = {
            'tasks': [asdict(t) for t in self.tasks],
            'updated_at': datetime.now().isoformat()
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_task(self, name: str, search_query: str, schedule_type: str,
                 schedule_time: str, summary_type: str = "medium",
                 project_id: int = 1) -> ScheduledTask:
        """
        Add a new scheduled task.
        
        Args:
            name: Task name
            search_query: YouTube search query
            schedule_type: "daily", "weekly", or "interval"
            schedule_time: Time specification (e.g., "09:00" or "6h")
            summary_type: Type of synthesis
            project_id: Project to save results to
            
        Returns:
            Created task
        """
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.tasks)}"
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            search_query=search_query,
            schedule_type=schedule_type,
            schedule_time=schedule_time,
            summary_type=summary_type,
            project_id=project_id,
            enabled=True,
            created_at=datetime.now().isoformat(),
            next_run=self._calculate_next_run(schedule_type, schedule_time)
        )
        
        self.tasks.append(task)
        self._save_config()
        return task
    
    def _calculate_next_run(self, schedule_type: str, schedule_time: str) -> str:
        """Calculate next run time based on schedule."""
        now = datetime.now()
        
        if schedule_type == "daily":
            # Parse time HH:MM
            hour, minute = map(int, schedule_time.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        
        elif schedule_type == "weekly":
            # Parse time HH:MM, run every Monday
            hour, minute = map(int, schedule_time.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0 and next_run <= now:
                days_until_monday = 7
            next_run += timedelta(days=days_until_monday)
        
        elif schedule_type == "interval":
            # Parse interval (e.g., "6h", "30m")
            value = int(schedule_time[:-1])
            unit = schedule_time[-1]
            if unit == 'h':
                next_run = now + timedelta(hours=value)
            elif unit == 'm':
                next_run = now + timedelta(minutes=value)
            else:
                next_run = now + timedelta(hours=1)
        
        else:
            next_run = now + timedelta(hours=24)
        
        return next_run.isoformat()
    
    def get_all_tasks(self) -> List[ScheduledTask]:
        """Get all scheduled tasks."""
        return self.tasks
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a specific task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def update_task(self, task_id: str, **kwargs) -> Optional[ScheduledTask]:
        """Update a task's properties."""
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                # Recalculate next run if schedule changed
                if 'schedule_type' in kwargs or 'schedule_time' in kwargs:
                    task.next_run = self._calculate_next_run(
                        task.schedule_type, task.schedule_time
                    )
                self._save_config()
                return task
        return None
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks.pop(i)
                self._save_config()
                return True
        return False
    
    def toggle_task(self, task_id: str) -> Optional[bool]:
        """Toggle task enabled/disabled state."""
        task = self.get_task(task_id)
        if task:
            task.enabled = not task.enabled
            self._save_config()
            return task.enabled
        return None
    
    def get_due_tasks(self) -> List[ScheduledTask]:
        """Get tasks that are due to run."""
        now = datetime.now().isoformat()
        due_tasks = []
        for task in self.tasks:
            if task.enabled and task.next_run and task.next_run <= now:
                due_tasks.append(task)
        return due_tasks
    
    def mark_task_run(self, task_id: str):
        """Mark a task as having been run and update next run time."""
        task = self.get_task(task_id)
        if task:
            task.last_run = datetime.now().isoformat()
            task.next_run = self._calculate_next_run(task.schedule_type, task.schedule_time)
            self._save_config()


# --- Alert System ---

@dataclass
class Alert:
    """Represents an alert/notification."""
    id: str
    type: str  # "new_video", "synthesis_complete", "error"
    title: str
    message: str
    created_at: str
    read: bool = False
    data: Optional[Dict] = None


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            config_path = os.path.join(data_dir, "alerts.json")
        
        self.config_path = config_path
        self._load_alerts()
    
    def _load_alerts(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.alerts = [Alert(**a) for a in data.get('alerts', [])]
            except:
                self.alerts = []
        else:
            self.alerts = []
    
    def _save_alerts(self):
        # Keep only last 100 alerts
        self.alerts = self.alerts[-100:]
        data = {'alerts': [asdict(a) for a in self.alerts]}
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_alert(self, alert_type: str, title: str, message: str, 
                  data: Dict = None) -> Alert:
        """Add a new alert."""
        alert = Alert(
            id=f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.alerts)}",
            type=alert_type,
            title=title,
            message=message,
            created_at=datetime.now().isoformat(),
            read=False,
            data=data
        )
        self.alerts.append(alert)
        self._save_alerts()
        return alert
    
    def get_unread_alerts(self) -> List[Alert]:
        """Get all unread alerts."""
        return [a for a in self.alerts if not a.read]
    
    def get_all_alerts(self, limit: int = 50) -> List[Alert]:
        """Get recent alerts."""
        return self.alerts[-limit:][::-1]  # Most recent first
    
    def mark_read(self, alert_id: str):
        """Mark an alert as read."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.read = True
                self._save_alerts()
                return
    
    def mark_all_read(self):
        """Mark all alerts as read."""
        for alert in self.alerts:
            alert.read = True
        self._save_alerts()
    
    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts = []
        self._save_alerts()


# Singletons
_scheduler_instance = None
_alert_instance = None

def get_scheduler() -> SchedulerManager:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerManager()
    return _scheduler_instance

def get_alert_manager() -> AlertManager:
    global _alert_instance
    if _alert_instance is None:
        _alert_instance = AlertManager()
    return _alert_instance
