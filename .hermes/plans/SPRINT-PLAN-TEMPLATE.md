---
# SRA Sprint Plan 标准模板
#
# 每次开始新 Sprint 前，复制此文件为 .hermes/plans/YYYY-MM-DD_sprint-N-plan.md
# 遵循 Spec-Anchored SDD 模式

sprint: "Sprint N"
target_version: ""
status: draft  # draft | approved | in_progress | completed
created: YYYY-MM-DD
updated: YYYY-MM-DD
estimated_hours: 0

# 测试基线 — 开始前的测试状态
test_baseline: 0

# 引用的 Story Specs
story_refs: []

# 引用的 Epic
epic_ref: ""
---

# Sprint N — 计划

> **目标版本:** {version}
> **估时:** ~{hours}h
> **测试基线:** {N} passed

**Goal:** {一句话描述 Sprint 目标}

**前提:** {git checkout / 前置条件}

**验证:** pytest tests/ -q（预期 {N} passed）

---

## Story / Tasks

### Story 1: {标题} [参考: STORY-XXX-NN.md]

| Task | 文件 | 估时 | 验证 |
|:-----|:-----|:----:|:-----|
| {Task 1} | {文件路径} | {h} | {v} |
| {Task 2} | {文件路径} | {h} | {v} |

### Story 2: {标题} [参考: STORY-XXX-NN.md]

| Task | 文件 | 估时 | 验证 |
|:-----|:-----|:----:|:-----|
| {Task 1} | {文件路径} | {h} | {v} |

---

## 完成检查清单

- [ ] 所有 Story 的 AC 全部通过
- [ ] pytest 全量测试 ≥ baseline
- [ ] doc-alignment --verify 通过
- [ ] CHANGELOG.md 更新
- [ ] project-report.json + HTML 生成
- [ ] 代码 + 文档同次 commit
