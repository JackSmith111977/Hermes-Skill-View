---
name: sra-agent
license: MIT
github: https://github.com/JackSmith111977/Hermes-Skill-View
description: |
  运行时技能推荐引擎。每个用户消息到达 Agent 时都会先经过 SRA，由它推荐最匹配的技能。
  触发场景：用户提出任何任务请求时，自动优先查询 SRA 获取上下文相关的技能推荐。
metadata:
  author: Emma (小喵)
  version: "1.1.0"
  hermes:
    tags:
      - skill-recommendation
      - rag
      - runtime
      - context-injection
    category: meta
    skill_type: middleware
    design_pattern: proxy-chain
---

# SRA — Skill Runtime Advisor (Agent Skill)

## 设计哲学（Philosophy）

> **SRA = 给 AI 装上"技能导航仪"，让它永远知道当前任务该用什么工具。**

SRA 不是"推荐引擎"，而是 **AI 的运行时上下文感知层**。它解决的问题是：AI 在拿到任务请求时，如何知道自己该调哪些技能？

### 两个核心思想

#### 思想 1：消息前置推理（Pre-emptive RAG）

传统 RAG 是"用户问→搜索→回答"。SRA 是"用户说→先问 SRA 该用啥技能→再执行"。每次用户消息到达 Agent 时，都不是直接执行，而是：

```
用户消息
  → SRA Proxy 拦截
  → 语义分析，匹配技能
  → 注入 RAG 上下文（rag_context）
  → Agent 带着推荐的技能去执行
```

**为什么重要**：AI 不知道它不知道的。SRA 是 AI 的"盲杖"，帮它在技能库中找到最合适的工具。

#### 思想 2：技能即上下文（Skill-as-Context）

每个 SKILL.md 文件不只是一份"操作手册"，更是一份 **"Agent 世界观"**。SRA 推荐技能时，不只是返回技能文件名，而是将技能的内容摘要（rag_context）注入到 Agent 的上下文中。

### 技术事实（不一定是操作指导，而是世界观）

- **SRA Proxy 必须优先于所有工具调用**：在 Agent 决定使用任何工具之前，必须先查询 SRA。这不是"建议"，这是工作流约束。
- **SRA 的推荐是"导航"不是"指令"**：推荐的 skill 可能不完全匹配，Agent 需要结合上下文判断是否真正加载。
- **技能覆盖率 = 知识盲区探测器**：长期未被推荐的技能意味着要么过时了，要么从没用过。定期的 `sra coverage` 报告就是知识审计。
- **SRA 的 daemon 必须 7x24 运行**：它是 Agent 的运行时依赖，不是临时工具。如果 daemon 挂了，Agent 的上下文注入层就断了。
- **推荐质量依赖技能索引质量**：如果技能文件本身写得不好（没有清晰的 trigger、description），SRA 的匹配效果会大幅下降。

---

## 前置检查（Pre-flight Check）

在任何使用 SRA 的操作之前，先执行环境自检：

```bash
# 安装目录下的自检脚本
python3 scripts/check-sra.py
```

### 检查清单

| 检查项 | 预期输出 | 失败时操作 |
|--------|----------|------------|
| Python 版本 | `python: ok (3.8+)` | 安装/升级 Python |
| sra CLI | `sra cli: ok (sra v1.1.0)` | `pip install sra-agent` |
| sra daemon | `sra daemon: ok (port 8536)` | `sra start` |
| 技能目录 | `skills dir: ok (~/.hermes/skills)` | 检查技能目录配置 |
| 配置文件 | `sra config: ok (~/.sra/config.json)` | 初始化配置 |

### 自检未通过怎么办

```
检查项未通过 → 看输出中的 "→" 提示
  → 执行提示中的修复命令
  → 再次运行 check-sra.py 确认修复
```

---

## 推荐引擎工作流程

### 标准流程（Hermes Agent）

```
用户消息
  ↓
① SRA Proxy 拦截（http://127.0.0.1:8536/recommend）
  ↓
② 语义相似度匹配（基于 synonyms + TF-IDF + co-occurrence）
  ↓
③ 三档返回：
   - ⭐≥80 分 → should_auto_load = true → 自动加载 skill
   - ⭐50-79 分 → medium 推荐 → 建议加载
   - ⭐<50 分   → low 推荐 → 仅作为参考
  ↓
④ 注入 rag_context 到 Agent 上下文
  ↓
⑤ Agent 按需决定是否加载推荐技能
```

### 关键技术事实

- **相似度计算不只依赖关键词**：匹配器使用同义词扩展（synonyms）、共现矩阵（co-occurrence）、TF-IDF 加权
- **线程安全**：所有路由和匹配操作是线程安全的，可在并发请求下使用
- **索引是内存缓存**：匹配器在首次调用时加载索引，后续调用不需要重复加载
- **HTTP API 是无状态的**：每个请求独立处理，没有 session 状态

---

## 命令参考

| 命令 | 说明 | 预期输出包含 |
|------|------|-------------|
| `sra start` | 启动守护进程 | "Daemon started" |
| `sra stop` | 停止守护进程 | "Daemon stopped" |
| `sra status` | 查看运行状态 | 版本、技能数、运行时长 |
| `sra recommend <输入>` | 查询技能推荐 | 推荐技能、得分、置信度 |
| `sra coverage` | 技能覆盖率统计 | 使用/未使用技能分布 |
| `sra stats` | 使用统计 | 总请求数、平均响应时间 |
| `sra version` | 版本信息 | 版本号、提交 hash |
| `python3 check-sra.py` | 环境自检 | 各组件状态 |
| `curl /health` | 健康检查 | `{"status": "ok"}` |

---

## Proxy API 详情

| 端点 | 方法 | body | 返回 |
|------|------|------|------|
| `/health` | GET | — | `{"status":"ok","version":"1.1.0","skills_count":275}` |
| `/recommend` | POST | `{"message":"画个架构图"}` | `{"recommendations":[...],"top_skill":"...","timing_ms":42}` |
| `/targets` | GET | — | 当前管理的 tab 列表 |
| `/stats` | GET | — | 使用统计汇总 |

---

## 集成方式

### Hermes Agent（推荐）

设置环境变量后自动集成：

```bash
export SRA_PROXY_ENABLED=true
export SRA_PROXY_URL=http://127.0.0.1:8536
```

或在代码中以 Python SDK 方式集成：

```python
from sra_agent.adapters import get_adapter
adapter = get_adapter('hermes')
recs = adapter.recommend("画个架构图")
if recs:
    print(adapter.format_suggestion(recs))
```

### 其他 Agent

SRA 提供多种 Agent 适配器：

```bash
sra install claude    # Claude Code
sra install codex     # OpenAI Codex
sra install generic   # 通用适配
```

---

## 故障排除

| 症状 | 原因 | 解决 |
|------|------|------|
| 推荐为空 | 技能索引未加载 | 检查 `~/.sra/data/` 目录 |
| connection refused | Daemon 未启动 | `sra start` |
| 推荐质量低 | 技能文件缺少 trigger | 检查技能文件的 triggers 字段 |
| 响应慢 | 技能库过大 | 检查技能数量（推荐 < 500） |
