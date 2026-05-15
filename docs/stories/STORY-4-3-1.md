---
story: STORY-4-3-1
title: "pre_tool_call → POST /validate 核心链路"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-3
epic: EPIC-004
estimated_hours: 2
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-3.md
  - ~/.hermes/hermes-agent/model_tools.py (L722-726)
dependencies:
  - Phase 0 (client.py)
out_of_scope:
  - Force level 感知（STORY-4-3-2）
  - 集成测试（STORY-4-3-3）
---

# STORY-4-3-1: pre_tool_call → POST /validate 核心链路

## 用户故事

> As a **Hermes Agent 运行环境**,
> I want **在 Agent 调用 write_file/patch 等工具前自动调 SRA 校验**,
> So that **防止 Agent 因忘记加载对应技能而产出低质量结果**。

---

## 验收标准

### AC-1: pre_tool_call hook 被注册
- [x] 条件: `register(ctx)` 调用 `ctx.register_hook("pre_tool_call", callback)`
- [x] 验证: mock PluginRegistrationContext 检查 hooks
- [x] 预期: pre_tool_call 列表包含 sra-guard 的回调

### AC-2: 回调签名匹配
- [x] 条件: 回调函数接收 `(tool_name, args, task_id, session_id, tool_call_id, **kwargs)`
- [x] 验证: 检查函数签名
- [x] 预期: 不因参数不匹配抛异常

### AC-3: 调用 SraClient.validate()
- [x] 条件: 工具调用时触发
- [x] 验证: mock SraClient 检查 validate 是否被调用
- [x] 预期: validate(tool, args, loaded_skills=[]) 被调用

### AC-4: compliant=True 放行
- [x] 条件: SRA 返回 {"compliant": true}
- [x] 验证: 检查回调返回值
- [x] 预期: 返回 None（不阻断）

### AC-5: severity=warning 放行
- [x] 条件: SRA 返回 {"compliant": false, "severity": "warning"}
- [x] 验证: 检查回调返回值
- [x] 预期: 返回 None（不阻断，仅记录日志）

### AC-6: severity=block 阻断
- [x] 条件: SRA 返回 {"compliant": false, "severity": "block", "message": "..."}
- [x] 验证: 检查回调返回值
- [x] 预期: 返回 {"action": "block", "message": "..."}

### AC-7: SRA 不可用放行
- [x] 条件: SRA Daemon 不可用
- [x] 验证: mock SraClient 抛出异常
- [x] 预期: 返回 None

### AC-8: 异常不传播
- [x] 条件: 回调内抛出任何异常
- [x] 验证: try/except 包裹
- [x] 预期: 返回 None，记录 WARNING 日志

---

## 技术要求

- 注册 `pre_tool_call` hook（与已有的 `pre_llm_call` 并列）
- 回调中通过 `_get_client().validate()` 调 SRA
- 遵循 Hermes hook 规范（pre_tool_call 回调签名）

### Hermes pre_tool_call 文档

```python
# 来自 hermes_cli/plugins.py 的 get_pre_tool_call_block_message()
# 回调签名：(tool_name, args, task_id, session_id, tool_call_id, **kwargs)
# 返回值：None（放行）或 {"action": "block", "message": "..."}（阻断）
```

---

## 实施计划

### Task 1: 在 __init__.py 中注册 pre_tool_call hook
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 添加 `_on_pre_tool_call()` 回调 + 在 `register()` 中注册
- **验证**: test_plugin 中验证 pre_tool_call hook

### Task 2: 实现校验逻辑
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 实现 `_on_pre_tool_call()` 提取 tool/args → validate → 判断 severity
- **验证**: 手动 mock 测试

### Task 3: 编写单元测试
- **文件**: `plugins/sra-guard/tests/test_validate_hook.py`
- **操作**: 覆盖 AC 1-8
- **验证**: pytest 通过

---

## 完成检查清单

- [x] 所有 8 个 AC 通过
- [x] pre_tool_call hook 注册成功
- [x] severity=block 时阻断工具
- [x] severity=warning/info 时放行
- [x] 异常/不可用时降级
