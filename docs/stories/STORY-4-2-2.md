---
story: STORY-4-2-2
title: "模块级缓存 — MD5 hash 消息去重"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-2
epic: EPIC-004
estimated_hours: 0.5
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-2.md
dependencies:
  - STORY-4-1-3
out_of_scope:
  - 持久化缓存（仅进程级）
  - 缓存过期策略（当前不实现）
  - 跨 session 缓存共享
---

# STORY-4-2-2: 模块级缓存 — MD5 hash 消息去重

## 用户故事

> As a **sra-guard 插件**,
> I want **对相同的用户消息不重复请求 SRA Daemon**,
> So that **减少 API 调用次数，避免 Hermes API 重试时重复查询**。

---

## 背景

在 Hermes 的 `run_conversation()` 中，当工具调用失败时，LLM 会用相同消息重试。此时如果 SRA 被重复调用，既浪费资源又增加延迟。

解决方案：用 MD5 hash 对消息内容做缓存，相同消息直接返回缓存结果。

---

## 验收标准

### AC-1: 相同消息命中缓存
- [x] 条件: 对同一字符串调用两次 `_get_sra_context("帮我画架构图")`
- [x] 验证: 第二次不发起 HTTP 请求
- [x] 预期: 第二次直接返回第一次的结果

### AC-2: 不同消息不命中缓存
- [x] 条件: 调用 `_get_sra_context("A")` 和 `_get_sra_context("B")`
- [x] 验证: 检查是否发起两次 HTTP 请求
- [x] 预期: 两次请求都发送到 SRA（消息不同）

### AC-3: 缓存 key 使用 MD5 前 12 位
- [x] 条件: 100 位字符串
- [x] 验证: `hashlib.md5(msg.encode()).hexdigest()[:12]`
- [x] 预期: 返回 12 字符的 hash

### AC-4: 缓存为进程级（不持久化）
- [x] 条件: 模块级 `_SRA_CACHE` 字典
- [x] 验证: 检查实现
- [x] 预期: 字典在内存中，不写文件

---

## 技术要求

- 使用 Python 标准库 `hashlib.md5`
- 缓存 key 取前 12 位（平衡碰撞概率和内存）
- 字典容量不设上限（当前使用场景下消息数量非常有限）
- 不实现 TTL 过期（当前场景不需要）

### 实现参考

```python
import hashlib

_SRA_CACHE: Dict[str, str] = {}

def _cache_key(message: str) -> str:
    return hashlib.md5(message.encode("utf-8")).hexdigest()[:12]

def _get_cached(message: str) -> str:
    return _SRA_CACHE.get(_cache_key(message), "")

def _set_cached(message: str, context: str) -> None:
    _SRA_CACHE[_cache_key(message)] = context
```

---

## 实施计划

### Task 1: 在 __init__.py 中添加缓存
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 添加 `_SRA_CACHE` 字典 + `_cache_key()` + `_get_cached()` + `_set_cached()`
- **验证**: 回归测试 19 passed

### Task 2: 接入 _on_pre_llm_call
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 在调用 `client.recommend()` 前检查缓存，调用后更新缓存
- **验证**: 测试缓存命中/未命中

### Task 3: 编写测试
- **文件**: `plugins/sra-guard/tests/test_cache.py`
- **操作**: 测试 AC 1-4
- **验证**: `pytest tests/test_cache.py -v`

---

## 测试策略

- **Fixture**: mock SraClient（验证是否发起请求）
- **新测试文件**: `tests/test_cache.py`
- **CI 环境**: 完全独立

---

## 完成检查清单

- [x] 所有 4 个 AC 通过
- [x] 缓存命中时跳过 HTTP 请求
- [x] 不同消息正确区分
- [x] MD5 前 12 位作为 key
- [x] 进程级（不持久化）
