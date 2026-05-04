# SRA Hermes 原生集成指南

> **SRA v1.1.0+** 支持直接注入 Hermes Agent 的消息管道，在每次用户消息进入 LLM 前自动触发 SRA 获取技能推荐，**不需要手动 curl 调用**，**不依赖 AGENTS.md 或 SOUL.md 的"劝告"**。

---

## 📋 目录

- [原理](#-原理)
- [前提条件](#-前提条件)
- [一键安装](#-一键安装)
- [手动安装（打补丁）](#-手动安装打补丁)
- [验证集成](#-验证集成)
- [卸载](#-卸载)
- [效果演示](#-效果演示)
- [降级行为](#-降级行为)
- [工作原理详解](#-工作原理详解)
- [与其他方案的对比](#-与其他方案的对比)
- [常见问题](#-常见问题)

---

## 🎯 原理

```
用户消息
    ↓
Hermes AIAgent.run_conversation()
    ↓
_query_sra_context(user_message)  ← 自动触发（每次消息都会）
    ↓                      ┌──────────────────┐
    ├── HTTP POST ────────→│    SRA Daemon     │
    │   :8536/recommend    │  (:8536)          │
    │   ← rag_context      │  ┌─────────────┐  │
    │                      │  │四维匹配引擎   │  │
    │                      │  │词法/语义/场景 │  │
    │                      │  │/类别 推荐     │  │
    │                      │  └─────────────┘  │
    │                      └──────────────────┘
    ↓ 注入到用户消息前
[SRA] Skill Runtime Advisor 推荐:
── [SRA Skill 推荐] ──────────────────────────
  ⭐ [high] architecture-diagram (90.0分) — ...
── ──────────────────────────────────────────

用户消息原文...
    ↓
LLM 感知推荐 → 自动加载 skill → 回复
```

### 与"文档式"方案的区别

| 方式 | 可靠性 | 说明 |
|------|--------|------|
| **AGENTS.md 写规则** | ❌ 低 | 劝告式，模型可能忽略，上下文压缩后丢失 |
| **SOUL.md 写前置推理** | ❌ 低 | 同上，依赖模型遵循自然语言指令 |
| **✅ 代码层注入** | ✅ 极高 | 修改 `run_agent.py`，每次消息**强制调 SRA**，100% 拦截 |

---

## ✅ 前提条件

1. **Hermes Agent** 已安装（Gateway 或 CLI 模式均可）
2. **SRA v1.1.0+** 已安装并启动 Daemon

```bash
# 启动 SRA Daemon
cd /path/to/sra-agent
python3 -m skill_advisor.runtime.daemon attach
# 或用 CLI
sra start
```

3. 健康检查通过

```bash
curl http://127.0.0.1:8536/health
# 返回: {"status":"ok","sra_version":"1.1.0"}
```

---

## 🚀 一键安装

```bash
# 从 SRA 仓库目录运行
bash scripts/install-hermes-integration.sh

# 输出示例：
# ==============================================
#   SRA Hermes 集成 v1.1.0
# ==============================================
# [OK] Hermes Agent 已发现: /home/eragon/.hermes/hermes-agent/run_agent.py
# [OK] 已备份: /home/eragon/.hermes/hermes-agent/run_agent.py.sra-backup
# [OK] SRA Hermes 集成安装完成！
# ...
# [OK] SRA Daemon 运行中 (127.0.0.1:8536)
```

### 安装脚本做了什么？

1. **备份** `run_agent.py` → `run_agent.py.sra-backup`
2. **注入** `_query_sra_context()` 函数（模块级，在 `class AIAgent` 前）
3. **注入** SRA 调用点（在 `run_conversation()` 的 `# Add user message` 前）

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HERMES_HOME` | `~/.hermes` | Hermes Agent 家目录 |
| `SRA_PROXY_URL` | `http://127.0.0.1:8536` | SRA Daemon 地址 |

---

## 🔧 手动安装（打补丁）

如果一键脚本因环境差异无法使用，可以手动打补丁：

```bash
# 1. 备份原文件
cp ~/.hermes/hermes-agent/run_agent.py ~/.hermes/hermes-agent/run_agent.py.bak

# 2. 进入目录
cd ~/.hermes/hermes-agent

# 3. 打补丁（补丁文件在 SRA 源码中）
patch -p1 < /path/to/sra-agent/patches/hermes-sra-integration.patch
```

### 补丁内容说明

补丁文件 `patches/hermes-sra-integration.patch` 包含两处改动：

**1. 新增 `_query_sra_context()` 函数**（约 60 行）

在 `run_agent.py` 的 `class AIAgent` 定义前插入。功能：
- 接收用户消息 → HTTP POST 到 SRA Daemon
- 解析返回的 `rag_context`、`should_auto_load`、`top_skill`
- 格式化加 `[SRA]` 前缀
- 模块级缓存（MD5 hash）避免相同消息重复请求
- 2 秒超时 + 异常捕获，绝不影响主流程

**2. 在 `run_conversation()` 中注入调用点**（~10 行）

在 `# Add user message` 之前加入：
```python
_sra_ctx = _query_sra_context(user_message)
if _sra_ctx:
    user_message = f"{_sra_ctx}\n\n{user_message}"
```

---

## ✅ 验证集成

```bash
# 1. 确认 SRA Daemon 运行
curl http://127.0.0.1:8536/health
# → {"status":"ok","sra_version":"1.1.0"}

# 2. 确认 run_agent.py 已被修改
grep -n "_query_sra_context" ~/.hermes/hermes-agent/run_agent.py
# → 出现行号说明注入成功

# 3. 重启 Hermes（如果是 Gateway 模式）
hermes gateway restart

# 4. 发一条消息，回复开头会看到 [SRA] 标记
# 例如：用户说"帮我画个架构图"
# 回复开头：[SRA] Skill Runtime Advisor 推荐: ...
```

---

## ♻️ 卸载

### 从备份恢复

```bash
bash scripts/install-hermes-integration.sh --uninstall
```

### 手动恢复

```bash
cp ~/.hermes/hermes-agent/run_agent.py.bak ~/.hermes/hermes-agent/run_agent.py
```

### 从 git 恢复

```bash
cd ~/.hermes/hermes-agent
git checkout -- run_agent.py
```

---

## 📊 效果演示

### 用户消息带 SRA 上下文

```
你: 帮我画个架构图

思考过程 (自动触发 SRA):
  POST :8536/recommend → {"message": "帮我画个架构图"}
  ← {"rag_context": "── [SRA Skill 推荐] ─── ...", 
     "should_auto_load": true, 
     "top_skill": "architecture-diagram"}

回复:
[SRA] Skill Runtime Advisor 推荐:
── [SRA Skill 推荐] ──────────────────────────────
  ⭐ [high] architecture-diagram (90.0分) — 
     Generate dark-themed SVG diagrams...
  ⚡ 强推荐自动加载: architecture-diagram
── ──────────────────────────────────────────────

好的喵～boku 来帮你画架构图！先加载 architecture-diagram skill...
```

### 无匹配时的表现

```
你: 今天天气怎么样

回复: (无 [SRA] 标记，正常回复)
今天天气不错喵～boku 查一下...
```

---

## 🛡️ 降级行为

| 状况 | 行为 |
|------|------|
| SRA Daemon 正常运行 | 注入推荐上下文到每次消息 |
| 连接超时（>2秒） | 完全静默降级，不阻塞消息 |
| 连接被拒绝（Daemon 未启动） | try/except 捕获，静默跳转 |
| 返回空推荐 | 正常执行，无 RAG 注入 |
| 相同消息重试 | MD5 缓存避免重复 HTTP 调用 |

**核心原则：SRA 是增强型插件，不是阻塞式依赖。**

---

## 🔍 工作原理详解

### `_query_sra_context()` 函数

```python
def _query_sra_context(user_message: str) -> str:
    """Query SRA Daemon for skill recommendations.
    
    调用链: run_conversation() → _query_sra_context()
    1. 计算消息的 MD5 hash
    2. 如果 hash 命中缓存 → 直接返回缓存结果
    3. 如果未命中 → HTTP POST :8536/recommend
    4. 格式化返回为 [SRA] 前缀文本
    5. 更新缓存
    6. 异常或超时 → 返回空字符串
    """
```

### 注入点位置

在 `run_agent.py` 的 `AIAgent.run_conversation()` 方法中：

```python
def run_conversation(self, user_message, ...):
    ...
    # ── SRA Context Injection ─────────────────
    _sra_ctx = _query_sra_context(user_message)
    if _sra_ctx:
        user_message = f"{_sra_ctx}\n\n{user_message}"
    # ──────────────────────────────────────────
    
    # Add user message (原代码)
    self.messages.append({"role": "user", "content": user_message})
    ...
```

### 为什么不是 Hook 方案？

Hermes 已有的 Hook 系统（`hooks.emit("agent:start")`）是**异步非阻塞**的——错误被捕获但永不阻断流程。Hook 可以"看到"消息，但不能修改 system prompt 或消息内容。因此最终方案是直接改 `run_agent.py` 的核心方法。

---

## ⚖️ 与其他方案的对比

| 方案 | 侵入性 | 可靠性 | 维护成本 | 实现难度 |
|------|--------|--------|----------|----------|
| **AGENTS.md 写规则** | 无 | ❌ 低 | 无 | 极低 |
| **SOUL.md 写前置流程** | 无 | ❌ 低 | 无 | 极低 |
| **Hook 拦截** | 低 | ❌ 中（非阻塞） | 中 | 中 |
| **✅ run_agent.py 注入** | 中 | ✅ 极高 | 低 | 中 |
| **改写 prompt_builder** | 中 | ✅ 高 | 低 | 中 |

---

## ❓ 常见问题

### Q: 修改 `run_agent.py` 会被 Hermes 升级覆盖吗？

A: 会。升级 Hermes 后需要重新运行 `install-hermes-integration.sh` 重新注入。

### Q: Gateway 和 CLI 模式都能生效吗？

A: 都能！修改的是 `run_agent.py` 的 `run_conversation()` 方法，Gateway 和 CLI 都通过这个方法处理消息。

### Q: AGENTS.md 中还有 SRA 规则，需要删掉吗？

A: 不需要删，但可以简化。代码层的拦截 100% 可靠，AGENTS.md 的规则作为冗余备份保留即可。推荐保留但标记为"冗余"。

### Q: SRA 响应慢会影响用户体验吗？

A: 不会。`_query_sra_context()` 有 2 秒超时，超时或异常都会立即返回空字符串，不阻塞消息流程。

### Q: 多个 session 之间会共享 SRA 缓存吗？

A: 当前是模块级缓存（`_SRA_CACHE` 字典），仅在同一个进程内共享。不同工作进程的缓存不共享，但这是可接受的——缓存只是为了避免同一消息在 API 重试时的重复调用。
