# EPIC-003: SRA v2.0 — 从技能推荐者到运行时守护者

> **Epic ID:** SRA-EPIC-003
> **状态:** 📋 planning
> **目标版本:** SRA v2.0.0 (+ Hermes 集成 v2.0)
> **创建日期:** 2026-05-09
> **分析者:** Emma (小玛)

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
- [ ] SRA Daemon 新增 `POST /validate` 端点
- [ ] 端点接收 `{tool, args, loaded_skills[], task_context}` 参数
- [ ] 端点返回 `{compliant: bool, missing: [], severity: "info"|"warning"|"block"}`
- [ ] Hermes pre_tool_call hook 集成：在 write_file/patch/terminal/execute_code 前自动调用
- [ ] 非阻塞设计：SRA 不可用时优雅降级（不影响工具执行）

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
- [ ] 创建 `FILE_SKILL_MAP` 映射表（`.html` → html-presentation, `.md` → markdown-guide, 等）
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
- [ ] 增强 `POST /record` 端点，支持 `action: "viewed"|"used"|"skipped"` 类型
- [ ] Hermes `skill_view()` 调用后自动触发 `POST /record {action: "viewed"}`
- [ ] Hermes 工具调用后自动触发 `POST /record {action: "used"}`
- [ ] SRA 场景记忆记录技能使用序列
- [ ] 提供 `GET /stats/compliance` 查看历史遵循率

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
- [ ] Hermes run_agent.py 每 5 轮对话自动重查询 SRA
- [ ] 重查询基于**当前对话摘要**而非原始用户消息
- [ ] SRA 返回「需要提醒」的未使用技能列表
- [ ] 提醒以轻量级 `[SRA 提醒]` 格式注入，不干扰当前任务
- [ ] 可配置提醒间隔（默认 5 轮）

**实现文件:**
- 修改: `hermes-agent/run_agent.py`（`run_conversation()` 中重注入逻辑）
- 修改: `sra-latest/skill_advisor/advisor.py`（新增 `recheck()` 方法）

---

### Story 5: SRA 契约机制

> **作为** 系统管理员
> **我希望** 在任务开始时 SRA 自动生成一个「技能契约」
> **以便** Agent 明确知道当前任务类型下哪些技能是强烈推荐的

**验收标准:**
- [ ] SRA 在 `POST /recommend` 返回中加入 `contract` 字段
- [ ] 契约包含 `{task_type, required_skills[], optional_skills[], confidence}`
- [ ] 契约信息格式化到 `rag_context` 中
- [ ] Agent 在 SOUL.md 规则下被要求遵守契约
- [ ] 契约内容在 `/validate` 校验时作为上下文参考

**实现文件:**
- 修改: `sra-latest/skill_advisor/runtime/daemon.py`（`POST /recommend` 响应增强）
- 修改: `sra-latest/skill_advisor/advisor.py`（新增 `build_contract()` 方法）

---

### Story 6: 可配置的严格度级别

> **作为** 在不同场景下使用 Hermes 的用户
> **我希望** SRA 的校验严格度可配置
> **以便** 开发调试时宽松，生产部署时严格

**验收标准:**
- [ ] 三个严格度级别：`relaxed`（仅提醒）/ `normal`（提醒+建议）/ `strict`（可阻断）
- [ ] 级别配置在 `~/.sra/config.json` 中
- [ ] 级别配置在 Hermes `~/.hermes/config.yaml` 中可覆盖
- [ ] 不同级别影响 `/validate` 返回的 `severity` 字段
- [ ] 默认级别为 `normal`

**实现文件:**
- 修改: `sra-latest/skill_advisor/runtime/daemon.py`（配置读取）
- 修改: `hermes-agent/run_agent.py`（配置传递）

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
- [x] 在 `hermes-gateway.service` 中添加 `Requires=srad.service` + `After=srad.service`
- [x] `systemctl --user enable srad` 后用户登录自动启动
- [x] SRA 在 Gateway 之前就绪，首次消息即有技能推荐
- [x] 支持独立 `start/stop/restart/status` 管理

**实现文件:**
- 新增: `~/.config/systemd/user/srad.service`
- 新增: `~/.config/systemd/user/hermes-gateway.service.d/sra-dep.conf`
- 修改: `/tmp/sra-latest/docs/ROADMAP.md`（添加 Sprint 条目）

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

**优先级说明：**
- 🔴 P0 — 核心功能，必须完成才能发布 v2.0
- 🟡 P1 — 重要增强，建议在 v2.0 中包含
- 🟢 P2 — 锦上添花，可在 v2.1 中发布

---

## 🚀 发布计划

### v2.0.0-alpha (Phase 1: 核心校验)

| Sprint | Stories | 目标 |
|:---|:---|:---|
| Sprint 1 | SRA-003-01 + SRA-003-02 | 完成 `POST /validate` + FILE_SKILL_MAP，Hermes hook 集成 |
| Sprint 2 | SRA-003-03 + SRA-003-04 | 完成轨迹记录 + 长任务保护 |
| Sprint 3 | SRA-003-05 + SRA-003-06 + SRA-003-07 | 契约机制 + 严格度 + 压缩保护 |

### v2.1.0 (Phase 2: 智能优化)

| Sprint | Stories | 目标 |
|:---|:---|:---|
| Sprint 4 | SRA-003-08 + SRA-003-09 | 仪表盘 + 反馈闭环 |

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
