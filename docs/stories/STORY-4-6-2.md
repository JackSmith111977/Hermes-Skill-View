---
story: STORY-4-6-2
title: "RUNTIME.md + README.md 一致性检查"
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
  - RUNTIME.md
  - README.md
dependencies:
  - STORY-4-6-1（可并行）
out_of_scope:
  - EPIC-003 AC 更新（STORY-4-6-1）
  - INTEGRATION.md（Phase 0 已完成）
  - 补丁文件（Phase 0 已完成）
---

# STORY-4-6-2: RUNTIME.md + README.md 一致性检查

## 用户故事

> As a **新开发者**,
> I want **README 和 RUNTIME 文档反映最新的插件方案**,
> So that **我按文档操作时不会走到已废弃的补丁方案**。

---

## 验收标准

### AC-1: RUNTIME.md 无旧补丁方案引用
- [x] 条件: 搜索 RUNTIME.md 中的 "patch" "sed" "补丁" "run_agent.py 修改"
- [x] 操作: 如有引用则更新为插件方案说明
- [x] 预期: 文档描述当前插件方案的 SRA-Hermes 集成方式

### AC-2: README.md 集成章节准确
- [x] 条件: README.md 中的安装/集成章节
- [x] 操作: 搜索 "patch" "补丁" 等关键词
- [x] 预期: 集成指引指向插件方案（参考 INTEGRATION.md）

### AC-3: 无旧补丁方案残留引用
- [x] 条件: 全仓搜索关键路径（grep -r "hermes-sra-integration.patch"）
- [x] 操作: 如有其他文档引用了已废弃的补丁文件，更新为 EPIC-004 引用
- [x] 预期: 补丁文件仅出现在 patches/ 目录和 EPIC-001 废弃说明中

### AC-4: 日期更新
- [x] 条件: 修改过的文档
- [x] 操作: 更新 last_modified 或文档日期
- [x] 预期: 日期反映最新修改

---

## 完成检查清单

- [x] 所有 4 个 AC 通过
- [x] RUNTIME.md 无旧方案引用
- [x] README.md 集成指引准确
- [x] 全仓无补丁方案残留引用
- [x] 日期更新
