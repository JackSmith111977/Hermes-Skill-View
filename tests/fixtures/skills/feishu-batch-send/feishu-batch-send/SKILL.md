---
name: feishu-batch-send
description: 飞书批量发送文件/图片技能。支持一次发送多个文件到同一个或多个聊天，自动处理 token 刷新、错误重试、速率限制。 包含批量发送脚本和速率控制策略。
version: 1.0.0
triggers:
- 批量发送飞书
- 飞书批量发送
- feishu batch send
- 发送多个文件到飞书
- 飞书多发
- 批量发文件
depends_on:
- feishu
- feishu-send-file
design_pattern: Pipeline
skill_type: generator
category: feishu-batch-send
---
# feishu-batch-send

飞书批量发送文件/图片技能。支持一次发送多个文件到同一个或多个聊天，自动处理 token 刷新、错误重试、速率限制。 包含批量发送脚本和速率控制策略。
