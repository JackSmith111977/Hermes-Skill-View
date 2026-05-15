---
story: STORY-4-6-1
title: "EPIC-003 AC 真相更新 — 4 个 Hermes 侧 AC 标记为已完成"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-6
epic: EPIC-004
estimated_hours: 0.5
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-6.md
  - EPIC-003-v2-enforcement-layer.md
dependencies:
  - Phase 2 (pre_tool_call)
  - Phase 3 (轨迹追踪)
  - Phase 4 (周期重注入)
out_of_scope:
  - RUNTIME.md/README.md 更新（STORY-4-6-2）
---

# STORY-4-6-1: EPIC-003 AC 真相更新

## 用户故事

> As a **项目维护者**,
> I want **EPIC-003 的 AC 标记反映真实完成状态**,
> So that **后续开发者不会被虚假的 [ ] 或 [x] 误导**。

---

## 验收标准

### AC-1: Story 1 pre_tool_call AC → [x]
- [x] 条件: EPIC-003 Story 1 的 "Hermes pre_tool_call hook 集成" AC
- [x] 操作: 从 `[ ]` 改为 `[x]`
- [x] 验证: 添加注释 `<!-- 验证: python3 -m pytest plugins/sra-guard/tests/test_validate_hook.py -q -->`

### AC-2: Story 3 skill_view AC → [x]
- [x] 条件: EPIC-003 Story 3 的 "skill_view → POST /record" AC
- [x] 操作: 从 `[ ]` 改为 `[x]`
- [x] 验证: 添加注释 `<!-- 验证: python3 -m pytest plugins/sra-guard/tests/test_tracking.py -q -->`

### AC-3: Story 3 工具调用 AC → [x]
- [x] 条件: EPIC-003 Story 3 的 "工具调用 → POST /record" AC
- [x] 操作: 从 `[ ]` 改为 `[x]`
- [x] 验证: 同上（同一测试文件）

### AC-4: Story 4 每5轮重查 AC → [x]
- [x] 条件: EPIC-003 Story 4 的 "每 5 轮自动重查" AC
- [x] 操作: 从 `[ ]` 改为 `[x]`
- [x] 验证: 添加注释 `<!-- 验证: python3 -m pytest plugins/sra-guard/tests/test_recheck.py -q -->`

### AC-5: 头部状态更新
- [x] 条件: EPIC-003 头部状态行
- [x] 操作: 从「进行中」改为「已完成 — SRA 侧 + Hermes 侧（EPIC-004 Phase 2/3/4）」
- [x] 验证: 检查头部

---

## 完成检查清单

- [x] 所有 5 个 AC 通过
- [x] 4 个 AC 标记为 [x] + 验证注释
- [x] 头部状态更新
