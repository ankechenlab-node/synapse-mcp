"""
state_manager.py — Session state persistence for Synapse MCP

Mirrors synapse-brain's state_manager.py logic.
Stores state in ~/.synapse/state-{project}.json
Correlations in ~/.synapse/correlations.json
"""

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

# Valid project name pattern: alphanumeric, hyphens, underscores
_PROJECT_RE = re.compile(r'^[a-zA-Z0-9_-]+$')

# Correlation types
CORRELATION_TYPES = {
    "auth": "Authentication patterns (JWT, OAuth, session, etc.)",
    "server": "Server/DB connection sharing (same host, cluster, etc.)",
    "dependency": "Shared libraries, APIs, or microservices",
    "architecture": "Similar architectural patterns (MVC, event-driven, etc.)",
    "knowledge": "Shared wiki pages, decisions, or guides",
    "custom": "User-defined correlation",
}


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

    # =========================================================================
    # Session CRUD
    # =========================================================================

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

    def list_sessions(self, status: str | None = None, mode: str | None = None,
                      search: str | None = None) -> list[dict]:
        """List session states, with optional filtering.

        Args:
            status: Filter by status (active, archived)
            mode: Filter by mode (standalone, lite, full, parallel)
            search: Filter by keyword in project name or title
        """
        sessions = []
        for f in sorted(self.state_dir.glob("state-*.json")):
            try:
                with open(f) as fh:
                    state = json.load(fh)
            except (json.JSONDecodeError, IOError):
                continue  # skip corrupted file

            # Apply filters
            if status and state.get("status") != status:
                continue
            if mode and state.get("mode") != mode:
                continue
            if search:
                search_lower = search.lower()
                project_match = search_lower in state.get("project", "").lower()
                title_match = search_lower in state.get("title", "").lower()
                if not (project_match or title_match):
                    continue

            sessions.append(state)
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

    # =========================================================================
    # Cross-project correlations
    # =========================================================================

    def _correlations_file(self) -> Path:
        return self.state_dir / "correlations.json"

    def _load_correlations(self) -> dict:
        """Load correlations, or return empty structure."""
        cf = self._correlations_file()
        if cf.exists():
            try:
                with open(cf) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"links": [], "updated_at": None}

    def _save_correlations(self, data: dict):
        """Atomically save correlations."""
        data["updated_at"] = datetime.now().isoformat()
        self._atomic_save(self._correlations_file(), data)

    def correlate_projects(self, source: str, target: str,
                           corr_type: str, description: str = "") -> dict | str:
        """Create a correlation link between two projects.

        Args:
            source: Source project name
            target: Target project name
            corr_type: Correlation type (auth, server, dependency, architecture, knowledge, custom)
            description: Human-readable description of the correlation
        """
        err = _validate_project(source)
        if err:
            return err
        err = _validate_project(target)
        if err:
            return err
        if corr_type not in CORRELATION_TYPES:
            return f"Invalid correlation type: '{corr_type}'. Valid: {', '.join(CORRELATION_TYPES.keys())}"

        data = self._load_correlations()

        # Check for duplicate
        for link in data.get("links", []):
            if (link["source"] == source and link["target"] == target
                    and link["type"] == corr_type):
                return f"Correlation already exists: {source} → {target} ({corr_type})"

        link = {
            "source": source,
            "target": target,
            "type": corr_type,
            "description": description or CORRELATION_TYPES[corr_type],
            "created_at": datetime.now().isoformat(),
        }
        data.setdefault("links", []).append(link)
        self._save_correlations(data)
        return link

    def remove_correlation(self, source: str, target: str, corr_type: str) -> str:
        """Remove a correlation link."""
        data = self._load_correlations()
        before = len(data.get("links", []))
        data["links"] = [
            l for l in data.get("links", [])
            if not (l["source"] == source and l["target"] == target and l["type"] == corr_type)
        ]
        if len(data["links"]) == before:
            return "Correlation not found"
        self._save_correlations(data)
        return f"Correlation removed: {source} → {target} ({corr_type})"

    def get_correlations(self, project: str | None = None,
                         corr_type: str | None = None) -> dict:
        """Get correlations, optionally filtered by project or type."""
        data = self._load_correlations()
        links = data.get("links", [])

        if project:
            links = [l for l in links if l["source"] == project or l["target"] == project]
        if corr_type:
            links = [l for l in links if l["type"] == corr_type]

        return {"links": links, "total": len(links), "updated_at": data.get("updated_at")}

    def get_related_projects(self, project: str) -> list[dict]:
        """Get all projects related to a given project, grouped by correlation type."""
        data = self._load_correlations()
        related: dict[str, list[str]] = {}

        for link in data.get("links", []):
            if link["source"] == project:
                related.setdefault(link["type"], []).append(link["target"])
            elif link["target"] == project:
                related.setdefault(link["type"], []).append(link["source"])

        return [{"type": t, "type_desc": CORRELATION_TYPES.get(t, t), "projects": projects}
                for t, projects in related.items()]

    # =========================================================================
    # Internal
    # =========================================================================

    def _save(self, project: str, state: dict):
        """Atomically save state to disk."""
        self._atomic_save(self._state_file(project), state)
