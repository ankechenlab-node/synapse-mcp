"""MCP Tools: Session management (create, status, list, save, archive, correlate)."""

from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from synapse_mcp.state.manager import StateManager, CORRELATION_TYPES


def register_session_tools(mcp: FastMCP, state_dir: str | None = None):
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
        mgr = StateManager(state_dir=state_dir)
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
        mgr = StateManager(state_dir=state_dir)
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
    def session_list(
        status: str | None = None,
        mode: str | None = None,
        search: str | None = None,
    ) -> str:
        """List sessions across projects, with optional filtering.

        Args:
            status: Filter by status (active, archived)
            mode: Filter by mode (standalone, lite, full, parallel)
            search: Filter by keyword in project name or title
        """
        mgr = StateManager(state_dir=state_dir)
        sessions = mgr.list_sessions(status=status, mode=mode, search=search)
        if not sessions:
            filters = []
            if status: filters.append(f"status={status}")
            if mode: filters.append(f"mode={mode}")
            if search: filters.append(f"search='{search}'")
            filter_str = f" (filters: {', '.join(filters)})" if filters else ""
            return f"No sessions found{filter_str}."

        lines = [f"Sessions ({len(sessions)}):", ""]
        for s in sessions:
            related = mgr.get_related_projects(s["project"])
            rel_str = ""
            if related:
                rel_projects = [p for r in related for p in r["projects"]]
                rel_str = f" → linked: {', '.join(rel_projects)}"
            lines.append(
                f"  {s['project']}: {s.get('title', 'Untitled')} "
                f"({s.get('mode', '?')}, {s.get('status', '?')}){rel_str}"
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
        mgr = StateManager(state_dir=state_dir)
        state = mgr.get_session(project)
        if not state:
            return f"No session found for '{project}'."
        mgr.update_session(project, state)
        return f"Session '{project}' saved to disk."

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
        mgr = StateManager(state_dir=state_dir)
        state = mgr.archive_session(project)
        if not state:
            return f"No session found for '{project}'."
        return f"Session '{project}' archived at {state.get('archived_at', 'N/A')}."

    @mcp.tool(annotations=ToolAnnotations(
        title="Correlate Projects",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ))
    def session_correlate(
        source: str,
        target: str,
        corr_type: str,
        description: str = "",
    ) -> str:
        """Link two projects with a correlation.

        Correlation types:
        - **auth**: Shared authentication patterns (JWT, OAuth, session)
        - **server**: Shared server/DB connections (same host, cluster)
        - **dependency**: Shared libraries, APIs, or microservices
        - **architecture**: Similar architectural patterns (MVC, event-driven)
        - **knowledge**: Shared wiki pages, decisions, or guides
        - **custom**: User-defined correlation

        Args:
            source: Source project name
            target: Target project name
            corr_type: Correlation type (auth, server, dependency, architecture, knowledge, custom)
            description: Human-readable description (optional, uses type default if omitted)
        """
        mgr = StateManager(state_dir=state_dir)
        result = mgr.correlate_projects(source, target, corr_type, description)
        if isinstance(result, str) and "already exists" in result:
            return result
        if isinstance(result, dict):
            return (
                f"Correlation created: {result['source']} ↔ {result['target']}\n"
                f"Type: {result['type']} ({CORRELATION_TYPES.get(result['type'], '')})\n"
                f"Description: {result['description']}"
            )
        return f"Error: {result}"

    @mcp.tool(annotations=ToolAnnotations(
        title="Remove Correlation",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def session_uncorrelate(
        source: str,
        target: str,
        corr_type: str,
    ) -> str:
        """Remove a correlation link between two projects.

        Args:
            source: Source project name
            target: Target project name
            corr_type: Correlation type
        """
        mgr = StateManager(state_dir=state_dir)
        return mgr.remove_correlation(source, target, corr_type)

    @mcp.tool(annotations=ToolAnnotations(
        title="Project Relations",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def session_relations(project: str) -> str:
        """Show all correlations for a project.

        Args:
            project: Project name
        """
        mgr = StateManager(state_dir=state_dir)
        related = mgr.get_related_projects(project)
        if not related:
            return f"No correlations found for '{project}'."

        lines = [f"Correlations for '{project}':", ""]
        for r in related:
            lines.append(f"  {r['type']} ({r['type_desc']}):")
            for p in r["projects"]:
                lines.append(f"    → {p}")
        return "\n".join(lines)

    @mcp.tool(annotations=ToolAnnotations(
        title="All Correlations",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def session_correlations(
        corr_type: str | None = None,
    ) -> str:
        """List all cross-project correlations.

        Args:
            corr_type: Optional filter by type (auth, server, dependency, architecture, knowledge, custom)
        """
        mgr = StateManager(state_dir=state_dir)
        data = mgr.get_correlations(corr_type=corr_type)
        links = data.get("links", [])
        if not links:
            filter_str = f" (type={corr_type})" if corr_type else ""
            return f"No correlations found{filter_str}."

        lines = [f"Correlations ({len(links)}):", ""]
        for l in links:
            desc = f" — {l['description']}" if l.get("description") else ""
            lines.append(f"  {l['source']} ↔ {l['target']} [{l['type']}]{desc}")
        return "\n".join(lines)
