---
name: skill-creator
description: 创建、优化、评估 Skill 的完整工作流。支持从实战任务中提取知识、从学习笔记转化 Skill。内置 5 种设计模式，9 阶段创作流程（含快速更新通道），引用依赖检查，以及
  skill-manage 联动拦截。
version: 4.1.0
triggers:
- skill
- 创建技能
- 优化技能
- 模板
- 技能升级
- 依赖检查
- skill-manage 联动
allowed-tools:
- terminal
- read_file
- write_file
- patch
- search_files
- skill_manage
- skills_list
- skill_view
metadata:
  hermes:
    tags:
    - skill-creation
    - evaluation
    - knowledge-extraction
    - versioning
    - dependency-tracking
    category: meta
    skill_type: generator
    design_pattern: pipeline
category: skill-creator
---
# skill-creator

创建、优化、评估 Skill 的完整工作流。支持从实战任务中提取知识、从学习笔记转化 Skill。内置 5 种设计模式，9 阶段创作流程（含快速更新通道），引用依赖检查，以及 skill-manage 联动拦截。
