---
story: STORY-4-7-1
title: "Hermes 端到端集成测试 — 全链路验证"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-7
epic: EPIC-004
estimated_hours: 2
test_data:
  source: tests/fixtures/skills
  ci_independent: true
spec_references:
  - EPIC-004.md
  - SPEC-4-7.md
dependencies:
  - Phase 0-5 全部完成
out_of_scope:
  - AC 代码存在性门禁脚本（STORY-4-7-2）
  - EPIC-004 收尾对齐（STORY-4-7-3）
  - 依赖真实 SRA Daemon（使用 mock）
---

# STORY-4-7-1: Hermes 端到端集成测试

## 用户故事

> As a **SRA 开发者**,
> I want **验证 sra-guard 插件在完整 Hermes 插件生命周期中的行为**,
> So that **确保 Phase 1-4 的 4 个 hook 在真实场景中正确协作**。

---

## 验收标准

### AC-1: mock SRA Daemon 启动
- [x] 条件: 创建 HTTP mock 服务器，模拟 `/health` `/recommend` `/validate` `/record`
- [x] 验证: 服务器能响应请求
- [x] 预期: 端口随机，不与其他测试冲突

### AC-2: 插件加载 + 3 hook 注册
- [x] 条件: 通过 importlib 加载 sra-guard 插件
- [x] 验证: 检查 `register()` 是否注册了 pre_llm_call + pre_tool_call + post_tool_call
- [x] 预期: 3 个 hook 全部注册

### AC-3: 消息注入（Phase 1）
- [x] 条件: 调用 `_on_pre_llm_call()` 发送用户消息
- [x] 验证: 返回值包含 `{"context": ...}` 且以 `[SRA]` 开头
- [x] 预期: SRA 上下文成功注入

### AC-4: 工具校验（Phase 2）
- [x] 条件: 调用 `_on_pre_tool_call()` 模拟 write_file
- [x] 验证: 返回 None（放行）
- [x] 预期: 工具不被阻断

### AC-5: 轨迹记录（Phase 3）
- [x] 条件: 调用 `_on_post_tool_call()` 模拟 skill_view + write_file
- [x] 验证: mock client 的 record() 被调用
- [x] 预期: skill_view → viewed, write_file → used

### AC-6: 重注入（Phase 4）
- [x] 条件: 5 次缓存命中的 pre_llm_call
- [x] 验证: 第 5 次清除缓存并调 recommend()
- [x] 预期: fresh context 被注入

### AC-7: SRA 不可用降级
- [x] 条件: mock 服务器关闭后
- [x] 验证: 所有 hook 返回 None
- [x] 预期: 不抛异常，不阻塞

### AC-8: 独立可运行
- [x] 条件: `pytest tests/test_e2e.py -v`
- [x] 验证: 不依赖已安装的 Hermes
- [x] 预期: 使用 importlib 直接加载

---

## 技术要求

- 使用 `http.server.HTTPServer` 创建 mock SRA Daemon（复用已有模式）
- 测试不依赖已安装的 Hermes 实例
- 所有测试使用 importlib 直接加载插件模块
- 遵循 Hermes plugin API 的调用约定

---

## 实施计划

### Task 1: 创建 test_e2e.py
- **文件**: `plugins/sra-guard/tests/test_e2e.py`
- **操作**: 实现 AC 1-8
- **验证**: pytest -v

### Task 2: 回归测试
- **操作**: 运行 83 + 新增
- **验证**: 全绿

---

## 完成检查清单

- [x] 所有 8 个 AC 通过
- [x] mock SRA 可独立启停
- [x] 全链路覆盖 Phase 1-4
- [x] SRA 不可用时降级
- [x] 可独立运行
