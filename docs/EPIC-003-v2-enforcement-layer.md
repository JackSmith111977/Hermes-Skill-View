# EPIC-003: SRA v2.0 — 从技能推荐者到运行时守护者

> **Epic ID:** SRA-EPIC-003
> **状态:** ✅ 全部完成 (v2.0.0)
> **目标版本:** SRA v2.0.0
> **创建日期:** 2026-05-09
> **完成日期:** 2026-05-11
> **分析者:** Emma (小玛)
> **测试数据契约:**
>   - source: tests/fixtures/skills (317 个真实技能)
>   - ci_independent: true
>   - pattern_reference: test_matcher.py::TestAdvisor

---

## 🎯 Epic 概述

当前 SRA 是**被动推荐者**（passive recommender）：在消息到达前注入一段文本建议，Agent 可以自由选择忽略。**v2.0** 将其升级为**运行时守护者**（runtime guardian）：在 Agent 执行关键工具调用时主动校验技能遵循度，并支持长任务上下文保持。

### 核心转变

```
v1.x: SRA ──→ [建议文本] ──→ Agent 可选择忽略
                              ↑ 
                         没有强制力

v2.0: SRA ──→ [建议] + [运行时校验] + [漂移保护]
                              ↑
                   pre_tool_call hook 拦截点
```

### 关键洞察

在 Hermes 的 `model_tools.py` **第 722-737 行**，已经存在 `pre_tool_call` 插件钩子系统：

```python
# 已有基础设施！无需改 core loop
block_message = get_pre_tool_call_block_message(function_name, function_args, ...)
if block_message is not None:
    return json.dumps({"error": block_message})  # 阻断工具执行！
```

这意味着 SRA 校验可以**零侵入**地插入到现有钩子系统中。

---

## 📦 用户故事 (Stories)

### Story 1: 工具执行前的 SRA 校验

> **作为** Hermes Agent 的运行环境
> **我希望** 在 Agent 调用 `write_file` / `patch` / `terminal` / `execute_code` 前，自动校验是否已加载对应技能
> **以便** 防止 Agent 因忘记加载技能而产出低质量结果

**验收标准:**
- [x] SRA Daemon 新增 `POST /validate` 端点
- [x] 端点接收 `{tool, args, loaded_skills[], task_context}` 参数
- [x] 端点返回 `{compliant: bool, missing: [], severity: "info"|"warning"|"block"}`
- [x] Hermes pre_tool_call hook 集成
- [x] 非阻塞设计：SRA 不可用时优雅降级（不影响工具执行）

**实现文件:**
- 新增: `sra-latest/skill_advisor/runtime/endpoints/validate.py`
- 新增: `sra-latest/plugins/sra-guard/plugin.py`
- 修改: `sra-latest/skill_advisor/runtime/daemon.py`
- 修改: `hermes-agent/tools/skills_guard.py` 或 `hermes-agent/model_tools.py`

---

### Story 2: 文件类型到技能的映射注册表

> **作为** SRA 校验引擎
> **我希望** 能够根据文件扩展名自动推导所需的技能列表
> **以便** `write_file` 时校验不依赖于任务上下文的语义理解，直接通过扩展名映射

**验收标准:**
- [x] 创建 `FILE_SKILL_MAP` 映射表（`.html` → html-presentation, `.md` → markdown-guide, 等）
- [ ] 映射表作为配置文件，支持用户自定义扩展
- [ ] 在 `/validate` 端点中集成文件类型检查
- [ ] 映射表覆盖率：覆盖 Hermes 中所有常见产出文件类型

**实现文件:**
- 新增: `sra-latest/skill_advisor/skill_map.py`
- 新增: `sra-latest/skill_advisor/config/skill_map.json`（默认配置）

---

### Story 3: 技能使用轨迹记录

> **作为** SRA 系统
> **我希望** 追踪 Agent 的技能加载和实际使用情况
> **以便** 检测「已加载但未使用」和「未加载却被需要」两种模式

**验收标准:**
- [x] 增强 `POST /record` 端点，支持 `action: "viewed"|"used"|"skipped"` 类型
- [ ] Hermes `skill_view()` 调用后自动触发 `POST /record {action: "viewed"}`
- [ ] Hermes 工具调用后自动触发 `POST /record {action: "used"}`
- [x] SRA 场景记忆记录技能使用序列
- [x] 提供 `GET /stats/compliance` 查看历史遵循率

**实现文件:**
- 修改: `sra-latest/skill_advisor/runtime/daemon.py`
- 修改: `sra-latest/skill_advisor/memory.py`
- 修改: `hermes-agent/run_agent.py`（`skill_view` 拦截）

---

### Story 4: 长任务上下文漂移保护

> **作为** 执行长任务（> 10 轮对话）的 Agent
> **我希望** SRA 在任务执行过程中定期重注入技能建议
> **以便** 初始的 SRA 推荐不会因上下文增长而被「冲走」

**验收标准:**
- [x] Hermes run_agent.py 每 5 轮对话自动重查询 SRA
- [x] 重查询基于**当前对话摘要**而非原始用户消息
- [x] SRA 返回「需要提醒」的未使用技能列表
- [x] 提醒以轻量级 `[SRA 提醒]` 格式注入，不干扰当前任务
- [ ] 可配置提醒间隔（默认 5 轮）

**实现文件:**
- 修改: `hermes-agent/run_agent.py`（`run_conversation()` 中重注入逻辑）
- 修改: `sra-latest/skill_advisor/advisor.py`（新增 `recheck()` 方法）

---

### Story 5: SRA 契约机制 ✅ _v1.3.0_

> **作为** 系统管理员
> **我希望** 在任务开始时 SRA 自动生成一个「技能契约」
> **以便** Agent 明确知道当前任务类型下哪些技能是强烈推荐的

**验收标准:**
- [x] SRA 在 `POST /recommend` 返回中加入 `contract` 字段
- [x] 契约包含 `{task_type, required_skills[], optional_skills[], confidence}`
- [x] 契约信息格式化到 `rag_context` 中
- [ ] Agent 在 SOUL.md 规则下被要求遵守契约
- [ ] 契约内容在 `/validate` 校验时作为上下文参考

**实现文件:**
- 修改: `sra-latest/skill_advisor/runtime/daemon.py`（`POST /recommend` 响应增强）
- 修改: `sra-latest/skill_advisor/advisor.py`（新增 `build_contract()` 方法）

---

### Story 6: 运行时力度体系 ✅ _v1.3.0_

> **作为** 在不同场景下使用 Hermes 的用户
> **我希望** SRA 的运行时力度通过注入点的多少来控制
> **以便** 最轻量只拦截用户消息注入推荐，最重量在所有钩子+周期性注入

**核心设计理念**：SRA **永不阻断**（no blocking）。强度只决定 **SRA 在哪些时机注入推荐上下文**。力度越高，注入点越多、注入频率越高。

```
力度不是「阻断强度」，而是「注入覆盖度」：
                       
     用户消息    工具调用前    工具调用后    周期性注入
       ↓           ↓           ↓           ↓
L1 🐣  ●                                    
L2 🦅  ●           ●                        
L3 🦖  ●           ●           ●            
L4 🐉  ●           ●           ●           ●
```

**4 个注入层级**：

| 层级 | 名称 | 注入点 | 行为描述 |
|:----:|:-----|:-------|:---------|
| 🐣 **L1 — basic** | 消息级注入 | 用户消息到达时 | 当前 v1 行为：`POST /recommend` 注入 rag_context |
| 🦅 **L2 — medium** | 消息+关键工具钩子 | 用户消息 + pre_tool_call (write_file/patch/terminal/execute_code) | 关键工具调用前检查是否已加载对应 skill，未加载时注入 `[SRA 推荐]` 到助手回复 |
| 🦖 **L3 — advanced** | 消息+全工具钩子+后检 | 用户消息 + pre_tool_call (全部工具) + post_tool_call | 全部工具调用前检查+调用后核查 skill 是否被遵守，未遵守时注入提醒 |
| 🐉 **L4 — omni** | 全钩子+频率注入 | 全部 L3 注入点 + 每 N 轮对话周期性重注入 | 在 L3 基础上，每 5 轮对话自动重查询 SRA 并注入最新推荐，防止上下文漂移 |

**各层级注入点详情**：

```yaml
# ~/.sra/config.json
{
  "runtime_force": {
    "level": "medium",          # basic / medium / advanced / omni
    
    # 各层级自动展开为以下配置（用户无需手动修改）：
    # "injection_points": {
    #   "on_user_message": true,           # L1 起
    #   "pre_tool_call": ["write_file", "patch", "terminal", "execute_code"],  # L2 起
    #   "post_tool_call": true,            # L3 起
    #   "periodic_injection": {            # L4 起
    #     "interval_rounds": 5,
    #     "strategy": "conversation_summary"
    #   }
    # }
  }
}
```

**各层级对比**：

| 特性 | 🐣 basic | 🦅 medium | 🦖 advanced | 🐉 omni |
|:-----|:--------:|:---------:|:-----------:|:-------:|
| 用户消息时推荐注入 | ✅ | ✅ | ✅ | ✅ |
| 关键工具调用前检查+注入 | — | ✅ | ✅ | ✅ |
| 全部工具调用前检查+注入 | — | — | ✅ | ✅ |
| 工具调用后核查遵守度 | — | — | ✅ | ✅ |
| 周期性重注入防漂移 | — | — | — | ✅ |
| 额外 Token 开销 | ~100 | ~300 | ~500 | ~800 |
| 适用场景 | 尝鲜体验 | 日常开发 | 质量敏感 | 长任务/合规 |

**没有阻断**：任何层级都不阻断工具执行。SRA 只负责在适当时机注入「主人，boku 觉得你可能需要 XX skill」这类建议，让 Agent 自主决定是否采纳。

**验收标准:**
- [x] 4 级注入覆盖度体系：basic / medium / advanced / omni
- [x] 每级严格定义对应的注入点集合（非简单线性递增）
- [x] `~/.sra/config.json` 中 `runtime_force.level` 配置
- [ ] Hermes `~/.hermes/config.yaml` 可覆盖
- [x] 默认级别为 `medium`
- [x] `sra config set runtime_force.level advanced` CLI 命令
- [x] 所有注入点均为非阻塞（info/warning 级别，无 block）
- [x] L4 的周期性注入间隔可配置（默认 5 轮）
- [x] 编写测试用例验证各层级注入点启停

**实现文件:**
- 新增: `sra-latest/skill_advisor/runtime/force.py`（力度引擎+注入点路由）
- 修改: `sra-latest/skill_advisor/runtime/daemon.py`（按力度级别条件启用端点）
- 修改: `sra-latest/skill_advisor/cli.py`（`sra config` 命令）
- 修改: `sra-latest/skill_advisor/advisor.py`（周期性重注入 recheck 方法）
- 新增: `tests/test_force.py`

---

### Story 7: SOUL.md Context Compaction 保护

> **作为** Hermes Agent
> **我希望** SRA 校验规则在上下文压缩时不被裁剪
> **以便** 即使在长对话压缩后，SRA 强制规则仍然生效

**验收标准:**
- [ ] SOUL.md 中新增 `🛡️ SRA Skill 遵循规则（受压缩保护）` 段
- [ ] 压缩保护标记 `protect_first_n` 包含该段
- [ ] AGENTS.md 中明确 SRA 校验流程
- [ ] pre_flight.py 在任务启动时检查 SRA 契约是否存在

**实现文件:**
- 修改: `~/.hermes/SOUL.md`
- 修改: `~/.hermes/AGENTS.md`

---

### Story 8: 遵循率仪表盘

> **作为** SRA 管理员
> **我希望** 能看到 SRA 推荐的技能被 Agent 实际遵循的比例
> **以便** 评估 SRA 推荐质量和校验机制的有效性

**验收标准:**
- [ ] `GET /stats/compliance` 返回遵循率统计
- [ ] 统计维度：整体遵循率、按 skill 维度、按任务类型维度
- [ ] `sra compliance` CLI 命令
- [ ] 数据来源：`POST /record` 积累的历史轨迹

**实现文件:**
- 新增: `sra-latest/skill_advisor/runtime/endpoints/stats.py`
- 修改: `sra-latest/skill_advisor/cli.py`
- 修改: `sra-latest/skill_advisor/memory.py`

---

### Story 9: 推荐质量反馈闭环

> **作为** SRA 推荐引擎
> **我希望** 能根据 Agent 的实际技能使用情况自动调整推荐权重
> **以便** 高频使用的技能获得更高推荐优先级，低频/无用推荐逐渐降权

**验收标准:**
- [ ] 场景记忆记录每次推荐是否被采纳
- [ ] 采纳率影响 `matcher.py` 中的权重计算
- [ ] 负反馈（明确忽略高推荐技能）记录并用于降权
- [ ] 效果可通过 `GET /stats/recommendation` 查看

**实现文件:**
- 修改: `sra-latest/skill_advisor/matcher.py`
- 修改: `sra-latest/skill_advisor/memory.py`
- 修改: `sra-latest/skill_advisor/advisor.py`

---

### Story 10: SRA 用户级 systemd 服务自启动 (SRA-003-10)

> **作为** 服务器管理员
> **我希望** SRA Daemon 随 Hermes Gateway 自动启动，无需手动干预
> **以便** 系统重启后 SRA 自动恢复，保持技能推荐服务的持续可用

**验收标准:**
- [x] 创建 `~/.config/systemd/user/srad.service` — 用户级 systemd 服务单元
- [x] 服务使用 `Type=simple` + `sra attach` 前台运行模式
- [x] 服务设置 `Restart=on-failure`，崩溃后自动重启
- [x] 在 `hermes-gateway.service` 中添加 `Wants=srad.service` + `After=srad.service`（用 `Wants=` 而非 `Requires=` — 软依赖，SRA 不存在时不阻塞 Gateway 启动）
- [x] `systemctl --user enable srad` 后用户登录自动启动
- [x] SRA 在 Gateway 之前就绪，首次消息即有技能推荐
- [x] 支持独立 `start/stop/restart/status` 管理

**实现文件:**
- 新增: `~/.config/systemd/user/srad.service`
- 新增: `~/.config/systemd/user/hermes-gateway.service.d/sra-dep.conf`
- 修改: `docs/ROADMAP.md`（添加 Sprint 条目）

---

### Story 11: 安装脚本自动配置 — 跨平台自启方案 (SRA-003-11)

> **作为** 在任何 Linux/macOS/Docker 机器上部署 SRA 的 AI Agent
> **我希望** 运行 `bash install.sh --systemd` 后脚本自动检测我的系统并配置自启
> **以便** 我不需要手动处理 systemd/launchd 等差异，一条命令完成全流程安装

**背景:** Story 10 (SRA-003-10) 已在当前服务器上手动完成 systemd 配置。但项目要求**所有 Agent 通过阅读 README 就能自主安装**，因此需要将配置能力内置到 `install.sh` 中。

**设计原则:**
1. **不要"移植"文件** — 不要将 systemd 文件作为静态文件放入仓库
2. **生成而非复制** — 安装脚本根据检测到的宿主系统自动生成适配的配置
3. **每步必有验证** — 每个步骤后自动运行 `check-sra.py` 确认

**验收标准:**
- [x] 系统检测模块：`install.sh` 在安装前自动检测 OS 类型、init 系统、sudo 权限
- [x] Linux + systemd + 有 sudo → 安装系统级 service (`/etc/systemd/system/`)
- [x] Linux + systemd + 无 sudo → 安装用户级 service (`~/.config/systemd/user/`)
- [x] Linux + systemd + 无 sudo + Hermes Gateway 检测到 → 自动配置 gateway 依赖
- [x] macOS → 生成 launchd plist (`~/Library/LaunchAgents/`)
- [x] WSL → 生成入口脚本 + 提示 WSL 自启方式
- [x] Docker → 生成入口脚本 + 提示 docker run 的 `--restart` 用法
- [x] 其他系统 → 提示手动配置 + 给出文档链接
- [x] 安装后自动运行 `check-sra.py` 验证自启配置是否生效
- [x] 所有路径使用 `$HOME` 等变量（跨用户兼容）

**实现文件:**
- 修改: `scripts/install.sh`（系统检测 + 多路径自启配置）
- 修改: `skill_advisor/runtime/daemon.py`（`cmd_install_service` 增加 `--user` 标志）
- 修改: `scripts/check-sra.py`（增加自启配置检测项）
- 修改: `README.md`（更新安装说明，展示多平台支持）

---

### Story 12: Daemon 单例守护 — 防多实例冲突 (SRA-003-12)

> **作为** SRA 守护进程
> **我希望** 在任何时刻最多只有一个 SRA Daemon 实例在运行
> **以便** 防止端口冲突、状态文件损坏和资源竞争

**问题背景：** 当前 `cmd_start` 通过 PID 文件做单例检查，但存在竞态条件（fork 前检查 → 无原子锁 → 两个 `start` 可同时通过）。且 `cmd_attach`（systemd 前台模式）完全不检查 PID 文件。实际运行已观察到 **3 个 SRA 实例同时运行**，争抢端口 8536。

**根因分析：**

| # | 漏洞 | 场景 | 严重程度 |
|:---|:---|:---|:---:|
| 1 | PID 检查无原子锁 | `sra start` 两次快速调用 | 🔴 竞态 → 多实例 |
| 2 | `cmd_attach` 无 PID 检查 | systemd `sra attach` 调用 | 🔴 无条件多重启动 |
| 3 | 端口级无保护 | HTTP 端口被前一个残骸占用 | 🟡 启动失败无声 |
| 4 | `_update_status` 无归属验证 | 多个实例同时写 status.json | 🟡 状态文件损坏 |

**验收标准：**
- [ ] **OS 级文件锁**: `~/.sra/srad.lock` 使用 `fcntl.flock` 实现原子性获取，防止竞态条件
- [ ] `cmd_start` 启动前先尝试获取文件锁，获取失败则打印「SRA Daemon 已在运行 (PID: xxx)」并优雅退出
- [ ] `cmd_attach` 启动前同样检查文件锁，systemd 模式下也不会启动重复实例
- [ ] **端口活性探测**: 绑定 HTTP 前检查 `0.0.0.0:{port}` 是否已被占用（`SO_REUSEADDR` 开启前先 `socket.connect` 探测）
- [ ] **锁自动释放**: 进程异常退出时 lock 文件自动释放（`atexit` + `signal.SIGTERM/SIGINT` 处理器），无需手动清理
- [ ] **状态文件归属验证**: `_update_status` 写入时验证当前 PID 是否为 lock 持有者，防止交叉写入
- [ ] **优雅降级**: 检测到已有实例时新进程以 `exit code 0` 退出并打印可读信息，不抛 `RuntimeError`
- [ ] **守护目录锁**: 在 `cmd_start` fork 之前获取锁，确保 fork 前后一致性
- [ ] **测试用例**: 并发 `sra start` 场景、systemd `attach` 重复启动场景、端口冲突场景的集成测试
- [ ] **文档补充**: 在 `sra start`/`sra attach` 的 `--help` 中说明单例机制

**实现文件：**
- 修改: `sra-latest/skill_advisor/runtime/daemon.py`
  - `cmd_start()`: fork 前先获取文件锁
  - `cmd_attach()`: 启动前检查文件锁
  - `SRaDDaemon.start()`: HTTP 绑定前做端口活性探测
  - 新增 `_acquire_lock()` / `_release_lock()` 辅助方法
- 新增: `sra-latest/skill_advisor/runtime/lock.py`（文件锁 + 端口探测工具函数）
- 新增: `tests/test_singleton.py`
- 修改: `sra-latest/skill_advisor/cli.py`（`--help` 补充单例说明）

---

### Story 17: Drop-in 依赖生命周期管理 — 防止孤儿配置 (SRA-003-17)

> **作为** SRA 系统管理员
> **我希望** 在 SRA 卸载/迁移时自动清理 `hermes-gateway.service.d/sra-dep.conf`
> **以便** 避免 Gateway 因孤儿依赖配置而启动失败

**背景：** 2026-05-11 实际测试发现 `sra uninstall --all` 后 `sra-dep.conf` 仍然残留在 `~/.config/systemd/user/hermes-gateway.service.d/` 中，成为孤儿配置。虽然当前使用 `Wants=` 不会导致 Gateway 崩溃，但残留文件会造成用户困惑和配置污染。

**验收标准:**
- [x] `sra uninstall` 和 `sra uninstall --all` 自动清理 `sra-dep.conf`，输出明确提示 "已清理 Gateway 依赖配置"
- [ ] `sra uninstall` 清理后 `sra-dep.conf` 文件物理删除（`ls -la ~/.config/systemd/user/hermes-gateway.service.d/sra-dep.conf` 返回 `No such file`）
- [ ] `install.sh` 新增 `--uninstall` 分支，执行相同的清理逻辑
- [x] `check-sra.py` 新增检查：`sra-dep.conf` 中存在 `Requires=` 时报警（应使用 `Wants=`）
- [ ] `check-sra.py` 新增检查：`sra-dep.conf` 存在但 `srad.service` 不存在时报错
- [x] `sra dep-check` CLI 命令可视化 SRA 依赖链健康度
- [ ] 跨平台兼容：macOS launchd 无此问题（无 drop-in 概念），仅 Linux systemd 需要

**实现文件:**
- 修改: `skill_advisor/cli.py` — `cmd_uninstall()` 函数末尾添加 `_cleanup_gateway_dropin()` 调用
- 修改: `scripts/install.sh` — 新增 `--uninstall` 分支清理 drop-in
- 修改: `scripts/check-sra.py` — 新增 drop-in 健康检查项（`check_dropin`）
- 新增: `skill_advisor/runtime/dropin.py` — Gateway 依赖 drop-in 管理工具函数
- 修改: `README.md` — 文档同步

---

### 🧹 技术债修复 Stories

以下 4 个 Story 基于 [`docs/TECHDEBT-ANALYSIS.md`](./TECHDEBT-ANALYSIS.md) 的全面分析，覆盖 **23 个已识别问题**中优先级最高的项目。

---

### Story 13: 紧急修复 — HTTP 架构 + 异常处理 (SRA-003-13)

> **作为** SRA 守护进程的维护者
> **我希望** 修复 HTTP 服务器的线程模型问题并消除所有被静默吞噬的异常
> **以便** 保障多请求并发能力，以及致命错误不被隐藏

**问题背景：** 
1. HTTP 服务器使用 `handle_request()` 而非 `serve_forever()`，`ThreadingMixIn` 不生效，无法真正并发处理请求
2. 全库 16 处 `except: pass` 隐藏真实错误，导致故障难以排查

**验收标准：**
- [ ] HTTP 服务器改用 `serve_forever()`，配合 `server.timeout` 实现可中断循环
- [ ] 或采用 `select.poll()` 实现非阻塞事件循环
- [ ] 所有 `except: pass` 升级为 `logger.warning()` / `logger.error()`（至少记录异常消息）
- [ ] 关键路径（YAML 解析、配置加载、状态写入）的异常向上传播而非静默忽略
- [ ] `SUPPRESSED_EXCEPTIONS` 白名单机制：明确标记哪些异常允许静默（如 `socket.timeout`）
- [ ] 编写异常处理单元测试：验证不同异常场景不会静默吞没

**实现文件：**
- 修改: `skill_advisor/runtime/daemon.py`（`_run_http_server` 重构 + 所有 `except:` 增强）
- 修改: `skill_advisor/indexer.py`（`except:` 增强）
- 修改: `skill_advisor/memory.py`（`except:` 增强）
- 修改: `skill_advisor/cli.py`（`except:` 增强）
- 新增: `tests/test_daemon_http.py`

---

### Story 14: 测试覆盖 — 守护进程 + CLI (SRA-003-14)

> **作为** SRA 开发团队
> **我希望** 为 daemon.py（21 个函数）和 cli.py（700+ 行）增加自动化测试
> **以便** 核心守护进程的任何修改都能自动验证，防止回归

**问题背景：** daemon.py 和 cli.py 合计 ~1,500 行代码，测试覆盖率为 0%。当前所有测试（4 个测试文件）只覆盖 `indexer` 和 `matcher` 模块。

**验收标准：**
- [ ] daemon 核心类测试：
  - [ ] `SRaDDaemon.__init__()` — 配置合并、目录创建
  - [ ] `SRaDDaemon.start()` / `stop()` — 生命周期管理
  - [ ] `get_stats()` — 统计数据正确性
  - [ ] `_compute_skills_checksum()` — 校验和一致性（相同输入 → 相同输出）
  - [ ] `_update_status()` — 状态文件写入
  - [ ] `_handle_request()` — 各 action 分派
- [ ] CLI 命令测试（通过 `_socket_request` mock）：
  - [ ] `cmd_recommend()` — 有结果/无结果
  - [ ] `cmd_stats()` — daemon 模式/本地模式
  - [ ] `cmd_start()` — PID 文件创建/清理
  - [ ] `cmd_stop()` — 信号发送/PID 清理
  - [ ] `cmd_restart()` — 完整生命周期
- [ ] HTTP API 集成测试（启动临时 server）：
  - [ ] `GET /health` 返回 200
  - [ ] `POST /recommend` 返回推荐结果
  - [ ] `POST /refresh` 返回索引数
- [ ] 所有测试使用 `tmp_path` fixture，不污染真实环境
- [ ] 测试门禁：daemon 核心函数覆盖率 ≥ 60%

**实现文件：**
- 新增: `tests/test_daemon.py`
- 新增: `tests/test_cli.py`
- 新增: `tests/test_api_integration.py`

---

### Story 15: 质量增强 — 配置验证 + 日志统一 + 魔法数字 (SRA-003-15)

> **作为** SRA 系统管理员
> **我希望** 配置文件有 schema 验证、日志系统统一输出、匹配分值有命名常量
> **以便** 减少配置错误、提高可调试性、降低维护成本

**验收标准：**
- [ ] 配置系统：
  - [ ] 新增 `~/.sra/config.schema.json` 定义配置 schema
  - [ ] 启动时自动校验配置合法性，非法字段打印警告
  - [ ] `sra config validate` CLI 子命令
  - [ ] 环境变量覆盖支持：`SRA_HTTP_PORT`, `SRA_LOG_LEVEL` 等
- [ ] 日志系统：
  - [ ] cli.py 改用 `logging` 统一输出
  - [ ] 新增日志轮转（`RotatingFileHandler`, max 10MB × 5 份）
  - [ ] DEBUG 级别日志覆盖核心路径（建索引、同义词匹配、请求处理）
  - [ ] daemon 日志格式统一为 `[时间] [级别] [模块] 消息`
- [ ] Matcher 魔法数字提取：
  - [ ] 所有 14 个硬编码分值提取为 `MatchWeight` 命名空间常量
  - [ ] `_match_lexical` 函数拆分为 3 个子函数（`_score_name`, `_score_triggers`, `_score_description`）
  - [ ] `reasons` 去重改用 `set` 而非 `str(reasons)` 字符串匹配

**实现文件：**
- 修改: `skill_advisor/runtime/daemon.py`（配置验证 + 环境变量）
- 新增: `~/.sra/config.schema.json`
- 修改: `skill_advisor/cli.py`（日志统一 + `sra config validate`)
- 修改: `skill_advisor/matcher.py`（魔法数字命名化 + 函数拆分）
- 新增: `tests/test_config.py`

---

### Story 16: 架构优化 — 并发安全 + 路由统一 (SRA-003-16)

> **作为** SRA 守护进程
> **我希望** 多线程场景下状态一致、请求路由统一
> **以便** 在高并发下不丢失数据、新增端点只需修改一处

**问题背景：** `_update_status` 无锁写入、`memory.py` 的 load/save 非线程安全、双协议路由重复

**验收标准：**
- [ ] 并发安全：
  - [ ] `_update_status()` 加锁保护（复用 `self._lock`）
  - [ ] `memory.py` 的 `save()` 增加文件锁（`fcntl.flock`），防止多实例交叉写入
  - [ ] `_last_refresh` 读写原子化（`threading.Lock` 或 `atomic` 操作）
  - [ ] 所有 `self._stats` 的更新统一通过 `self._lock` 保护
- [ ] 路由统一：
  - [ ] 提取 `ROUTER = {"recommend": ..., "record": ..., "refresh": ...}` 路由表
  - [ ] Socket `/action` 和 HTTP `POST /{action}` 共用同一路由
  - [ ] 新增端点在路由表中注册即可，无需修改两处

**实现文件：**
- 修改: `skill_advisor/runtime/daemon.py`（并发安全 + 路由统一）
- 修改: `skill_advisor/memory.py`（文件锁）
- 新增: `tests/test_concurrency.py`
- 修改: `tests/test_daemon.py`（路由测试）

## 🏗️ 架构变更

### v2.0 运行时架构

```
用户消息
   │
   ▼
┌─────────────────────────────────────────────────────┐
│  Layer 1: Pre-message 技能推荐 (已有)                │
│  ┌───────────────────────────────────────────────┐  │
│  │  SRA POST /recommend → [SRA] 上下文注入       │  │
│  │  + 契约字段 (Story 5)                         │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  Layer 2: Pre-tool 校验 (Story 1, 2, 6)【新增】     │
│  ┌───────────────────────────────────────────────┐  │
│  │  pre_tool_call hook → SRA POST /validate      │  │
│  │     ├─ compliant=true → 放行                   │  │
│  │     ├─ warning → 提醒 + Agent 可继续           │  │
│  │     └─ blocked → 阻断工具调用                  │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  Layer 3: 运行时上下文保持 (Story 4)【新增】         │
│  ┌───────────────────────────────────────────────┐  │
│  │  每 5 轮对话 → SRA recheck                    │  │
│  │  → 检测已推荐但未加载的技能                    │  │
│  │  → [SRA 提醒] 轻量注入                        │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  Layer 4: 反馈闭环 (Story 3, 8, 9)【新增】          │
│  ┌───────────────────────────────────────────────┐  │
│  │  skill_view → POST /record {action: "viewed"} │  │
│  │  工具调用   → POST /record {action: "used"}   │  │
│  │  场景记忆自动调整推荐权重                       │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 新增模块

```
sra-latest/
├── skill_advisor/
│   ├── runtime/
│   │   ├── daemon.py              # 已有：守护进程
│   │   ├── endpoints/
│   │   │   ├── validate.py         # [NEW] POST /validate
│   │   │   └── stats.py            # [NEW] GET /stats/compliance
│   ├── skill_map.py                # [NEW] FILE_SKILL_MAP + 配置加载
│   ├── config/
│   │   └── skill_map.json          # [NEW] 默认文件→技能映射表
│   ├── advisor.py                  # 修改：新增 build_contract()/recheck()
│   ├── matcher.py                  # 修改：采纳率权重调整
│   └── memory.py                   # 修改：遵循率记录、轨迹追踪
└── plugins/
    └── sra-guard/
        └── plugin.py               # [NEW] Hermes pre_tool_call hook 插件
```

---

## 📐 关键设计决策

### 决策 1：为什么不硬阻断？

| 选项 | 优点 | 缺点 | 决策 |
|:---|:---|:---|:---:|
| 硬阻断（返回 error 阻止工具） | 强制遵循 | 误报损伤体验、破坏自主性 | ❌ |
| 仅提醒（注入文本不阻止） | 安全、零误报 | 可忽略、和现有方案重复 | ❌ |
| **可配置严格度** | 灵活、适配多场景 | 实现复杂度中等 | ✅ |

### 决策 2：SRA 校验是同步还是异步？

| 选项 | 优点 | 缺点 | 决策 |
|:---|:---|:---|:---:|
| 同步（等待 SRA 返回再执行） | 实时校验 | 增加工具调用延迟 ~50ms | ✅ 默认 |
| 异步（SRA 校验不阻塞） | 零延迟 | 校验结果到达时工具已执行 | ❌ |

**降级策略**：SRA 超时（默认 200ms）时自动跳过校验，不阻塞工具执行。

### 决策 3：校验知识存在哪里？

| 选项 | 优点 | 缺点 | 决策 |
|:---|:---|:---|:---|
| SRA 仅基于当前推荐 | 简单 | 无状态、无历史 | ❌ |
| **SRA 维护 session 级别状态** | 可追踪已加载/已使用 | 需要 session ID 传递 | ✅ |
| 完全由 Hermes 维护 | 去中心化 | 重复实现 | ❌ |

---

## 📋 验收总表

| Story | ID | 优先级 | 估时 | 依赖 |
|:---|:---:|:---:|:---:|:---:|
| 工具执行前 SRA 校验 | SRA-003-01 | 🔴 P0 | 2d | SRA `/validate` + Hermes hook |
| 文件类型技能映射 | SRA-003-02 | 🔴 P0 | 1d | 无 |
| 技能使用轨迹记录 | SRA-003-03 | 🟡 P1 | 1d | SRA-003-01 |
| 长任务上下文保护 | SRA-003-04 | 🟡 P1 | 2d | SRA-003-01 |
| SRA 契约机制 | SRA-003-05 | 🟡 P1 | 1d | 无 |
| 可配置严格度 | SRA-003-06 | 🟢 P2 | 0.5d | SRA-003-01 |
| 压缩保护 | SRA-003-07 | 🟢 P2 | 0.5d | 无 |
| 遵循率仪表盘 | SRA-003-08 | 🟢 P2 | 1d | SRA-003-03 |
| 推荐质量反馈闭环 | SRA-003-09 | 🟢 P2 | 2d | SRA-003-03 |
| systemd 自启动部署 | SRA-003-10 | 🟢 P2 | 0.5d | 无 |
| 安装脚本自动配置 | SRA-003-11 | 🟡 P1 | 1d | SRA-003-10 |
| **Daemon 单例守护** | **SRA-003-12** | **🔴 P0** | **0.5d** | **无** |
| **HTTP 架构 + 异常处理** | **SRA-003-13** | **🔴 P0** | **1d** | **无** |
| **测试覆盖增强** | **SRA-003-14** | **🟡 P1** | **2d** | **SRA-003-13** |
| **配置验证 + 日志 + 魔法数字** | **SRA-003-15** | **🟡 P1** | **1d** | **无** |
| **并发安全 + 路由统一** | **SRA-003-16** | **🟢 P2** | **1d** | **SRA-003-13** |

**优先级说明：**
- 🔴 P0 — 核心功能，必须完成才能发布 v2.0
- 🟡 P1 — 重要增强，建议在 v2.0 中包含
- 🟢 P2 — 锦上添花，可在 v2.1 中发布

---

## 🚀 发布计划

### v2.0.0-alpha (Phase 1: 核心校验 + 基础加固)

| Sprint | Stories | 目标 |
|:---|:---|:---|
| Sprint 1 | SRA-003-01 + SRA-003-02 + **SRA-003-12** + **SRA-003-13** | 完成 `POST /validate` + FILE_SKILL_MAP + **单例守护** + **HTTP/异常修复**，Hermes hook 集成 |
| Sprint 2 | SRA-003-03 + SRA-003-04 + **SRA-003-14** | 完成轨迹记录 + 长任务保护 + **测试覆盖增强** |
| Sprint 3 | SRA-003-05 + SRA-003-06 + SRA-003-07 + **SRA-003-15** | 契约机制 + 严格度 + 压缩保护 + **配置/日志/魔法数字** |

### v2.1.0 (Phase 2: 智能优化 + 架构优化)

| Sprint | Stories | 目标 |
|:---|:---|:---|
| Sprint 4 | SRA-003-08 + SRA-003-09 | 仪表盘 + 反馈闭环 |
| Sprint 5 | SRA-003-16 | 并发安全 + 路由统一 |

---

## ⚠️ 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|:---|:---:|:---:|:---|
| `/validate` 增加工具延迟 | 中 | 低 | 200ms 超时 + 降级 |
| FILE_SKILL_MAP 不完整导致误报 | 中 | 低 | 可配置 + Agent 可忽略提醒 |
| pre_tool_call hook 修改影响多个 Agent | 低 | 中 | 只监控 MONITORED_TOOLS 白名单 |
| 长任务重注入干扰 Agent 上下文 | 低 | 低 | 间隔可配置 + 轻量提醒格式 |
| 现有测试需要适配新端点 | 高 | 低 | 按 L0-L4 分级测试 |

---

## 🔗 关联文档

- [RUNTIME.md](../RUNTIME.md) — 运行时架构
- [ROADMAP.md](../ROADMAP.md) — 开发路线图
- [EPIC-001: Hermes 原生集成](./EPIC-001-hermes-integration.md) — v1.1.0
- [EPIC-002: P0 质量提升](./EPIC-002-p0-analysis-and-fix.md) — v1.2.0
- [CHANGELOG.md](../CHANGELOG.md) — 版本历史
