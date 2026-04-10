"""
state_manager.py — Session state persistence for Synapse MCP

Mirrors synapse-brain's state_manager.py logic.
Stores state in ~/.synapse/state-{project}.json
"""

import json
from datetime import datetime
from pathlib import Path


class StateManager:
    """Manages session state as JSON files on disk."""

    def __init__(self, state_dir: str | None = None):
        if state_dir:
            self.state_dir = Path(state_dir).expanduser()
        else:
            self.state_dir = Path.home() / ".synapse"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _state_file(self, project: str) -> Path:
        return self.state_dir / f"state-{project}.json"

    def create_session(self, project: str, title: str, mode: str = "standalone") -> dict:
        """Create a new session state."""
        state = {
            "project": project,
            "title": title,
            "mode": mode,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "active",
            "tasks": [],
            "log": [],
        }
        self._save(project, state)
        return state

    def get_session(self, project: str) -> dict | None:
        """Get session state, or None if not exists."""
        state_file = self._state_file(project)
        if not state_file.exists():
            return None
        with open(state_file) as f:
            return json.load(f)

    def update_session(self, project: str, updates: dict) -> dict:
        """Update session state with new fields."""
        state = self.get_session(project)
        if not state:
            state = self.create_session(project, updates.get("title", project))
        state.update(updates)
        state["updated_at"] = datetime.now().isoformat()
        self._save(project, state)
        return state

    def add_task(self, project: str, task: dict) -> dict:
        """Add a task to the session."""
        state = self.get_session(project)
        if not state:
            state = self.create_session(project, project)
        if "tasks" not in state:
            state["tasks"] = []
        state["tasks"].append(task)
        state["log"].append({
            "action": "task_added",
            "task": task.get("title", "Untitled"),
            "timestamp": datetime.now().isoformat(),
        })
        self._save(project, state)
        return state

    def update_task(self, project: str, task_id: str, updates: dict) -> dict | None:
        """Update a specific task by ID."""
        state = self.get_session(project)
        if not state:
            return None
        for task in state.get("tasks", []):
            if task.get("id") == task_id:
                task.update(updates)
                state["log"].append({
                    "action": "task_updated",
                    "task_id": task_id,
                    "status": updates.get("status", "unknown"),
                    "timestamp": datetime.now().isoformat(),
                })
                state["updated_at"] = datetime.now().isoformat()
                self._save(project, state)
                return state
        return None

    def list_sessions(self) -> list[dict]:
        """List all session states."""
        sessions = []
        for f in sorted(self.state_dir.glob("state-*.json")):
            with open(f) as fh:
                sessions.append(json.load(fh))
        return sessions

    def archive_session(self, project: str) -> dict | None:
        """Archive a session."""
        state = self.get_session(project)
        if not state:
            return None
        state["status"] = "archived"
        state["archived_at"] = datetime.now().isoformat()
        self._save(project, state)
        return state

    def _save(self, project: str, state: dict):
        """Save state to disk."""
        with open(self._state_file(project), "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
