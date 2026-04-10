# Synapse MCP 开发日记

## 项目起源

Synapse MCP 项目始于 2026-04-11，目标是将 synapse-brain/code/wiki 三个 OpenClaw Skills 封装为 **独立的 MCP Server**，让任何 MCP 客户端（Claude Desktop, Cursor, Windsurf, Claude Code 等）都能使用 Synapse 的代码开发与知识管理能力。

核心驱动力：ClawHub 是封闭生态，通过 PyPI + GitHub 发布可以触达更广泛的开发者。

---

## 开发阶段

### Phase 1: 架构设计
- 确认方案 C：MCP Server 为核心引擎，Skills 为 OpenClaw 专属薄包装层
- 确定技术选型：FastMCP 3.x + STDIO/HTTP 双 transport
- 设计 12 个 Tools + 3 个 Resources + 2 个 Prompts
- 确定状态存储：`~/.synapse/state-{project}.json`

### Phase 2: 核心实现
- state/manager.py — Session 状态持久化（CRUD + archive + list）
- tools/session.py — 5 个 session 管理工具
- tools/pipeline.py — 3 个 pipeline 工具（带 MCP progress reporting）
- tools/wiki.py — 4 个 wiki 管理工具（init/ingest/query/lint）
- resources/wiki.py — 3 个 URI 资源模板（wiki://, state://, log://）
- prompts/templates.py — 6 个 pipeline 阶段 + 3 个 wiki 页面模板
- server.py — FastMCP 主入口，整合所有模块

### Phase 3: 测试验证
- Server 创建测试 — 通过
- 12 tools 注册验证 — 12/12 通过
- 3 resources URI 模板验证 — 3/3 通过
- 2 prompts 验证 — 2/2 通过

### Phase 4: 发布
- pyproject.toml — setuptools 打包，entry point: synapse-mcp-server
- README.md — 中英文双语文档
- GitHub 推送 + v1.0.0 tag
- PyPI 发布 — https://pypi.org/project/synapse-mcp/1.0.0/

---

## 关键决策

### 1. 发布渠道
- **GitHub** — 源代码托管
- **PyPI** — Python 包分发（`pip install synapse-mcp`, `uvx synapse-mcp`）
- **不走 ClawHub** — ClawHub 只接受 OpenClaw Skills（基于 SKILL.md），MCP Server 是独立进程

### 2. 运行模式
- 默认 stdio — 作为 MCP 客户端子进程，读写本地文件系统
- 可选 HTTP — 远程访问场景
- 不部署到服务器 — 99% 场景是本地运行

### 3. 资源设计
- 使用动态 URI 模板而非静态资源
- `wiki://{path}` — 支持任意 wiki 页面
- `state://{project}` — 支持任意项目状态
- `log://{project}` — 支持任意项目日志

### 4. 依赖策略
- 仅依赖 fastmcp>=2.0.0
- pipeline 通过 subprocess 调用外部 pipeline.py（不内建）
- wiki 工具直接操作文件系统（不依赖 synapse-wiki skill）

---

## 测试报告

| 模块 | 测试项 | 结果 |
|------|--------|------|
| server | 创建 + 注册 | **通过** |
| tools/session | 5 个工具注册 | **5/5 通过** |
| tools/pipeline | 3 个工具注册 | **3/3 通过** |
| tools/wiki | 4 个工具注册 | **4/4 通过** |
| resources | 3 个 URI 模板读取 | **3/3 通过** |
| prompts | 2 个模板注册 | **2/2 通过** |
| 构建 | build + twine upload | **通过** |

---

## 经验教训

### 有效做法
- 直接复用 synapse-brain 的 state_manager 逻辑
- 用 FastMCP 的 @tool/@resource/@prompt 装饰器，代码简洁
- 测试时通过 `Client(mcp)` 模拟调用，验证真实行为

### 踩过的坑
1. **Resources 不显示在 list_resources()** — 动态 URI 模板不会出现在列表中，但 `read_resource()` 可以正常调用，这是 FastMCP 的预期行为
2. **git init 目录错误** — Bash tool 的 CWD 不是预期的 synapse-mcp 目录，需要用 `cd` 显式切换

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-04-11 | 初始发布：12 tools + 3 resources + 2 prompts，发布到 GitHub + PyPI |

---

### v2.0.1 (增强)
- task_router ML 增强
- Pipeline 长任务 MCP Tasks API
- 子代理自动重试
- GitNexus 代码分析工具集成
- 进度通知系统

### v2.0.2 (扩展)
- 多项目并行会话
- synapse-design Skill
- synapse-analytics Skill

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-04-11 | 初始发布：12 tools + 3 resources + 2 prompts，发布到 GitHub + PyPI |
