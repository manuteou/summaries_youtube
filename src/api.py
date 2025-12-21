"""
REST API for SynthetIA - FastAPI-based API for external integrations.
Run with: uvicorn api:app --reload --port 8001
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_database, Project, Tag
from scheduler import get_scheduler, get_alert_manager

# --- FastAPI App ---
app = FastAPI(
    title="SynthetIA API",
    description="API REST pour intégration externe de SynthetIA",
    version="1.0.0"
)

# CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str
    created_at: str

class TagCreate(BaseModel):
    name: str
    color: str = "#FF4B4B"

class TagResponse(BaseModel):
    id: int
    name: str
    color: str

class SynthesisResponse(BaseModel):
    id: int
    project_id: Optional[int]
    title: str
    summary: str
    sources: List[Dict]
    summary_type: str
    created_at: str

class ScheduledTaskCreate(BaseModel):
    name: str
    search_query: str
    schedule_type: str  # "daily", "weekly", "interval"
    schedule_time: str  # "HH:MM" or "Xh"
    summary_type: str = "medium"
    project_id: int = 1

class ScheduledTaskResponse(BaseModel):
    id: str
    name: str
    search_query: str
    schedule_type: str
    schedule_time: str
    summary_type: str
    project_id: int
    enabled: bool
    last_run: Optional[str]
    next_run: Optional[str]

class AlertResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    created_at: str
    read: bool

class StatsResponse(BaseModel):
    total_syntheses: int
    total_projects: int
    total_tags: int
    top_tags: List[Dict]
    recent_activity: List[Dict]


# --- Health Check ---

@app.get("/")
async def root():
    return {"status": "ok", "service": "SynthetIA API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# --- Projects ---

@app.get("/projects", response_model=List[ProjectResponse])
async def get_projects():
    """Get all projects."""
    db = get_database()
    projects = db.get_all_projects()
    return [ProjectResponse(
        id=p.id, name=p.name, description=p.description, created_at=p.created_at
    ) for p in projects]

@app.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """Create a new project."""
    db = get_database()
    project_id = db.create_project(project.name, project.description)
    created = db.get_project(project_id)
    return ProjectResponse(
        id=created.id, name=created.name, 
        description=created.description, created_at=created.created_at
    )

@app.delete("/projects/{project_id}")
async def delete_project(project_id: int):
    """Delete a project."""
    if project_id == 1:
        raise HTTPException(status_code=400, detail="Cannot delete default project")
    db = get_database()
    db.delete_project(project_id)
    return {"status": "deleted"}


# --- Tags ---

@app.get("/tags", response_model=List[TagResponse])
async def get_tags():
    """Get all tags."""
    db = get_database()
    tags = db.get_all_tags()
    return [TagResponse(id=t.id, name=t.name, color=t.color) for t in tags]

@app.post("/tags", response_model=TagResponse)
async def create_tag(tag: TagCreate):
    """Create a new tag."""
    db = get_database()
    tag_id = db.create_tag(tag.name, tag.color)
    return TagResponse(id=tag_id, name=tag.name, color=tag.color)


# --- Syntheses ---

@app.get("/syntheses", response_model=List[SynthesisResponse])
async def get_syntheses(
    project_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get syntheses with optional filtering."""
    db = get_database()
    syntheses = db.get_all_syntheses(project_id=project_id, search=search, limit=limit)
    return [SynthesisResponse(
        id=s['id'],
        project_id=s['project_id'],
        title=s['title'],
        summary=s['summary'],
        sources=s['sources'],
        summary_type=s['summary_type'],
        created_at=s['created_at']
    ) for s in syntheses]

@app.get("/syntheses/{synthesis_id}", response_model=SynthesisResponse)
async def get_synthesis(synthesis_id: int):
    """Get a specific synthesis."""
    db = get_database()
    s = db.get_synthesis(synthesis_id)
    if not s:
        raise HTTPException(status_code=404, detail="Synthesis not found")
    return SynthesisResponse(
        id=s['id'],
        project_id=s['project_id'],
        title=s['title'],
        summary=s['summary'],
        sources=s['sources'],
        summary_type=s['summary_type'],
        created_at=s['created_at']
    )

@app.delete("/syntheses/{synthesis_id}")
async def delete_synthesis(synthesis_id: int):
    """Delete a synthesis."""
    db = get_database()
    db.delete_synthesis(synthesis_id)
    return {"status": "deleted"}


# --- Scheduled Tasks ---

@app.get("/tasks", response_model=List[ScheduledTaskResponse])
async def get_scheduled_tasks():
    """Get all scheduled tasks."""
    scheduler = get_scheduler()
    tasks = scheduler.get_all_tasks()
    return [ScheduledTaskResponse(
        id=t.id, name=t.name, search_query=t.search_query,
        schedule_type=t.schedule_type, schedule_time=t.schedule_time,
        summary_type=t.summary_type, project_id=t.project_id,
        enabled=t.enabled, last_run=t.last_run, next_run=t.next_run
    ) for t in tasks]

@app.post("/tasks", response_model=ScheduledTaskResponse)
async def create_scheduled_task(task: ScheduledTaskCreate):
    """Create a new scheduled task."""
    scheduler = get_scheduler()
    t = scheduler.add_task(
        name=task.name,
        search_query=task.search_query,
        schedule_type=task.schedule_type,
        schedule_time=task.schedule_time,
        summary_type=task.summary_type,
        project_id=task.project_id
    )
    return ScheduledTaskResponse(
        id=t.id, name=t.name, search_query=t.search_query,
        schedule_type=t.schedule_type, schedule_time=t.schedule_time,
        summary_type=t.summary_type, project_id=t.project_id,
        enabled=t.enabled, last_run=t.last_run, next_run=t.next_run
    )

@app.delete("/tasks/{task_id}")
async def delete_scheduled_task(task_id: str):
    """Delete a scheduled task."""
    scheduler = get_scheduler()
    if scheduler.delete_task(task_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Task not found")

@app.post("/tasks/{task_id}/toggle")
async def toggle_task(task_id: str):
    """Toggle task enabled/disabled."""
    scheduler = get_scheduler()
    result = scheduler.toggle_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"enabled": result}


# --- Alerts ---

@app.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(unread_only: bool = False):
    """Get alerts."""
    alert_mgr = get_alert_manager()
    if unread_only:
        alerts = alert_mgr.get_unread_alerts()
    else:
        alerts = alert_mgr.get_all_alerts()
    return [AlertResponse(
        id=a.id, type=a.type, title=a.title, 
        message=a.message, created_at=a.created_at, read=a.read
    ) for a in alerts]

@app.post("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str):
    """Mark an alert as read."""
    alert_mgr = get_alert_manager()
    alert_mgr.mark_read(alert_id)
    return {"status": "marked_read"}

@app.post("/alerts/read-all")
async def mark_all_alerts_read():
    """Mark all alerts as read."""
    alert_mgr = get_alert_manager()
    alert_mgr.mark_all_read()
    return {"status": "all_marked_read"}


# --- Stats ---

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get usage statistics."""
    db = get_database()
    stats = db.get_stats()
    return StatsResponse(**stats)


# --- Run instructions ---
if __name__ == "__main__":
    import uvicorn
    print("Starting SynthetIA API on http://localhost:8001")
    print("Documentation: http://localhost:8001/docs")
    uvicorn.run(app, host="0.0.0.0", port=8001)
