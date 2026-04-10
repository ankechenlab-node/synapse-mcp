# Synapse MCP

Universal MCP server for code development pipeline and knowledge management.

通用 MCP 服务器，一体化完成代码开发流水线与知识管理。

---

[English](#english) | [中文](#chinese)

---

## English

### Features

**Session Management** — Create, track, and archive development sessions across projects.

**Pipeline Execution** — Multi-stage code delivery pipeline (REQ → ARCH → DEV → INT → QA → DEPLOY) with real-time progress reporting via MCP Tasks API.

**Knowledge Management** — Initialize wikis, ingest content, query knowledge, and run health checks.

**URI Resources** — Direct access to wiki pages and session state via `wiki://`, `state://`, `log://` URIs.

**Prompt Templates** — Built-in templates for pipeline stages and wiki pages.

### Quick Start

#### Via uv (recommended)

```bash
uvx synapse-mcp
```

#### Via pip

```bash
pip install synapse-mcp
python -m synapse_mcp.server
```

### Client Configuration

**Claude Desktop / Cursor / Windsurf**

```json
{
  "mcpServers": {
    "synapse": {
      "command": "uv",
      "args": ["run", "--from", "synapse-mcp", "synapse-mcp-server"]
    }
  }
}
```

**Claude Code**

```bash
claude mcp add synapse -- uv run --from synapse-mcp synapse-mcp-server
```

**HTTP Transport (remote)**

```bash
python -m synapse_mcp.server --transport http --port 8000
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `session_create` | Create a new development session |
| `session_status` | Check session progress and tasks |
| `session_list` | List all sessions |
| `session_save` | Force-save session state |
| `session_archive` | Archive a completed session |
| `pipeline_run` | Execute pipeline stages with progress |
| `pipeline_status` | Check pipeline run status |
| `pipeline_stages` | List available pipeline stages |
| `wiki_init` | Initialize a wiki knowledge base |
| `wiki_ingest` | Ingest content into wiki |
| `wiki_query` | Query wiki with natural language |
| `wiki_lint` | Run wiki health check |

### MCP Resources

| URI Pattern | Description |
|-------------|-------------|
| `wiki://{path}` | Read wiki page (e.g., `wiki://CLAUDE.md`) |
| `state://{project}` | Read session state JSON |
| `log://{project}` | Read session activity log |

### MCP Prompts

| Prompt | Description |
|--------|-------------|
| `pipeline_template` | Get prompt for pipeline stage (REQ/ARCH/DEV/INT/QA) |
| `wiki_page_template` | Get template for wiki page (concept/decision/guide) |

### Architecture

```
┌─────────────────────────────────────┐
│        MCP Client (any host)         │
│  Claude Desktop / Cursor / Claude Code│
└──────────────┬──────────────────────┘
               │ stdio / http
               ▼
┌─────────────────────────────────────┐
│       Synapse MCP Server             │
│  Tools: session/pipeline/wiki        │
│  Resources: wiki:// state:// log://  │
│  Prompts: pipeline/wiki templates    │
│  State: ~/.synapse/ (persistent)     │
└──────────────┬──────────────────────┘
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
  Pipeline   Wiki    State (JSON)
```

---

## 中文

### 功能特性

**会话管理** — 创建、追踪和归档跨项目的开发会话状态。

**流水线执行** — 多阶段代码交付流水线（REQ → ARCH → DEV → INT → QA → DEPLOY），通过 MCP Tasks API 实时报告进度。

**知识管理** — 初始化知识库、摄取内容、智能查询、健康检查。

**URI 资源** — 通过 `wiki://`、`state://`、`log://` URI 直接访问 wiki 页面和会话状态。

**提示词模板** — 内置流水线阶段和 wiki 页面的提示词模板。

### 快速开始

#### 使用 uv（推荐）

```bash
uvx synapse-mcp
```

#### 使用 pip

```bash
pip install synapse-mcp
python -m synapse_mcp.server
```

### 客户端配置

**Claude Desktop / Cursor / Windsurf**

```json
{
  "mcpServers": {
    "synapse": {
      "command": "uv",
      "args": ["run", "--from", "synapse-mcp", "synapse-mcp-server"]
    }
  }
}
```

**Claude Code**

```bash
claude mcp add synapse -- uv run --from synapse-mcp synapse-mcp-server
```

**HTTP 传输（远程模式）**

```bash
python -m synapse_mcp.server --transport http --port 8000
```

### MCP 工具

| 工具 | 说明 |
|------|------|
| `session_create` | 创建新的开发会话 |
| `session_status` | 查看会话进度和任务 |
| `session_list` | 列出所有会话 |
| `session_save` | 强制保存会话状态 |
| `session_archive` | 归档已完成的会话 |
| `pipeline_run` | 执行流水线阶段，带进度报告 |
| `pipeline_status` | 查看流水线运行状态 |
| `pipeline_stages` | 列出可用的流水线阶段 |
| `wiki_init` | 初始化知识库 |
| `wiki_ingest` | 摄取内容到知识库 |
| `wiki_query` | 自然语言查询知识库 |
| `wiki_lint` | 知识库健康检查 |

### MCP 资源

| URI 模式 | 说明 |
|---------|------|
| `wiki://{路径}` | 读取 wiki 页面（如 `wiki://CLAUDE.md`） |
| `state://{项目}` | 读取会话状态 JSON |
| `log://{项目}` | 读取会话活动日志 |

### MCP 提示词

| 提示词 | 说明 |
|--------|------|
| `pipeline_template` | 获取流水线阶段提示词（REQ/ARCH/DEV/INT/QA） |
| `wiki_page_template` | 获取 wiki 页面模板（concept/decision/guide） |

### 架构

```
┌─────────────────────────────────────┐
│        MCP 客户端（任意宿主）          │
│  Claude Desktop / Cursor / Claude Code│
└──────────────┬──────────────────────┘
               │ stdio / http
               ▼
┌─────────────────────────────────────┐
│       Synapse MCP Server             │
│  Tools: session/pipeline/wiki        │
│  Resources: wiki:// state:// log://  │
│  Prompts: pipeline/wiki 模板          │
│  State: ~/.synapse/（持久化）         │
└──────────────┬──────────────────────┘
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
  Pipeline   Wiki    State (JSON)
```

---

## Related Projects / 相关项目

- [synapse-brain](https://github.com/ankechenlab-node/synapse-brain) — OpenClaw 持久化编排代理
- [synapse-code](https://github.com/ankechenlab-node/synapse-code) — 智能代码开发工作流引擎
- [synapse-wiki](https://github.com/ankechenlab-node/synapse-wiki) — 智能知识库管理系统

## License

MIT
