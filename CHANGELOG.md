# Changelog

All notable changes to the SRA Agent project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### 🛠️ Changed

- **CI/CD**: 添加 GitHub Actions 自动测试流水线（pytest × Python 3.10/3.11/3.12 + 构建验证）
- **文档**: README 添加 CI 徽章、补全 CLI 命令表和 API 端点表
- **文档**: RUNTIME.md 更新 watch_skills_dir 状态（已修复，30s 感知）
- **元数据**: pyproject.toml 添加 license 字段和 project.urls
- **元数据**: 版本号硬编码修复（cli.py help/stats 默认值）
- **签名**: 增加 Kei 为共同作者

## [1.1.0] — 2026-05-04

### 🚀 Added

- **Hermes 原生集成** — SRA 从独立 API 服务升级为 Hermes Agent 的消息前置推理层
  - `_query_sra_context()` 代码级拦截注入，不依赖 AGENTS.md 自然语言指令
  - 每次用户消息自动触发 SRA 推荐（`run_conversation()` 内硬编码）
  - 补丁文件 `patches/hermes-sra-integration.patch`
  - 一键安装脚本 `scripts/install-hermes-integration.sh`

- **SRA Proxy 模式** — HTTP API 消息前置推理中间件
  - `POST /recommend` 端点（带 JSON 格式推荐输出）
  - `GET /health` 健康检查端点
  - `GET /stats` 统计信息端点
  - Agent 适配器系统（Hermes / Claude / Codex 原生格式输出）

- **守护进程 (Daemon)** — 7×24 后台运行
  - Unix Socket + HTTP 双协议支持
  - 自动定时刷新技能索引（3600s 间隔）
  - `watch_skills_dir` 文件变更监听（30s 检测周期，基于 MD5 校验和）
  - PID 文件管理 + 优雅退出

- **覆盖率分析引擎** — 驱动技能库质量改进
  - `sra coverage` 命令查看技能覆盖率
  - 分层测试查询体系（60 个查询，4 个 IR 指标）
  - 每技能独立验证机制

- **中文触发器补充** — 为 6 个全英文 skill 添加中文 trigger
  - `audiocraft` → 音频生成/音乐生成/文生音乐
  - `creative-ideation` → 头脑风暴/创意生成/点子/灵感
  - `lm-evaluation-harness` → 模型评估/LLM评测/大模型评估
  - `segment-anything` → 图像分割/抠图/SAM模型
  - `trl-fine-tuning` → 微调/RLHF/强化学习微调
  - `vllm` → 模型部署/推理加速/LLM推理

### 🛠️ Changed

- 从单脚本 `skill-advisor.py` → 完整模块化包结构
  - 按功能域拆分为 `advisor.py` / `cli.py` / `indexer.py` / `matcher.py` / `memory.py` / `synonyms.py`
  - 新增 `runtime/daemon.py`（守护进程模块）
  - 新增 `adapters/`（多 Agent 适配器模块）

- **评估基线**：综合得分 59.4/100

### 🐛 Fixed

- **P0-1**: `watch_skills_dir` 文件监听生效修复
  - 根因：原实现 `time.sleep(3600)` 纯时间等待，无文件系统事件监听
  - 修复：双模式刷新（定时 + 文件 MD5 校验和变更检测）
  - 实测：新增 skill → ~30 秒自动感知

- **P0-2**: 中文长文本匹配精度不足（部分修复）
  - `body_keywords` 已通过 `_match_semantic` 路径被使用

### 🧪 Testing

- 38 个测试用例（单元测试 + 集成测试 + 覆盖率测试 + 基准测试）
- 端到端覆盖率测试（使用真实技能目录）
- 性能基准测试（构建时间、推荐延迟、内存使用）

---

## [1.0.0] — 2026-05-04

### 🚀 Added

- **初始发布** — 从 Hermes 内部脚本 `skill-advisor.py` 提取为独立开源项目
- **核心匹配引擎** — 四维混合匹配算法
  - 词法匹配（40%）+ 语义匹配（25%）+ 场景记忆（20%）+ 类别匹配（15%）
  - 同义词桥接（中文→英文双向映射，127 个同义词对）
  - Name 精确/部分匹配、Trigger 匹配、Tag 匹配、Description 关键词匹配
- **CLI 工具** — 完整命令行接口
  - `sra start` / `sra stop` / `sra status` / `sra recommend` / `sra coverage` / `sra stats`
- **技能索引构建** — 从 `~/.hermes/skills/` 目录索引技能，支持关键词提取和同义词扩展
- **场景记忆** — 基于历史使用模式的推荐提升
- **PyPI 发布** — `pip install sra-agent` 即装即用
- **MIT License**

### 📚 Documentation

- `README.md` — 项目介绍、安装、快速开始、命令大全、FAQ
- `RUNTIME.md` — 运行时架构设计文档
- `docs/DESIGN.md` — 算法设计、四维匹配、数据结构
- `docs/INTEGRATION.md` — Hermes 集成指南
- `docs/EPIC-001-hermes-integration.md` — Epic 1 设计文档
- `docs/EPIC-002-p0-analysis-and-fix.md` — Epic 2 根因分析与修复
- `docs/TEST-FRAMEWORK-DESIGN.md` — 测试框架设计
- `CONTRIBUTING.md` — 贡献指南
- `CODE_OF_CONDUCT.md` — 行为准则
- `SECURITY.md` — 安全策略
