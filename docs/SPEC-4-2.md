---
spec_id: SPEC-4-2
title: "消息前置注入 — 在 pre_llm_call 中注入 [SRA] 上下文"
status: completed
epic: EPIC-004
created: 2026-05-15
updated: 2026-05-15
stories:
  - STORY-4-2-1
  - STORY-4-2-2
  - STORY-4-2-3
test_data_contract:
  source: tests/fixtures/skills
  ci_independent: true
---

# SPEC-4-2: 消息前置注入

> **所属 Epic**: EPIC-004
> **状态**: draft
> **目标**: 在 pre_llm_call hook 回调中调用 SRA `/recommend`，将返回的 `rag_context` 格式化为 `[SRA]` 前缀注入到用户消息前
> **估时**: 3.5h
> **依赖**: Phase 0 (sra-guard 插件框架已就绪)

---

## 背景

Phase 0 已完成 sra-guard 插件的基础框架：
- `pre_llm_call` hook 已注册（`__init__.py`）
- `SraClient` 通信模块已就绪（`client.py`）
- 与 SRA Daemon 的通信链路已验证

但当前的 `_on_pre_llm_call` 回调**只有框架代码（返回 None）**，还没有真正调用 `SraClient.recommend()` 并将结果注入到用户消息中。

Phase 1 的目标是补上这段核心逻辑，让每次用户消息到达时自动注入 SRA 推荐上下文。

### 当前状态

```python
def _on_pre_llm_call(messages, session_id, **kwargs):
    try:
        if not messages or not isinstance(messages, list):
            return None
        last = messages[-1]
        if not isinstance(last, dict):
            return None
        if last.get("role") != "user":
            return None
        text = last.get("content", "")
        if not text or not isinstance(text, str):
            return None

        client = _get_client()
        if client is None:
            return None

        ctx = client.recommend(text)  # ← 已有！但返回的是原始 rag_context
        if ctx:
            return {"context": ctx}   # ← 已有！Hermes 自动注入到 user_message
    except Exception:
        logger.warning("SRA pre_llm_call 异常", exc_info=True)
    return None
```

实际上，核心调用链已经通了！但需要：
1. 格式化 `rag_context` 为更友好的 `[SRA]` 前缀格式
2. 实现模块级缓存（避免同一消息重复请求）
3. 编写集成测试验证消息注入

---

## Scope（范围内）

- 格式化 `rag_context` → `[SRA]` 前缀格式（与现有 Proxy 输出一致）
- 实现模块级缓存（MD5 hash 消息去重）
- 消息提取增强（处理多轮对话场景）
- 编写集成测试（使用 mock SRA Daemon）

## Out of Scope（不做）

- ❌ 工具调用校验（Phase 2）
- ❌ 轨迹追踪（Phase 3）
- ❌ 周期性重注入（Phase 4）

---

## 架构设计

### 上下文注入流程

```
用户消息 "帮我画架构图"
    ↓
pre_llm_call hook 触发
    ↓
提取最后一条 user message
    ↓
MD5 hash 检查缓存 → 命中 → 返回缓存结果
    ↓ 未命中
SraClient.recommend("帮我画架构图")
    ↓ HTTP POST /recommend
rag_context = "── [SRA Skill 推荐] ───..."
    ↓
formatter(rag_context, top_skill, should_auto_load)
    ↓
formatted = "[SRA] Skill Runtime Advisor 推荐:\n── [SRA Skill 推荐] ───..."
    ↓
更新缓存 (MD5 → formatted)
    ↓
返回 {"context": formatted}
    ↓
Hermes 自动注入到 user_message 前
```

### 格式化输出示例

```
[SRA] Skill Runtime Advisor 推荐:
── [SRA Skill 推荐] ──────────────────────────────
  ⭐ [medium] architecture-diagram (42.5分) — name部分'architecture'
     [medium] hermes-ops-tips (40.7分) — trigger'架构图'
── ──────────────────────────────────────────────
```

### 缓存机制

```python
_SRA_CACHE: Dict[str, str] = {}  # msg_md5 → formatted_context

def _get_cached(message: str) -> str:
    msg_hash = hashlib.md5(message.encode()).hexdigest()[:12]
    return _SRA_CACHE.get(msg_hash, "")

def _set_cached(message: str, context: str):
    msg_hash = hashlib.md5(message.encode()).hexdigest()[:12]
    _SRA_CACHE[msg_hash] = context
```

---

## Stories

### STORY-4-2-1: [SRA] 上下文格式化

| 字段 | 值 |
|:-----|:-----|
| **估时** | 1h |
| **文件** | `plugins/sra-guard/__init__.py` + `plugins/sra-guard/formatter.py` [NEW] |

**验收标准**:
- [x] `format_sra_context(rag_context, top_skill, should_auto_load)` 返回格式化字符串
- [x] 输出以 `[SRA] Skill Runtime Advisor 推荐:` 开头
- [x] 包含 `rag_context` 的原始内容
- [x] `should_auto_load=True` 时追加 `⚡ 建议自动加载: {skill}`
- [x] 超过 2500 字符时截断
- [x] 空的 `rag_context` 返回空字符串

### STORY-4-2-2: 模块级缓存

| 字段 | 值 |
|:-----|:-----|
| **估时** | 0.5h |
| **文件** | `plugins/sra-guard/__init__.py` |

**验收标准**:
- [x] MD5 hash 作为缓存 key（取前 12 位）
- [x] 相同消息在缓存期内直接返回缓存结果
- [x] 缓存不持久化（进程级缓存）
- [x] 测试：同一消息调用两次，第二次命中缓存

### STORY-4-2-3: 集成测试

| 字段 | 值 |
|:-----|:-----|
| **估时** | 2h |
| **文件** | `tests/test_injection.py` [NEW] |

**验收标准**:
- [x] mock SRA Daemon 验证消息注入包含 `[SRA]` 前缀
- [x] 多轮对话场景测试（只注入最后一条 user message）
- [x] 空消息/非 user role 不注入
- [x] 缓存命中测试
- [x] 长消息截断测试
- [x] SRA 不可用时回退测试

---

## 完成条件

- [x] 所有 3 个 Story 的 AC 全部通过
- [x] 格式化输出格式与现有 Proxy 输出一致
- [x] 缓存机制正常工作（非持久化）
- [x] 集成测试覆盖正常/异常/边界场景
- [x] 回归测试（19 + 新增）全绿
