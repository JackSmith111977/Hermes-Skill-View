---
spec_id: SPEC-4-3
title: "工具调用校验 — pre_tool_call → POST /validate"
status: completed
epic: EPIC-004
created: 2026-05-15
updated: 2026-05-15
stories:
  - STORY-4-3-1
  - STORY-4-3-2
  - STORY-4-3-3
test_data_contract:
  source: tests/fixtures/skills
  ci_independent: true
---

# SPEC-4-3: 工具调用校验

> **所属 Epic**: EPIC-004
> **状态**: draft
> **目标**: 在 pre_tool_call hook 中调用 SRA `/validate`，在 Agent 执行 `write_file` / `patch` 等工具前检查是否已加载对应技能
> **估时**: 3.5h
> **依赖**: Phase 1 (消息注入已就绪)

---

## 背景

当前 SRA Daemon 已经有完善的 `/validate` 端点（EPIC-003 实现）：
- `POST /validate` — 接收 `{tool, args, loaded_skills[]}`
- 返回 `{compliant, missing[], severity, message}`
- 内部集成 `SkillMapRegistry`（文件扩展名→技能映射）

但 Hermes 侧从未接入此端点（EPIC-003 Story 1 的虚假 ✅）。

Hermes 已有 `pre_tool_call` hook 系统（`model_tools.py:722-726`），插件可以注册回调，在工具执行前获得拦截机会。

Phase 2 的目标是创建 `sra-guard` 插件的 `pre_tool_call` hook，在 Agent 调用关键工具前自动校验技能加载。

### Hermes pre_tool_call hook 机制

```python
# model_tools.py — 已有代码
block_message = get_pre_tool_call_block_message(
    tool_name, args, task_id, session_id, tool_call_id
)
if block_message is not None:
    return json.dumps({"error": block_message})  # 阻断工具执行
```

插件通过 `ctx.register_hook("pre_tool_call", callback)` 注册回调。
回调返回 `{"action": "block", "message": "..."}` 时阻断工具。

---

## Scope（范围内）

- 注册 `pre_tool_call` hook 回调
- 回调中提取工具名称和参数 → `POST /validate`
- 根据返回的 `severity` 决定是否阻断
- 支持 force level 配置（basic 级别不校验）
- 编写集成测试

## Out of Scope（不做）

- ❌ 修改 SRA Daemon 的 `/validate` 端点（已完成）
- ❌ 技能使用轨迹追踪（Phase 3）
- ❌ 周期性重注入（Phase 4）

---

## 架构设计

### 校验流程

```
Agent 调用 write_file("test.html")
    ↓
pre_tool_call hook 触发
    ↓
提取 tool_name="write_file", args={"path": "test.html"}
    ↓
检查 force level → "basic" → 放行（不校验）
                     ↓
SraClient.validate(tool, args, loaded_skills)
    ↓ HTTP POST /validate
返回 {"compliant": false, "missing": ["html-presentation"], "severity": "warning"}
    ↓
severity="block" → return {"action": "block", "message": "..."}
severity="warning" → return None（仅提醒，不阻断）
severity="info" → return None（不阻断）
SRA 不可用 → return None（优雅降级）
```

### 阻断策略

| severity | 动作 | 说明 |
|:---------|:-----|:------|
| `block` | 阻断工具执行 | 返回 `{"action": "block", "message": "..."}` |
| `warning` | 不阻断，仅记录日志 | 返回 None（Hermes 不拦截） |
| `info` | 不阻断 | 返回 None |
| SRA 超时/不可用 | 不阻断 | 返回 None（优雅降级） |

### Force Level 感知

```python
# 根据当前 force level 决定是否校验
force_levels = {
    "basic":    {"pre_tool_call": False},  # 消息级推荐 仅 Phase 1
    "medium":   {"pre_tool_call": ["write_file", "patch", "terminal", "execute_code"]},
    "advanced": {"pre_tool_call": "__all__"},
    "omni":     {"pre_tool_call": "__all__"},
}
```

Phase 2 默认使用 `medium` 级别的监控工具集。

---

## Stories

### STORY-4-3-1: pre_tool_call → POST /validate

| 字段 | 值 |
|:-----|:-----|
| **估时** | 2h |
| **文件** | `plugins/sra-guard/__init__.py` |

**验收标准**:
- [x] `register()` 中注册 `pre_tool_call` hook
- [x] 回调签名匹配 `(tool_name, args, task_id, session_id, tool_call_id, **kwargs)`
- [x] 回调调用 `SraClient.validate(tool, args, loaded_skills=[])`
- [x] `compliant=True` 时返回 None（放行）
- [x] `severity="warning"` 时返回 None（仅提醒）
- [x] `severity="block"` 时返回 `{"action": "block", "message": "..."}`（阻断）
- [x] SRA 不可用时返回 None（优雅降级）
- [x] 异常时返回 None（不阻塞工具执行）

### STORY-4-3-2: Force Level 感知

| 字段 | 值 |
|:-----|:-----|
| **估时** | 0.5h |
| **文件** | `plugins/sra-guard/__init__.py` |

**验收标准**:
- [x] `medium` 级别：仅监控 write_file / patch / terminal / execute_code
- [x] `advanced/omni` 级别：监控全部工具
- [x] `basic` 级别：不校验任何工具
- [x] 默认级别为 `medium`
- [x] 可在 `register()` 时通过 ctx.config 覆盖

### STORY-4-3-3: 集成测试

| 字段 | 值 |
|:-----|:-----|
| **估时** | 1h |
| **文件** | `tests/test_validate_hook.py` [NEW] |

**验收标准**:
- [x] 正常工具调用 → SRA 返回 compliant → 放行
- [x] 不合规工具（missing skills）→ severity=warning → 放行（非阻断）
- [x] SRA 不可用 → 不阻断（优雅降级）
- [x] basic 级别不校验
- [x] 回归测试通过

---

## 完成条件

- [x] 所有 3 个 Story 的 AC 全部通过
- [x] pre_tool_call hook 注册成功
- [x] 校验链路完整（tool → /validate → compliant/block）
- [x] force level 感知正确
- [x] 集成测试覆盖正常/异常/降级场景
- [x] 回归测试（40 + 新增）全绿
