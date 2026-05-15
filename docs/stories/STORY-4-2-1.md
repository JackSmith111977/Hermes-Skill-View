---
story: STORY-4-2-1
title: "[SRA] 上下文格式化 — format_sra_context()"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-2
epic: EPIC-004
estimated_hours: 1
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-2.md
dependencies:
  - STORY-4-1-3
out_of_scope:
  - 缓存逻辑（STORY-4-2-2）
  - 集成测试（STORY-4-2-3）
---

# STORY-4-2-1: [SRA] 上下文格式化

## 用户故事

> As a **sra-guard 插件**,
> I want **将 SRA Daemon 返回的 rag_context 格式化为带 [SRA] 前缀的可读文本**,
> So that **注入到用户消息前时 LLM 能清晰知道这是 SRA 技能推荐**。

---

## 验收标准

### AC-1: 格式化函数存在
- [x] 条件: `formatter.py` 中存在 `format_sra_context()` 函数
- [x] 验证: `from formatter import format_sra_context`
- [x] 预期: 函数可调用

### AC-2: 输出以 [SRA] 开头
- [x] 条件: 调用 `format_sra_context(rag_context, "test-skill", False)`
- [x] 验证: 检查返回值开头
- [x] 预期: 以 `[SRA] Skill Runtime Advisor 推荐:` 开头

### AC-3: 包含原始 rag_context 内容
- [x] 条件: 传入包含 "test-skill" 的 rag_context
- [x] 验证: 检查返回值是否包含 "test-skill"
- [x] 预期: 原始内容被保留

### AC-4: should_auto_load=True 时追加 skill 名称
- [x] 条件: `format_sra_context(ctx, "architecture-diagram", True)`
- [x] 验证: 检查返回值是否包含 `⚡ 建议自动加载`
- [x] 预期: 包含 `⚡ 建议自动加载: architecture-diagram`

### AC-5: 超过 2500 字符时截断
- [x] 条件: 传入超过 2500 字符的上下文
- [x] 验证: 检查返回值长度
- [x] 预期: 长度 ≤ 2500

### AC-6: 空 rag_context 返回空字符串
- [x] 条件: `format_sra_context("", None, False)`
- [x] 验证: 检查返回值
- [x] 预期: 返回 `""`

---

## 技术要求

- 独立模块 `formatter.py`，与 hook 回调解耦
- 输出格式与现有 SRA Proxy 输出一致（参考 `daemon.py` 的 POST /recommend 响应）
- 不引入外部依赖

### 格式化模板

```
[SRA] Skill Runtime Advisor 推荐:
── [SRA Skill 推荐] ──────────────────────────────
  ⭐ [medium] skill-name (42.5分) — reason1 | reason2
     [medium] skill-name2 (40.0分) — reason1
── ──────────────────────────────────────────────
⚡ 建议自动加载: skill-name     # 仅 when should_auto_load=True
```

---

## 实施计划

### Task 1: 创建 formatter.py
- **文件**: `plugins/sra-guard/formatter.py`
- **操作**: 实现 `format_sra_context()` 函数
- **验证**: 手动调用验证输出格式

### Task 2: 接入 __init__.py
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 在 `_on_pre_llm_call` 中调用 formatter 格式化结果
- **验证**: 回归测试 19 passed

### Task 3: 编写单元测试
- **文件**: `plugins/sra-guard/tests/test_formatter.py`
- **操作**: 覆盖 AC 1-6
- **验证**: `pytest tests/test_formatter.py -v`

---

## 测试策略

- **Fixture**: 无（纯函数，无外部依赖）
- **新测试文件**: `tests/test_formatter.py`
- **CI 环境**: 完全独立

---

## 完成检查清单

- [x] 所有 6 个 AC 通过
- [x] 输出格式与现有 Proxy 输出一致
- [x] 2500 字符截断正常工作
- [x] 空输入处理正确
- [x] 代码 + 文档同次 commit
