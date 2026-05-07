---
name: news-briefing
description: 新闻采集与报刊级别简报生成技能。涵盖 RSS/API 采集管线、新闻分类筛选去重、AI 辅助摘要、以及使用 WeasyPrint 生成专业报刊级
  PDF 文档（4+页，网格系统+视觉层次+多栏布局）。
version: 2.2.0
triggers:
- 新闻采集
- 新闻简报
- news briefing
- 报刊
- 报纸
- 日报
- 周报
- 看新闻
- 新闻汇总
depends_on:
- web-access
- pdf-layout-weasyprint
allowed-tools:
- terminal
- read_file
- write_file
- patch
- mcp_tavily_tavily_search
- mcp_tavily_tavily_extract
metadata:
  hermes:
    tags:
    - news
    - briefing
    - rss
    - aggregation
    - newspaper
    - layout
    - weasyprint
    - pdf
    category: research
    skill_type: doc-generation
    design_pattern: generator
category: news-briefing
---
# news-briefing

新闻采集与报刊级别简报生成技能。涵盖 RSS/API 采集管线、新闻分类筛选去重、AI 辅助摘要、以及使用 WeasyPrint 生成专业报刊级 PDF 文档（4+页，网格系统+视觉层次+多栏布局）。
