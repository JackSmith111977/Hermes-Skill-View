---
name: learning-workflow
description: 所有学习/研究任务的强制流程拦截器。通过状态机+文件标志物实现防跳过机制。任何涉及'学习、研究、了解、搞懂'的请求必须先走此流程。v4.0
  重大更新：三层迭代循环架构（子主题递归+中间反思+质量门禁）、螺旋式学习模式。
version: 4.0.0
triggers:
- 学习
- 研究
- 了解
- 搞懂
- 看看
- 学学
- 查一下
- 调研
- 探索
- 掌握
- 沉淀
- 总结复盘
- 学习周报
- 学习月报
- 技能盘点
- study
- learn
- research
- explore
- review
depends_on:
- skill-creator
- web-access
- learning
- learning-review-cycle
design_pattern: Pipeline
skill_type: Workflow
category: learning-workflow
---
# learning-workflow

所有学习/研究任务的强制流程拦截器。通过状态机+文件标志物实现防跳过机制。任何涉及'学习、研究、了解、搞懂'的请求必须先走此流程。v4.0 重大更新：三层迭代循环架构（子主题递归+中间反思+质量门禁）、螺旋式学习模式。
