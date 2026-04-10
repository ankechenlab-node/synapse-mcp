"""
state_manager.py — Session state persistence for Synapse MCP

Mirrors synapse-brain's state_manager.py logic.
Stores state in ~/.synapse/state-{project}.json
"""

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

# Valid project name pattern: alphanumeric, hyphens, underscores
_PROJECT_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


def _validate_project(project: str) -> str | None:
    """Validate project name. Returns error message or None if valid."""
    if not project or not project.strip():
        return "Project name is required"
    if not _PROJECT_RE.match(project):
        return f"Invalid project name: '{project}'. Use only letters, numbers, hyphens, and underscores"
    return None


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

    def _atomic_save(self, path: Path, data: dict):
        """Write to a temp file, then atomically rename. Prevents corruption on crash."""
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def create_session(self, project: str, title: str, mode: str = "standalone") -> dict | str:
        """Create a new session state. Returns state dict or error message."""
        err = _validate_project(project)
        if err:
            return err
        if not title or not title.strip():
            return "Session title is required"

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
        """Get session state, or None if not exists or corrupted."""
        state_file = self._state_file(project)
        if not state_file.exists():
            return None
        try:
            with open(state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def update_session(self, project: str, updates: dict) -> dict | None:
        """Update session state with new fields."""
        state = self.get_session(project)
        if not state:
            state = self.create_session(project, updates.get("title", project))
            if isinstance(state, str):  # error message
                return None
        state.update(updates)
        state["updated_at"] = datetime.now().isoformat()
        self._save(project, state)
        return state

    def add_task(self, project: str, task: dict) -> dict | None:
        """Add a task to the session."""
        state = self.get_session(project)
        if not state:
            result = self.create_session(project, project)
            if isinstance(result, str):
                return None
            state = result
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
        """List all session states, skipping corrupted files."""
        sessions = []
        for f in sorted(self.state_dir.glob("state-*.json")):
            try:
                with open(f) as fh:
                    sessions.append(json.load(fh))
            except (json.JSONDecodeError, IOError):
                continue  # skip corrupted file
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
        """Atomically save state to disk."""
        self._atomic_save(self._state_file(project), state)
