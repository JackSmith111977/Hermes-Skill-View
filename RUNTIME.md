# SRA Runtime — 运行时设计文档

> **SRA 不是技能。它是 Hermes Agent 消息管道中的一个运行时中间件。**
>
> 技能（SKILL.md）是 Agent 可以加载的"工具"。
> SRA 是 Agent 消息到达你的工具之前，先帮你决定该用什么工具的那一层。

---

## 为什么要有一个"运行时"？

### 痛点回顾

Hermes Agent 在技能库扩大到 60+ 后，面临四个问题：

1. **静态列表失效** — `<available_skills>` 列表越来越长，Agent 经常忽略合适的技能
2. **新技能不可见** — 添加一个新的 SKILL.md 后，Agent 不会自动知道它
3. **没有反馈闭环** — Agent 用了哪个技能、效果如何，不可追踪
4. **发现成本高** — Agent 需要遍历所有技能的 triggers 和 description 才能做出选择

SRA 解决这四个问题的方式是：**在消息路径上插入一个语义感知层**。

---

## 架构设计

```
用户消息
   │
   ▼
┌──────────────────────────────────────────────────────────────────┐
│  v1.x Layer: 消息前置推理                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ① Hermes Agent 收到消息                                 │   │
│  │                                                           │   │
│  │  ┌────────────────────────────────────────────────────┐   │   │
│  │  │  ② SRA Proxy (消息前置推理)                        │   │   │
│  │  │     curl POST /recommend {"message": ...}          │   │   │
│  │  │     ↓                                               │   │   │
│  │  │     语义匹配 → rag_context + 推荐列表 + 契约        │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  │                                                           │   │
│  │  ┌────────────────────────────────────────────────────┐   │   │
│  │  │  ③ Agent 决策 + 工具调用                            │   │   │
│  │  │     should_auto_load → 自动/手动加载 SKILL.md       │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  v2.0 Layer: 运行时强制校验【新增】                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ④ Pre-tool 校验 (PRE_TOOL_CALL hook)                    │   │
│  │     write_file / patch / terminal / execute_code 前      │   │
│  │        ↓                                                  │   │
│  │     curl POST /validate {tool, args, loaded_skills}       │   │
│  │        ↓                                                  │   │
│  │     ├─ compliant → 放行                                    │   │
│  │     ├─ warning  → 注入提醒 + Agent 继续                     │   │
│  │     └─ blocked  → 返回 block_message 阻止执行               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ⑤ 长任务上下文保持【新增】                                     │
│     ┌───────────────────────────────────────┐                   │
│     │  每 5 轮对话 → SRA recheck             │                   │
│     │  → 检测已推荐但未加载的技能              │                   │
│     │  → [SRA 提醒] 轻量注入                  │                   │
│     └───────────────────────────────────────┘                   │
│                                                                  │
│  v2.0 Layer: 反馈闭环【新增】                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ⑥ 技能使用轨迹记录                                       │   │
│  │     skill_view → POST /record {action: "viewed"}         │   │
│  │     工具调用   → POST /record {action: "used"}           │   │
│  │     场景记忆 → 采纳率自动调整推荐权重                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 关键设计决策

| 决策 | 为什么 |
|------|--------|
| **独立进程，非 Agent 子进程** | Agent 可能重启、切换模型，SRA 必须独立运行保证索引不丢失 |
| **Unix Socket + HTTP 双协议** | Socket 低延迟适合本地 Agent，HTTP 适合 Proxy 模式和远程集成 |
| **无状态 API** | 每个 /recommend 请求独立处理，不维护客户端 session |
| **定时自动刷新索引** / **文件变更检测** | 双模式：1小时定时 + 30秒 MD5 变更检测，新增 SKILL.md 约 30 秒后自动感知 |
| **rag_context 格式固定** | Agent 无论什么模型，收到的 rag_context 格式一致，降低集成成本 |

---

## SRA 不是什么

| 不是 | 说明 |
|------|------|
| ❌ 不是 Agent 技能 | SRA 不会被 `skill_view('sra-agent')` 加载，它和 Hermes Agent 是平行关系 |
| ❌ 不是搜索/问答系统 | 它不回答问题，只回答"当前任务应该用哪个技能" |
| ❌ 不是推荐系统 | 不是"你可能也喜欢"的被动推荐，是"这条消息你应该用这个"的主动注入 |
| ❌ 不是知识库 | SRA 不存储领域知识，只存储技能元数据（triggers、description、使用历史） |

---

## 集成到 Hermes Agent 的方式

### 方式一：消息前置推理（推荐）

在 Hermes 的 AGENTS.md 或消息管道中配置：

```yaml
# 每条用户消息到达 Agent 前，先调 SRA
pre_process:
  - curl -s -X POST http://127.0.0.1:8536/recommend
    -H "Content-Type: application/json"
    -d '{"message": "<用户消息原文>"}'
  - 将返回的 rag_context 注入到 Agent 的系统提示中
```

### 方式二：Python SDK

```python
from sra_agent.adapters import get_adapter

adapter = get_adapter('hermes')
recs = adapter.recommend("画个架构图")
print(adapter.format_suggestion(recs))

# 生成系统提示块
system_block = adapter.to_system_prompt_block()
print(system_block)
```

### 方式三：HTTP API（通用）

```bash
curl -s -X POST http://127.0.0.1:8536/recommend \
  -H "Content-Type: application/json" \
  -d '{"message": "画个架构图"}'
```

---

## 返回格式说明

`POST /recommend` 返回的 JSON 包含以下几个关键字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `rag_context` | string | 格式化的 RAG 上下文文本，直接注入 Agent 系统提示 |
| `recommendations` | array | 推荐技能列表，按得分降序 |
| `top_skill` | string | 得分最高的技能名称 |
| `should_auto_load` | bool | 最高分 ≥ 80 时为 true，建议 Agent 自动加载该技能 |
| `sra_available` | bool | SRA 是否可用（daemon 健康） |
| `sra_version` | string | SRA 版本 |
| `timing_ms` | number | 处理耗时（毫秒） |

---

## 已知限制和未来方向

### 当前限制

| 限制 | 说明 | 影响 |
|------|------|------|
| 语义理解待改进 | 自然语言长查询（L3）召回偏低（26.7/100） | 复杂自然语言描述的任务匹配不精准 |
| 部分 skill 只有英文 trigger | "html-guide"等74个skill完全没有中文trigger | 纯中文查询需要同义词映射桥接 |
| 无运行时技能遵循校验 | SRA 推荐只是建议，Agent 可选择忽略 | 长任务中 Agent 经常跳过推荐 skill |

### v2.0 改进方向（EPIC-003）

| 优先级 | 改进项 | 目标 |
|--------|--------|------|
| 🔴 P0 | **Tool 层 SRA 校验** — `POST /validate` + pre_tool_call hook | Agent 调用 write_file 前自动校验技能 |
| 🔴 P0 | **文件类型技能映射** — FILE_SKILL_MAP | `.html` → html-presentation 自动关联 |
| 🟡 P1 | **技能使用轨迹记录** — POST /record 扩展 | 追踪「已加载/已使用/已忽略」 |
| 🟡 P1 | **长任务上下文保持** — 每 5 轮重注入 | 防止 SRA 推荐被对话上下文「冲走」 |
| 🟡 P1 | **SRA 契约机制** — recommend 返回 contract 字段 | 任务开始时生成明确的技能需求清单 |
| 🟢 P2 | **可配置严格度** — relaxed / normal / strict | 适应不同场景的校验强度需求 |
| 🟢 P2 | **遵循率仪表盘** — GET /stats/compliance | 可视化展示 SRA 推荐被遵循的比例 |
| 🟢 P2 | **推荐质量反馈闭环** — 采纳率权重调整 | 高频技能获得更高优先级 |

### 远期愿景

- **主动学习**：根据场景记忆自动调整推荐权重，高频场景更快匹配
- **多级推荐**：不仅是 skill 级别，还能推荐 skill 内的具体章节
- **Agent 反馈回路**：Agent 用了推荐技能后自动反馈结果给 SRA
- **多 Agent 适配器**：Claude Code / Codex CLI / OpenCode 统一接入
