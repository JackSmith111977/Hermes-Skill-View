# SRA 开发路线图 (Roadmap)

> Skill Runtime Advisor — 让 AI Agent 知道自己有什么能力，以及什么时候该用什么能力。
> 版本: v1.2.0 | 更新: 2026-05-09

---

## ✅ v1.1.0 已完成

- [x] 测试框架重构：从 15 个假 fixtures → 313 个真实技能 YAML 提取
- [x] L0-L4 五级验证体系：pytest → CLI → HTTP → 仿真 → 压力
- [x] 测试门禁：assert skills >= 300 阻止 CI 退化到假数据
- [x] 覆盖率分析：整体 94.9%，有 trigger 技能 99.4%
- [x] 复盘经验沉淀到 skill-eval-cranfield
- [x] Hermes 原生集成：_query_sra_context() 代码级拦截注入
- [x] SRA Proxy 模式：HTTP API 消息前置推理中间件
- [x] 守护进程 (Daemon)：双协议 + 文件变更监听

---

## ✅ v1.2.0 已完成

- [x] 真实技能测试 Fixture：313 个真实技能 YAML（`tests/fixtures/skills/`）
- [x] 测试门禁：assert skills >= 300
- [x] L0-L4 五级验证体系
- [x] ROADMAP.md 文档
- [x] QA 经验沉淀到 skill-eval-cranfield §10.6-10.7
- [x] 同义词桥接修复（部分）
- [x] EPIC-002: P0 质量提升分析

---

## 🚀 v2.0 — SRA Enforcement Layer（当前 Epic）

> **核心主题**: 从「技能推荐者」升级为「运行时守护者」

### EPIC-003 详细规划 → [`docs/EPIC-003-v2-enforcement-layer.md`](docs/EPIC-003-v2-enforcement-layer.md)

| 优先级 | 故事 | 描述 |
|:------:|:-----|:------|
| 🔴 P0 | Tool 层 SRA 校验 | `POST /validate` + pre_tool_call hook 集成 |
| 🔴 P0 | 文件类型技能映射 | FILE_SKILL_MAP + 配置文件 |
| 🟡 P1 | 技能使用轨迹记录 | POST /record 扩展 + loaded_skills 追踪 |
| 🟡 P1 | 长任务上下文保护 | 每 5 轮重注入 + 漂移检测 |
| 🟡 P1 | SRA 契约机制 | 任务开始时自动生成技能契约 |
| 🟢 P2 | 可配置严格度 | relaxed / normal / strict 三级 |
| 🟢 P2 | SOUL.md 压缩保护 | 保护 SRA 规则不被 Context Compaction 裁剪 |
| 🟢 P2 | 遵循率仪表盘 | GET /stats/compliance + CLI 命令 |
| 🟢 P2 | 推荐质量反馈闭环 | 采纳率自动调整推荐权重 |

**目标版本**: SRA v2.0.0 | 估时: ~10 个工作日

---

## 🔮 远期规划

### v2.x — 多 Agent 适配器生态
- [ ] 标准协议层：统一各 Agent 的 skill 接口
- [ ] Claude Code 适配器完善
- [ ] Codex CLI 适配器
- [ ] OpenCode 适配器
- [ ] 自定义 Agent 适配器 SDK

### v3.x — 智能推荐引擎
- [ ] 场景记忆持久化（跨会话）
- [ ] 用户行为学习（基于 accept/reject 反馈）
- [ ] 负反馈学习（明确不推荐的 skill）
- [ ] 组合技能推荐（多 skill 编排）
- [ ] 主动学习：根据场景记忆自动调整推荐权重

---

## 📋 当前 Sprint 状态

| 状态 | 任务 | Epic | 负责人 |
|:----:|:-----|:----:|:-------|
| 📋 planning | Tool 层 SRA 校验 (SRA-003-01) | EPIC-003 | — |
| 📋 planning | 文件类型技能映射 (SRA-003-02) | EPIC-003 | — |
| 📋 planning | 技能使用轨迹记录 (SRA-003-03) | EPIC-003 | — |
| 📋 planning | 长任务上下文保护 (SRA-003-04) | EPIC-003 | — |
| 📋 planning | SRA 契约机制 (SRA-003-05) | EPIC-003 | — |
| 📋 planning | 可配置严格度 (SRA-003-06) | EPIC-003 | — |
| 📋 planning | 压缩保护 (SRA-003-07) | EPIC-003 | — |
| 📋 planning | 遵循率仪表盘 (SRA-003-08) | EPIC-003 | — |
| 📋 planning | 推荐质量反馈闭环 (SRA-003-09) | EPIC-003 | — |
| ✅ completed | **systemd 自启动部署 (SRA-003-10)** | EPIC-003 | — |
| ✅ completed | **安装脚本自动配置 (SRA-003-11)** | EPIC-003 | — |
