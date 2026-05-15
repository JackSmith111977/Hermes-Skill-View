---
spec_id: SPEC-4-6
title: "修复文档漂移 — 更新 EPIC-003 AC 真相 + README/RUNTIME 一致性"
status: completed
epic: EPIC-004
created: 2026-05-15
updated: 2026-05-15
stories:
  - STORY-4-6-1
  - STORY-4-6-2
test_data_contract:
  source: tests/fixtures/skills
  ci_independent: true
---

# SPEC-4-6: 修复文档漂移

> **所属 Epic**: EPIC-004
> **状态**: draft
> **目标**: 更新 EPIC-003 的 AC 标记为真实状态，同步 RUNTIME.md / README.md 一致性
> **估时**: 1h
> **依赖**: Phase 0-4 全部完成（文档对齐前提）

---

## 背景

### 为什么还需要 Phase 5？

STORY-4-1-5（Phase 0）已完成了大部分文档对齐：
- INTEGRATION.md → 插件方案 ✅
- EPIC-001 → 废弃标记 ✅
- patches → DEPRECATED 标记 ✅

但有一个关键遗漏：**EPIC-003 的 AC 标记仍停留在修正前的状态**。

### 当前 EPIC-003 的 AC 状态

```
修正前（STORY-4-1-5）：6个虚假 ✅ → 改为 [ ] + 注释指向 EPIC-004
现在（Phase 2/3/4 完成）：4个 AC 已真正实现！应更新为 [x] + 验证说明

具体：
[ ] Hermes pre_tool_call hook 集成  →  Phase 2 完成 ✅  (test_validate_hook.py)
[ ] Hermes skill_view → POST /record →  Phase 3 完成 ✅  (test_tracking.py)
[ ] Hermes 工具调用 → POST /record   →  Phase 3 完成 ✅  (test_tracking.py)
[ ] Hermes 每5轮自动重查            →  Phase 4 完成 ✅  (test_recheck.py)
```

---

## Scope（范围内）

- 更新 EPIC-003 的 4 个 Hermes 侧 AC 标记为 `[x]` + 验证方式说明
- 更新 EPIC-003 头部状态为「完成（Hermes 侧通过 EPIC-004 插件实现）」
- 检查 RUNTIME.md 是否引用旧补丁方案，更新为插件方案
- 验证 README.md 集成说明一致性

## Out of Scope（不做）

- ❌ 修改 INTEGRATION.md（Phase 0 已完成）
- ❌ 修改 EPIC-001（Phase 0 已完成）
- ❌ 补丁文件（Phase 0 已完成）
- ❌ 重写完整的项目文档体系

---

## Stories

### STORY-4-6-1: EPIC-003 AC 真相更新

| 字段 | 值 |
|:-----|:-----|
| **估时** | 0.5h |
| **文件** | `docs/EPIC-003-v2-enforcement-layer.md` |

**验收标准**:
- [x] 4 个 Hermes 侧 AC（pre_tool_call/skill_view view/工具调用 used/每 5 轮重查）更新为 `[x]`
- [x] 每个 `[x]` 后附加验证说明（`<!-- 验证: ... -->`）
- [x] 头部状态从「进行中」更新为「已完成（SRA 侧 + Hermes 侧均实现）」
- [x] 更新日期

### STORY-4-6-2: RUNTIME.md + README.md 一致性检查

| 字段 | 值 |
|:-----|:-----|
| **估时** | 0.5h |
| **文件** | `RUNTIME.md`, `README.md` |

**验收标准**:
- [x] RUNTIME.md 不引用旧补丁方案（如引用则更新为插件方案）
- [x] README.md 集成章节准确（插件方案而非补丁方案）
- [x] 无旧补丁方案的残留引用
- [x] 日期更新

---

## 完成条件

- [x] 所有 2 个 Story 的 AC 全部通过
- [x] EPIC-003 AC 反映真实完成状态
- [x] 每个 [x] AC 有验证方式注释
- [x] RUNTIME.md / README.md 不引用旧补丁方案
