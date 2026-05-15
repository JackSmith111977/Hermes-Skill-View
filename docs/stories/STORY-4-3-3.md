---
story: STORY-4-3-3
title: "集成测试 — 工具校验场景全覆盖"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-3
epic: EPIC-004
estimated_hours: 1
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-3.md
dependencies:
  - STORY-4-3-1
  - STORY-4-3-2
out_of_scope:
  - 端到端测试（依赖真实 SRA Daemon）
  - 与 pre_llm_call hook 交互测试
---

# STORY-4-3-3: 集成测试

## 用户故事

> As a **sra-guard 插件维护者**,
> I want **完整的集成测试覆盖工具校验的各类场景**,
> So that **每次修改后都能自动验证校验逻辑的正确性**。

---

## 验收标准

### AC-1: 正常工具调用放行
- [x] 条件: write_file 调用，SRA 返回 compliant
- [x] 验证: 检查 `_on_pre_tool_call()` 返回值
- [x] 预期: 返回 None

### AC-2: 不合规工具放行（severity=warning）
- [x] 条件: write_file 调用，SRA 返回 {"compliant": false, "severity": "warning"}
- [x] 验证: 检查返回值
- [x] 预期: 返回 None（仅提醒，不阻断）

### AC-3: SRA 不可用放行
- [x] 条件: SRA Daemon 不可用
- [x] 验证: 检查返回值
- [x] 预期: 返回 None

### AC-4: basic 级别不校验
- [x] 条件: force_level="basic"
- [x] 验证: 检查返回值
- [x] 预期: 返回 None（直接跳过校验）

### AC-5: 回归测试通过
- [x] 条件: 所有测试运行
- [x] 验证: pytest tests/ -q
- [x] 预期: 40 + 新增 passed

---

## 技术要求

- 复用 `test_injection.py` 中的 `MockSRAHandler`
- 测试使用 mock client，不依赖真实 SRA Daemon
- pre_tool_call 回调与 pre_llm_call 互不干扰

---

## 实施计划

### Task 1: 创建 test_validate_hook.py
- **文件**: `plugins/sra-guard/tests/test_validate_hook.py`
- **操作**: 实现 AC 1-5
- **验证**: pytest -v

### Task 2: 回归测试
- **操作**: 运行全部测试
- **验证**: 40 + 新增全部通过

---

## 完成检查清单

- [x] 所有 5 个 AC 通过
- [x] 正常/不合规/SRA不可用/basic级别 4 场景覆盖
- [x] 回归测试无退化
- [x] 不依赖真实 SRA Daemon
