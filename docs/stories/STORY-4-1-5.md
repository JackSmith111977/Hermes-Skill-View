---
story: STORY-4-1-5
title: "文档对齐 — 修正历史文档漂移，反映插件方案真实状态"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-1
epic: EPIC-004
estimated_hours: 2
test_data:
  source: tests/fixtures/skills
  ci_independent: true
  pattern_reference: ""
spec_references:
  - EPIC-004.md
  - SPEC-4-1.md
  - docs/INTEGRATION.md
  - docs/EPIC-001-hermes-integration.md
  - docs/EPIC-003-v2-enforcement-layer.md
  - patches/hermes-sra-integration.patch
dependencies:
  - STORY-4-1-1
  - STORY-4-1-2
  - STORY-4-1-3
out_of_scope:
  - 修改 SRA 功能代码
  - 删除旧补丁文件（仅标记 DEPRECATED）
  - 修改 EPIC-002/EPIC-003 的功能性内容
---

# STORY-4-1-5: 文档对齐

## 用户故事

> As a **SRA 项目维护者**,
> I want **所有文档反映 SRA 集成的真实状态**,
> So that **后续开发者不会基于虚假的 ✅ 标记做出错误决策**。

---

## 背景

EPIC-004 的深度分析发现三重文档漂移：

| 文档 | 宣称状态 | 真实状态 | 差距 |
|:-----|:---------|:---------|:-----|
| INTEGRATION.md | 自动注入已实现（补丁方案） | 补丁从未执行 | 🔴 幻影文档 |
| EPIC-001 | ✅ 6/6 AC 全部完成 | Hermes 侧从未集成 | 🔴 虚假 ✅ |
| EPIC-003 | Story 1/3/4/6/7 标记 ✅ | Hermes 侧代码不存在 | 🔴 虚假 ✅ |
| patches/ | 补丁文件有效 | 从未被应用 | 🟡 遗留文件 |

本 Story 的目标是修正所有文档，让文字描述与代码现实一致。

---

## 验收标准

### AC-1: INTEGRATION.md 重写
- [x] 标题改为 "SRA Hermes 插件集成指南（EPIC-004）"
- [x] 删除「自动注入已实现」「不需要手动 curl」等虚假描述
- [x] 替换为插件方案的架构说明和安装步骤
- [x] 添加「旧补丁方案已废弃，见 EPIC-004」的提示

### AC-2: EPIC-001 标记为「被取代」
- [x] 文档顶部 status 改为 `deprecated`
- [x] 添加醒目提示：「⚠️ 本 Epic 描述的补丁方案从未执行。已被 EPIC-004 的插件方案取代」
- [x] 保留历史记录（不删除文件）

### AC-3: EPIC-003 修正虚假 AC
- [x] Story 1: 「Hermes pre_tool_call hook 集成」→ ✅ 改为 ❌，添加「见 EPIC-004 Phase 2」
- [x] Story 3: 「skill_view 自动触发 POST /record」→ ✅ 改为 ❌
- [x] Story 4: 「每 5 轮自动重查 SRA」→ ✅ 改为 ❌
- [x] Story 6: 「config.yaml 可覆盖 force level」→ ✅ 改为 ❌
- [x] Story 7: 「protect_first_n 包含 SRA 段」→ ✅ 改为 ❌
- [x] 顶部状态从「全部完成」改为「部分完成，见 EPIC-004」

### AC-4: README.md 同步
- [x] 集成部分增加插件方案说明
- [x] 安装步骤中补充 `bash scripts/install-hermes-plugin.sh`

### AC-5: 旧补丁文件标记 DEPRECATED
- [x] `patches/hermes-sra-integration.patch` 头部添加 DEPRECATED 注释
- [x] 指向 EPIC-004

### AC-6: 交叉引用一致性
- [x] INTEGRATION.md → EPIC-004.md 引用正确
- [x] EPIC-001 → EPIC-004 引用正确
- [x] EPIC-003 → EPIC-004 引用正确
- [x] README → INTEGRATION.md 引用正确

---

## 技术要求

- 所有文档修改基于 **真实状态**，不虚构
- 修改原则：标记为「历史」「已废弃」「被取代」，**不删除**原始内容
- 使用醒目标记（`> **⚠️**`）突出关键变化
- 保持向后可读性：旧文档仍可阅读，但不会误导

---

## 修改清单

| 文件 | 改动类型 | 具体操作 |
|:-----|:---------|:---------|
| `docs/INTEGRATION.md` | 🔄 重写 | 从补丁方案重写为插件方案 |
| `docs/EPIC-001-hermes-integration.md` | ✏️ 标记废弃 | status=deprecated + 醒目提示 |
| `docs/EPIC-003-v2-enforcement-layer.md` | ✏️ 修正 AC | 5 个 AC 从 ✅ 改为 ❌ |
| `README.md` | ✏️ 更新 | 集成说明指向插件方案 |
| `patches/hermes-sra-integration.patch` | ✏️ 标记 | 头部加 DEPRECATED 注释 |

---

## 实施计划

### Task 1: 重写 INTEGRATION.md
- **文件**: `docs/INTEGRATION.md`
- **操作**: 从补丁方案重写为插件方案
- **验证**: 阅读全文，确认没有虚假描述

### Task 2: 标记 EPIC-001 废弃
- **文件**: `docs/EPIC-001-hermes-integration.md`
- **操作**: 添加 status + 醒目提示
- **验证**: 阅读确认

### Task 3: 修正 EPIC-003 AC
- **文件**: `docs/EPIC-003-v2-enforcement-layer.md`
- **操作**: 5 个 AC 从 ✅ 改为 ❌
- **验证**: 对比原 AC 清单

### Task 4: 同步 README
- **文件**: `README.md`
- **操作**: 集成说明更新
- **验证**: 阅读确认

### Task 5: 标记旧补丁
- **文件**: `patches/hermes-sra-integration.patch`
- **操作**: 文件头部添加 DEPRECATED
- **验证**: 阅读确认

---

## 测试策略

- **Fixture**: 无（文档修改）
- **验证方式**: 手动阅读 + 交叉引用检查
- **门禁**: `grep` 确认没有残留的「自动注入已实现」等虚假描述

---

## 完成检查清单

- [x] 所有 6 个 AC 通过
- [x] INTEGRATION.md 描述真实状态
- [x] EPIC-001 标记废弃
- [x] EPIC-003 虚假 AC 修正
- [x] README 同步
- [x] 旧补丁标记 DEPRECATED
- [x] 交叉引用一致性检查通过
