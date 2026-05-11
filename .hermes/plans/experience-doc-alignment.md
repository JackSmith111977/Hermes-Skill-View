# 文档对齐协议实战经验

> **日期:** 2026-05-10
> **场景:** 完成 Sprint 2 后，主人指出工作流缺少文档对齐环节
> **类型:** workflow-improvement

## 发现的问题

1. **API-REFERENCE.md 完全缺少 Sprint 2 新增端点：** `/recheck`、`/stats/compliance`、`/validate`、`compliance` CLI、action-based `/record` 全部缺失
2. **工作流缺陷：** 原有的 AGENTS.md 只定义了 PRE-FLIGHT 步骤，没有 POST-TASK 文档对齐步骤
3. **上下文污染机制：** 文档漂移是累积性的——一个 Sprint 不更新就缺失 3 个端点，两个 Sprint 不更新会导致 AI 完全不知道新功能

## 解决方案

| 层次 | 交付 | 关键设计 |
|:-----|:-----|:---------|
| 方法论 skill | `doc-alignment` | 5 步对齐协议：识别域→定位漂移→逐文档对齐→跨文档验证→提交 |
| 流程强制 | AGENTS.md | POST-TASK 步骤排在「提交」之前，代码+文档同一次提交 |
| 具体修复 | API-REFERENCE.md | 加入 Sprint 2 全部 3 个新增端点 + 2 个 CLI 命令 + 3 个 Python 方法 |

## 关键教训

1. **「先提交代码，文档以后补」= 永不会补。** 必须强制代码与文档同一次提交
2. **跨文档一致性验证不可省略。** 只更新 API-REFERENCE.md 而不同步 PROJECT-PANORAMA.html 等于没对齐
3. **最小的变更也可能导致最大的污染。** 新增一个参数（如 `/record` 的 `action` 字段）如果不同步到文档，后续 AI 完全不知道这个参数存在
4. **多文档对齐比单文档更难。** 需要同时追踪 ROADMAP.md + API-REFERENCE.md + ARCHITECTURE.md + PROJECT-PANORAMA.html + EPIC 文档的一致性
