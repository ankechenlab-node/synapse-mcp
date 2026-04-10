"""MCP Tools: Pipeline execution with progress reporting via Tasks API."""

import asyncio
import json as _json
import re
import uuid
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

_VALID_PROJECT_RE = re.compile(r'^[a-zA-Z0-9_-]+$')
_VALID_STAGES = {s["name"] for s in PIPELINE_STAGES}

# Default pipeline workspace — user should override via config
_DEFAULT_WORKSPACE = Path.home() / "pipeline-workspace"

# Task state directory
_TASK_STATE_DIR = Path.home() / ".synapse" / "tasks"


def _task_state_dir() -> Path:
    _TASK_STATE_DIR.mkdir(parents=True, exist_ok=True)
    return _TASK_STATE_DIR


def _task_file(task_id: str) -> Path:
    return _task_state_dir() / f"{task_id}.json"


def _write_task_state(task_id: str, state: dict):
    """Atomically write task state."""
    import tempfile
    import os
    target = _task_file(task_id)
    fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            _json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp, target)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_task_state(task_id: str) -> dict | None:
    """Read task state, return None if not found or corrupted."""
    tf = _task_file(task_id)
    if not tf.exists():
        return None
    try:
        with open(tf) as f:
            return _json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


async def _run_pipeline_bg(
    task_id: str,
    ws: Path,
    cmd: list[str],
    project: str,
):
    """Background task: run pipeline subprocess and update state."""
    stage_names = [s["name"] for s in PIPELINE_STAGES]
    start_idx = 0
    # Determine starting stage from command
    for i, arg in enumerate(cmd):
        if arg == "--stage" and i + 1 < len(cmd):
            stage_name = cmd[i + 1]
            if stage_name in stage_names:
                start_idx = stage_names.index(stage_name)
            break

    task_state = {
        "task_id": task_id,
        "project": project,
        "status": "running",
        "current_stage": stage_names[start_idx],
        "stage_index": start_idx,
        "stages_completed": [],
        "total_stages": len(stage_names),
        "started_at": None,  # will be set by pipeline_run
        "finished_at": None,
        "stdout": "",
        "stderr": "",
        "exit_code": None,
    }
    _write_task_state(task_id, task_state)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=ws,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

        task_state["stdout"] = stdout.decode()[-2000:]  # last 2KB
        task_state["stderr"] = stderr.decode()[-2000:]
        task_state["exit_code"] = proc.returncode

        if proc.returncode == 0:
            task_state["status"] = "completed"
            task_state["stages_completed"] = stage_names[start_idx:]
            task_state["current_stage"] = stage_names[-1]
        else:
            task_state["status"] = "failed"
    except asyncio.TimeoutError:
        task_state["status"] = "timeout"
        task_state["stderr"] = "Pipeline timed out (10 min limit)"
    except Exception as e:
        task_state["status"] = "error"
        task_state["stderr"] = str(e)

    task_state["finished_at"] = asyncio.get_event_loop().time()
    _write_task_state(task_id, task_state)


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

        Returns a task_id for non-blocking execution. Use pipeline_status to check progress.

        Args:
            project: Project name (must exist in pipeline workspace)
            requirement: Natural language description of what to build
            mode: Execution mode (standard, verbose, dry-run)
            stage: Starting stage (REQ, ARCH, DEV, INT, QA, DEPLOY)
            workspace: Pipeline workspace directory (default: ~/pipeline-workspace)
        """
        # Validate inputs
        if not _VALID_PROJECT_RE.match(project):
            return f"Invalid project name: '{project}'. Use only letters, numbers, hyphens, and underscores"

        if stage not in _VALID_STAGES:
            return f"Invalid stage: '{stage}'. Valid stages: {', '.join(sorted(_VALID_STAGES))}"

        if not requirement or not requirement.strip():
            return "Requirement is required"

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

        # Dry-run mode: simulate without executing
        if mode == "dry-run":
            lines = [
                f"Pipeline dry-run for '{project}'",
                f"Requirement: {requirement[:100]}...",
                f"Starting stage: {stage}",
                f"Planned execution:",
            ]
            stage_idx = _stage_index(stage)
            for i, s in enumerate(PIPELINE_STAGES):
                if i >= stage_idx:
                    arrow = ">>>" if i == stage_idx else "   "
                    lines.append(f"  {arrow} [{s['name']}] {s['description']}")
                else:
                    lines.append(f"  [ok] [{s['name']}] (skipped)")
            return "\n".join(lines)

        cmd = [
            "python3", "pipeline.py", "run-pipeline",
            project,
            "--input", requirement,
            "--stage", stage,
        ]
        if mode == "verbose":
            cmd.append("--verbose")

        # Generate task ID and initialize state
        task_id = str(uuid.uuid4())[:12]
        _write_task_state(task_id, {
            "task_id": task_id,
            "project": project,
            "status": "queued",
            "current_stage": stage,
            "stages_completed": [],
            "total_stages": len(PIPELINE_STAGES),
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        })

        # Launch background execution
        asyncio.ensure_future(_run_pipeline_bg(task_id, ws, cmd, project))

        return (
            f"Pipeline started for '{project}'\n"
            f"Task ID: {task_id}\n"
            f"Starting stage: {stage}\n"
            f"Mode: {mode}\n\n"
            f"Check progress: pipeline_status --project {project} --task-id {task_id}"
        )

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
        task_id: str | None = None,
    ) -> str:
        """Check the current status of a pipeline run.

        Args:
            project: Project name
            workspace: Pipeline workspace directory
            task_id: Optional specific task ID to query
        """
        if not _VALID_PROJECT_RE.match(project):
            return f"Invalid project name: '{project}'"

        # If task_id provided, check task-level state
        if task_id:
            state = _read_task_state(task_id)
            if not state:
                return f"Task '{task_id}' not found"
            return _format_task_state(state)

        # Otherwise check project-level status
        ws = Path(workspace).expanduser() if workspace else _DEFAULT_WORKSPACE
        project_dir = ws / project

        if not project_dir.exists():
            return f"Project '{project}' not found in {ws}"

        # Find the most recent task for this project
        tasks = _find_project_tasks(project)
        if tasks:
            latest = tasks[-1]
            return _format_task_state(latest)

        # Fallback: check which stage outputs exist
        stages_completed = []
        for stage_info in PIPELINE_STAGES:
            stage_file = project_dir / ".pipeline" / f"{stage_info['name']}.done"
            if stage_file.exists():
                stages_completed.append(stage_info["name"])

        if stages_completed:
            next_stage = _next_stage(stages_completed[-1])
            return (
                f"Pipeline '{project}' progress:\n"
                f"  Completed stages: {', '.join(stages_completed)}\n"
                f"  Next stage: {stages_completed[-1]} → {next_stage}"
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


def _find_project_tasks(project: str) -> list[dict]:
    """Find all task state files for a project, sorted by creation time."""
    tasks = []
    for tf in _task_state_dir().glob("*.json"):
        try:
            with open(tf) as f:
                state = _json.load(f)
            if state.get("project") == project:
                tasks.append(state)
        except (json.JSONDecodeError, IOError):
            continue
    return sorted(tasks, key=lambda t: t.get("started_at", ""))


def _format_task_state(state: dict) -> str:
    """Format a task state for display."""
    status = state.get("status", "unknown")
    stage = state.get("current_stage", "?")
    completed = state.get("stages_completed", [])
    total = state.get("total_stages", 6)
    task_id = state.get("task_id", "?")
    project = state.get("project", "?")

    stage_idx = state.get("stage_index", 0)
    progress = f"{len(completed)}/{total}"

    lines = [
        f"Pipeline: {project}",
        f"Task ID: {task_id}",
        f"Status: {status}",
        f"Progress: {progress}",
        f"Current stage: {stage}",
    ]
    if completed:
        lines.append(f"Completed: {', '.join(completed)}")
    if state.get("stderr"):
        lines.append(f"Error: {state['stderr'][:200]}")

    return "\n".join(lines)


def _next_stage(current: str) -> str:
    """Get the next stage after the given one."""
    names = [s["name"] for s in PIPELINE_STAGES]
    if current in names:
        idx = names.index(current)
        if idx + 1 < len(names):
            return names[idx + 1]
    return "DEPLOY"


def _stage_index(stage_name: str) -> int:
    """Get the index of a stage by name."""
    for i, s in enumerate(PIPELINE_STAGES):
        if s["name"] == stage_name:
            return i
    return 0
