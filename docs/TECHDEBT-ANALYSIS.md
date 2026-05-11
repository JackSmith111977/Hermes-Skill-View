# SRA 技术债与架构问题分析报告

> **分析日期:** 2026-05-11 (v2 — 合并 Sprint 2 修复进展 + 新增审计发现)
> **分析者:** Emma (小玛)
> **覆盖范围:** 全部 14 个 Python 源文件（~3,919 行 skill_advisor/）、4 个脚本、11 个测试文件（174 测试）
> **目标:** 识别并分类所有技术债，为修复规划输入

---

## TL;DR — 核心发现

| 维度 | 上次 (05-10) | 本次 (05-11) | 变化 |
|:---|:---:|:---:|:---:|
| 🔴 P0 | 3 | **3** | 旧问题已修复，新问题出现 |
| 🟡 P1 | 11 | **8** | 大幅下降 |
| 🟢 P2 | 9 | **8** | 微降 |
| **合计** | **23** | **19** | **-4** |

**Sprint 2 已修复的主要债务：**
- ✅ HTTP 服务器 `handle_request()` → `serve_forever()` (SRA-003-13)
- ✅ 16 处 `except: pass` → 仅剩 2 处 (SRA-003-13)
- ✅ daemon.py 零测试 → 3 个测试文件 (SRA-003-13/14)
- ✅ cli.py 零测试 → test_cli.py (SRA-003-14)

**本次新增发现的 7 个问题：**

| # | 问题 | 等级 |
|:---|:-----|:----:|
| 🆕 A-7 | SceneMemory / SkillIndexer 线程零保护 — 并发数据损坏 | 🔴 P0 |
| 🆕 A-8 | `os.fork()` + 线程不兼容 — 子进程锁状态未定义 | 🔴 P0 |
| 🆕 A-9 | daemon.py 937 行 = 5 种职责 — 需拆分 | 🟡 P1 |
| 🆕 T-7 | dropin.py (206 行) + adapters/__init__.py (316 行) 零测试 | 🟡 P1 |
| 🆕 D-7 | 8 处版本号过时（README/install.sh/check-sra.py/ROADMAP） | 🔴 P0 |
| 🆕 C-9 | daemon.py 类型标注仅 33%（14/21 函数无类型） | 🟡 P1 |
| 🆕 D-8 | README 命令表缺 upgrade/uninstall/dep-check | 🟡 P1 |

---

## 2. 🔴 架构层面问题

### #A1 — Daemon 单例机制缺失 (✅ 已修复 SRA-003-12)

**状态:** ⏳ `feat/v2.0-enforcement-layer` 分支中已实现 PID 检查 + FileLock

### #A2 — HTTP 服务器实现原始 (✅ 已修复 SRA-003-13)

**状态:** `handle_request()` → `serve_forever()` 已修复。当前 HTTP 服务器使用 `ThreadingMixIn` + `serve_forever()` 正确模式。

### #A3 — CLI 和 Daemon 职责耦合 🟡 **P1**

**状态:** ⚠️ 未修复。daemon.py 从 789 行增长到 937 行，但 CLI 桥接函数（`cmd_start/stop/status/restart/attach`）仍留在 daemon.py 中。

**问题：**
- `cli.py:34-37` 从 daemon.py 导入 CLI 函数
- 修改 CLI 逻辑需修改 daemon.py
- 无 IPC 抽象层

**预期修复：**
- 将 CLI 命令函数移入 `runtime/commands.py`
- daemon.py 只保留 `SRaDDaemon` 核心类
- CLI 通过 Unix Socket IPC 控制 daemon

### #A4 — 全量索引重建非增量 🟡 **P1**

**状态:** ⏳ 未修复。`build()` 每次全量扫描所有 SKILL.md。

**建议:** 推迟到技能库超过 500+ 时再优化。

### #A5 — 双协议请求处理冗余 🟡 **P1**

**状态:** ⏳ 未修复。Socket 和 HTTP 仍有两套路由逻辑。

**建议:** 可在 CLI/daemon 解耦时一并处理。

### #A6 — 配置系统不统一 🟢 **P2**

**状态:** ⏳ 未修复。

### #A7 — 🆕 线程安全 — 核心模块零锁保护 🔴 **P0**

**位置:** `memory.py`, `indexer.py`, `daemon.py:get_stats()`

**问题：**
| 位置 | 问题 | 风险 |
|:-----|:-----|:-----|
| `SceneMemory.load/save()` | 无锁，多线程并发调用争抢 `self._cache` 和文件 I/O | 🔴 数据损坏 |
| `SkillIndexer._skills` | `build()` 替换列表 + `get_skills()` 返回引用 — 并发读取不一致状态 | 🔴 推荐错误 |
| `get_stats()` | 读取 `self._stats`、`self.running`、`self.advisor.indexer` 无锁 | 🟡 脏数据 |
| `_handle_request` 锁粒度 | 锁仅覆盖计数器递增，不保护 `self.advisor.recommend()` | 🟡 计数不准 |

**影响：**
- 多线程 HTTP/Socket 并发请求下，统计计数器丢失更新
- 技能索引损坏（推荐结果不一致）
- 内存数据与文件持久化不一致

**修复建议：**
- `SceneMemory` 添加 `threading.RLock`
- `SkillIndexer` 添加 `threading.RLock` 或 copy-on-read 模式
- `get_stats()` 中加入 `with self._lock` 保护

### #A8 — 🆕 `os.fork()` + 线程不兼容 🔴 **P0**

**位置:** `daemon.py:654` (`os.fork()`)

**问题：** `cmd_start()` 使用 `os.fork()` 创建守护进程子进程。Python 中 fork() 后只有调用线程存活，其他线程中的锁状态未定义。虽然锁在 fork 后创建（安全），但 logging 模块的内部锁可能在 fork 时被其他线程持有。

**影响：** 偶发子进程启动后 logging 卡死，难以复现和调试。

**修复建议：**
- 替换为 `multiprocessing` 方式启动
- 或 fork 后立即 `logging.basicConfig` 重新初始化（已部分实现）
- 或使用 `multiprocessing.set_start_method('spawn')` 完全避免 fork

### #A9 — 🆕 daemon.py 职责过多（937 行 = 5 种职责）🟡 **P1**

**现状：** daemon.py 937 行，承载 5 类不同职责：

| 职责 | 行号范围 |
|:-----|:---------|
| SRaDDaemon 核心类 (HTTP/Socket 双服务器 + 索引 + 状态) | 93–620 |
| 模块级路径常量 + 配置加载/保存 | 41–91 |
| CLI 生命周期命令 (cmd_start/stop/status/restart/attach) | 624–838 |
| systemd 服务模板 + 安装器 | 840–937 |
| 文件校验和计算 (hashlib/md5) | 475–501 |

**影响：** 修改 CLI 影响 daemon、难以单元测试 CLI 命令、违反单一职责。

---

## 3. 🟡 代码质量问题

### #C1 — 16 处 `except: pass` 吞噬异常 (✅ 大部分已修复)

**状态：** 原 16 处中 14 处已修复（SRA-003-13），仅剩 2 处在评估脚本中：

| 文件 | 行 | 代码 | 风险 |
|:-----|:--:|:-----|:----:|
| `scripts/sra-eval.py` | 371 | `except: pass` | 🟡 吞异常 |
| `scripts/sra-eval-v2.py` | 113 | `except: pass` | 🟡 吞异常 |

### #C2 — 魔法数字 (Magic Numbers) 🟢 **P2**

**状态:** ⏳ 未修复。matcher.py 中仍有 9 个硬编码分值。

### #C3 — 类型标注不完整 🟢 **P2**

**状态:** 部分修复。整体覆盖率 72%（117/161 函数）。

### #C4 — `_match_lexical()` 过长 🟢 **P2**

**状态:** ⏳ 未修复。

### #C5 — 中英文拆词效率 🟢 **P2**

**状态:** ⏳ 未修复。

### #C6 — 并发安全不足 (✅ 已部分修复 SRA-003-13)

**状态：** `_update_status` 和 `stats` 计数器的锁保护已改善。

### #C7 — 日志系统不统一 🟡 **P1**

**状态:** ⏳ 未修复。`indexer.py`、`dropin.py`、`daemon.py` 仍混用 `print()` + `logging`。

### #C8 — 缺乏监控指标 🟢 **P2**

**状态:** ⏳ 未修复。

### #C9 — 🆕 daemon.py 类型标注仅 33% 🟡 **P1**

| 文件 | 已标注 | 总数 | 覆盖率 |
|:-----|:------:|:----:|:------:|
| `runtime/daemon.py` | 7 | 21 | **33%** 🔴 |
| `runtime/dropin.py` | 4 | 7 | 57% 🟡 |
| `runtime/lock.py` | 5 | 9 | 56% 🟡 |
| **合计** | **117** | **161** | **72%** |

---

## 4. 🟡 测试与文档问题

### #T1 — daemon.py 零测试覆盖 (✅ 已修复 SRA-003-13/14)

**状态：** 2026-05-10 的原始报告指出 daemon.py 21 个函数零测试。当前已有 `test_daemon.py`（283 行，21 个测试）、`test_daemon_http.py`（196 行，10 个测试）、`test_singleton.py`（186 行，11 个测试）。

### #T2 — cli.py 零测试覆盖 (✅ 已修复 SRA-003-14)

**状态：** 现有 `test_cli.py`（264 行）覆盖 CLI 命令。

### #T3 — 测试只针对 Fixture (🟡 **P1**)

**状态:** ⏳ 未修复。所有测试基于固定 313 个 YAML fixture，和真实环境技能库不同。

### #T4 — `test_coverage.py` 死代码 (✅ 已修复)

**状态：** 无意义自我赋值已清除。

### #T5 — 缺少集成测试 🟡 **P1**

**状态:** ⏳ 未修复。

### #T6 — 文档缺口 (✅ 已修复)

**状态：** docs/ 目录已有完整架构文档、API 参考、设计文档。

### #T7 — 🆕 2 个核心模块零测试覆盖 🟡 **P1**

| 源文件 | 行数 | 职责 | 测试 |
|:-------|:----:|:-----|:----:|
| `runtime/dropin.py` | 206 | systemd drop-in 生命周期管理 | ❌ 无 |
| `adapters/__init__.py` | 316 | 4 种 Agent 适配器 | ❌ 无 |

**修复建议：**
- `test_dropin.py`: mock 文件系统 + subprocess.run()
- `test_adapters.py`: mock socket 连接 + 验证每种 Agent 格式

---

## 5. 🟢 文档与基础设施问题

### #D1 — 🆕 版本号过时 🔴 **P0**

| 文件 | 旧值 | 应改为 | 位置 |
|:-----|:-----|:-------|:----:|
| `README.md` | `sra v1.1.0`, `275 skills` | `sra v1.2.1`, `313+ skills` | 行 356-357 |
| `scripts/install.sh` | `VERSION="v1.1.0"` | `VERSION="v1.2.1"` | 行 3,185,244,279,566 |
| `scripts/check-sra.py` | `SRA_VER="1.1.0"` | `SRA_VER="1.2.1"` | 行 3,209 |
| `ROADMAP.md` header | `v1.2.0` | `v1.2.1` | 第 4 行 |
| `docs/TEST-FRAMEWORK-DESIGN.md` | `279 skills` | `313+ skills` | — |

### #D2 — 🆕 README 命令表不完整 🟡 **P1**

**缺少命令：**
- `sra upgrade` — 已实现于 cli.py
- `sra uninstall` — 已实现于 cli.py
- `sra dep-check` — 已实现于 cli.py (SRA-003-17)

### #D3 — CHANGELOG Sprint 状态交叉不一致 🟡 **P1**

- `CHANGELOG.md [Unreleased]` 中 Sprint 1 故事状态仍标记为 `📋 pending`
- `ROADMAP.md` 中对应故事已 `✅ completed`
- 需同步

---

## 6. 📊 当前健康度评估

### 修复进展对比

```text
05-10 状态:   ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░  23 issues
05-11 状态:   ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░  19 issues (-4)
                      ↑
              已修复: HTTP架构, except:pass×14, daemon/cli测试, 死代码, 文档缺口
              新增:   线程安全, fork兼容, daemon拆分, 2模块零测试, 版本号, 类型标注
```

### 问题分布

```
架构    🔴A7,🔴A8  🟡A3,A4,A5,A9  🟢A6        = 7
代码质量           🟡C1,C7,C9     🟢C2,C3,C4,C5,C8 = 8 (C6已修复)
测试               🟡T3,T5,T7                   = 3 (T1/T2/T4已修复)
文档     🔴D1      🟡D2,D3                      = 3 (T6已修复)
                      
合计:    3🔴       8🟡            8🟢           = 19
```

---

## 7. 💡 修复计划（优先排序）

### 🏆 立即修复（当前 Sprint）

| 优先级 | 问题 | 工作量 | 收益 | Story 编号 |
|:------:|:-----|:------:|:----:|:----------:|
| 🔴 D1 | 8 处版本号同步 | 0.5h | 📐 高 | SRA-003-18 |
| 🔴 A7 | 线程安全锁保护 | 1.5h | 🛡️ 高 | SRA-003-18 |
| 🔴 A8 | fork + 线程兼容 | 1h | 🛡️ 高 | SRA-003-18 |
| 🟡 C1 | 2 处 except:pass 修复 | 0.2h | 🧹 中 | SRA-003-18 |
| 🟡 D2/D3 | README 命令表 + CHANGELOG 同步 | 0.5h | 📐 高 | SRA-003-18 |

### 📋 下个 Sprint

| 优先级 | 问题 | 工作量 | 收益 |
|:------:|:-----|:------:|:----:|
| 🟡 T7 | dropin.py + adapters 测试 | 3h | 🛡️ 高 |
| 🟡 A9 | daemon.py 职责拆分 | 2h | 🧹 中 |
| 🟡 C7 | print/logging 统一 | 1h | 🧹 中 |
| 🟡 C9 | daemon.py 类型标注补齐 | 1h | 📐 中 |
| 🟡 A3 | CLI ↔ daemon IPC 解耦 | 2h | 🧹 中 |

### ⏳ 远期

| 优先级 | 问题 | 工作量 |
|:------:|:-----|:------:|
| 🟢 A4 | 增量索引 | 4h |
| 🟡 A5 | 双协议路由统一 | 2h |
| 🟢 C2-C5 | 魔法数字/代码质量 | 2h |
| 🟢 C8 | 监控指标 | 3h |
| 🟡 T3/T5 | 集成测试 / 真实环境测试 | 4h |
