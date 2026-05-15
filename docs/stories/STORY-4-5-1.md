---
story: STORY-4-5-1
title: "轮数跟踪 + 重查触发"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-5
epic: EPIC-004
estimated_hours: 1.5
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-5.md
dependencies:
  - Phase 1 (pre_llm_call + 缓存机制)
out_of_scope:
  - 提醒格式（STORY-4-5-2）
  - 集成测试（STORY-4-5-3）
---

# STORY-4-5-1: 轮数跟踪 + 重查触发

## 用户故事

> As a **执行长任务的 Agent**,
> I want **每 5 轮工具调用后自动刷新 SRA 推荐**,
> So that **即使长对话中上下文变化，技能推荐仍保持新鲜**。

---

## 验收标准

### AC-1: 模块级轮数计数器
- [x] 条件: `_turn_counter` 在模块级别定义
- [x] 验证: 检查模块属性
- [x] 预期: 初始值为 0

### AC-2: 每轮递增
- [x] 条件: 每次 `_on_pre_llm_call()` 被调用（无论缓存是否命中）
- [x] 验证: 调用后检查 `_turn_counter`
- [x] 预期: 每次调用后 counter +1

### AC-3: RECHECK_INTERVAL = 5
- [x] 条件: 模块级常量 `RECHECK_INTERVAL = 5`
- [x] 验证: 直接检查常量
- [x] 预期: 值为 5

### AC-4: 未达间隔不重查
- [x] 条件: `_turn_counter < RECHECK_INTERVAL` 且缓存命中
- [x] 验证: mock client.recommend() 检查是否被调用
- [x] 预期: client.recommend() 未被调用（返回缓存）

### AC-5: 达到间隔强制重查
- [x] 条件: `_turn_counter >= RECHECK_INTERVAL` 且缓存命中
- [x] 验证: mock client.recommend() 检查是否被调用
- [x] 预期: client.recommend() 被调用（清除缓存键后）

### AC-6: 重查后计数器重置
- [x] 条件: 重查触发后
- [x] 验证: 检查 `_turn_counter`
- [x] 预期: 重置为 0

### AC-7: 缓存未命中时不额外触发
- [x] 条件: 缓存未命中（首次调用）
- [x] 验证: 检查行为
- [x] 预期: 正常调 SRA，计数器重置为 0（不触发额外重查）

---

## 技术要求

- 在 `__init__.py` 模块级添加 `_turn_counter` 和 `RECHECK_INTERVAL`
- 在 `_on_pre_llm_call()` 的缓存命中分支中增加轮数检查
- 重查通过清除 `_SRA_CACHE` 中当前消息的缓存键实现
- 清除后后续代码自然走「缓存未命中→调 SRA」分支

### 伪代码

```python
# 模块级
_turn_counter: int = 0
RECHECK_INTERVAL: int = 5

def _on_pre_llm_call(messages, session_id, **kwargs):
    try:
        # ... 现有参数检查 ...
        
        text = last.get("content", "")
        
        # 递增轮数计数器
        _turn_counter += 1
        
        # Phase 4: 检查是否需要重查
        cached = _get_cached(text)
        if cached:
            if _turn_counter >= RECHECK_INTERVAL:
                _turn_counter = 0
                # 清除缓存 → 后续强制重查
                # 注意：不清除全部缓存，只清除当前消息的
                _clear_cache(text)
                # 继续执行下面的 SRA 请求逻辑
            else:
                return {"context": cached}
        
        # ... 正常调 SRA 逻辑 ...
        client = _get_client()
        if client is None:
            return None
        
        rag_context = client.recommend(text)
        _turn_counter = 0  # 调了 SRA 就重置计数器
        # ... 其余逻辑 ...
```

---

## 实施计划

### Task 1: 添加 _turn_counter + RECHECK_INTERVAL
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 模块级添加两个常量
- **验证**: 直接检查属性

### Task 2: 修改 _on_pre_llm_call 缓存命中分支
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 在缓存命中后增加轮数检查
- **验证**: AC 4-7 测试通过

---

## 完成检查清单

- [x] 所有 7 个 AC 通过
- [x] 计数器初始 0，每轮递增
- [x] 5 轮间隔强制重查
- [x] 重查后计数器重置
- [x] 未达间隔返回缓存
