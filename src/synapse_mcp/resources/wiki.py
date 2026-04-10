"""MCP Resources: Wiki pages and session state via URI."""

import json
from pathlib import Path

from fastmcp import FastMCP


def register_resources(mcp: FastMCP):
    """Register wiki:// and state:// URI resources."""

    @mcp.resource("wiki://{path}")
    def wiki_page(path: str, wiki_root: str = "~/.synapse/wiki") -> str:
        """Read a wiki page by path.

        URI: wiki://CLAUDE.md, wiki://index.md, wiki://concepts/xyz.md
        """
        root = Path(wiki_root).expanduser()
        target = root / path
        if not target.exists():
            return f"Page not found: wiki://{path}\nRoot: {root}"
        return target.read_text()

    @mcp.resource("state://{project}")
    def session_state(project: str, state_dir: str = "~/.synapse") -> str:
        """Read session state for a project.

        URI: state://my-project
        """
        state_dir_path = Path(state_dir).expanduser()
        state_file = state_dir_path / f"state-{project}.json"
        if not state_file.exists():
            return f"No session state for '{project}'"
        with open(state_file) as f:
            state = json.load(f)
        return json.dumps(state, indent=2, ensure_ascii=False)

    @mcp.resource("log://{project}")
    def session_log(project: str, state_dir: str = "~/.synapse") -> str:
        """Read activity log for a project session.

        URI: log://my-project
        """
        state_dir_path = Path(state_dir).expanduser()
        state_file = state_dir_path / f"state-{project}.json"
        if not state_file.exists():
            return f"No session log for '{project}'"
        with open(state_file) as f:
            state = json.load(f)
        log_entries = state.get("log", [])
        if not log_entries:
            return f"No activity log for '{project}'"
        lines = [f"Activity Log: {project}", ""]
        for entry in log_entries[-20:]:  # Last 20 entries
            lines.append(
                f"[{entry.get('timestamp', '?')}] {entry.get('action', '?')}"
                f" — {entry.get('task', entry.get('task_id', ''))}"
            )
        return "\n".join(lines)
