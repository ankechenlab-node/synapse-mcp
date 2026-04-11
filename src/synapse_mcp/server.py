"""Synapse MCP Server — Universal MCP server for code development & knowledge management."""

import argparse

from fastmcp import FastMCP

from synapse_mcp.tools.session import register_session_tools
from synapse_mcp.tools.pipeline import register_pipeline_tools
from synapse_mcp.tools.wiki import register_wiki_tools
from synapse_mcp.tools.gitnexus import register_gitnexus_tools
from synapse_mcp.tools.notifier import register_notifier_tools
from synapse_mcp.resources.wiki import register_resources
from synapse_mcp.prompts.templates import register_prompts


def create_server(state_dir: str | None = None) -> FastMCP:
    """Create and configure the Synapse MCP server."""
    mcp = FastMCP(
        name="synapse",
        instructions=(
            "Synapse MCP Server — 一体化代码开发与知识管理工具。\n"
            "Session 管理：创建/查询项目会话状态\n"
            "Pipeline 执行：多阶段代码交付流水线 (REQ→ARCH→DEV→INT→QA→DEPLOY)\n"
            "Wiki 管理：知识库初始化/内容摄取/智能查询/健康检查\n"
            "Resources：通过 wiki://, state://, log:// URI 直接访问知识和状态"
        ),
    )

    # Register tools with configurable state_dir
    register_session_tools(mcp, state_dir=state_dir)
    register_pipeline_tools(mcp)
    register_wiki_tools(mcp)
    register_gitnexus_tools(mcp)
    register_notifier_tools(mcp)

    # Register resources
    register_resources(mcp, state_dir=state_dir)

    # Register prompts
    register_prompts(mcp)

    return mcp


def main():
    parser = argparse.ArgumentParser(
        description="Synapse MCP Server — Code development + knowledge management"
    )
    parser.add_argument(
        "--state-dir",
        default="~/.synapse",
        help="State directory (default: ~/.synapse)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="HTTP server host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP server port (default: 8000)",
    )
    args = parser.parse_args()

    mcp = create_server(state_dir=args.state_dir)

    if args.transport == "http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
