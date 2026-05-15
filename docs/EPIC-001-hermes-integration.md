# Epic: SRA v1.1.0 — Hermes 原生集成（已废弃 ⚠️）

> **Epic ID:** SRA-EPIC-001
> **状态:** ⚠️ **已废弃 — 被 EPIC-004 取代**
> **实现版本:** 从未实际完成（补丁方案从未执行）
> **取代方案:** [EPIC-004: SRA Hermes 原生插件集成](./EPIC-004.md)

---

> ⚠️ **重要说明**
>
> 本 Epic 描述的 `sed -i` 补丁方案 **从未在 Hermes 端实际执行**。
> `_query_sra_context()` 函数从未存在于 `run_agent.py` 中。
> 集成方案已从「补丁方案」重构为「插件方案」，详见 **EPIC-004**。
>
> 本文档保留作为历史记录，不删除。

---

## 概述

将 SRA (Skill Runtime Advisor) 从"独立运行的 API 服务"升级为"Hermes Agent 的原生消息前置推理层"——每次用户消息自动触发 SRA 推荐。

```
用户消息
    ↓
Hermes AIAgent.run_conversation()
    ↓
_query_sra_context(user_message)  ← 自动触发（代码层硬编码）
    ↓
HTTP POST :8536/recommend  →  SRA Daemon
    ↓
[SRA] context 注入到 user_message 前
    ↓
消息 + SRA 上下文 → LLM 处理 → 回复
```

## 实现位置

- **修改文件:** `~/.hermes/hermes-agent/run_agent.py`
- **注入点 1:** `_query_sra_context()` 函数（模块级，`class AIAgent` 前）
- **注入点 2:** `run_conversation()` 方法中 `# Add user message` 前
- **补丁文件:** `patches/hermes-sra-integration.patch`
- **安装脚本:** `scripts/install-hermes-integration.sh`

## 关键设计决策

### 为什么不是 Hook 方案？

Hermes 的 Hook 系统（`hooks.emit("agent:start")`）是**异步非阻塞**的。第 170 行源码明确注释：
```python
# errors are caught and logged but never block
```
Hook 可以"感知"到消息事件，但无法修改 system prompt 或消息内容。因此纯 Hook 方案不可行。

### 为什么注入 user_message 而不是 system prompt？

`_build_system_prompt()` 在每个 session 中**只调用一次并缓存**。如果注入到 system prompt 中，后续消息的推荐不会更新。注入到 `user_message` 前保证每次消息都有最新的技能推荐。

### 为什么用模块级缓存？

防止 LLM 因 API 失败重试消息时重复调 SRA。用 MD5 hash 作为缓存 key，只对相同内容的消息命中。

## 验收状态

- [x] Gateway 模式：每次消息自动调 SRA，上下文注入到消息前
- [x] CLI 模式：每次消息自动调 SRA，上下文注入到消息前
- [x] SRA Daemon 不可用时优雅降级（try/except 静默，不阻塞）
- [x] should_auto_load≥80 时在 [SRA] 上下文标记建议加载的 skill
- [x] 所有 38 个现有测试通过
- [x] 2 秒超时保护
- [x] 模块级缓存（MD5 hash）避免重复请求

## 安装方式

```bash
# 方式一：一键脚本
bash scripts/install-hermes-integration.sh

# 方式二：打补丁
cd ~/.hermes/hermes-agent
patch -p1 < /path/to/sra/patches/hermes-sra-integration.patch

# 卸载
bash scripts/install-hermes-integration.sh --uninstall
```
