# SRA-003-19 质量修复 Sprint 2 — 计划

> **For Hermes:** 使用 subagent-driven-development 按 Task 逐个实施。
> **目标版本:** SRA v1.2.2

**Goal:** 补全 2 个零测试覆盖模块的测试 + 补齐 daemon.py 类型标注

**范围:** tests/ + skill_advisor/runtime/dropin.py + skill_advisor/adapters/ + skill_advisor/runtime/daemon.py

**前提:** git checkout feat/v2.0-enforcement-layer && git pull

**验证:** pytest tests/ -q (当前 174 passed)

---

### Task 1: dropin.py 测试 (T7 — 206 行零测试)

**Objective:** 为 systemd drop-in 生命周期管理模块添加完整测试

**Files:**
- Create: `tests/test_dropin.py`
- Reference: `skill_advisor/runtime/dropin.py`

**测试要点：**
1. `get_dropin_path()` — 返回正确的 drop-in 文件路径
2. `get_dropin_dir()` — 返回正确的目录路径
3. `get_service_path()` — 返回正确的 service 路径
4. `create_dropin()` — 创建 drop-in 文件 + daemon-reload
5. `cleanup_dropin()` — 删除 drop-in 文件 + daemon-reload
6. `check_dropin_health()` — 检查 drop-in 文件存在性和 `Wants=` 配置
7. `print_health_report()` — 输出格式化报告

**Mock 策略：** 使用 `tempfile` + `unittest.mock.patch` 模拟 `subprocess.run()` 和文件系统操作

---

### Task 2: adapters/__init__.py 测试 (T7 — 316 行零测试)

**Objective:** 为 Agent 适配器层添加完整测试

**Files:**
- Create: `tests/test_adapters.py`
- Reference: `skill_advisor/adapters/__init__.py`

**测试要点：**
1. `get_adapter("hermes")` — 返回 HermesAdapter 实例
2. `get_adapter("claude")` — 返回 ClaudeCodeAdapter 实例
3. `get_adapter("codex")` — 返回 CodexCLIAdapter 实例
4. `get_adapter("opencode")` — 返回 OpenCodeAdapter 实例
5. `get_adapter("unknown")` — 返回默认适配器或抛出异常
6. `list_adapters()` — 返回所有支持的适配器列表
7. 每种适配器的 `format_recommendation()` — 输出格式正确
8. HermesAdapter 的 socket 通信路径（mock socket）

**Mock 策略：** mock `socket.socket` 连接，使用真实 adapter 实例验证格式

---

### Task 3: daemon.py 类型标注补齐 (C9 — 14 个函数缺类型)

**Objective:** 将 daemon.py 类型标注覆盖率从 33% 提升到 ≥ 80%

**Files:**
- Modify: `skill_advisor/runtime/daemon.py`

**需要补齐的函数（14 个）：**
1. `ensure_sra_home()` → `-> None`
2. `SRaDDaemon.start()` → `-> None`
3. `SRaDDaemon.stop()` → `-> None`
4. `SRaDDaemon.attach()` → `-> None`
5. `_run_socket_server()` → `-> None`
6. `_run_http_server()` → `-> None`
7. `_auto_refresh_loop()` → `-> None`
8. `_compute_skills_checksum()` → `-> str`
9. `cmd_start()` → `-> None`
10. `cmd_stop()` → `-> None`
11. `cmd_status()` → `-> None`
12. `cmd_restart()` → `-> None`
13. `cmd_attach()` → `-> None`
14. `cmd_install_service()` → `-> None`

**注意：** 不改逻辑，只加类型标注
