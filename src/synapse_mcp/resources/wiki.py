"""MCP Resources: Wiki pages and session state via URI."""

import json
import re
from pathlib import Path

from fastmcp import FastMCP

# Valid project name pattern
_PROJECT_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


def register_resources(mcp: FastMCP, state_dir: str | None = None):
    """Register wiki:// and state:// URI resources."""

    @mcp.resource("wiki://{path}")
    def wiki_page(path: str, wiki_root: str | None = None) -> str:
        """Read a wiki page by path.

        URI: wiki://CLAUDE.md, wiki://index.md, wiki://concepts/xyz.md
        """
        root = Path(wiki_root).expanduser().resolve() if wiki_root else Path.cwd()
        target = (root / path).resolve()

        # Prevent path traversal
        if not str(target).startswith(str(root)):
            return "Access denied: path traversal not allowed"

        if not target.is_file():
            return f"Page not found: wiki://{path}\nRoot: {root}"
        return target.read_text()

    @mcp.resource("state://{project}")
    def session_state(project: str) -> str:
        """Read session state for a project.

        URI: state://my-project
        """
        if not _PROJECT_RE.match(project):
            return f"Invalid project name: {project}"

        sdir = Path(state_dir).expanduser() if state_dir else Path.home() / ".synapse"
        state_file = sdir / f"state-{project}.json"
        if not state_file.exists():
            return f"No session state for '{project}'"
        try:
            with open(state_file) as f:
                state = json.load(f)
        except (json.JSONDecodeError, IOError):
            return f"Corrupted session state for '{project}'"
        return json.dumps(state, indent=2, ensure_ascii=False)

    @mcp.resource("log://{project}")
    def session_log(project: str) -> str:
        """Read activity log for a project session.

        URI: log://my-project
        """
        if not _PROJECT_RE.match(project):
            return f"Invalid project name: {project}"

        sdir = Path(state_dir).expanduser() if state_dir else Path.home() / ".synapse"
        state_file = sdir / f"state-{project}.json"
        if not state_file.exists():
            return f"No session log for '{project}'"
        try:
            with open(state_file) as f:
                state = json.load(f)
        except (json.JSONDecodeError, IOError):
            return f"Corrupted session log for '{project}'"
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
