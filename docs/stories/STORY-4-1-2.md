---
story: STORY-4-1-2
title: "注册 pre_llm_call hook 实现 SRA 调用预约"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-1
epic: EPIC-004
estimated_hours: 1
test_data:
  source: tests/fixtures/skills
  ci_independent: true
  pattern_reference: ""
spec_references:
  - EPIC-004.md
  - SPEC-4-1.md
  - ~/.hermes/hermes-agent/hermes_cli/plugins.py
dependencies:
  - STORY-4-1-1
out_of_scope:
  - 实现实际的 SRA Daemon HTTP 调用（STORY-4-1-3）
  - 格式化 [SRA] 上下文的 UI 逻辑（Phase 1）
  - 工具调用校验（Phase 2）
---

# STORY-4-1-2: 注册 pre_llm_call hook 实现 SRA 调用预约

## 用户故事

> As a **SRAGuardPlugin**,
> I want **注册 `pre_llm_call` hook 并在钩子中预留 SRA 调用点**,
> So that **每次 Hermes 即将调用 LLM 时，插件有机会注入技能推荐上下文**。

---

## 验收标准

### AC-1: pre_llm_call hook 被正确注册
- [x] 条件: `SRAGuardPlugin.__init__` 调用 `manager.register_hook("pre_llm_call", callback)`
- [x] 验证方式: 检查 Hermes hook 注册表
- [x] 预期结果: `pre_llm_call` 钩子列表包含 sra-guard 的回调

### AC-2: 回调签名匹配 Hermes 规范
- [x] 条件: 回调函数签名应为 `on_pre_llm_call(self, messages, session_id, **kwargs)`
- [x] 验证方式: 检查函数签名
- [x] 预期结果: Hermes 调用插件时不因参数不匹配而抛出异常

### AC-3: 返回值格式正确
- [x] 条件: 有推荐时返回 `{"context": "..."}`
- [x] 验证方式: 检查返回值类型
- [x] 预期结果: 格式符合 Hermes `pre_llm_call` hook 规范

### AC-4: 无推荐时返回 None
- [x] 条件: SRA Daemon 返回空推荐或不可用时
- [x] 验证方式: 模拟 SRA 不可用
- [x] 预期结果: 回调返回 `None`，不注入任何内容

### AC-5: 异常不向上传播
- [x] 条件: 回调内抛出任何异常
- [x] 验证方式: 模拟异常场景
- [x] 预期结果: 异常被 `try/except` 捕获，记录 WARNING 日志，返回 None

---

## 技术要求

- Hook 回调在 STORY-4-1-3 的通信模块就绪后会自动调用 `client.recommend()`
- 当前 Story **只需要注册 hook + 预留调用点**，通信逻辑留到 STORY-4-1-3
- 使用 `try/except Exception as e` 包裹，不静默（记录日志级别 WARNING）

### Hermes pre_llm_call hook 文档

```python
# 来自 hermes_cli/plugins.py 的文档（L1093-1103）：
"""
For ``pre_llm_call``, callbacks may return a dict describing
context to inject into the current turn's user message::

    {"context": "recalled text..."}
    "recalled text..."          # plain string, equivalent

Context is ALWAYS injected into the user message, never the
system prompt.  This preserves the prompt cache prefix — the
system prompt stays identical across turns so cached tokens
are reused.  All injected context is ephemeral — never
persisted to session DB.
"""
```

### Callback 伪代码

```python
def on_pre_llm_call(self, messages, session_id, **kwargs):
    """pre_llm_call hook 回调 — 在 LLM 调用前注入 SRA 推荐"""
    try:
        # 从 messages 中提取最后一条用户消息
        if not messages:
            return None
        last_msg = messages[-1]
        if last_msg.get("role") != "user":
            return None
        user_message = last_msg.get("content", "")
        if not user_message or not isinstance(user_message, str):
            return None

        # 交给 client 模块（STORY-4-1-3 实现）
        # context = self.client.get_recommendation(user_message)
        # if context:
        #     return {"context": context}
        return None  # TODO: STORY-4-1-3 后接入
    except Exception as e:
        logger.warning("SRA pre_llm_call 异常: %s", e)
        return None
```

---

## 实施计划

### Task 1: 在 plugin.py 中实现 hook 注册
- **文件**: `~/.hermes/hermes-agent/plugins/sra-guard/plugin.py`
- **操作**: 
  - 修改 `SRAGuardPlugin.__init__` 接收 `manager` 参数
  - 调用 `manager.register_hook("pre_llm_call", self.on_pre_llm_call)`
  - 实现 `on_pre_llm_call` 方法（框架版，预留调用点）
- **验证**: `python3 -c "from sra_guard import SRAGuardPlugin; print('OK')"`

### Task 2: 编写单元测试
- **文件**: `~/.hermes/hermes-agent/plugins/sra-guard/tests/test_hook.py`
- **操作**: 
  - mock Hermes PluginManager
  - 验证 hook 注册
  - 验证回调签名
  - 验证异常降级
- **验证**: `python3 -m pytest tests/test_hook.py -v`

---

## 测试策略

- **Fixture**: mock PluginManager（无需 Hermes 完整环境）
- **新测试文件**: `tests/test_hook.py`
- **CI 环境**: 完全独立

---

## 完成检查清单

- [x] 所有 AC 通过
- [x] pre_llm_call hook 注册成功
- [x] 回调异常时返回 None（不阻塞 Hermes）
- [x] 单元测试覆盖正常/异常/空推荐场景
- [x] 代码 + 文档同次 commit
