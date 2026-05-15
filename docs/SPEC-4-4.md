---
spec_id: SPEC-4-4
title: "技能使用轨迹追踪 — post_tool_call → POST /record"
status: completed
epic: EPIC-004
created: 2026-05-15
updated: 2026-05-15
stories:
  - STORY-4-4-1
  - STORY-4-4-2
  - STORY-4-4-3
test_data_contract:
  source: tests/fixtures/skills
  ci_independent: true
---

# SPEC-4-4: 技能使用轨迹追踪

> **所属 Epic**: EPIC-004
> **状态**: draft
> **目标**: 在 post_tool_call hook 中自动向 SRA Daemon 发送技能/工具使用记录，让 SRA 掌握 Hermes 实际使用了哪些技能和工具
> **估时**: 2.5h
> **依赖**: Phase 2 (工具校验已就绪 + SraClient 已有 HTTP 通信能力)

---

## 背景

### 当前状态

SRA Daemon 已有 `/record` 端点（Sprint 2 实现），接受 `{skill, action, tool, timestamp}` 格式的记录。但目前**没有任何 Hermes 侧代码调用此端点**——这是一个能力孤岛。

### 为什么需要轨迹追踪

```
当前:                        目标:
┌──────────────────┐        ┌──────────────────┐
│ SRA Daemon       │        │ SRA Daemon       │
│ /record 端点     │        │ /record 端点     │
│ 存在但无数据 ❌  │        │ 收到实时数据 ✅  │
│                  │        │                  │
│ 推荐引擎只看     │        │ 推荐引擎结合     │
│ 技能描述匹配     │        │ 实际使用数据     │
└──────────────────┘        └──────────────────┘
                                    ↑
                            ┌───────┴───────┐
                            │ sra-guard 插件  │
                            │ post_tool_call  │
                            │ → POST /record  │
                            └───────────────┘
```

轨迹数据将帮助 SRA：
1. **推荐质量提升** — 知道哪些技能被实际使用，哪些被冷落
2. **技能健康度** — 统计技能的使用频率
3. **自动降级** — 长期不用的技能可以降低推荐优先级

### Hermes post_tool_call hook

```python
# 来自 hermes_cli/plugins.py VALID_HOOKS
VALID_HOOKS = {
    "pre_tool_call",    # Phase 2 已使用
    "post_tool_call",   # Phase 3 使用 ⬅️
    "pre_llm_call",     # Phase 1 已使用
    "post_llm_call",
    "transform_tool_result",
    "transform_terminal_output",
    "on_session_start",
    "on_session_end",
    # ...
}
```

回调签名：
```python
def _on_post_tool_call(
    tool_name: str,        # "skill_view", "write_file", "web_search"...
    args: dict,            # 工具参数字典
    result: str,           # 工具执行结果
    task_id: str,
    session_id: str,
    tool_call_id: str,
    duration_ms: int,      # 执行耗时（毫秒）
    **kwargs
) -> None:
    """Observational only — 返回值被忽略"""
```

关键发现：
- `skill_view` 是 Hermes 的内置工具，调用时会触发 tool_call
- 在 `post_tool_call` 中通过 `tool_name` 判断调用类型
- hook 是观察性的（observational），返回值被框架忽略——不会阻塞工具

---

## Scope（范围内）

- 注册 `post_tool_call` hook 回调
- 在 SraClient 中添加 `record()` 方法
- 回调中分发：skill_view/skills_list → action="viewed"，其他工具 → action="used"
- 编写集成测试（mock SRA，不依赖真实 Daemon）
- SRA 不可用时静默降级（记录 WARNING 日志）

## Out of Scope（不做）

- ❌ 修改 SRA Daemon 的 `/record` 端点（Sprint 2 已完成）
- ❌ 批量回填历史数据
- ❌ 实现实时 Dashboard（属于 SRA 前端范畴）
- ❌ 从 SRA 拉取统计数据进行本地缓存
- ❌ on_session_end 时批量 flush（当前设计为实时单条记录）

---

## 架构设计

### 时序图

```
Agent 调用 skill_view("html-presentation")
    ↓
model_tools.py handle_function_call() 分发工具
    ↓
工具执行完成
    ↓
post_tool_call hook 触发
    ↓
sra-guard _on_post_tool_call()
    ├── tool_name = "skill_view"
    ├── args["name"] = "html-presentation"
    ├── action = "viewed"
    └── client.record(skill="html-presentation", action="viewed", tool="skill_view")
        ↓ HTTP POST /record
SRA Daemon 存储记录
```

### 记录内容

```python
# POST /record payload
{
    "skill": "html-presentation",   # 技能名称（viewed 时填充，used 时空字符串）
    "action": "viewed | used",      # 操作类型
    "tool": "skill_view",           # 触发工具名称
    "timestamp": 1715731800,        # Unix 时间戳
    "session_id": "sess-xxx"        # 当前会话 ID
}
```

### action 分类规则

| 工具名 | action | skill 字段 | 说明 |
|:-------|:------|:-----------|:------|
| `skill_view` | `viewed` | args["name"] | 主动加载技能 |
| `skills_list` | `viewed` | ""（列表浏览） | 浏览技能列表 |
| `skill_manage` | `viewed` | args["name"]（如有） | 管理技能 |
| 其他工具 | `used` | "" | 常规工具使用 |
| `todo` / `memory` | 忽略 | — | 内部工具不记录 |

---

## Stories

### STORY-4-4-1: skill_view → POST /record {action: "viewed"}

| 字段 | 值 |
|:-----|:-----|
| **估时** | 1h |
| **文件** | `plugins/sra-guard/client.py`（新增 `record()`） + `__init__.py`（新增 `_on_post_tool_call()`） |

**验收标准**:
- [x] SraClient 新增 `record(skill, action, tool, session_id)` 方法，调 POST /record
- [x] `_on_post_tool_call()` 注册为 post_tool_call hook
- [x] `tool_name == "skill_view"` → 提取 args["name"] → action="viewed" → client.record()
- [x] `tool_name == "skills_list"` → action="viewed"（不带 skill 名称）
- [x] SRA 不可用时静默降级（不抛异常）

### STORY-4-4-2: 工具调用 → POST /record {action: "used"}

| 字段 | 值 |
|:-----|:-----|
| **估时** | 1h |
| **文件** | `plugins/sra-guard/__init__.py` |

**验收标准**:
- [x] 非 skill 工具调用时 action="used"
- [x] 工具名写入 `tool` 字段
- [x] `todo` / `memory` 等内部工具被忽略（不记录）
- [x] 已记录的调用不重复记录（简单去重）
- [x] 异常时不影响工具执行结果

### STORY-4-4-3: 集成测试

| 字段 | 值 |
|:-----|:-----|
| **估时** | 0.5h |
| **文件** | `tests/test_tracking.py` [NEW] |

**验收标准**:
- [x] skill_view 调用 → SRA 收到 action="viewed"
- [x] write_file 调用 → SRA 收到 action="used"
- [x] SRA 不可用 → 不抛出异常（优雅降级）
- [x] TODO 工具被忽略（不记录）
- [x] 回归测试通过

---

## 完成条件

- [x] 所有 3 个 Story 的 AC 全部通过
- [x] post_tool_call hook 注册成功
- [x] client.record() 发送 POST /record 成功
- [x] skill_view → viewed / 工具 → used 分类正确
- [x] 内部工具（todo/memory）被忽略
- [x] SRA 不可用时降级不阻塞
- [x] 回归测试全绿（55 + 新增）
