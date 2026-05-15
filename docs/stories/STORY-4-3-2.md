---
story: STORY-4-3-2
title: "Force Level 感知 — 根据力度级别决定监控哪些工具"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-3
epic: EPIC-004
estimated_hours: 0.5
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-3.md
  - ~/projects/sra/skill_advisor/runtime/force.py
dependencies:
  - STORY-4-3-1
out_of_scope:
  - 从 SRA Daemon 获取 force level（当前硬编码默认值）
  - 实现 force level 的运行时切换
---

# STORY-4-3-2: Force Level 感知

## 用户故事

> As a **SRA 管理员**,
> I want **根据力度级别决定是否校验工具调用**,
> So that **basic 级别不增加额外延迟，advanced/omni 级别全面监控**。

---

## 背景

SRA Daemon 的 `force.py` 定义了 4 级力度：

| 级别 | pre_tool_call 监控 | 说明 |
|:-----|:------------------|:------|
| basic | 无 | 仅消息推荐，不校验工具 |
| medium | 关键工具 | write_file, patch, terminal, execute_code |
| advanced | 全部工具 | 所有工具都校验 |
| omni | 全部工具 | 同 advanced |

当前 sra-guard 插件在 Phase 2 默认使用 `medium` 级别。

---

## 验收标准

### AC-1: medium 级别监控关键工具
- [x] 条件: `should_validate("write_file", "medium")`
- [x] 验证: 检查监控列表
- [x] 预期: write_file / patch / terminal / execute_code 被监控

### AC-2: advanced/omni 监控全部工具
- [x] 条件: `should_validate("any_tool", "advanced")`
- [x] 验证: 检查返回值
- [x] 预期: 全部工具返回 True

### AC-3: basic 级别不监控
- [x] 条件: `should_validate("write_file", "basic")`
- [x] 验证: 检查返回值
- [x] 预期: 返回 False

### AC-4: 默认级别为 medium
- [x] 条件: 未配置 force level 时
- [x] 验证: 检查默认值
- [x] 预期: `DEFAULT_FORCE_LEVEL = "medium"`

---

## 技术要求

- 在 `__init__.py` 中定义 `MONITORED_TOOLS` 映射表
- 与 SRA Daemon 的 `force.py` 定义对齐
- 简单实现（当前不依赖 SRA Daemon 返回 force level）

### 映射表

```python
FORCE_TOOL_MAP = {
    "basic":    set(),
    "medium":   {"write_file", "patch", "terminal", "execute_code"},
    "advanced": "__all__",
    "omni":     "__all__",
}
```

---

## 实施计划

### Task 1: 在 __init__.py 中添加 force level 配置
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 添加 `DEFAULT_FORCE_LEVEL` + `_should_validate()` 函数
- **验证**: pytest 通过

### Task 2: 在 _on_pre_tool_call 中集成
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 在回调开始时检查 `_should_validate()`，false 则直接返回 None
- **验证**: 测试 basic 级别不校验

---

## 完成检查清单

- [x] 所有 4 个 AC 通过
- [x] medium 级别监控 4 个关键工具
- [x] basic 级别不监控
- [x] advanced/omni 监控全部
- [x] 默认 medium
