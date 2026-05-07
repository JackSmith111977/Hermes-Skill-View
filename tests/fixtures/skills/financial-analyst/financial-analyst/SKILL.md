---
name: financial-analyst
description: 金融数据分析与研报生成技能。使用 akshare 获取行情，ta 库计算指标，matplotlib 绘制图表，LLM 生成研报。
version: 1.0.0
triggers:
- 股票分析
- 行情查询
- 研报生成
- financial analysis
- stock report
- 大盘走势
depends_on:
- web-access
- pdf-layout-weasyprint
metadata:
  hermes:
    tags:
    - finance
    - analysis
    - report
    category: data-science
    skill_type: generator
    design_pattern: pipeline
category: financial-analyst
---
# financial-analyst

金融数据分析与研报生成技能。使用 akshare 获取行情，ta 库计算指标，matplotlib 绘制图表，LLM 生成研报。
