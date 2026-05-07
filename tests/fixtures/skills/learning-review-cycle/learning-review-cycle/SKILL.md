---
name: learning-review-cycle
description: 学习-Review-总结自驱动循环。定时扫描 skill 新鲜度、自动生成学习总结/周报/月报、探测知识缺口并生成学习建议。让整个 learning
  ecosystem 自动运转。
version: 1.0.0
triggers:
- review
- 复盘
- 总结
- 学习总结
- 学习周报
- 学习月报
- 自动学习
- 自驱动
- 知识缺口
- 知识审计
- skill review
- 技能盘点
- 定期回顾
- learning review
depends_on:
- learning-workflow
- learning
- skill-creator
design_pattern: Pipeline + Generator
skill_type: Workflow
category: learning-review-cycle
---
# learning-review-cycle

学习-Review-总结自驱动循环。定时扫描 skill 新鲜度、自动生成学习总结/周报/月报、探测知识缺口并生成学习建议。让整个 learning ecosystem 自动运转。
