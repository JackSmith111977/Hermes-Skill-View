# Sprint 2 规划 — 轨迹记录 + 长任务保护 + 测试覆盖

> **Sprint 周期:** 2026-05-10 ~ 2026-05-11
> **分支:** `feat/v2.0-enforcement-layer`
> **版本目标:** SRA v2.0.0-alpha

---

## Sprint 2 目标

完成「观测能力」建设 + 「测试安全网」：

```
Sprint 2 ──┬── SRA-003-03  技能使用轨迹记录  🟡 P1  1d  ✅
           ├── SRA-003-04  长任务上下文漂移   🟡 P1  2d  ✅
           └── SRA-003-14  测试覆盖增强       🟡 P1  2d  ✅
```

---

## Story 1: SRA-003-03 技能使用轨迹记录

### 现状分析
- `POST /record` 已存在，只支持 `record_usage`（记录推荐是否被采纳）
- `memory.py` 的 `SceneMemory` 已有基础存储结构
- 缺少的是：追踪「技能被查看」和「技能被使用」的事件

### 需要修改的内容

**SRA 侧:**
| 文件 | 改动 |
|:---|:---|
| `memory.py` | 新增 `record_view()` / `record_use()` / `record_skip()` 方法 |
| | 新增 `compliance_stats` 统计结构 |
| `daemon.py` | 扩展 `POST /record` 支持 `action: "viewed"\|"used"\|"skipped"` |
| | 新增 `GET /stats/compliance` 端点 |
| `cli.py` | 新增 `sra compliance` 命令 |

**Hermes 侧（后续集成）:**
- `run_agent.py`: `skill_view()` 后触发 `POST /record {action: "viewed"}`
- 工具调用后触发 `POST /record {action: "used"}`

### 估算: 1 天

---

## Story 2: SRA-003-04 长任务上下文漂移保护

### 现状分析
- SRA 当前仅在用户消息到达时触发一次推荐
- 长任务（10+轮）中初始推荐被后续上下文「冲走」
- Hermes `run_agent.py` 已有 `run_conversation()` 循环（SRA-003-01 的 hook）

### 需要修改的内容

**SRA 侧:**
| 文件 | 改动 |
|:---|:---|
| `advisor.py` | 新增 `recheck(conversation_summary)` 方法 |
| | 返回「已推荐但未加载」的技能 + 「新匹配」的技能 |
| `daemon.py` | 新增 `POST /recheck` 端点 |

**Hermes 侧（后续集成）:**
- `run_agent.py`: `run_conversation()` 中每 N 轮调 SRA `/recheck`

### 估算: 2 天

---

## Story 3: SRA-003-14 测试覆盖增强

### 现状分析
- 当前总测试数: **103**（Sprint 1 从 39→103）
- 已有 HTTP 测试: `test_daemon_http.py`（10 个测试，覆盖 health/recommend/stats/并发）
- **仍然缺失的测试:**
  - `daemon.py` 核心类方法（`__init__`, `get_stats`, `_update_status`, `_compute_skills_checksum`, `_handle_request`）
  - `cli.py` 命令（`cmd_start`, `cmd_stop`, `cmd_recommend`, `cmd_stats`）
  - `memory.py` 场景记忆读写

### 测试计划

| 测试文件 | 覆盖内容 | 估时 |
|:---|:---|:---:|
| `tests/test_daemon.py` | SRaDDaemon 核心生命周期 + 状态管理 | 1d |
| `tests/test_cli.py` | CLI 命令（mock socket） | 0.5d |
| `tests/test_memory.py` | SceneMemory 读写 + 场景模式 | 0.5d |

### 估算: 2 天

---

## 实施顺序

```
SRA-003-03 (轨迹记录) ──→ SRA-003-04 (长任务保护) ──→ SRA-003-14 (测试覆盖)
     ↓                         ↓                          ↓
 memory.py 增强            advisor.py recheck()        test_daemon.py
 daemon.py /record 扩展     daemon.py /recheck          test_cli.py
 GET /stats/compliance      Hermes 集成                test_memory.py
```

**理由：** 先建观测能力（轨迹记录），再建保护机制（长任务漂移），最后补测试安全网

---

## 预计产出

| 指标 | Sprint 1 | Sprint 2 达成 |
|:---|:---:|:---:|
| 总测试数 | 103 | **174** |
| 新测试文件 | — | `test_memory.py`(27), `test_daemon.py`(22), `test_cli.py`(22) |
| 新端点 | `/validate` | `/recheck`, `/stats/compliance` |
| 新文件 | 6 个 | 3-4 个 |

---

## 风险

| 风险 | 可能性 | 缓解 |
|:---|:---:|:---|
| Hermes 侧集成依赖 | 高 | SRA 侧先独立完成，留下 hook 接口 |
| 测试 mock 复杂度 | 中 | daemon 测试用 `tmp_path`+`monkeypatch`，不启动真进程 |
| 长任务重注入干扰 Agent | 低 | 轻量 `[SRA]` 格式 + 可配置间隔 |
