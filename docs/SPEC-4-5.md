---
spec_id: SPEC-4-5
title: "周期性重注入防漂移 — 长任务 SRA 上下文新鲜度保护"
status: completed
epic: EPIC-004
created: 2026-05-15
updated: 2026-05-15
stories:
  - STORY-4-5-1
  - STORY-4-5-2
  - STORY-4-5-3
test_data_contract:
  source: tests/fixtures/skills
  ci_independent: true
---

# SPEC-4-5: 周期性重注入防漂移

> **所属 Epic**: EPIC-004
> **状态**: draft
> **目标**: 在长任务（5+ 轮对话）中自动重查 SRA 推荐，防止上下文漂移
> **估时**: 2.5h
> **依赖**: Phase 1 (消息注入已就绪)

---

## 背景

### 问题

当前 sra-guard 的 `_on_pre_llm_call()` 只在**消息级别**注入 SRA 上下文。每轮用户新消息都会触发一次注入（Phase 1 的 MD5 缓存保证同一消息不重复调 SRA）。

但存在一个缺口：**在单轮会话中，Agent 执行长任务时**——例如 Agent 先画架构图，然后写代码，然后修 Bug——10+ 轮工具调用后，初始的 SRA 推荐可能已经完全过时了。

```
轮次 1: 用户说「画架构图」 → SRA 推荐 architecture-diagram skill ✅
轮次 2-3: Agent 调用 write_file 画图
轮次 4-5: 用户说「代码实现」→ Agent 继续用同一个 session
         但 SRA 推荐仍是 architecture-diagram（可能已过时） ⚠️
```

### 现有保护机制

| 机制 | 说明 | 覆盖 Phase 4？ |
|:-----|:------|:---------------:|
| 每轮消息 MD5 缓存 | 同一消息不重复请求 SRA | ❌ 消息不变时不会重查 |
| pre_llm_call 每轮触发 | 但缓存命中直接返回 | ❌ 不重查 |
| post_tool_call 轨迹记录 | 只记录，不刷新推荐 | ❌ |

Phase 4 填补的正是这个缺口：**即使缓存命中，每 N 轮也强制重查 SRA**。

---

## Scope（范围内）

- 在 `__init__.py` 中添加对话轮数计数器（模块级）
- 每 `RECHECK_INTERVAL=5` 轮强制清除缓存 + 重查 SRA
- 重查结果以标准 `[SRA]` 格式注入（复用 Phase 1 的格式）
- 重查使用 `client.recommend()`（已有方法）
- 编写集成测试验证重注入时机

## Out of Scope（不做）

- ❌ 内容级漂移检测（如语义相似度比较）
- ❌ 自动切换 force level
- ❌ 用户侧的「刷新推荐」命令
- ❌ 重查频率的动态调整

---

## 架构设计

### 时序图

```
用户消息 → _on_pre_llm_call()
    │
    ├── 缓存命中 → _turn_counter++
    │   ├── _turn_counter < 5 → 返回缓存（不重查）
    │   └── _turn_counter >= 5 → 清除缓存 + 重查 SRA
    │       ├── 有新推荐 → 返回新鲜上下文
    │       └── 无新推荐 → 返回原缓存
    │
    └── 缓存未命中 → 调 SRA → _turn_counter = 0 → 注入
```

### 关键变量

```python
# 模块级（在 __init__.py 中）
_turn_counter: int = 0          # 当前轮数计数器
RECHECK_INTERVAL: int = 5       # 每 5 轮重查一次

# 重查后重置计数器（不管是否真有新推荐）
# 防止频繁调 SRA
```

### 与现有机制的交互

| 现有代码 | Phase 4 修改 | 兼容性 |
|:---------|:-------------|:-------|
| `_SRA_CACHE` 缓存 | 重查时主动清除特定消息的缓存 | ✅ 缓存清除后自然触发新请求 |
| `_get_cached()` / `_set_cached()` | 不修改，只增加清除逻辑 | ✅ |
| `_on_pre_llm_call()` | 在缓存命中分支增加轮数检查 | ✅ 不改变现有流程 |
| `client.recommend()` | 复用已有方法 | ✅ |

---

## Stories

### STORY-4-5-1: 轮数跟踪 + 重查触发

| 字段 | 值 |
|:-----|:-----|
| **估时** | 1.5h |
| **文件** | `plugins/sra-guard/__init__.py` |

**验收标准**:
- [x] 模块级 `_turn_counter` 计数器，每次 pre_llm_call 递增
- [x] `RECHECK_INTERVAL = 5`（可配置）
- [x] 缓存命中时，检查 `_turn_counter >= RECHECK_INTERVAL`
- [x] 达到间隔 → 清除缓存键 → 强制重查 SRA
- [x] 重查后无论结果如何，重置 `_turn_counter = 0`
- [x] 间隔未达到 → 返回缓存（不重查）

### STORY-4-5-2: 轻量提醒格式

| 字段 | 值 |
|:-----|:-----|
| **估时** | 0.5h |
| **文件** | `plugins/sra-guard/__init__.py` |

**验收标准**:
- [x] 重查结果使用标准 `[SRA]` 格式（复用 Phase 1 的 `_format_context()`）
- [x] 重查结果为空时不注入额外上下文
- [x] 返回格式与 Phase 1 完全一致（`{"context": str}`）
- [x] 不影响现有缓存机制

### STORY-4-5-3: 集成测试

| 字段 | 值 |
|:-----|:-----|
| **估时** | 0.5h |
| **文件** | `tests/test_recheck.py` [NEW] |

**验收标准**:
- [x] 未达重查间隔 → 返回缓存（不调 client.recommend）
- [x] 达到重查间隔 → 调 client.recommend
- [x] 重查后计数器重置
- [x] 异常时回退到缓存
- [x] 回归测试通过

---

## 完成条件

- [x] 所有 3 个 Story 的 AC 全部通过
- [x] pre_llm_call 缓存命中时每 5 轮重查一次
- [x] 重查格式与 Phase 1 一致
- [x] 计数器正确递增/重置
- [x] 异常/空结果时回退到缓存
- [x] 回归测试全绿（67 + 新增）
