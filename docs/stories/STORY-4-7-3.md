---
story: STORY-4-7-3
title: "回归测试 + 文档对齐 — EPIC-004 收尾"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-7
epic: EPIC-004
estimated_hours: 1
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-7.md
dependencies:
  - STORY-4-7-1
  - STORY-4-7-2
out_of_scope:
  - 端到端测试逻辑（STORY-4-7-1）
  - AC 门禁脚本（STORY-4-7-2）
---

# STORY-4-7-3: 回归测试 + 文档对齐

## 用户故事

> As a **项目维护者**,
> I want **EPIC-004 的所有文档反映真实完成状态**,
> So that **EPIC-004 可以正式标记为完成**。

---

## 验收标准

### AC-1: 全量回归测试通过
- [x] 条件: 运行全部测试
- [x] 验证: `pytest tests/ -q`
- [x] 预期: 83 + 新增全部通过

### AC-2: STORY-4-7-1/2 文档完成
- [x] 条件: 端到端测试和实施完成
- [x] 操作: 更新状态 + AC 标记
- [x] 预期: `status: completed`

### AC-3: SPEC-4-7 完成
- [x] 条件: 3 个 Story 全部完成
- [x] 操作: 更新状态 + 完成条件
- [x] 预期: `status: completed`

### AC-4: EPIC-004 Phase 6 标记完成
- [x] 条件: Phase 6 出口里程碑达成
- [x] 操作: 更新已完成 Phase 表
- [x] 预期: Phase 6 出现在已完成列表中

### AC-5: EPIC-004 顶部状态 "done"
- [x] 条件: 所有 Phase 完成
- [x] 操作: EPIC-004.md 顶部状态从 active → done
- [x] 预期: `status: done`

---

## 技术要求

- 文档状态必须与代码/测试实际状态一致
- 每个 AC 的 `[x]` 必须有 `<!-- 验证: ... -->` 注释
- EPIC-004 的完成条件表全部 ✅

---

## 实施计划

### Task 1: 运行回归测试
- **操作**: `pytest tests/ -q`
- **验证**: 全绿

### Task 2: 更新文档状态
- **文件**: 4 个（STORY-4-7-1/2, SPEC-4-7, EPIC-004）
- **操作**: 状态更新 + AC 标记 + Phase 6 完成

### Task 3: EPIC-004 完成标记
- **操作**: 顶部 status → done
- **验证**: 最终一致性检查

---

## 完成检查清单

- [x] 所有 5 个 AC 通过
- [x] 回归测试全绿
- [x] 所有 Phase 6 文档 completed
- [x] EPIC-004 标记 done
- [x] EPIC-004 全部完成 🎉
