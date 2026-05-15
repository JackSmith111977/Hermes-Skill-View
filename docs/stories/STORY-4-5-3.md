---
story: STORY-4-5-3
title: "集成测试 — 重注入场景全覆盖"
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
  - STORY-4-5-1
  - STORY-4-5-2
out_of_scope:
  - 端到端测试（依赖真实 SRA Daemon）
  - 长期集成测试
---

# STORY-4-5-3: 集成测试

## 用户故事

> As a **sra-guard 插件维护者**,
> I want **完整的测试覆盖重注入触发逻辑**,
> So that **每次修改后都能自动验证重查时机的正确性**。

---

## 验收标准

### AC-1: 未达间隔不重查
- [x] 条件: `_turn_counter < RECHECK_INTERVAL` + 缓存命中
- [x] 验证: mock client.recommend() 检查
- [x] 预期: recommend() 未被调用，返回缓存

### AC-2: 达到间隔重查
- [x] 条件: `_turn_counter >= RECHECK_INTERVAL` + 缓存命中
- [x] 验证: mock client.recommend() 检查
- [x] 预期: recommend() 被调用，返回新上下文

### AC-3: 重查后计数器重置
- [x] 条件: 重查触发
- [x] 验证: 检查模块级 `_turn_counter`
- [x] 预期: 重置为 0

### AC-4: 异常时回退
- [x] 条件: 重查时 SRA 不可用
- [x] 验证: mock client.recommend() 返回空或抛异常
- [x] 预期: 返回 None（不注入新上下文，原缓存丢失可接受）

### AC-5: 回归测试通过
- [x] 条件: 所有测试运行
- [x] 验证: pytest tests/ -q
- [x] 预期: 67 + 新增 passed

---

## 技术要求

- 复用 Phase 1 的 mock 测试模式
- 通过 `monkeypatch` 或直接设置 `mod._turn_counter` 控制测试条件
- 测试 `_on_pre_llm_call()` 的行为而不是内部实现细节

---

## 实施计划

### Task 1: 创建 test_recheck.py
- **文件**: `plugins/sra-guard/tests/test_recheck.py`
- **操作**: 实现 AC 1-5
- **验证**: pytest -v

### Task 2: 回归测试
- **操作**: 运行全部测试
- **验证**: 67 + 新增全部通过

---

## 完成检查清单

- [x] 所有 5 个 AC 通过
- [x] 未达间隔 / 达间隔 / 异常 / 重置 4 场景覆盖
- [x] 回归测试无退化
- [x] 不依赖真实 SRA Daemon
