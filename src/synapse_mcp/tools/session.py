"""MCP Tools: Session management (create, status, list, save, archive)."""

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from synapse_mcp.state.manager import StateManager


def register_session_tools(mcp: FastMCP):
    """Register session management tools."""

    @mcp.tool(annotations=ToolAnnotations(
        title="Create Session",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ))
    def session_create(project: str, title: str, mode: str = "standalone") -> str:
        """Create a new development session for a project.

        Args:
            project: Project name (alphanumeric, hyphens, underscores only)
            title: Session title describing the work
            mode: Session mode (standalone, lite, full, parallel)
        """
        mgr = StateManager()
        result = mgr.create_session(project, title, mode)
        if isinstance(result, str):  # error message
            return f"Error: {result}"
        return (
            f"Session created for '{project}'\n"
            f"Title: {title}\n"
            f"Mode: {mode}\n"
            f"Created: {result['created_at']}\n"
            f"Status: {result['status']}"
        )

    @mcp.tool(annotations=ToolAnnotations(
        title="Session Status",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def session_status(project: str) -> str:
        """Get current session status for a project.

        Args:
            project: Project name
        """
        mgr = StateManager()
        state = mgr.get_session(project)
        if not state:
            return f"No active session for '{project}'. Use session_create to start."

        lines = [
            f"Session: {state.get('title', project)}",
            f"Mode: {state.get('mode', 'standalone')}",
            f"Status: {state.get('status', 'unknown')}",
            f"Created: {state.get('created_at', 'N/A')}",
            f"Updated: {state.get('updated_at', 'N/A')}",
            "",
            f"Tasks ({len(state.get('tasks', []))}):",
        ]
        for task in state.get("tasks", []):
            status = task.get("status", "pending")
            title = task.get("title", "Untitled")
            lines.append(f"  [{status}] {title}")

        return "\n".join(lines)

    @mcp.tool(annotations=ToolAnnotations(
        title="List Sessions",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def session_list() -> str:
        """List all sessions across all projects."""
        mgr = StateManager()
        sessions = mgr.list_sessions()
        if not sessions:
            return "No sessions found."

        lines = [f"Sessions ({len(sessions)}):", ""]
        for s in sessions:
            lines.append(
                f"  {s['project']}: {s.get('title', 'Untitled')} "
                f"({s.get('status', 'unknown')})"
            )
        return "\n".join(lines)

    @mcp.tool(annotations=ToolAnnotations(
        title="Save Session",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def session_save(project: str) -> str:
        """Force-save current session state and refresh timestamp.

        Args:
            project: Project name
        """
        mgr = StateManager()
        state = mgr.get_session(project)
        if not state:
            return f"No session found for '{project}'."
        mgr.update_session(project, {})  # just refresh timestamp
        return f"Session '{project}' saved."

    @mcp.tool(annotations=ToolAnnotations(
        title="Archive Session",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def session_archive(project: str) -> str:
        """Archive a completed session.

        Args:
            project: Project name
        """
        mgr = StateManager()
        state = mgr.archive_session(project)
        if not state:
            return f"No session found for '{project}'."
        return f"Session '{project}' archived at {state.get('archived_at', 'N/A')}."
