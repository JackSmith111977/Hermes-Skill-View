---
spec_id: SPEC-4-7
title: "端到端测试 + CI 门禁 — EPIC-004 收尾"
status: completed
epic: EPIC-004
created: 2026-05-15
updated: 2026-05-15
stories:
  - STORY-4-7-1
  - STORY-4-7-2
  - STORY-4-7-3
test_data_contract:
  source: tests/fixtures/skills
  ci_independent: true
---

# SPEC-4-7: 端到端测试 + CI 门禁

> **所属 Epic**: EPIC-004
> **状态**: draft
> **目标**: 验证 SRA 全链路真实可用 + 建立 AC 代码存在性门禁 + EPIC-004 收尾
> **估时**: 4h
> **依赖**: Phase 0-5 全部完成

---

## 背景

### 为什么还需要 Phase 6？

83 个单元测试覆盖了 Phase 1-4 的每个组件，但存在两个缺口：

**缺口 1：没有端到端测试**
```
单元测试：           ✓ 每个组件独立测试
集成测试：           ✓ client → mock server
端到端测试：         ❌ 从未在真实 Hermes 中加载插件验证
```

**缺口 2：没有 AC 代码存在性门禁**
```
EPIC-001/003 的教训：
  AC 标记 [x] → 但代码从未实现 → 整个集成方案从未工作
  根因：没有机制验证「[x] = 代码真实存在」
```

Phase 6 填补这两个缺口，为整个 EPIC-004 画上句号。

---

## Scope（范围内）

- 创建端到端测试：mock SRA Daemon + 真实 Hermes 插件加载
- 端到端覆盖：插件加载 → 消息注入 → 工具校验 → 轨迹记录 → 重注入
- 创建 AC 代码存在性门禁脚本
- 全量回归测试 + 文档对齐
- EPIC-004 标记为完成

## Out of Scope（不做）

- ❌ 修改 SRA Daemon 代码
- ❌ 修改 Hermes 核心代码
- ❌ CI 配置文件（项目无 CI；门禁脚本可被任何 CI 调用）
- ❌ 性能测试

---

## 架构设计

### 端到端测试

```python
# tests/test_e2e.py — 端到端测试
# 测试策略：mock SRA Daemon + 直接调用插件 hook

class MockSRADaemon:
    """模拟 SRA Daemon HTTP 服务器"""
    # /health → {"status": "running"}
    # /recommend → {"rag_context": "..."}
    # /validate → {"compliant": true, ...}
    # /record → {"status": "ok"}

def test_e2e_full_flow():
    """Phase 1→2→3→4 全链路"""
    # 1. 启动 mock 服务器
    # 2. 加载 sra-guard 插件
    # 3. 发送用户消息 → pre_llm_call → [SRA] 注入
    # 4. 触发 write_file → pre_tool_call → validate → 放行
    # 5. 触发 skill_view → post_tool_call → record viewed
    # 6. 触发 write_file → post_tool_call → record used
    # 7. 5 轮后缓存清除 → 重查触发
```

### AC 代码存在性门禁

```python
# scripts/ac-audit-code-check.py
# 输入：EPIC-004.md（或任何含 [x] AC 的文档）
# 流程：
#   1. 提取所有 [x] 标记的 AC
#   2. 读取 AC 行后的 <!-- 验证: ... --> 注释
#   3. 执行验证命令（如 pytest 路径）
#   4. 任何验证失败 → exit 1
# 输出：AC 真实存在报告
```

---

## Stories

### STORY-4-7-1: Hermes 端到端集成测试

| 字段 | 值 |
|:-----|:-----|
| **估时** | 2h |
| **文件** | `tests/test_e2e.py` [NEW] |

**验收标准**:
- [x] 启动 mock SRA Daemon（HTTP :random_port）
- [x] 加载 sra-guard 插件 → 验证 3 个 hook 注册
- [x] 用户消息 → pre_llm_call → 返回 `{"context": ...}`
- [x] write_file 调用 → pre_tool_call → 返回 None（放行）
- [x] skill_view 调用 → post_tool_call → client.record() 被调用
- [x] 连续 5 轮消息 → 第 5 轮触发重查
- [x] SRA Daemon 停止 → 所有 hook 降级不抛异常
- [x] 端到端测试可独立运行（不依赖已安装的 Hermes）

### STORY-4-7-2: AC 代码存在性门禁

| 字段 | 值 |
|:-----|:-----|
| **估时** | 1h |
| **文件** | `scripts/ac-audit-code-check.py` [NEW] |

**验收标准**:
- [x] 脚本读取 EPIC-004.md 的完成条件表
- [x] 提取每个 `✅` 条件后的说明文字
- [x] 对有测试验证的条件，执行 `pytest --collect-only` 确认测试存在
- [x] 测试不存在时 → exit 1 + 错误列表
- [x] 测试都存在时 → exit 0 + 成功报告
- [x] `--help` 显示用法

### STORY-4-7-3: 回归测试 + 文档对齐

| 字段 | 值 |
|:-----|:-----|
| **估时** | 1h |
| **文件** | 全部插件测试 + EPIC-004.md |

**验收标准**:
- [x] 全量 83 测试通过
- [x] STORY-4-7-1/2 文档 → `completed`
- [x] SPEC-4-7 → `completed`
- [x] EPIC-004 Phase 6 标记完成
- [x] EPIC-004 顶部状态 "done"

---

## 完成条件

- [x] 所有 3 个 Story 的 AC 全部通过
- [x] 端到端测试覆盖 Phase 1-4 全链路
- [x] AC 代码存在性门禁可执行
- [x] 全量 83 测试通过
- [x] EPIC-004 标记为已完成
