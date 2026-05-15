---
story: STORY-4-4-1
title: "post_tool_call hook 注册 + skill_view → POST /record {action: 'viewed'}"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-4
epic: EPIC-004
estimated_hours: 1
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-4.md
  - hermes_cli/plugins.py (VALID_HOOKS → post_tool_call)
dependencies:
  - client.py (已有 record() 方法)
out_of_scope:
  - 非 skill 类工具的记录（STORY-4-4-2）
  - 集成测试（STORY-4-4-3）
---

# STORY-4-4-1: post_tool_call hook + skill_view 轨迹记录

## 用户故事

> As a **SRA 推荐引擎**,
> I want **每次 Agent 调用 skill_view 时自动记录到 SRA**,
> So that **SRA 知道哪些技能被实际加载过，从而优化推荐排序**。

---

## 验收标准

### AC-1: post_tool_call hook 被注册
- [x] 条件: `register(ctx)` 调用 `ctx.register_hook("post_tool_call", callback)`
- [x] 验证: mock PluginRegistrationContext 检查 hooks
- [x] 预期: post_tool_call 列表包含 sra-guard 的回调

### AC-2: 回调签名匹配
- [x] 条件: 回调函数接收 `(tool_name, args, result, task_id, session_id, tool_call_id, duration_ms, **kwargs)`
- [x] 验证: 直接调用回调检查参数
- [x] 预期: 不因参数不匹配抛异常

### AC-3: skill_view → action="viewed"
- [x] 条件: `tool_name == "skill_view"` 且 args 包含 name
- [x] 验证: mock client.record() 检查调用参数
- [x] 预期: `client.record(skill=name, action="viewed")` 被调用

### AC-4: skills_list 也被记录
- [x] 条件: `tool_name == "skills_list"`
- [x] 验证: mock client.record() 检查调用
- [x] 预期: `client.record(skill="", action="viewed")` 被调用（无具体技能名）

### AC-5: SRA 不可用时静默降级
- [x] 条件: client.record() 返回 False 或抛出异常
- [x] 验证: mock client 模拟失败
- [x] 预期: 回调不抛异常，返回 None

---

## 技术要求

- 在 `__init__.py` 中添加 `_on_post_tool_call()` 函数
- 在 `register()` 中添加 `ctx.register_hook("post_tool_call", _on_post_tool_call)`
- 利用已有的 `client.record()` 方法（已在 client.py 中实现）
- 回调是观察性的（observational），返回值被框架忽略

### 伪代码

```python
SKILL_TOOLS = {"skill_view", "skills_list", "skill_manage"}

def _on_post_tool_call(tool_name, args, result, task_id, session_id, tool_call_id, duration_ms, **kwargs):
    try:
        if tool_name in SKILL_TOOLS:
            skill_name = args.get("name", "") if isinstance(args, dict) else ""
            client.record(skill=skill_name, action="viewed")
        return None
    except Exception:
        logger.warning(...)
    return None
```

---

## 实施计划

### Task 1: 在 __init__.py 中添加 _on_post_tool_call()
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 添加 `_on_post_tool_call()` 函数 + hook 注册
- **验证**: test_tracking.py 中验证 post_tool_call hook 注册

### Task 2: 实现 skill_view 记录逻辑
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 实现 skill_view/skills_list → client.record() 调用
- **验证**: mock 测试验证调用参数

---

## 完成检查清单

- [x] 所有 5 个 AC 通过
- [x] post_tool_call hook 注册成功
- [x] skill_view → viewed 记录正确
- [x] skills_list 也被记录
- [x] 异常时静默降级
