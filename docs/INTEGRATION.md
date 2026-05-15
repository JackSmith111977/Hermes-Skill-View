# SRA Hermes 插件集成指南（EPIC-004）

> ⚠️ **旧版补丁方案已废弃。本文档描述 EPIC-004 的插件方案。**
> 旧方案见 `patches/hermes-sra-integration.patch`（DEPRECATED）。

---

## 📋 目录

- [原理](#-原理)
- [前提条件](#-前提条件)
- [安装](#-安装)
- [验证集成](#-验证集成)
- [卸载](#-卸载)
- [效果演示](#-效果演示)
- [降级行为](#-降级行为)
- [插件方案 vs 补丁方案](#-插件方案-vs-补丁方案)

---

## 🎯 原理

SRA 通过 **Hermes 插件系统** 集成，不修改 Hermes 核心代码：

```
用户消息
    ↓
Hermes 消息处理 → pre_llm_call hook
    ↓                          ┌──────────────────┐
sra-guard 插件  ──HTTP POST──→│    SRA Daemon     │
POST /recommend                │  (:8536)          │
    ← rag_context              │  ┌─────────────┐  │
    ↓                          │  │四维匹配引擎   │  │
注入到 user_message 前         │  │推荐          │  │
    ↓                          │  └─────────────┘  │
[SRA] Skill Runtime Advisor    └──────────────────┘
推荐: ...
用户消息原文...
    ↓
LLM 感知推荐 → 处理
```

### 与旧补丁方案的区别

| 方式 | 可靠性 | 维护成本 | 说明 |
|:-----|:------:|:--------:|:-----|
| **❌ 旧：补丁方案** (patches/) | 低 | 高 | `sed -i` 修改 `run_agent.py`，每次 Hermes 升级覆盖 |
| **✅ 新：插件方案** (EPIC-004) | 极高 | 低 | 利用 Hermes 插件 API，零侵入，自动保留 |

---

## ✅ 前提条件

1. **Hermes Agent** 已安装（Gateway 或 CLI 模式均可）
2. **SRA v2.0+** 已安装并启动 Daemon

```bash
# 检查 SRA Daemon
curl http://127.0.0.1:8536/health
# → {"status":"running","version":"2.0.3",...}
```

3. **sra-guard 插件** 已安装

---

## 🚀 安装

```bash
# 在 SRA 项目目录中运行
cd /path/to/sra
bash scripts/install-hermes-plugin.sh install

# 输出：
# ==============================================
#   sra-guard 插件安装
# ==============================================
# [OK] 源目录完整
# [OK] 文件已复制到: ~/.hermes/hermes-agent/plugins/sra-guard/
# [OK] sra-guard 插件安装完成！
```

### 安装脚本做了什么？

1. 从 `plugins/sra-guard/` 复制所有文件
2. 验证目标目录完整性
3. Hermes 下次启动时自动加载插件

### 环境变量

| 变量 | 默认值 | 说明 |
|:-----|:-------|:------|
| `HERMES_HOME` | `~/.hermes` | Hermes Agent 家目录 |

---

## ✅ 验证集成

```bash
# 1. 确认插件文件已安装
ls ~/.hermes/hermes-agent/plugins/sra-guard/
# → client.py  __init__.py  plugin.yaml  tests/

# 2. 确认 SRA Daemon 运行
curl http://127.0.0.1:8536/health
# → {"status":"running"}

# 3. 重启 Hermes Gateway
hermes gateway restart

# 4. 确认插件被加载
# 检查日志中有 "sra-guard 插件已注册" 条目

# 5. 发一条消息，回复开头应看到 [SRA] 标记
# 例如：用户说"帮我画个架构图"
# 回复开头：[SRA] Skill Runtime Advisor 推荐: ...
```

---

## ♻️ 卸载

```bash
# 在 SRA 项目目录中运行
bash scripts/install-hermes-plugin.sh uninstall
# → [OK] sra-guard 插件已卸载
```

---

## 📊 效果演示

### 用户消息带 SRA 上下文

```
你: 帮我画个架构图

思考过程 (sra-guard 插件自动触发):
  pre_llm_call hook → POST /recommend → rag_context

回复:
[SRA] Skill Runtime Advisor 推荐:
── [SRA Skill 推荐] ──────────────────────────────
  ⭐ [medium] architecture-diagram (42.5分) — ...
── ──────────────────────────────────────────────

好的喵～boku 来帮你画架构图！
```

---

## 🛡️ 降级行为

| 状况 | 行为 |
|:-----|:------|
| SRA Daemon 正常运行 | 注入推荐上下文到每次消息 |
| 连接超时（>2秒） | 完全静默降级，不阻塞消息 |
| 连接被拒绝（Daemon 未启动） | try/except 捕获，返回 None |
| 返回空推荐 | 正常执行，无上下文注入 |
| 相同消息重试 | 模块级缓存避免重复 HTTP 调用 |

**核心原则：SRA 是增强型插件，不是阻塞式依赖。**

---

## ⚖️ 插件方案 vs 补丁方案

| 维度 | 旧：补丁方案 ❌ | 新：插件方案 ✅ |
|:-----|:---------------|:---------------|
| 侵入性 | 修改 Hermes 核心代码（`run_agent.py`） | 零侵入（标准插件 API） |
| 升级维护 | 每次 Hermes 升级需重新打补丁 | 自动保留，升级不影响 |
| 安装方式 | `sed -i` 依赖行号 | 复制到 `plugins/` 目录 |
| 通信库 | `urllib.request` | `httpx`（与 Hermes 一致） |
| 错误处理 | `except Exception: pass` | `logger.warning` + 返回 None |
| 自动化测试 | 无 | 19 个单元测试 |
| 源码管理 | 补丁文件在 SRA 项目 | 插件源码在 SRA 项目（版本管理） |

---

## ❓ 常见问题

### Q: 插件方式需要修改 run_agent.py 吗？

A: **不需要。** Hermes 的插件系统会自动发现 `plugins/sra-guard/` 目录并加载插件。零侵入。

### Q: Hermes 升级后会丢失吗？

A: **不会。** Hermes 升级时 `plugins/` 目录下的用户插件会被保留。（升级脚本不删除用户插件）

### Q: Gateway 和 CLI 模式都能生效吗？

A: **都能。** `pre_llm_call` hook 在 Gateway 和 CLI 模式下都会触发。

### Q: SRA 响应慢会影响用户体验吗？

A: **不会。** `SraClient` 有 2 秒超时，超时或异常立即返回空字符串，不阻塞消息流程。
