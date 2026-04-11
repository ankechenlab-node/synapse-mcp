"""MCP Tools: GitNexus code analysis integration.

Wraps GitNexus CLI and eval-server for impact analysis,
symbol context, code graph queries, and cypher queries.
"""

import asyncio
import json
import os
import shutil
from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

_GITNEXUS_BIN = shutil.which("gitnexus")
_EVAL_SERVER_URL = "http://localhost:4848"


def _gitnexus_available() -> bool:
    return _GITNEXUS_BIN is not None


async def _gitnexus_cli(cmd: list[str], cwd: str | None = None) -> str:
    """Run gitnexus CLI command, return stdout."""
    if not _gitnexus_available():
        return "GitNexus not installed. Install: npm install -g @gitnexus/cli"

    try:
        proc = await asyncio.create_subprocess_exec(
            _GITNEXUS_BIN, *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode == 0:
            return stdout.decode().strip()
        else:
            err = stderr.decode().strip()
            return f"GitNexus error: {err}"
    except asyncio.TimeoutError:
        return "GitNexus command timed out (60s limit)"
    except Exception as e:
        return f"GitNexus error: {e}"


async def _gitnexus_http(endpoint: str, params: dict) -> str:
    """Call GitNexus eval-server via HTTP."""
    try:
        import urllib.request
        import urllib.parse
        qs = urllib.parse.urlencode({k: v for k, v in params.items() if v})
        url = f"{_EVAL_SERVER_URL}{endpoint}?{qs}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode()
            return data
    except Exception:
        return ""  # HTTP not available, fall back to CLI


def _format_result(title: str, output: str, limit: int = 3000) -> str:
    """Format a GitNexus tool result."""
    if not output:
        return f"{title}\n\n(empty result — repository may not be indexed)"
    if len(output) > limit:
        output = output[:limit] + f"\n\n... (truncated, {len(output)} chars total)"
    return f"{title}\n\n{output}"


def register_gitnexus_tools(mcp: FastMCP):
    """Register GitNexus code analysis tools."""

    @mcp.tool(annotations=ToolAnnotations(
        title="GitNexus Impact",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    async def gitnexus_impact(
        target: str,
        direction: str = "upstream",
        repo: str | None = None,
        depth: int = 3,
        cwd: str | None = None,
    ) -> str:
        """Blast radius analysis: what breaks if you change a symbol.

        Args:
            target: Symbol name (function, class, file, etc.)
            direction: upstream (dependants) or downstream (dependencies)
            repo: Target repository name
            depth: Max relationship depth (1-5)
            cwd: Working directory (for repo auto-detection)
        """
        cmd = ["impact", target, "--direction", direction, "--depth", str(depth)]
        if repo:
            cmd.extend(["--repo", repo])
        return _format_result(f"Impact Analysis: '{target}' ({direction})",
                              await _gitnexus_cli(cmd, cwd=cwd))

    @mcp.tool(annotations=ToolAnnotations(
        title="GitNexus Context",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    async def gitnexus_context(
        name: str,
        repo: str | None = None,
        uid: str | None = None,
        file: str | None = None,
        content: bool = False,
        cwd: str | None = None,
    ) -> str:
        """360-degree view of a code symbol: callers, callees, processes.

        Args:
            name: Symbol name
            repo: Target repository name
            uid: Direct symbol UID (zero-ambiguity lookup)
            file: File path to disambiguate common names
            content: Include full symbol source code
            cwd: Working directory
        """
        cmd = ["context"]
        if uid:
            cmd.extend(["--uid", uid])
        elif name:
            cmd.append(name)
        if repo:
            cmd.extend(["--repo", repo])
        if file:
            cmd.extend(["--file", file])
        if content:
            cmd.append("--content")
        return _format_result(f"Context: '{name or uid}'",
                              await _gitnexus_cli(cmd, cwd=cwd))

    @mcp.tool(annotations=ToolAnnotations(
        title="GitNexus Query",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    async def gitnexus_query(
        search_query: str,
        repo: str | None = None,
        context: str | None = None,
        goal: str | None = None,
        limit: int = 5,
        content: bool = False,
        cwd: str | None = None,
    ) -> str:
        """Search the knowledge graph for execution flows related to a concept.

        Args:
            search_query: What to search for
            repo: Target repository name
            context: Task context to improve ranking
            goal: What you want to find
            limit: Max processes to return (default: 5)
            content: Include full symbol source code
            cwd: Working directory
        """
        cmd = ["query", search_query, "--limit", str(limit)]
        if repo:
            cmd.extend(["--repo", repo])
        if context:
            cmd.extend(["--context", context])
        if goal:
            cmd.extend(["--goal", goal])
        if content:
            cmd.append("--content")
        return _format_result(f"Query: '{search_query}'",
                              await _gitnexus_cli(cmd, cwd=cwd))

    @mcp.tool(annotations=ToolAnnotations(
        title="GitNexus List Repos",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    async def gitnexus_list() -> str:
        """List all indexed GitNexus repositories."""
        return await _gitnexus_cli(["list"])

    @mcp.tool(annotations=ToolAnnotations(
        title="GitNexus Status",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    async def gitnexus_status(cwd: str | None = None) -> str:
        """Show index status for current repository."""
        return await _gitnexus_cli(["status"], cwd=cwd)

    @mcp.tool(annotations=ToolAnnotations(
        title="GitNexus Cypher",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    async def gitnexus_cypher(query: str, cwd: str | None = None) -> str:
        """Execute a raw Cypher query against the knowledge graph.

        Args:
            query: Cypher query string
            cwd: Working directory
        """
        return _format_result(f"Cypher Query",
                              await _gitnexus_cli(["cypher", "--query", query], cwd=cwd))
