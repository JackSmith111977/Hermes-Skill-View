# 项目报告生成器 — 设计文档

## 核心痛点

1. PROJECT-PANORAMA.html 是手写的 → 每次更新容易遗漏、不一致
2. doc-alignment 只有「更新指南」没有「自动化工具」
3. 版本号需要在 N 个文件中同步 → 容易遗忘
4. 不同项目需要各自维护 HTML 报告 → 无法复用

## 解决方案：数据驱动的报告生成系统

```
┌─────────────────────────────────────────────────────────────┐
│                   项目报告生命周期                            │
│                                                             │
│  ① 初始化                 ② 每次开发变更          ③ 发布前  │
│  ┌─────────┐              ┌─────────┐            ┌────────┐ │
│  │ 创建     │              │ 更新     │            │ 最终   │ │
│  │ project- │  →  代码变更  │ project │  →  版本   │ 验证 + │ │
│  │ report   │              │ report  │            │ 发布   │ │
│  │ .json    │              │ .json   │            │        │ │
│  └─────────┘              └────┬────┘            └────────┘ │
│        │                       │                            │
│        ▼                       ▼                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           generate-project-report.py                 │    │
│  │  读取 JSON 数据 → 渲染 HTML → 输出 PROJECT-PANORAMA │    │
│  │                  .html                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 数据格式标准 (project-report.json)

每个项目在 `docs/project-report.json` 中定义报告数据：

```json
{
  "project": {
    "name": "SRA Agent",
    "package": "sra-agent",
    "version": "1.3.0",
    "description": "让 AI Agent 知道自己有什么能力...",
    "author": "Emma (SRA Team), Kei",
    "repo": "github.com/JackSmith111977/Hermes-Skill-View",
    "license": "MIT",
    "python": "≥ 3.8",
    "dependencies": ["pyyaml"],
    "entry_cli": "sra / srad",
    "daemon_port": "HTTP :8536 + Unix Socket ~/.sra/srad.sock",
    "skills_source": "~/.hermes/skills/**/SKILL.md"
  },
  "architecture": {
    "layers": [
      {
        "name": "Layer 3 — 接口层 Interface",
        "modules": ["CLI (sra)", "HTTP API (:8536)", "Unix Socket (~/.sra/srad.sock)"],
        "direction": "delegate"
      },
      {
        "name": "Layer 2 — 业务逻辑层 Service",
        "modules": ["SRaDDaemon (daemon.py)", "SkillAdvisor (advisor.py)", "SkillMatcher (matcher.py)", "SkillIndexer (indexer.py)", "SceneMemory (memory.py)", "Synonyms (synonyms.py)"],
        "direction": "read-write"
      },
      {
        "name": "Layer 1 — 数据层 Data",
        "modules": ["~/.hermes/skills/", "~/.sra/data/", "~/.sra/config.json"],
        "direction": null
      }
    ],
    "module_table": [
      {"module": "SkillAdvisor", "file": "advisor.py", "desc": "推荐引擎主入口，Facade 封装", "methods": ["recommend()", "recheck()", "record_view/use/skip()", "analyze_coverage()"]},
      {"module": "SRaDDaemon", "file": "runtime/daemon.py", "desc": "守护进程，HTTP + Socket 双协议", "methods": ["start()", "stop()", "_handle_request()", "get_stats()"]}
    ]
  },
  "api_endpoints": {
    "http": [
      {"method": "GET", "path": "/health", "desc": "健康检查 + 基本统计", "sprint": "v1.x"},
      {"method": "POST", "path": "/recommend", "desc": "技能推荐", "sprint": "v1.x"}
    ],
    "socket_actions": [
      {"action": "recommend", "params": "query", "desc": "技能推荐", "sprint": "v1.x"}
    ]
  },
  "cli_commands": [
    {"cmd": "sra start", "desc": "启动守护进程（后台）", "section": "daemon"},
    {"cmd": "sra recommend", "desc": "技能推荐", "section": "query"}
  ],
  "epics": [
    {"id": "SRA-EPIC-003", "name": "v2.0 Enforcement Layer", "stories": [
      {"id": "SRA-003-01", "name": "Tool 层 SRA 校验", "pri": "P0", "status": "completed", "sprint": "Sprint 1"},
      {"id": "SRA-003-05", "name": "SRA 契约机制", "pri": "P1", "status": "completed", "sprint": "Sprint 2"}
    ]}
  ],
  "tests": {
    "passing": 290,
    "total": 290,
    "duration_seconds": 25,
    "coverage_pct": null,
    "files": ["test_matcher.py", "test_indexer.py", "test_coverage.py", "test_benchmark.py", "test_daemon.py", "test_cli.py", "test_contract.py", "test_force.py"]
  },
  "sprint_history": [
    {"sprint": "Sprint 1", "version": "v2.0-alpha", "date": "2026-05-10", "stories_completed": 7, "tests_growth": "103→174"}
  ],
  "footer": "由 generate-project-report.py 自动生成"
}
```

## 架构设计

```
~/.hermes/scripts/
├── generate-project-report.py    ← 核心生成器（所有项目共用）
└── templates/
    └── project-report.html.j2    ← HTML 模板（Jinja2 风格字符串模板）
```

### 生成器的工作模式

```
python3 ~/.hermes/scripts/generate-project-report.py \
  --data docs/project-report.json \
  --output PROJECT-PANORAMA.html \
  [--verify]  # 验证模式：对比当前代码状态，输出漂移报告
```

### 集成到 doc-alignment 工作流

```
开发完成 → 更新 project-report.json → 运行 generator → 验证 → git commit
                ↑                            ↑
          手动更新关键字段            自动生成完整 HTML
         (版本号、Story状态、        (保证 HTML 与数据一致)
          测试数量、新端点)
```

### 对比现状

| 维度 | 现状 (手写 HTML) | 改进后 (数据驱动) |
|:-----|:----------------:|:----------------:|
| HTML 一致性 | 每次手动编辑，易遗漏 | 自动生成，保证一致 |
| 跨项目复用 | 每个项目各自维护 | 同一 generator |
| 版本号同步 | N 处手动更新 | 改 1 处 JSON → 全同步 |
| 新增模块 | 手动加行 | 加到 JSON → 自动渲染 |
| Story 状态 | 手动改 | 改 JSON 状态字段 |
| 验证能力 | 无 | --verify 模式自动对比代码 |
