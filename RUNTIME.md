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
┌───────────────────────────────────────────────┐
│  ① Hermes Agent 收到消息                      │
│                                                │
│  ┌─────────────────────────────────────────┐   │
│  │  ② SRA Proxy (消息前置推理)              │   │
│  │     curl POST /recommend {"message": ...} │   │
│  │     ↓                                    │   │
│  │     语义匹配 → rag_context + 推荐列表     │   │
│  └─────────────────────────────────────────┘   │
│                                                │
│  ┌─────────────────────────────────────────┐   │
│  │  ③ Agent 决策                            │   │
│  │     should_auto_load = true?            │   │
│  │     → 自动加载推荐的 SKILL.md            │   │
│  │     → 或参考 rag_context 自行决定        │   │
│  └─────────────────────────────────────────┘   │
│                                                │
│  ┌─────────────────────────────────────────┐   │
│  │  ④ Agent 执行任务 + 工具调用            │   │
│  └─────────────────────────────────────────┘   │
│                                                │
│  ┌─────────────────────────────────────────┐   │
│  │  ⑤ 反馈回路 (可选)                       │   │
│  │     POST /record 记录使用情况            │   │
│  │     下次推荐会参考历史场景               │   │
│  └─────────────────────────────────────────┘   │
└───────────────────────────────────────────────┘
```

### 关键设计决策

| 决策 | 为什么 |
|------|--------|
| **独立进程，非 Agent 子进程** | Agent 可能重启、切换模型，SRA 必须独立运行保证索引不丢失 |
| **Unix Socket + HTTP 双协议** | Socket 低延迟适合本地 Agent，HTTP 适合 Proxy 模式和远程集成 |
| **无状态 API** | 每个 /recommend 请求独立处理，不维护客户端 session |
| **定时自动刷新索引** | 新加的 SKILL.md 最迟 1 小时后被 SRA 感知（当前 watch_skills_dir 待修复） |
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
| watch_skills_dir 未生效 | 文件监听机制有问题，依赖定时刷新 | 新加 SKILL.md 后最多等 1 小时才被感知 |
| 推荐分数可优化 | "设计数据库"被推荐为 PDF 排版 | 匹配策略对中文长文本不够精准 |
| 未识别 36 个技能 | 覆盖率 86.9%，部分技能缺少中文 trigger | 需要分析原因并补充同义词 |
| Hermes 集成依赖手动配置 | 需要手动修改 AGENTS.md | 不是开箱即用 |

### 中期路线图

| 优先级 | 改进项 | 目标 |
|--------|--------|------|
| 🔴 P0 | 修复 watch_skills_dir 文件监听 | 新技能秒级感知 |
| 🔴 P0 | 改进中文匹配精度 | 覆盖率提升至 95%+ |
| 🟡 P1 | 自动 Agent 集成脚本 | 一条命令完成所有配置 |
| 🟡 P1 | 推荐反馈闭环自动化 | Agent 使用技能后自动记录 |
| 🟢 P2 | 推荐质量仪表盘 | 可视化展示推荐命中率 |

### 远期愿景

- **主动学习**：根据场景记忆自动调整推荐权重，高频场景更快匹配
- **多级推荐**：不仅是 skill 级别，还能推荐 skill 内的具体章节
- **Agent 反馈回路**：Agent 用了推荐技能后自动反馈结果给 SRA
