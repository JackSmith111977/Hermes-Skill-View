---
story: STORY-4-4-3
title: "集成测试 — 轨迹追踪场景全覆盖"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-4
epic: EPIC-004
estimated_hours: 0.5
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-4.md
dependencies:
  - STORY-4-4-1
  - STORY-4-4-2
out_of_scope:
  - 端到端测试（依赖真实 SRA Daemon）
  - 与 pre_llm_call / pre_tool_call hook 交互测试
---

# STORY-4-4-3: 集成测试

## 用户故事

> As a **sra-guard 插件维护者**,
> I want **完整的集成测试覆盖轨迹追踪各类场景**,
> So that **每次修改后都能自动验证记录逻辑的正确性**。

---

## 验收标准

### AC-1: skill_view 调用 → action="viewed"
- [x] 条件: 模拟 `_on_post_tool_call("skill_view", {"name": "test-skill"}, ...)` 调用
- [x] 验证: mock client.record() 检查调用参数
- [x] 预期: client.record(skill="test-skill", action="viewed") 被调用 1 次

### AC-2: write_file 调用 → action="used"
- [x] 条件: 模拟 `_on_post_tool_call("write_file", {"path": "test.html"}, ...)` 调用
- [x] 验证: mock client.record() 检查调用参数
- [x] 预期: client.record(skill="", action="used") 被调用 1 次

### AC-3: 内部工具被忽略
- [x] 条件: 模拟 `_on_post_tool_call("todo", {...}, ...)` 调用
- [x] 验证: mock client.record() 检查是否被调用
- [x] 预期: client.record() 未被调用

### AC-4: SRA 不可用降级
- [x] 条件: client 为 None（初始化失败）
- [x] 验证: 模拟 _get_client() 返回 None
- [x] 预期: 回调返回 None，不抛异常

### AC-5: 回归测试通过
- [x] 条件: 所有测试运行
- [x] 验证: pytest tests/ -q
- [x] 预期: 55 + 新增 passed

---

## 技术要求

- 复用 `test_injection.py` 中的 mock 模式
- 测试使用 mock client，不依赖真实 SRA Daemon
- 测试 `__init__.py` 中的 `_on_post_tool_call()` 函数直接调用
- 使用 `monkeypatch` 模拟 `_get_client()` 返回值

---

## 实施计划

### Task 1: 创建 test_tracking.py
- **文件**: `plugins/sra-guard/tests/test_tracking.py`
- **操作**: 实现 AC 1-5
- **验证**: pytest -v

### Task 2: 回归测试
- **操作**: 运行全部测试
- **验证**: 55 + 新增全部通过

---

## 完成检查清单

- [x] 所有 5 个 AC 通过
- [x] skill_view/viewed + used + 忽略 + 降级 4 场景覆盖
- [x] 回归测试无退化
- [x] 不依赖真实 SRA Daemon
