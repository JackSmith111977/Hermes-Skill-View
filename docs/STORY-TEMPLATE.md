---
# SRA Story 标准模板
#
# 使用说明：
# 1. 复制此文件为 docs/stories/STORY-XXX-NN.md
# 2. 填写 frontmatter 字段
# 3. 主人审阅并标记 status=approved → 开始实现
# 4. 实现完成后更新 status=completed

story: SRA-XXX-NN
title: ""
status: draft  # draft | approved | in_progress | completed | blocked | cancelled
created: YYYY-MM-DD
updated: YYYY-MM-DD
epic: EPIC-XXX
estimated_hours: 0

# 测试数据契约 — 声明测试所需的 fixture 和 CI 独立性
test_data:
  source: tests/fixtures/skills
  ci_independent: true
  pattern_reference: ""  # 参考已有测试文件的模式

# 引用链 — 追溯本 Story 的上下文来源
spec_references:
  - EPIC-XXX.md
  - docs/ARCHITECTURE.md

# 依赖 — 本 Story 所依赖的其他 Story 或外部条件
dependencies: []

# 明确不做的范围 — 防止 scope creep
out_of_scope: []
---

# SRA-XXX-NN: {标题}

## 用户故事

> As a {角色},
> I want {功能},
> So that {价值}.

---

## 验收标准 (Acceptance Criteria)

<!-- 每个 AC 必须可验证（自动化测试或手动检验） -->

### AC-1: {标题}
- [ ] 条件: {具体条件}
- [ ] 验证方式: {pytest / 手动 / curl}
- [ ] 预期结果: {明确的输出}

### AC-2: {标题}
- [ ] 条件: {具体条件}
- [ ] 验证方式: {pytest / 手动 / curl}
- [ ] 预期结果: {明确的输出}

---

## 技术要求

<!-- 架构约束、设计模式、技术选型 -->

- {约束 1}
- {约束 2}

---

## 实施计划

<!-- 由 writing-plans skill 填充，每个任务 2-5 分钟 -->

### Task 1: {标题}
- **文件**: {路径}
- **操作**: {具体操作描述}
- **验证**: {验证命令}

### Task 2: {标题}
- **文件**: {路径}
- **操作**: {具体操作描述}
- **验证**: {验证命令}

---

## 测试策略

- **Fixture**: {使用哪个 fixture}
- **新测试文件**: {路径}（如果新创建）
- **CI 环境**: {是否独立运行}

---

## 完成检查清单

- [ ] 所有 AC 通过
- [ ] pytest 全绿
- [ ] doc-alignment --verify 通过
- [ ] 代码 + 文档同次 commit
- [ ] AC-* 每个条件都被实测确认过（非仅自评）
