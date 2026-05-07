---
name: night-study-engine
description: Hermes 夜间自习引擎 v2.0 — 自驱动学习系统。涵盖动态领域引擎、学习质量门禁、知识追踪、间隔复习、结构化日志、晨间汇报增强、Artifact
  产出门禁。v2.0 核心升级：从简单批处理升级为完整学习系统。
version: 2.0.0
triggers:
- 夜间学习
- night study
- 夜间自习
- 自主学习
- 自动学习
- 知识更新
- skill 维护
- 学习系统
- 间隔复习
- 知识追踪
- 知识门禁
- 学习质量
- 自习改造
- self-driven learning
- autonomous study
- knowledge update
author: 小喵 (Emma)
license: MIT
allowed-tools:
- terminal
- read_file
- write_file
- patch
- cronjob
- mcp_tavily_tavily_search
- mcp_tavily_tavily_extract
- mcp_tavily_tavily_crawl
- delegate_task
depends_on:
- learning-workflow
- learning-review-cycle
- web-access
- skill-creator
metadata:
  hermes:
    tags:
    - autonomous-learning
    - knowledge-tracking
    - spaced-repetition
    - quality-gate
    category: meta
    skill_type: pipeline
    design_pattern: pipeline
category: night-study-engine
---
# night-study-engine

Hermes 夜间自习引擎 v2.0 — 自驱动学习系统。涵盖动态领域引擎、学习质量门禁、知识追踪、间隔复习、结构化日志、晨间汇报增强、Artifact 产出门禁。v2.0 核心升级：从简单批处理升级为完整学习系统。
