---
story: STORY-4-2-3
title: "集成测试 — 消息注入场景全覆盖"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-2
epic: EPIC-004
estimated_hours: 2
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-2.md
dependencies:
  - STORY-4-2-1
  - STORY-4-2-2
out_of_scope:
  - 端到端测试（依赖真实 SRA Daemon，在 Phase 6 做）
  - 性能测试
---

# STORY-4-2-3: 集成测试 — 消息注入场景全覆盖

## 用户故事

> As a **sra-guard 插件维护者**,
> I want **完整的集成测试覆盖消息注入的各类场景**,
> So that **每次修改后都能自动验证注入逻辑的正确性**。

---

## 验收标准

### AC-1: 正常消息注入 [SRA] 前缀
- [x] 条件: 发送 "帮我画架构图" 消息到 mock SRA
- [x] 验证: 检查 `_on_pre_llm_call` 返回值
- [x] 预期: 返回 `{"context": "..."}` 且以 `[SRA]` 开头

### AC-2: 多轮对话只提取最后一条 user message
- [x] 条件: messages=[assistant消息, user消息1, assistant消息, user消息2]
- [x] 验证: 检查发送到 mock SRA 的内容
- [x] 预期: 只发送 user消息2 到 SRA

### AC-3: 非 user role 不注入
- [x] 条件: messages=[{"role": "assistant", "content": "你好"}]
- [x] 验证: 检查返回值
- [x] 预期: 返回 None

### AC-4: 空消息不注入
- [x] 条件: messages=[{"role": "user", "content": ""}]
- [x] 验证: 检查返回值
- [x] 预期: 返回 None

### AC-5: 缓存命中测试
- [x] 条件: 同一消息调用两次
- [x] 验证: mock SRA 的请求计数
- [x] 预期: 第二次不调 SRA（请求计数不变）

### AC-6: 长消息截断测试
- [x] 条件: 传入超过 2500 字符的上下文
- [x] 验证: 检查返回值长度
- [x] 预期: ≤ 2500

### AC-7: SRA 不可用时优雅降级
- [x] 条件: SRA Daemon 未运行
- [x] 验证: 检查返回值
- [x] 预期: 返回 None（不报错，不阻塞）

---

## 技术要求

- 复用 `tests/test_client.py` 中的 `MockSRAHandler`
- 新测试文件专注于「消息注入」场景（`_on_pre_llm_call` 的集成行为）
- 使用 mock 服务器避免依赖真实 SRA Daemon

### 测试架构

```
test_injection.py
├── TestInjection
│   ├── test_normal_injection          — AC-1
│   ├── test_multi_turn_extraction      — AC-2
│   ├── test_non_user_role              — AC-3
│   ├── test_empty_message              — AC-4
│   ├── test_cache_hit                  — AC-5
│   ├── test_long_message_truncation    — AC-6
│   └── test_sra_unavailable            — AC-7
```

---

## 实施计划

### Task 1: 创建 test_injection.py
- **文件**: `plugins/sra-guard/tests/test_injection.py`
- **操作**: 实现 7 个测试用例
- **验证**: `pytest tests/test_injection.py -v`

### Task 2: 回归测试
- **操作**: 运行全部测试
- **验证**: `pytest tests/ -v` → 所有现有测试不受影响

---

## 测试策略

- **Fixture**: mock SRA HTTP 服务器（复用 test_client.py 的 MockSRAHandler）
- **新测试文件**: `tests/test_injection.py`
- **CI 环境**: 完全独立

---

## 完成检查清单

- [x] 所有 7 个 AC 通过
- [x] 正常/多轮/非user/空消息/缓存/截断/降级 7 场景全覆盖
- [x] 回归测试无退化
- [x] mock 服务器不依赖真实 SRA Daemon
