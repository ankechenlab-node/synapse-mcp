# Synapse MCP

**Where AI agents remember, plan, and ship — without losing context.**

一个让 AI 代理拥有持久记忆、结构化思考和端到端交付能力的 MCP 服务器。

---

[English](#english) | [中文](#chinese)

---

## English

### The Problem

Today's AI coding assistants are brilliant but amnesiac. They forget what they built between sessions, lose track of why decisions were made, and treat every request as if it's the first conversation. You end up repeating context, re-explaining architecture, and manually tracking what stage you're at.

**Synapse changes that.** It gives AI agents the infrastructure they need to persist across sessions — structured memory, disciplined engineering process, and a living knowledge base that grows with every interaction.

### What Makes Synapse Different

**Three pillars, one server:**

```
  MEMORY ──────── PROCESS ──────── KNOWLEDGE
  Session state   6-stage pipe    Living wiki
  Never forget    Quality gates   Self-growing
  Cross-project   Contract-first  Always queryable
```

**1. Persistent Session Memory** — Development sessions survive restarts, crashes, and coffee breaks. Every task, decision, and timestamp is atomically persisted. Pick up exactly where you left off, days or weeks later.

**2. Engineering Pipeline** — Natural language becomes structured delivery: requirements flow through architecture with contract generation, implementation, integration, adversarial QA, and deployment. Each stage must pass validation before the next begins. No shortcuts.

**3. Living Knowledge Base** — Initialize wikis, ingest any content, query with natural language. The knowledge base grows with every project, creating institutional memory that outlasts any single session.

### The Architecture

Synapse is the **infrastructure layer** of the Synapse ecosystem — the persistent backbone that connects the orchestration brain ([synapse-brain](https://github.com/ankechenlab-node/synapse-brain)) with specialized execution skills ([synapse-code](https://github.com/ankechenlab-node/synapse-code), [synapse-wiki](https://github.com/ankechenlab-node/synapse-wiki)).

```
┌──────────────────────────────────────────────┐
│              MCP Client (you)                 │
│    Claude Desktop / Cursor / Claude Code      │
└─────────────────┬────────────────────────────┘
                  │ "Build a REST API with auth"
                  ▼
┌──────────────────────────────────────────────┐
│           Synapse MCP Server                  │
│                                               │
│  MEMORY   session_create  ← "remember this"  │
│           session_status  ← "where are we?"  │
│           session_archive ← "ship & store"   │
│                                               │
│  PROCESS  pipeline_run    ← "execute plan"   │
│           pipeline_status ← "how's it going" │
│                                               │
│  KNOWLEDGE wiki_init     ← "new workspace"   │
│           wiki_ingest    ← "learn this"      │
│           wiki_query     ← "what do we know" │
│                                               │
│  URI      wiki:// state:// log://  ← direct   │
└─────────────────┬────────────────────────────┘
                  │
         ┌────────┼────────┐
         ▼        ▼        ▼
    ~/.synapse/  Pipeline  Wiki files
    (atomic)    (stages)  (growing)
```

### MCP Tools (12)

#### Session Management — Never Lose Context
| Tool | Description |
|------|-------------|
| `session_create` | Start a tracked development session |
| `session_status` | See progress, tasks, and decisions at a glance |
| `session_list` | Browse all sessions across projects |
| `session_save` | Checkpoint state with atomic persistence |
| `session_archive` | Store completed work with timestamps |

#### Pipeline Execution — Discipline Built In
| Tool | Description |
|------|-------------|
| `pipeline_run` | Execute REQ → ARCH → DEV → INT → QA → DEPLOY with live progress |
| `pipeline_status` | Check which stage passed, which is running |
| `pipeline_stages` | See what each stage validates |

#### Knowledge Management — Institutional Memory
| Tool | Description |
|------|-------------|
| `wiki_init` | Create a structured knowledge workspace |
| `wiki_ingest` | Feed it files, directories, or raw text |
| `wiki_query` | Ask questions in natural language |
| `wiki_lint` | Verify knowledge integrity |

### MCP Resources (3 URI Schemes)

| URI | Purpose |
|-----|---------|
| `wiki://{path}` | Read any wiki page directly |
| `state://{project}` | Access session state as JSON |
| `log://{project}` | View activity timeline |

### MCP Prompts (2 Templates)

| Prompt | Purpose |
|--------|---------|
| `pipeline_template` | Structured prompt for each pipeline stage |
| `wiki_page_template` | Consistent wiki page formats |

### Quick Start

```bash
# Via uv (recommended)
uvx --from synapse-mcp synapse-mcp-server

# Via pip
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

---

## 中文

### 问题所在

今天的 AI 编程助手才华横溢却患有"失忆症"。它们在会话之间遗忘已构建的内容，丢失决策背后的原因，把每次请求都当作第一次对话。你不得不重复上下文、重新解释架构、手动跟踪进度。

**Synapse 改变了这一切。** 它为 AI 代理提供了跨会话持久化的基础设施——结构化的记忆、严谨的工程流程、以及随每次交互共同成长的知识库。

### Synapse 的独特之处

**三大支柱，一个服务器：**

```
  记忆 ──────── 流程 ──────── 知识
  会话状态      6 阶段流水线   活体 Wiki
  永不遗忘      质量门禁       自我成长
  跨项目关联    契约驱动       随时可查
```

**1. 持久化会话记忆** — 开发会话在重启、崩溃、甚至隔天之后依然完整。每个任务、决策、时间戳都通过原子写入持久化。精确回到上次离开的地方，无论过了多久。

**2. 工程化流水线** — 自然语言驱动结构化交付：需求经过架构设计（含契约生成）、实现、集成、对抗性测试、部署。每个阶段必须通过校验才能进入下一阶段。没有捷径。

**3. 活体知识库** — 初始化知识空间，摄入任意内容，用自然语言查询。知识库随每个项目增长，形成超越单次会话的组织记忆。

### 架构定位

Synapse 是 Synapse 生态系统的**基础设施层**——连接编排大脑 ([synapse-brain](https://github.com/ankechenlab-node/synapse-brain)) 与专业执行技能 ([synapse-code](https://github.com/ankechenlab-node/synapse-code), [synapse-wiki](https://github.com/ankechenlab-node/synapse-wiki)) 的持久化骨干。

### 快速开始

```bash
# 使用 uv（推荐）
uvx --from synapse-mcp synapse-mcp-server

# 使用 pip
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

---

## Related Projects / 相关项目

- [synapse-brain](https://github.com/ankechenlab-node/synapse-brain) — OpenClaw 持久化编排代理，Synapse 的"大脑"
- [synapse-code](https://github.com/ankechenlab-node/synapse-code) — 智能代码开发工作流引擎，70 项测试全部通过
- [synapse-wiki](https://github.com/ankechenlab-node/synapse-wiki) — 智能知识管理系统

## License / 许可

MIT
