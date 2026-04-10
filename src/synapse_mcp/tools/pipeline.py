"""MCP Tools: Pipeline execution with progress reporting via Tasks API."""

import subprocess
import asyncio
from pathlib import Path

from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations

PIPELINE_STAGES = [
    {"name": "REQ", "description": "Requirements — Parse user requirement into structured spec"},
    {"name": "ARCH", "description": "Architecture — Design system architecture and contracts"},
    {"name": "DEV", "description": "Development — Implement code following contracts"},
    {"name": "INT", "description": "Integration — Wire components together"},
    {"name": "QA", "description": "Quality Assurance — Test and validate"},
    {"name": "DEPLOY", "description": "Deploy — Package and deliver"},
]

# Default pipeline workspace — user should override via config
_DEFAULT_WORKSPACE = Path.home() / "pipeline-workspace"


def register_pipeline_tools(mcp: FastMCP):
    """Register pipeline execution tools."""

    @mcp.tool(annotations=ToolAnnotations(
        title="Run Pipeline",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ))
    async def pipeline_run(
        project: str,
        requirement: str,
        mode: str = "standard",
        stage: str = "REQ",
        workspace: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """Run the Synapse Pipeline for a project.

        Executes a multi-stage code delivery pipeline: REQ → ARCH → DEV → INT → QA → DEPLOY.
        Each stage must pass validation before proceeding.

        Args:
            project: Project name (must exist in pipeline workspace)
            requirement: Natural language description of what to build
            mode: Execution mode (standard, verbose, dry-run)
            stage: Starting stage (REQ, ARCH, DEV, INT, QA, DEPLOY)
            workspace: Pipeline workspace directory (default: ~/pipeline-workspace)
        """
        ws = Path(workspace).expanduser() if workspace else _DEFAULT_WORKSPACE

        if not ws.exists():
            return (
                f"Pipeline workspace not found: {ws}\n"
                f"Create it first: mkdir -p {ws}\n"
                f"Then initialize: python3 pipeline.py new {project}"
            )

        if not (ws / "pipeline.py").exists():
            return (
                f"Pipeline engine not found at: {ws}/pipeline.py\n"
                f"Install the pipeline engine first."
            )

        cmd = [
            "python3", "pipeline.py", "run-pipeline",
            project,
            "--input", requirement,
            "--stage", stage,
        ]
        if mode == "verbose":
            cmd.append("--verbose")

        if ctx:
            await ctx.report_progress(progress=0, total=6, message=f"Starting pipeline: {stage}")

        try:
            result = subprocess.run(
                cmd,
                cwd=ws,
                capture_output=True,
                text=True,
                timeout=600,  # 10 min timeout
            )

            if ctx:
                await ctx.report_progress(progress=6, total=6, message="Pipeline complete")

            if result.returncode == 0:
                return f"Pipeline completed for '{project}':\n{result.stdout}"
            else:
                return (
                    f"Pipeline failed for '{project}'\n"
                    f"Exit code: {result.returncode}\n"
                    f"Stderr: {result.stderr[:500]}"
                )
        except subprocess.TimeoutExpired:
            return (
                f"Pipeline timed out for '{project}' (10 min limit).\n"
                f"Check progress manually in: {ws}/{project}/"
            )
        except Exception as e:
            return f"Pipeline error: {e}"

    @mcp.tool(annotations=ToolAnnotations(
        title="Pipeline Status",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    async def pipeline_status(
        project: str,
        workspace: str | None = None,
    ) -> str:
        """Check the current status of a pipeline run.

        Args:
            project: Project name
            workspace: Pipeline workspace directory
        """
        ws = Path(workspace).expanduser() if workspace else _DEFAULT_WORKSPACE
        project_dir = ws / project

        if not project_dir.exists():
            return f"Project '{project}' not found in {ws}"

        # Check for pipeline state files
        status_file = project_dir / ".pipeline" / "status.json"
        if status_file.exists():
            with open(status_file) as f:
                import json
                state = json.load(f)
                current = state.get("current_stage", "unknown")
                status = state.get("status", "unknown")
                return f"Pipeline '{project}':\n  Stage: {current}\n  Status: {status}"

        # Fallback: check which stage outputs exist
        stages_completed = []
        for stage_info in PIPELINE_STAGES:
            stage_file = project_dir / ".pipeline" / f"{stage_info['name']}.done"
            if stage_file.exists():
                stages_completed.append(stage_info["name"])

        if stages_completed:
            return (
                f"Pipeline '{project}' progress:\n"
                f"  Completed stages: {', '.join(stages_completed)}\n"
                f"  Next stage: {stages_completed[-1]} → "
                f"{_next_stage(stages_completed[-1])}"
            )
        return f"Pipeline '{project}': No runs detected"

    @mcp.tool(annotations=ToolAnnotations(
        title="Pipeline Stages",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def pipeline_stages() -> str:
        """List all available pipeline stages and their descriptions."""
        lines = ["Pipeline Stages:", ""]
        for i, stage in enumerate(PIPELINE_STAGES, 1):
            arrow = "→" if i < len(PIPELINE_STAGES) else ""
            lines.append(f"  {i}. {stage['name']} {arrow} {stage['description']}")
        return "\n".join(lines)


def _next_stage(current: str) -> str:
    """Get the next stage after the given one."""
    names = [s["name"] for s in PIPELINE_STAGES]
    if current in names:
        idx = names.index(current)
        if idx + 1 < len(names):
            return names[idx + 1]
    return "DEPLOY"
