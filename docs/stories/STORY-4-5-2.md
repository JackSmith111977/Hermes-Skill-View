---
story: STORY-4-5-2
title: "轻量提醒格式 — 复用 Phase 1 [SRA] 上下文格式"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-5
epic: EPIC-004
estimated_hours: 0.5
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-5.md
dependencies:
  - STORY-4-5-1 (共享 _on_pre_llm_call 修改)
  - Phase 1 formatter.py (_format_context)
out_of_scope:
  - 修改 formatter.py 格式
  - 重查触发逻辑（STORY-4-5-1）
---

# STORY-4-5-2: 轻量提醒格式

## 用户故事

> As a **Hermes Agent**,
> I want **重查结果以标准 [SRA] 格式注入**,
> So that **Agent 能一致地解析推荐信息，不受重查来源影响**。

---

## 验收标准

### AC-1: 复用 _format_context()
- [x] 条件: 重查得到新的 rag_context
- [x] 验证: mock _format_context 检查是否被调用
- [x] 预期: _format_context(rag_context) 被调用

### AC-2: 返回格式一致
- [x] 条件: 重查结果非空
- [x] 验证: 检查返回值
- [x] 预期: `{"context": str}` 与 Phase 1 格式完全一致

### AC-3: 空结果不注入
- [x] 条件: 重查返回空字符串
- [x] 验证: mock client.recommend() 返回空
- [x] 预期: 返回 None（不注入额外上下文）

### AC-4: 不影响缓存机制
- [x] 条件: 重查注入后
- [x] 验证: 检查缓存是否更新为新结果
- [x] 预期: 缓存更新为新 rag_context

---

## 技术要求

- 不修改 `formatter.py` 或 `_format_context()` 函数
- 重查流程完全复用 Phase 1 的现有代码路径
- 重查结果经过 `_format_context()` → `{"context": str}`

---

## 实施计划

### Task 1: 确保重查复用现有格式化路径
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 清除缓存后，代码自然走现有「缓存未命中→调 SRA→_format_context→_set_cached」路径
- **验证**: 不需要额外逻辑，测试覆盖即可

---

## 完成检查清单

- [x] 所有 4 个 AC 通过
- [x] 重查结果格式化与 Phase 1 一致
- [x] 空结果不注入
- [x] 缓存更新为新结果
