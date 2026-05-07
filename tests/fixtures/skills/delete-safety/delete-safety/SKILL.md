---
name: delete-safety
description: 删除操作安全边界与确认框架。涵盖 Git 分支/标签/文件删除的风险分级、确认信息模板、批量删除安全策略、AI Agent 操作铁律。任何涉及
  delete/remove/clear/truncate/drop 的操作，必须先走此框架评估。
version: 1.0.0
triggers:
- 删除
- 清理分支
- delete
- 删除操作
- 安全确认
- 危险操作
- 删除安全
- 删除风险
- 确认删除
- 删库
- 删除确认
author: Emma (小玛)
license: MIT
metadata:
  hermes:
    tags:
    - safety
    - delete
    - confirmation
    - risk-assessment
    - destructive-operations
    category: safety
    skill_type: reviewer
    design_pattern: pipeline
depends_on:
- commit-quality-check
category: delete-safety
---
# delete-safety

删除操作安全边界与确认框架。涵盖 Git 分支/标签/文件删除的风险分级、确认信息模板、批量删除安全策略、AI Agent 操作铁律。任何涉及 delete/remove/clear/truncate/drop 的操作，必须先走此框架评估。
