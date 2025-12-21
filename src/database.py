"""
Database module for SynthetIA - SQLite persistence layer.
Handles projects, syntheses, and tags storage.
"""
import sqlite3
import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict


# --- Data Models ---

@dataclass
class Project:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Tag:
    id: Optional[int] = None
    name: str = ""
    color: str = "#FF4B4B"  # Default SynthetIA color


@dataclass
class Synthesis:
    id: Optional[int] = None
    project_id: Optional[int] = None
    title: str = ""
    summary: str = ""
    sources: str = ""  # JSON string of source_info
    summary_type: str = "medium"
    created_at: str = ""
    updated_at: str = ""
    

# --- Database Manager ---

class DatabaseManager:
    """SQLite database manager for SynthetIA."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default: store in src/data/synthetia.db
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "synthetia.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#FF4B4B'
            )
        ''')
        
        # Syntheses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS syntheses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                sources TEXT DEFAULT '[]',
                summary_type TEXT DEFAULT 'medium',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
            )
        ''')
        
        # Synthesis-Tags junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS synthesis_tags (
                synthesis_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (synthesis_id, tag_id),
                FOREIGN KEY (synthesis_id) REFERENCES syntheses(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        ''')
        
        # Create default project if none exists
        cursor.execute("SELECT COUNT(*) FROM projects")
        if cursor.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO projects (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
                ("Général", "Projet par défaut", now, now)
            )
        
        conn.commit()
        conn.close()
    
    # --- Projects CRUD ---
    
    def create_project(self, name: str, description: str = "") -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO projects (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name, description, now, now)
        )
        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return project_id
    
    def get_all_projects(self) -> List[Project]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [Project(**dict(row)) for row in rows]
    
    def get_project(self, project_id: int) -> Optional[Project]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        conn.close()
        return Project(**dict(row)) if row else None
    
    def update_project(self, project_id: int, name: str = None, description: str = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(project_id)
        
        cursor.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        conn.close()
    
    def delete_project(self, project_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()
    
    # --- Tags CRUD ---
    
    def create_tag(self, name: str, color: str = "#FF4B4B") -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)",
            (name, color)
        )
        # Get the id (works for both insert and existing)
        cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
        tag_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return tag_id
    
    def get_all_tags(self) -> List[Tag]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tags ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [Tag(**dict(row)) for row in rows]
    
    def delete_tag(self, tag_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        conn.commit()
        conn.close()
    
    # --- Syntheses CRUD ---
    
    def save_synthesis(self, title: str, summary: str, sources: List[Dict], 
                       project_id: int = None, summary_type: str = "medium",
                       tag_ids: List[int] = None) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # If no project specified, use default (id=1)
        if project_id is None:
            project_id = 1
        
        cursor.execute('''
            INSERT INTO syntheses (project_id, title, summary, sources, summary_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (project_id, title, summary, json.dumps(sources, ensure_ascii=False), summary_type, now, now))
        
        synthesis_id = cursor.lastrowid
        
        # Add tags if provided
        if tag_ids:
            for tag_id in tag_ids:
                cursor.execute(
                    "INSERT OR IGNORE INTO synthesis_tags (synthesis_id, tag_id) VALUES (?, ?)",
                    (synthesis_id, tag_id)
                )
        
        conn.commit()
        conn.close()
        return synthesis_id
    
    def get_all_syntheses(self, project_id: int = None, tag_id: int = None, 
                          search: str = None, limit: int = 50) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT DISTINCT s.* FROM syntheses s"
        params = []
        conditions = []
        
        if tag_id:
            query += " JOIN synthesis_tags st ON s.id = st.synthesis_id"
            conditions.append("st.tag_id = ?")
            params.append(tag_id)
        
        if project_id:
            conditions.append("s.project_id = ?")
            params.append(project_id)
        
        if search:
            conditions.append("(s.title LIKE ? OR s.summary LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY s.updated_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            data = dict(row)
            data['sources'] = json.loads(data.get('sources', '[]'))
            # Get tags for this synthesis
            cursor.execute('''
                SELECT t.* FROM tags t
                JOIN synthesis_tags st ON t.id = st.tag_id
                WHERE st.synthesis_id = ?
            ''', (data['id'],))
            data['tags'] = [Tag(**dict(t)) for t in cursor.fetchall()]
            results.append(data)
        
        conn.close()
        return results
    
    def get_synthesis(self, synthesis_id: int) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM syntheses WHERE id = ?", (synthesis_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        data = dict(row)
        data['sources'] = json.loads(data.get('sources', '[]'))
        
        # Get tags
        cursor.execute('''
            SELECT t.* FROM tags t
            JOIN synthesis_tags st ON t.id = st.tag_id
            WHERE st.synthesis_id = ?
        ''', (synthesis_id,))
        data['tags'] = [Tag(**dict(t)) for t in cursor.fetchall()]
        
        conn.close()
        return data
    
    def update_synthesis(self, synthesis_id: int, title: str = None, summary: str = None,
                         project_id: int = None, tag_ids: List[int] = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        updates = ["updated_at = ?"]
        params = [datetime.now().isoformat()]
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if summary is not None:
            updates.append("summary = ?")
            params.append(summary)
        if project_id is not None:
            updates.append("project_id = ?")
            params.append(project_id)
        
        params.append(synthesis_id)
        cursor.execute(f"UPDATE syntheses SET {', '.join(updates)} WHERE id = ?", params)
        
        # Update tags if provided
        if tag_ids is not None:
            cursor.execute("DELETE FROM synthesis_tags WHERE synthesis_id = ?", (synthesis_id,))
            for tag_id in tag_ids:
                cursor.execute(
                    "INSERT INTO synthesis_tags (synthesis_id, tag_id) VALUES (?, ?)",
                    (synthesis_id, tag_id)
                )
        
        conn.commit()
        conn.close()
    
    def delete_synthesis(self, synthesis_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM syntheses WHERE id = ?", (synthesis_id,))
        conn.commit()
        conn.close()
    
    # --- Statistics ---
    
    def get_stats(self) -> Dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM syntheses")
        stats['total_syntheses'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM projects")
        stats['total_projects'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tags")
        stats['total_tags'] = cursor.fetchone()[0]
        
        # Most used tags
        cursor.execute('''
            SELECT t.name, COUNT(*) as count FROM tags t
            JOIN synthesis_tags st ON t.id = st.tag_id
            GROUP BY t.id ORDER BY count DESC LIMIT 5
        ''')
        stats['top_tags'] = [{"name": r[0], "count": r[1]} for r in cursor.fetchall()]
        
        # Recent activity (syntheses per day, last 7 days)
        cursor.execute('''
            SELECT DATE(created_at) as day, COUNT(*) as count
            FROM syntheses
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY day ORDER BY day
        ''')
        stats['recent_activity'] = [{"day": r[0], "count": r[1]} for r in cursor.fetchall()]
        
        conn.close()
        return stats


# Singleton instance
_db_instance = None

def get_database() -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
