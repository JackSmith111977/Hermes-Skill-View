---
name: doc-design
description: '文档排版设计索引技能。根据文档格式路由到对应的原子 skill。

  当用户需要创建、编辑、美化任何格式的文档时使用此技能，

  本 skill 负责识别格式...'
version: 5.1.0
triggers:
- 文档
- 排版
- doc
- 排版设计
depends_on:
- pdf-layout-reportlab
- pdf-layout-weasyprint
- docx-guide
- pptx-guide
- markdown-guide
- html-guide
- latex-guide
- epub-guide
author: 小喵
license: MIT
metadata:
  hermes:
    tags:
    - document
    - design
    - formatting
    - index
    related_skills:
    - pdf-layout-reportlab
    - pdf-layout-weasyprint
    - docx-guide
    - pptx-guide
    - markdown-guide
    - html-guide
    - latex-guide
    - epub-guide
    category: productivity
    skill_type: doc-generation
    design_pattern: index
category: doc-design
---
# doc-design

文档排版设计索引技能。根据文档格式路由到对应的原子 skill。
当用户需要创建、编辑、美化任何格式的文档时使用此技能，
本 skill 负责识别格式...
