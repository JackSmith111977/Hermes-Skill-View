# Epic: SRA v2.0 — Hermes 原生集成

> **Epic ID:** SRA-EPIC-001
> **状态:** 📋 规划中
> **优先级:** 🔴 高

## 概述

将 SRA (Skill Runtime Advisor) 从"独立运行的 API 服务"升级为"Hermes Agent 的原生消息前置推理层"。

## 目标

用户每次发消息时，在 LLM 处理前自动调 SRA 获取技能推荐，将 `rag_context` 注入到系统提示中，让 boku 知道自己该用什么技能。

## 架构

```
用户消息
    ↓
┌─ Gateway / CLI ─────────────────────┐
│  hooks.emit("agent:start")          │
│     ↓                                │
│  SRA Hook (自动触发)                 │
│  ┌─────────────────────────────┐    │
│  │ POST :8536/recommend        │    │
│  │  → rag_context              │    │
│  │  → should_auto_load         │    │
│  │  → top_skill                │    │
│  └──────────┬──────────────────┘    │
│             ↓ 注入 rag_context      │
│  System Prompt + SRA 上下文          │
│     ↓                                │
│  boku (LLM) 感知推荐                 │
└────────────────────────────────────┘
    ↓
回复用户
```

## 验收标准

- [ ] Gateway 模式：每次消息自动调 SRA，rag_context 注入系统提示
- [ ] CLI 模式：每次消息自动调 SRA，rag_context 注入系统提示
- [ ] SRA Daemon 不可用时优雅降级（不阻塞消息）
- [ ] should_auto_load≥80 时自动加载对应 skill
- [ ] 所有 38 个现有测试通过
- [ ] 新增 10+ 个测试覆盖 Hook + CLI 集成
