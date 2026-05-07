---
name: hermes-message-injection
description: 向 Hermes Agent 的消息管道注入外部服务上下文（如 SRA 技能推荐）。每次用户消息自动拦截 → 调外部服务 → 将结果作为
  [前缀] 注入到消息前。涵盖 run_agent.py 的 run_conversation() 注入点、module-level 缓存、降级策略。
version: 2.0.0
triggers:
- hermes 注入
- hermes 消息拦截
- message injection
- sra integration
- context injection
- hermes hook
- run_conversation
- sra daemon
- sra start
- sra管理
- 上下文注入
depends_on:
- hermes-agent
design_pattern: Pipeline Injection
skill_type: Pattern
category: autonomous-ai-agents
---
# hermes-message-injection

向 Hermes Agent 的消息管道注入外部服务上下文（如 SRA 技能推荐）。每次用户消息自动拦截 → 调外部服务 → 将结果作为 [前缀] 注入到消息前。涵盖 run_agent.py 的 run_conversation() 注入点、module-level 缓存、降级策略。
