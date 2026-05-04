# SRA — Skill Runtime Advisor

> **让 AI Agent 知道自己有什么能力，以及什么时候该用什么能力。**

SRA 是一个轻量级的**运行时技能推荐引擎**，解决 AI Agent"不知道自己有什么技能、不知道何时该用什么"的根本问题。它是一个独立于 LLM 推理的**中介层**，通过多维度匹配引擎主动推荐最合适的技能。

## 🎯 核心能力

| 能力 | 说明 |
|------|------|
| 🔍 **实时技能感知** | 扫描技能目录，构建完整索引（含 triggers / tags / description） |
| 🧠 **四维匹配引擎** | 词法 + 语义 + 场景 + 类别，四维加权推荐 |
| 🌐 **中英文互通** | 30+ 大类同义词映射，中文输入匹配英文技能 |
| 📊 **场景记忆** | 记录"什么输入→推荐了什么技能"，持续优化匹配 |
| ⚡ **超低延迟** | ~50ms 扫描 268 个技能，适合嵌入实时推理循环 |

## 🏗️ 架构

```
[用户输入]
    ↓
┌─────────────────────────────────────┐
│         SRA Runtime Engine          │
│                                     │
│  Layer 1: 实时技能索引               │
│  Layer 2: 四维匹配引擎               │
│    ├─ 词法 (triggers/name)  40%     │
│    ├─ 语义 (description)    25%     │
│    ├─ 场景 (使用历史)        20%     │
│    └─ 类别 (category/tags)  15%     │
│  Layer 3: 推荐决策器                 │
│  Layer 4: 场景记忆持久化             │
└──────────────┬──────────────────────┘
                │ 输出: skill_name + 匹配理由
                ▼
[Agent 使用 skill_view() 加载并执行]
```

## 🚀 快速开始

### 安装

```bash
# pip 安装
pip install sra-agent

# 或从源码
git clone https://github.com/yourname/sra-agent
cd sra-agent
pip install -e .
```

### 启动守护进程

```bash
# 启动后台守护进程（推荐）
sra start

# 查看状态
sra status

# 前台运行（调试）
sra attach
```

### 基本用法

```bash
# 查询推荐（自动连接守护进程）
sra recommend 帮我画个架构图

# 如果守护进程未运行，会自动降级为本地模式
```

## 🔌 多 Agent 集成

SRA 支持多种 AI Agent 系统：

| Agent | 适配器 | 集成方式 |
|-------|--------|----------|
| **Hermes Agent** | `HermesAdapter` | 原生 Skill 集成 |
| **Claude Code** | `ClaudeCodeAdapter` | Tool Use 格式 |
| **OpenAI Codex** | `CodexAdapter` | Function Calling |
| **OpenCode** | `GenericCLIAdapter` | CLI 输出 |
| **通用** | `GenericCLIAdapter` | 纯文本格式 |

```python
from sra_agent.adapters import get_adapter

# Hermes
adapter = get_adapter("hermes")
recs = adapter.recommend("帮我画个架构图")
print(adapter.format_suggestion(recs))

# Claude Code — 获取 Tool Use 格式
adapter = get_adapter("claude")
tools = adapter.to_claude_tool_format(recs)
```

## ⚙️ 守护进程管理

```bash
# 启动（后台）
sra start          # 或: srad

# 停止
sra stop

# 查看状态
sra status

# 重启
sra restart

# 安装 systemd 服务（开机自启）
sra install service

# 查看统计
sra stats

# 查看技能覆盖率
sra coverage

# 刷新索引
sra refresh
```

## 🌐 HTTP API

Daemon 启动后提供 HTTP API：

```bash
# 健康检查
curl http://localhost:8532/health

# 推荐查询
curl -X POST http://localhost:8532/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "帮我画个架构图"}'

# 记录使用
curl -X POST http://localhost:8532/record \
  -H "Content-Type: application/json" \
  -d '{"skill": "architecture-diagram", "input": "画架构图", "accepted": true}'

# 刷新索引
curl -X POST http://localhost:8532/refresh

# 统计
curl http://localhost:8532/stats
```

## 🔩 架构

```
┌─────────────────────────────────────────────────────────┐
│                    SRA Daemon (srad)                      │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │ Unix Socket │  │  HTTP API  │  │  Auto Refresher    │ │
│  │  (primary)  │  │  (:8532)   │  │  (every 1h)        │ │
│  └──────┬─────┘  └──────┬─────┘  └────────────────────┘ │
│         │               │                                 │
│         └───────┬───────┘                                 │
│                 ▼                                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │              SRA Recommendation Engine              │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌─────────┐  │  │
│  │  │Indexer │  │Matcher │  │ Memory │  │Synonyms │  │  │
│  │  └────────┘  └────────┘  └────────┘  └─────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
           │              │              │
           ▼              ▼              ▼
     ┌──────────┐ ┌──────────┐ ┌──────────────┐
     │ Hermes   │ │ Claude   │ │ OpenAI Codex │
     │ Adapter  │ │ Adapter  │ │ Adapter      │
     └──────────┘ └──────────┘ └──────────────┘
```

## 📊 基准测试

| 指标 | 值 |
|------|-----|
| 扫描 268 个技能 | ~50ms |
| 守护进程内存占用 | ~8MB |
| HTTP API 延迟 | ~5ms (overhead) |
| 技能识别率（有 trigger） | 90.6% |
| 总体技能识别率 | 86.6% |
| 常见查询通过率 | 67.5% |

## 🤝 贡献

欢迎 PR！请确保：

1. 新增测试覆盖
2. 通过所有现有测试
3. 匹配引擎改动需更新基准测试数据

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

## 🌟 相关项目

- [Hermes Agent](https://github.com/Hermes/hermes-agent) — 全能 AI 助手框架
- [Anthropic Claude Skills](https://docs.anthropic.com/claude/docs/skills) — Claude 技能系统
