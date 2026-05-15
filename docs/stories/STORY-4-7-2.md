---
story: STORY-4-7-2
title: "AC 代码存在性门禁脚本"
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
  - EPIC-001-hermes-integration.md
  - EPIC-003-v2-enforcement-layer.md
dependencies:
  - 无（独立脚本）
out_of_scope:
  - 端到端测试（STORY-4-7-1）
  - EPIC-004 收尾对齐（STORY-4-7-3）
  - 修改已有 AC 审计脚本
---

# STORY-4-7-2: AC 代码存在性门禁

## 用户故事

> As a **项目维护者**,
> I want **自动化验证每个 [x] AC 背后有真实代码/测试**,
> So that **EPIC-001/003 的「虚假 ✅」问题不再重现**。

---

## 背景

EPIC-001 和 EPIC-003 的教训：AC 标记 `[x]` 只说明「文档上打了勾」，不说明「代码真实存在」。

```
EPIC-001: 6 个 [x] AC → 全部虚假 → 补丁从未执行
EPIC-003: 6 个 [x] AC → 虚假 → Hermes 侧从未实现

根因: AC 审计只做文本匹配，不做代码存在性验证
```

本 Story 创建的门禁脚本，通过读取 AC 行后的 `<!-- 验证: ... -->` 注释，**实际执行验证命令**来判断 AC 是否真实完成。

---

## 验收标准

### AC-1: 脚本可执行
- [x] 条件: `python3 scripts/ac-audit-code-check.py`
- [x] 验证: 有 `--help` / `--check-file`
- [x] 预期: 正常运行，不崩溃

### AC-2: 提取 [x] AC 的验证注释
- [x] 条件: 读取 EPIC-004.md
- [x] 验证: 解析 `<!-- 验证: ... -->` 注释
- [x] 预期: 提取所有 `[x]` + `<!-- 验证:` 行

### AC-3: 测试文件存在性验证
- [x] 条件: 验证注释引用测试文件路径
- [x] 验证: `pytest <path> --collect-only -q`
- [x] 预期: 测试存在 → 通过，不存在 → 报错

### AC-4: 发现缺失时 exit 1
- [x] 条件: 引用不存在的测试文件
- [x] 验证: 检查 exit code
- [x] 预期: exit 1 + 输出缺失清单

### AC-5: 全部通过时 exit 0
- [x] 条件: 引用存在的测试文件
- [x] 验证: 检查 exit code
- [x] 预期: exit 0 + 通过报告

---

## 技术要求

- 纯 Python 3 脚本，无外部依赖
- 使用 re 正则解析 AC 行和验证注释
- 使用 `subprocess.run(["pytest", ...])` 执行验证
- 设计为可被 CI 调用（exit code 门禁）

---

## 实施计划

### Task 1: 创建 ac-audit-code-check.py
- **文件**: `scripts/ac-audit-code-check.py`
- **操作**: 实现 AC 1-5
- **验证**: 对 EPIC-004.md 执行检查

### Task 2: 测试验证
- **操作**: 用存在和不存在的路径测试
- **验证**: exit code 正确

---

## 完成检查清单

- [x] 所有 5 个 AC 通过
- [x] 脚本解析 EPIC-004 验证注释
- [x] 测试存在 → exit 0
- [x] 测试缺失 → exit 1 + 清单
- [x] 无外部依赖
