---
story: STORY-4-4-2
title: "工具调用 → POST /record {action: 'used'} + 内部工具过滤"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-4
epic: EPIC-004
estimated_hours: 1
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-4.md
dependencies:
  - STORY-4-4-1 (共享 _on_post_tool_call 回调)
out_of_scope:
  - skill_view 的记录（STORY-4-4-1）
  - 集成测试（STORY-4-4-3）
---

# STORY-4-4-2: 工具调用轨迹记录 + 内部工具过滤

## 用户故事

> As a **SRA 推荐引擎**,
> I want **每次 Agent 调用常规工具时自动记录到 SRA**,
> So that **SRA 了解哪些工具被频繁使用，结合技能使用数据优化推荐策略**。

---

## 验收标准

### AC-1: 非 skill 工具调用 → action="used"
- [x] 条件: `tool_name` 不是 skill 工具，且不是过滤列表中的内部工具
- [x] 验证: mock client.record() 检查调用
- [x] 预期: `client.record(skill="", action="used")` 被调用

### AC-2: 工具名写入 tool 字段
- [x] 条件: 记录中包含触发工具的名称
- [x] 验证: 检查 record 调用的参数
- [x] 预期: 调用中含有 tool 信息（当前 client.record 尚不支持 tool 字段 → 扩展签名）

### AC-3: 内部工具被忽略
- [x] 条件: tool_name 在过滤列表中（todo, memory, session_search 等）
- [x] 验证: mock client.record() 检查是否被调用
- [x] 预期: client.record() 未被调用

### AC-4: 简单去重不刷屏
- [x] 条件: 短时间内连续调用同工具（如 tool_call 重试）
- [x] 验证: 同 tool 在 2s 内第二次调用不再记录
- [x] 预期: client.record() 只被调用一次

### AC-5: 异常不传播
- [x] 条件: 回调内抛出任何异常
- [x] 验证: try/except 包裹
- [x] 预期: 返回 None，记录 WARNING 日志

---

## 技术要求

- 在 `_on_post_tool_call()` 中添加非 skill 工具的处理分支
- 定义 `IGNORE_TOOLS` 列表（含 todo, memory, session_search, delegate_task）
- 简单去重使用模块级 dict 记录上次调用时间

### 伪代码

```python
IGNORE_TOOLS = {"todo", "memory", "session_search", "delegate_task"}
_last_record_time: dict = {}  # tool_name → timestamp

def _on_post_tool_call(tool_name, args, result, task_id, session_id, tool_call_id, duration_ms, **kwargs):
    try:
        client = _get_client()
        if client is None:
            return None
        
        if tool_name in SKILL_TOOLS:
            # STORY-4-4-1: skill tools → action="viewed"
            ...
        elif tool_name in IGNORE_TOOLS:
            # 内部工具 → 不记录
            return None
        else:
            # 常规工具 → 去重检查
            now = time.time()
            last = _last_record_time.get(tool_name, 0)
            if now - last < 2.0:
                return None  # 防止刷屏
            _last_record_time[tool_name] = now
            client.record(skill="", action="used")
        
        return None
    except Exception:
        logger.warning(...)
    return None
```

---

## 实施计划

### Task 1: 在 __init__.py 中添加非 skill 记录逻辑
- **文件**: `plugins/sra-guard/__init__.py`
- **操作**: 添加 IGNORE_TOOLS + 去重逻辑 + used 记录分支
- **验证**: 单元测试通过

### Task 2: 扩展 client.record() 签名（可选）
- **文件**: `plugins/sra-guard/client.py`
- **操作**: 如果需要，为 record() 添加 tool 参数
- **验证**: 不破坏现有调用

---

## 完成检查清单

- [x] 所有 5 个 AC 通过
- [x] 非 skill 工具 → action="used"
- [x] 内部工具 (todo/memory) 被忽略
- [x] 简单去重防止刷屏
- [x] 异常时不影响工具执行
