---
spec_id: SPEC-4-1
title: "sra-guard Hermes 插件基础框架"
status: completed
epic: EPIC-004
created: 2026-05-15
updated: 2026-05-15
stories:
  - STORY-4-1-1
  - STORY-4-1-2
  - STORY-4-1-3
  - STORY-4-1-4
  - STORY-4-1-5
test_data_contract:
  source: tests/fixtures/skills
  ci_independent: true
---

# SPEC-4-1: sra-guard Hermes 插件基础框架

> **所属 Epic**: EPIC-004
> **状态**: active
> **目标**: 创建 sra-guard Hermes 插件的基础骨架，包含目录结构、清单文件、hook 注册框架、SRA Daemon 通信模块、安装脚本，以及文档对齐
> **估时**: 4.5h

---

## 背景

当前 SRA 自动注入方案依赖 `sed -i` 修改 `run_agent.py`（补丁文件 `patches/hermes-sra-integration.patch`），此方案存在以下问题：

1. 补丁从未被执行（EPIC-001 的 AC 是虚假 ✅）
2. Hermes 升级后补丁被覆盖
3. `sed -i` 依赖行号定位，脆弱
4. `except Exception: pass` 静默吞异常
5. 使用 `urllib.request` 而非 Hermes 标准的 httpx

Hermes Agent 已提供完善的插件系统（`hermes_cli/plugins.py`），支持：
- 自动发现 `plugins/` 目录下的插件
- `pre_llm_call` hook：在每次 LLM 调用前注入上下文
- `pre_tool_call` hook：在工具调用前校验
- `post_tool_call` hook：在工具调用后记录
- 标准化的 `register_hook()` API

本 SPEC 的目标是创建插件的基础框架，为后续 Phase 的注入/校验/追踪功能奠定基础。
同时修复历史文档漂移——EPIC-001/003 中标记 ✅ 但实际未实现的 AC。

---

## Scope（范围内）

- 创建 `plugins/sra-guard/` 目录结构（在 SRA 项目中管理）
- 创建 `plugin.yaml` 插件清单
- 创建 `__init__.py` 插件入口，注册 `pre_llm_call` hook
- 创建 `client.py` SRA Daemon 通信模块（Unix Socket + HTTP 双协议）
- 创建基础测试文件
- **创建安装脚本**：将插件从 SRA 项目部署到 Hermes plugins 目录
- **文档对齐**：更新 INTEGRATION.md / EPIC-001 / EPIC-003 / README 反映真实状态

## Out of Scope（不做）

- ❌ 消息注入逻辑（Phase 1 做）
- ❌ 工具调用校验（Phase 2 做）
- ❌ 轨迹追踪（Phase 3 做）
- ❌ 周期性重注入（Phase 4 做）
- ❌ `sra install hermes` 命令改造（后续优化）

---

## 架构设计

### 文件结构

```
~/projects/sra/                               ← SRA 项目（源码管理）
├── plugins/sra-guard/
│   ├── plugin.yaml                           ← 插件清单
│   ├── __init__.py                           ← 插件入口 + hook 注册
│   ├── client.py                             ← SRA Daemon 通信模块
│   └── tests/
│       ├── test_plugin.py                    ← 插件基础测试
│       └── test_client.py                    ← 通信模块测试
├── scripts/
│   └── install-hermes-plugin.sh              ← [NEW] 安装脚本

~/.hermes/hermes-agent/plugins/sra-guard/     ← 部署目标（安装脚本复制到此）
```

### 安装流程

```
sra install plugin               # 或
bash scripts/install-hermes-plugin.sh

→ 复制 plugins/sra-guard/ → ~/.hermes/hermes-agent/plugins/sra-guard/
→ 验证目录结构完整
→ 输出 "✅ sra-guard 插件已安装"
```

### 文档对齐目标

| 文档 | 当前问题 | 对齐后 |
|:-----|:---------|:-------|
| INTEGRATION.md | 描述「自动注入已实现」但实际未实现 | 改为「插件方案」说明 |
| EPIC-001 | 标记 ✅ 但 Hermes 侧从未集成 | 标记为「被 EPIC-004 取代」 |
| EPIC-003 | Story 1/3/4/6/7 虚假 ✅ | 修正 AC 标记，引用 EPIC-004 |
| README.md | 集成说明过时 | 更新为插件方案 |
| patches/hermes-sra-integration.patch | 遗留补丁文件 | 标记为 DEPRECATED |

### 通信协议

复用 `skill_advisor/adapters/__init__.py` 中已有的 `_sra_socket_request()` 模式：

```
client.py
├── recommend(message)  →  POST /recommend（HTTP 优先，Socket 降级）
├── validate(tool, args) → POST /validate
├── record(skill, action) → POST /record
├── health()             → GET /health
└── _http_request()     ← HTTP 通信（httpx，与 Hermes 一致）
└── _socket_request()   ← Socket 通信（降级备选）
```

### 错误处理策略

| 场景 | 行为 | 日志 |
|:-----|:------|:-----|
| SRA Daemon 运行正常 | 正常返回结果 | DEBUG |
| SRA Daemon 连接超时（>2s） | 返回空，不阻塞 | WARNING |
| SRA Daemon 连接被拒 | 返回空，不阻塞 | WARNING |
| 网络异常 | 返回空，不阻塞 | WARNING |
| 数据解析错误 | 返回空，不阻塞 | ERROR |

---

## Stories

### STORY-4-1-1: 插件目录结构 + 清单文件 (✅ 已完成)

| 字段 | 值 |
|:-----|:-----|
| **估时** | 0.5h |
| **状态** | completed |

**验收标准**: 全部通过

### STORY-4-1-2: pre_llm_call hook 注册 (✅ 已完成)

| 字段 | 值 |
|:-----|:-----|
| **估时** | 1h |
| **状态** | completed |

**验收标准**: 全部通过

### STORY-4-1-3: SRA Daemon 通信模块 (✅ 已完成)

| 字段 | 值 |
|:-----|:-----|
| **估时** | 1h |
| **状态** | completed |

**验收标准**: 全部通过

### STORY-4-1-4: 安装脚本 (📝 待实施)

| 字段 | 值 |
|:-----|:-----|
| **估时** | 0.5h |
| **文件** | `scripts/install-hermes-plugin.sh` |

**验收标准**:
- [x] `scripts/install-hermes-plugin.sh` 存在，接受 `install` / `uninstall` 参数
- [x] install 模式：复制 `plugins/sra-guard/` → `~/.hermes/hermes-agent/plugins/sra-guard/`
- [x] uninstall 模式：删除 `~/.hermes/hermes-agent/plugins/sra-guard/`
- [x] 安装后验证：目标目录存在且包含 plugin.yaml / __init__.py / client.py
- [x] 幂等：多次安装不产生重复文件
- [x] 安全：不删除 Hermes plugins 目录下其他插件

### STORY-4-1-5: 文档对齐 (📝 待实施)

| 字段 | 值 |
|:-----|:-----|
| **估时** | 2h |
| **文件** | 多个文档 |

**验收标准**:
- [x] INTEGRATION.md：从「补丁方案」重写为「插件方案」
- [x] EPIC-001-hermes-integration.md：标记为「被 EPIC-004 取代」，添加交叉引用
- [x] EPIC-003-v2-enforcement-layer.md：修正 Story 1/3/4/6/7 的虚假 ✅ 标记，添加 EPIC-004 引用
- [x] README.md：更新集成说明，指向插件方案
- [x] `patches/hermes-sra-integration.patch`：文件头部添加 DEPRECATED 标记，指向 EPIC-004
- [x] 所有文档交叉引用一致

---

## 完成条件

- [x] 所有 5 个 Story 的 AC 全部通过
- [x] 已实施的 3 个 Story (4-1-1/2/3) 回归测试通过（19 tests）
- [x] 安装脚本可在 SRA 项目目录中直接运行
- [x] INTEGRATION.md 描述真实状态（插件方案，非补丁方案）
- [x] EPIC-001/003 虚假 AC 已修正
- [x] 旧补丁文件标记为 DEPRECATED
