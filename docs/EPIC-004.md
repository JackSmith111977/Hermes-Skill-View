---
epic_id: EPIC-004
title: "SRA Hermes 原生插件集成 — 从补丁到插件的架构重构"
status: done
created: 2026-05-15
updated: 2026-05-15
target_version: v2.1.0
stories:
  - SPEC-4-1
  - SPEC-4-2
  - SPEC-4-3
  - SPEC-4-4
  - SPEC-4-5
  - SPEC-4-6
  - SPEC-4-7
test_data_contract:
  source: tests/fixtures/skills
  ci_independent: true
---

# EPIC-004: SRA Hermes 原生插件集成 — 从补丁到插件的架构重构

> **状态**: ✅ **已完成**
> **目标版本**: SRA v2.1.0
> **包含 Phase**: 7 个 (Phase 0-6)
> **分析日期**: 2026-05-15
> **分析者**: Emma (小玛)

---

## 📋 问题全景

### 核心问题

SRA 自动注入从未真正工作过：

```
[EPIC-001 宣称: ✅]                [现实: ❌]
  _query_sra_context() 已实现       run_agent.py 中零 SRA 代码
  Hermes 侧集成完成                 补丁从未执行
  自动注入正常工作                   唯一方式是手动 curl
```

### 三重背离

| 维度 | 问题 | 严重度 |
|:-----|:------|:------:|
| **SDD 背离** | AC 审计只检文档标记 `[x]`，不验代码存在性 | 🔴 P0 |
| **代码背离** | force.py 定义 4 级注入点但无消费者；`sra install hermes` 是 print 语句 | 🔴 P0 |
| **文档背离** | INTEGRATION.md 描述的系统不存在；EPIC-001/003 多个 AC 标记 ✅ 但未实现 | 🔴 P0 |

### 根因

1. **EPIC-001 验收标准只覆盖 SRA 侧** — 6 个 AC 全部针对补丁文件/脚本是否存在，**没有一个要求验证 Hermes 端是否实际被修改**
2. **AC 审计只检查文档标记** — `ac-audit.py` 只搜索 `[x]`，不验证对应代码真实存在
3. **补丁方案本身脆弱** — `sed -i` 依赖行号，Hermes 升级即覆盖，无自动恢复
4. **Hermes 已有插件系统但未被利用** — `pre_llm_call` / `pre_tool_call` hook 提供了原生集成点

---

## 🎯 Epic 目标

将 SRA 从「sed 补丁方案」重构为 **Hermes 原生插件**：

```diff
- ❌ 修改 run_agent.py（sed -i，每次升级覆盖）
+ ✅ 创建 Hermes 插件 sra-guard（plugins/ 目录，零侵入）

- ❌ 依赖行号定位注入点
+ ✅ 利用 pre_llm_call hook（标准 API，向前兼容）

- ❌ except Exception: pass 静默吞异常
+ ✅ 标准日志 + 错误传播

- ❌ urllib.request 不匹配 Hermes 风格
+ ✅ 使用 Hermes 标准 HTTP 客户端
```

### 核心转变

```
v1.x (当前):                        v2.1 (目标):
┌──────────────┐                   ┌──────────────────┐
│ SRA Daemon   │                   │ SRA Daemon        │
│  📡 广播     │                   │  📡 广播          │
│  :8536       │                   │  :8536            │
└──────┬───────┘                   └──────┬───────────┘
       │                                   │
       ▼                                   ▼
Hermes 侧:                           Hermes 侧:
┌──────────────────┐                ┌──────────────────┐
│ ❌ 没人收听      │                │ ✅ sra-guard 插件 │
│                  │                │                  │
│ 手动 curl 才是   │   ──→         │ pre_llm_call →   │
│ 唯一方式         │                │ POST /recommend  │
│                  │                │                  │
│ SOUL.md 规则     │                │ pre_tool_call →  │
│ (劝告式，不可靠) │                │ POST /validate   │
└──────────────────┘                └──────────────────┘
```

---

## 🏛️ 架构蓝图

### 最终文件结构

```
~/.hermes/hermes-agent/
├── plugins/                         ← Hermes 插件目录
│   └── sra-guard/                   ← [NEW] SRA 插件
│       ├── __init__.py              ← 插件入口 + hook 注册
│       ├── manifest.yaml            ← 插件清单（名称/版本/钩子）
│       ├── context_injector.py      ← pre_llm_call → POST /recommend
│       ├── tool_validator.py        ← pre_tool_call → POST /validate
│       └── usage_tracker.py         ← post_tool_call → POST /record
├── run_agent.py                     ← ❌ 不改动（零侵入）
└── model_tools.py                   ← ❌ 不改动（已有 hook 系统）

~/.hermes/config.yaml                 ← [新增] SRA 配置段

~/projects/sra/
├── docs/
│   ├── EPIC-004.md                   ← [NEW] 本文件
│   ├── INTEGRATION.md                ← [改] 从补丁方案→插件方案
│   ├── EPIC-001-hermes-integration.md ← [改] 标记为「被 EPIC-004 取代」
│   └── EPIC-003-v2-enforcement-layer.md ← [改] 修正虚假 AC 标记
```

### Hook 集成示意图

```python
# Hermes Plugin 注册方式（伪代码）
class SRAGuardPlugin:
    def __init__(self, manager):
        manager.register_hook("pre_llm_call", self.on_pre_llm_call)
        manager.register_hook("pre_tool_call", self.on_pre_tool_call)
        manager.register_hook("post_tool_call", self.on_post_tool_call)

    def on_pre_llm_call(self, messages, **kwargs):
        """每次 LLM 调用前注入 SRA 推荐上下文"""
        ctx = query_sra("/recommend", {"message": last_user_msg})
        if ctx:
            return {"context": ctx}  # Hermes 自动注入到 user_message 前

    def on_pre_tool_call(self, tool_name, args, **kwargs):
        """工具调用前校验是否已加载对应技能"""
        result = query_sra("/validate", {"tool": tool_name, "args": args})
        if not result.get("compliant", True):
            return {"action": "block", "message": result["message"]}
```

---

## 📦 Phase 分解

### Phase 0: 基础设施 — sra-guard 插件框架 (P0)

**入口门禁**: EPIC-004 已批准
**出口里程碑**: 插件加载成功 + Hermes `list_plugins` 显示 sra-guard + 安装脚本可部署 + 文档对齐完成

| SPEC | Story | 标题 | 估时 | 描述 |
|:-----|:------|:-----|:----:|:-----|
| SPEC-4-1 | STORY-4-1-1 | 插件目录结构 + 清单文件 | 0.5h | 创建 `plugins/sra-guard/` 目录 + `plugin.yaml` + `__init__.py` |
| SPEC-4-1 | STORY-4-1-2 | pre_llm_call hook 注册 | 1h | 注册 `pre_llm_call` hook，在 Hermes 启动时自动发现 |
| SPEC-4-1 | STORY-4-1-3 | SRA Daemon 通信模块 | 1h | Unix Socket + HTTP 双协议客户端，优雅降级 |
| SPEC-4-1 | STORY-4-1-4 | 安装脚本 | 0.5h | 将插件从 SRA 项目部署到 Hermes plugins 目录 |
| SPEC-4-1 | STORY-4-1-5 | 文档对齐（INTEGRATION/EPIC/README） | 2h | 修正虚假 AC 标记，更新为插件方案 |

### Phase 1: 消息前置注入 (P0)

**入口门禁**: Phase 0 完成 + 插件可加载
**出口里程碑**: 每次用户消息自动注入 [SRA] 上下文

| SPEC | Story | 标题 | 估时 | 描述 |
|:-----|:------|:-----|:----:|:-----|
| SPEC-4-2 | STORY-4-2-1 | POST /recommend 调用 + 上下文格式化 | 2h | pre_llm_call 中调 SRA Daemon，格式化 [SRA] 上下文 |
| SPEC-4-2 | STORY-4-2-2 | 模块级缓存（MD5 防重复） | 0.5h | 同一条消息不重复请求 SRA |
| SPEC-4-2 | STORY-4-2-3 | 集成测试 + 日志 | 1h | 验证注入后的消息包含 [SRA] 前缀 |

### Phase 2: 工具调用校验 (P1)

**入口门禁**: Phase 1 完成
**出口里程碑**: write_file/patch 时自动校验技能加载

| SPEC | Story | 标题 | 估时 | 描述 |
|:-----|:------|:-----|:----:|:-----|
| SPEC-4-3 | STORY-4-3-1 | pre_tool_call → POST /validate | 2h | 拦截 write_file/patch，调 SRA 校验 |
| SPEC-4-3 | STORY-4-3-2 | force level 感知 | 0.5h | 按配置的力度级别决定监控哪些工具 |
| SPEC-4-3 | STORY-4-3-3 | 集成测试 + 降级测试 | 1h | SRA 不可用时工具继续执行 |


### ✅ 已完成 Phase

| Phase | 状态 | Stories | 验证 |
|:------|:----:|:-------:|:----:|
| Phase 0: 插件框架+安装+文档 | ✅ 完成 | 5/5 | 55/55 测试全绿 |
| Phase 1: 消息注入 | ✅ 完成 | 3/5（与 0 共享测试） | 55/55 测试全绿 |
| Phase 2: 工具校验 | ✅ 完成 | 3/3 | 55/55 测试全绿 |
| Phase 3: 轨迹追踪 | ✅ 完成 | 3/3 | 67/67 测试全绿 |
| Phase 4: 周期重注入 | ✅ 完成 | 3/3 | 83/83 测试全绿 |
| Phase 5: 文档修复 | ✅ 完成 | 2/2 | EPIC-003 AC 真相更新 + 文档一致性 |
| Phase 6: 端到端+CI | ✅ 完成 | 3/3 | 93/93 测试全绿 + AC 门禁 |

### Phase 3: 技能使用轨迹追踪 (P1)

**入口门禁**: Phase 2 完成
**出口里程碑**: /record 端点收到 Hermes 发来的使用数据

| SPEC | Story | 标题 | 估时 | 描述 |
|:-----|:------|:-----|:----:|:-----|
| SPEC-4-4 | STORY-4-4-1 | skill_view → POST /record {action: "viewed"} | 1h ✅ | 拦截 skill_view 调用 |
| SPEC-4-4 | STORY-4-4-2 | 工具调用 → POST /record {action: "used"} | 1h ✅ | 拦截工具调用后记录 |
| SPEC-4-4 | STORY-4-4-3 | 集成测试 | 0.5h ✅ | 验证记录计数 |

### Phase 4: 周期性重注入防漂移 (P2)

**入口门禁**: Phase 2 完成
**出口里程碑**: 长任务（5+ 轮）自动获得新鲜推荐

| SPEC | Story | 标题 | 估时 | 描述 |
|:-----|:------|:-----|:----:|:-----|
| SPEC-4-5 | STORY-4-5-1 | 轮数跟踪 + 重查触发 | 1.5h ✅ | session 级别跟踪对话轮数 |
| SPEC-4-5 | STORY-4-5-2 | 轻量提醒格式 | 0.5h ✅ | 不干扰当前任务 |
| SPEC-4-5 | STORY-4-5-3 | 集成测试 | 0.5h ✅ | 验证重注入触发 |

### Phase 5: 修复文档漂移 (P1)

**入口门禁**: Phase 0-4 代码全部完成
**出口里程碑**: 所有文档反映真实状态

| SPEC | Story | 标题 | 估时 | 描述 |
|:-----|:------|:-----|:----:|:-----|
| SPEC-4-6 | STORY-4-6-1 | EPIC-003 AC 真相更新 | 0.5h ✅ | 4 个 Hermes 侧 AC → [x] + 验证说明 |
| SPEC-4-6 | STORY-4-6-2 | RUNTIME + README 一致性 | 0.5h ✅ | 清除旧补丁方案引用 |

### Phase 6: 端到端测试 + CI 门禁 (P1)

**入口门禁**: Phase 0-4 代码完成 + Phase 5 文档完成
**出口里程碑**: CI 全绿 + EPIC-004 ✅

| SPEC | Story | 标题 | 估时 | 描述 |
|:-----|:------|:-----|:----:|:-----|
| SPEC-4-7 | STORY-4-7-1 | Hermes 端到端集成测试 | 2h ✅ | 插件加载 → 消息注入 → 工具校验 |
| SPEC-4-7 | STORY-4-7-2 | AC 代码存在性门禁脚本 | 1h ✅ | 验证每个 [x] 有真实代码 |
| SPEC-4-7 | STORY-4-7-3 | 回归测试 + 文档对齐 | 1h ✅ | 全量测试 + doc-alignment |

---

## 📊 优先级与估时

| Phase | 优先级 | Stories | 估时 |
|:------|:------:|:-------:|:----:|
| Phase 0: 插件框架+安装+文档 | 🔴 P0 ✅ | 5 | 5h |
| Phase 1: 消息注入 | 🔴 P0 ✅ | 3 | 3.5h |
| Phase 2: 工具校验 | 🟡 P1 ✅ | 3 | 3.5h |
| Phase 3: 轨迹追踪 | 🟡 P1 ✅ | 3 | 2.5h |
| Phase 4: 周期重注入 | 🟢 P2 ✅ | 3 | 2.5h |
| Phase 5: 修复文档漂移 | 🟡 P1 ✅ | 2 | 1h ✅ |
| Phase 6: 端到端测试+CI | 🟡 P1 ✅ | 3 | 4h ✅ |
| **总计** | | **23** | **~23.5h** |

---

## 🔑 关键设计决策

### 决策 1：插件方案 vs 补丁方案

| 维度 | 补丁方案 ❌ | 插件方案 ✅ |
|:-----|:-----------|:-----------|
| 侵入性 | 修改 Hermes 核心代码 | 零侵入，纯扩展 |
| 升级兼容 | 每次升级覆盖需重装 | 自动保留 |
| 依赖 | sed + line number | 标准 plugin API |
| 错误处理 | `except Exception: pass` | 标准日志 + 异常传播 |
| 实现复杂度 | 低（但维护成本高） | 中（但维护成本低） |

**结论**: 插件方案。长期维护成本远低于补丁方案。

### 决策 2：pre_llm_call vs run_conversation 注入

| 维度 | run_conversation 注入 ❌ | pre_llm_call hook ✅ |
|:-----|:------------------------|:---------------------|
| 方法 | 修改 run_agent.py | 注册 hook |
| 侵入性 | 修改核心代码 | 零侵入 |
| 上下文注入 | 直接修改 user_message | 返回 `{"context": "..."}` 由框架注入 |
| 升级风险 | 高（行号变化） | 无（API 稳定） |

**结论**: pre_llm_call hook。Hermes 插件系统原生支持上下文注入。

### 决策 3：通信协议

| 协议 | 优点 | 缺点 | 选择 |
|:-----|:-----|:-----|:----:|
| HTTP (:8536) | 通用、简单、可调试 | 额外端口依赖 | ✅ 主协议 |
| Unix Socket (~/.sra/srad.sock) | 更安全、更快 | 仅本地可用 | ✅ 降级优先 |

**结论**: 双协议自适应。HTTP 优先，Socket 降级。（SRA 适配器已实现此模式）

---

## ⚠️ 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|:-----|:----:|:----:|:-----|
| Hermes 插件 API 变更 | 低 | 中 | 使用稳定 hook（`pre_llm_call` 已存在多个版本） |
| SRA Daemon 不稳定导致 Agent 延迟 | 低 | 低 | 200ms 超时 + 优雅降级 |
| plugin 与现有 Hermes 版本不兼容 | 中 | 中 | 先测试兼容性，再部署 |
| 插件方案比补丁方案实现更复杂 | 中 | 低 | 利用已有 `adapters/__init__.py` 的通信模块 |

---

## 🔗 关联文档

| 文档 | 关系 |
|:-----|:------|
| [EPIC-001: Hermes 原生集成](./EPIC-001-hermes-integration.md) | ❌ 被 EPIC-004 取代 |
| [EPIC-003: v2.0 强制层](./EPIC-003-v2-enforcement-layer.md) | 🔄 需要修正 AC 标记 |
| [INTEGRATION.md](./INTEGRATION.md) | 🔄 需要从补丁方案改写为插件方案 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 📖 参考架构约束 |
| [RUNTIME.md](../RUNTIME.md) | 📖 参考运行时设计 |
| `~/.hermes/hermes-agent/hermes_cli/plugins.py` | 📖 Hermes 插件系统 API |
| `~/.hermes/hermes-agent/model_tools.py` (L722-737) | 📖 pre_tool_call hook 实现 |
| `~/projects/sra/skill_advisor/adapters/__init__.py` | 📖 可复用的 SRA 通信模块 |

---

## ✅ 完成条件

| # | 条件 | 状态 | 说明 |
|:-:|:-----|:----:|:------|
| 1 | Phase 0-6 全部完成 | ✅ | **全部完成！** EPIC-004 DONE 🎉 |
| 2 | 全量测试（SRA 端 + Hermes 端）通过 | ✅ | 397 tests (SRA 314 + plugin 83) |
| 3 | SRA Daemon 健康检查通过 | ✅ | `sra status` 正常 |
| 4 | 端到端测试：消息注入 → 工具校验 → 轨迹记录 → 重注入 | ✅ | Phase 1/2/3/4 全部覆盖 |
| 5 | AC 代码存在性检查：每个 AC 对应代码真实存在 | ✅ | 每个已验证的 AC 有对应测试文件 |
| 6 | 文档对齐：INTEGRATION.md / EPIC-* / README 反映真实状态 | ✅ | Phase 0 + Phase 5 完成 |
| 7 | 遗留补丁文件标记为废弃 | ✅ | DEPRECATED 已标记 |
