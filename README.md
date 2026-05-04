# SRA — Skill Runtime Advisor

> **让 AI Agent 知道自己有什么能力，以及什么时候该用什么能力。**  
> 一个独立于 LLM 推理的轻量级运行时技能推荐引擎，通过多维度匹配引擎主动推荐最合适的技能。

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-38%20passed-brightgreen)](https://github.com/JackSmith111977/Hermes-Skill-View)
[![Coverage](https://img.shields.io/badge/coverage-86.6%25-yellow)](https://github.com/JackSmith111977/Hermes-Skill-View)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 📋 目录

- [为什么需要 SRA？](#-为什么需要-sra)
- [核心能力](#-核心能力)
- [架构](#-架构)
- [安装](#-安装)
- [快速开始](#-快速开始)
- [CLI 命令大全](#-cli-命令大全)
- [HTTP API](#-http-api)
- [Python SDK](#-python-sdk)
- [多 Agent 集成](#-多-agent-集成)
- [配置](#-配置)
- [基准测试](#-基准测试)
- [常见问题](#-常见问题)
- [开发](#-开发)
- [许可证](#-许可证)

---

## 🎯 为什么需要 SRA？

AI Agent（如 Hermes、Claude Code、OpenAI Codex）拥有大量技能（skill），但常常面临三个问题：

1. **不知道自己有哪些技能** — 技能列表在文档里，但推理时不会主动去查
2. **不知道何时该用什么技能** — 用户说"画个架构图"，却去写 HTML 而不是用架构图 skill
3. **不知道有什么技能可用** — 新安装的技能没有被发现

**SRA 解决这些问题：** 它作为一个独立的中介层，实时扫描技能目录、构建索引，在用户输入时主动推荐最匹配的技能。

---

## 🚀 核心能力

| 能力 | 说明 |
|------|------|
| 🔍 **实时技能感知** | 扫描技能目录，构建完整索引（含 triggers / tags / description） |
| 🧠 **四维匹配引擎** | 词法(40%) + 语义(25%) + 场景记忆(20%) + 类别(15%) 加权推荐 |
| 🌐 **中英文互通** | 30+ 大类同义词映射，中文输入匹配英文技能 |
| 📊 **场景记忆** | 记录"什么输入→推荐了什么技能"，持续优化匹配 |
| ⚡ **超低延迟** | ~50ms 扫描 268 个技能，适合嵌入实时推理循环 |
| 🔌 **多 Agent 支持** | Hermes、Claude Code、OpenAI Codex、通用 CLI 一键适配 |
| 🏠 **守护进程模式** | 后台运行 + Unix Socket + HTTP API + 自动刷新索引 |

---

## 🏗️ 架构

```
[用户输入]
    ↓
┌─────────────────────────────────────┐
│         SRA Runtime Engine          │
│                                     │
│  Layer 1: 实时技能索引               │
│  Layer 2: 四维匹配引擎               │
│    ├─ 词法 (triggers/name)  40%     │
│    ├─ 语义 (description)    25%     │
│    ├─ 场景 (使用历史)        20%     │
│    └─ 类别 (category/tags)  15%     │
│  Layer 3: 推荐决策器                 │
│  Layer 4: 场景记忆持久化             │
└──────────────┬──────────────────────┘
               │ 输出: skill_name + 匹配理由
               ▼
[Agent 使用 skill_view() 加载并执行]
```

### 进程架构

```
┌─────────────────────────────────────────────────────────┐
│                 SRA Daemon (srad / sra start)             │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │ Unix Socket │  │  HTTP API  │  │  Auto Refresher    │ │
│  │  (primary)  │  │  (:8532)   │  │  (every 1h)        │ │
│  └──────┬─────┘  └──────┬─────┘  └────────────────────┘ │
│         │               │                                 │
│         └───────┬───────┘                                 │
│                 ▼                                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │              SRA Recommendation Engine              │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌─────────┐  │  │
│  │  │Indexer │  │Matcher │  │ Memory │  │Synonyms │  │  │
│  │  └────────┘  └────────┘  └────────┘  └─────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
           │              │              │
           ▼              ▼              ▼
     ┌──────────┐ ┌──────────┐ ┌──────────────┐
     │ Hermes   │ │ Claude   │ │ OpenAI Codex │
     │ Adapter  │ │ Adapter  │ │ Adapter      │
     └──────────┘ └──────────┘ └──────────────┘
```

---

## 📦 安装

### 前置要求

- **Python ≥ 3.8**
- **pip**（Python 包管理器）
- **可选：** 技能目录（Hermes Agent 的 `~/.hermes/skills`）

### 方式一：从源码安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/JackSmith111977/Hermes-Skill-View.git
cd Hermes-Skill-View

# （推荐）创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装到当前环境
pip install -e .

# 或安装到用户目录（无需虚拟环境）
pip install --user -e .
```

### 方式二：一键安装脚本

```bash
# 从 GitHub 直接运行
curl -fsSL https://raw.githubusercontent.com/JackSmith111977/Hermes-Skill-View/main/scripts/install.sh | bash

# 或本地运行
cd Hermes-Skill-View
bash scripts/install.sh

# 自定义安装选项
bash scripts/install.sh --agent=hermes --systemd
```

**安装脚本支持的选项：**

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--prefix=PATH` | `~/.local` | 安装前缀 |
| `--agent=TYPE` | `hermes` | Agent 类型（hermes/claude/codex/opencode/generic） |
| `--skills=PATH` | `~/.hermes/skills` | 技能目录路径 |
| `--systemd` | 不启用 | 安装 systemd 服务（需 sudo） |
| `--skip-pip` | 不跳过 | 跳过 pip 安装（已安装时使用） |
| `--help` | — | 显示帮助 |

### 安装后验证

```bash
# 验证 CLI 可用
sra version

# 验证 Python 包可导入
python3 -c "from sra_agent import SkillAdvisor; print('SRA OK')"

# 查看帮助
sra help
```

---

## 🚀 快速开始

### 第 1 步：启动守护进程

```bash
# 启动后台守护进程（推荐）
sra start

# 查看是否启动成功
sra status

# 前台运行（调试用）
sra attach
```

**首次启动后，SRA 会自动：**
- 扫描默认技能目录 `~/.hermes/skills`
- 构建技能索引
- 启动 Unix Socket 和 HTTP API 服务
- 定时刷新索引（每小时）

### 第 2 步：测试推荐

```bash
# 查询推荐——SRA 会返回最匹配的技能
sra recommend 帮我画个架构图

# 输出示例：
# 🔍 查询: '帮我画个架构图'
# ⚡ 12ms | 📊 268 skills
# 
# 🎯 推荐技能:
#   ✅ architecture-diagram (得分: 90)
#      📄 Generate dark-themed SVG diagrams of software systems and...
#      📂 类别: creative
#      💬 触发器 'architecture' 匹配; 同义词'画'→'draw'; 同义词'图'→'diagram'
#      ⚡ 建议自动加载
```

### 第 3 步：查看状态

```bash
# 查看守护进程状态
sra status

# 查看技能覆盖率
sra coverage

# 查看运行统计
sra stats
```

---

## 📖 CLI 命令大全

### 守护进程管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `sra start` | 启动后台守护进程 | `sra start` |
| `sra stop` | 停止守护进程 | `sra stop` |
| `sra status` | 查看守护进程状态 | `sra status` |
| `sra restart` | 重启守护进程 | `sra restart` |
| `sra attach` | 前台运行（调试用） | `sra attach` |

### 技能推荐

| 命令 | 说明 | 示例 |
|------|------|------|
| `sra recommend <查询>` | 推荐匹配技能 | `sra recommend 帮我画个架构图` |
| `sra query <查询>` | 同 recommend | `sra query 写个Python脚本` |
| `sra record <skill> <输入>` | 记录技能使用 | `sra record architecture-diagram "画架构图" --accepted true` |
| `sra refresh` | 刷新技能索引 | `sra refresh` |
| `sra coverage` | 分析技能识别覆盖率 | `sra coverage` |

### 系统管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `sra stats` | 查看运行统计 | `sra stats` |
| `sra config show` | 查看当前配置 | `sra config show` |
| `sra config set <key> <value>` | 修改配置项 | `sra config set http_port 8532` |
| `sra config reset` | 重置配置为默认值 | `sra config reset` |
| `sra version` | 版本信息 | `sra version` |

### Agent 集成

| 命令 | 说明 | 示例 |
|------|------|------|
| `sra adapters` | 列出支持的 Agent 类型 | `sra adapters` |
| `sra install <agent>` | 安装到指定 Agent | `sra install hermes` |

### 一行快速使用（省略子命令）

如果输入的不是子命令，SRA 会自动将其作为推荐查询：

```bash
# 以下等价于 sra recommend "帮我写代码"
sra "帮我写代码"
```

---

## 🌐 HTTP API

启动守护进程后，可以通过 HTTP API 与 SRA 交互：

```bash
# 健康检查
curl http://localhost:8532/health

# 推荐查询
curl -X POST http://localhost:8532/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "帮我画个架构图"}'

# 记录使用
curl -X POST http://localhost:8532/record \
  -H "Content-Type: application/json" \
  -d '{"skill": "architecture-diagram", "input": "画架构图", "accepted": true}'

# 查看统计
curl http://localhost:8532/stats

# 刷新索引
curl -X POST http://localhost:8532/refresh
```

---

## 🐍 Python SDK

### 直接使用（独立模式）

```python
from sra_agent import SkillAdvisor

# 初始化引擎
advisor = SkillAdvisor()

# 查询推荐
results = advisor.recommend("帮我画个架构图")
for r in results["recommendations"][:3]:
    print(f"  {r['skill']} (得分: {r['score']})")
```

### 通过适配器使用（推荐）

```python
from sra_agent.adapters import get_adapter

# 获取对应 Agent 的适配器
adapter = get_adapter("hermes")  # 或 "claude" / "codex" / "opencode" / "generic"

# 查询推荐
recs = adapter.recommend("帮我画个架构图")

# 格式化为该 Agent 的提示
print(adapter.format_suggestion(recs))

# 检查守护进程是否运行
if adapter.ping():
    print("SRA Daemon 运行中")
```

### 通过守护进程 Socket 交互

```python
import socket, json

client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
client.connect("/root/.sra/srad.sock")
client.sendall(json.dumps({
    "action": "recommend",
    "params": {"query": "画架构图", "top_k": 3}
}).encode())
response = json.loads(client.recv(65536).decode())
client.close()
print(response["result"]["recommendations"])
```

---

## 🔌 多 Agent 集成

SRA 支持多种 AI Agent 系统，每种有对应的适配器：

| Agent | 适配器类 | 注册名 | 推荐输出格式 |
|-------|----------|--------|-------------|
| **Hermes Agent** | `HermesAdapter` | `hermes` | 原生 Skill 推荐块 + 自动加载建议 |
| **Claude Code** | `ClaudeCodeAdapter` | `claude` | Tool Use 格式 + CLI 提示 |
| **OpenAI Codex** | `CodexAdapter` | `codex` | Function Calling 格式 |
| **OpenCode** | `GenericCLIAdapter` | `opencode` | 纯文本 CLI 输出 |
| **通用** | `GenericCLIAdapter` | `generic` | 纯文本格式 |

### Hermes 集成（推荐）

在 Hermes 的 learning-workflow 前置层添加：

```python
from sra_agent.adapters import get_adapter

adapter = get_adapter("hermes")
recs = adapter.recommend(user_input)
if recs:
    print(adapter.format_suggestion(recs))
```

### Claude Code 集成

```python
from sra_agent.adapters import get_adapter

adapter = get_adapter("claude")
recs = adapter.recommend("帮我画个架构图")

# 获取 Tool Use 格式
tools = adapter.to_claude_tool_format(recs)
```

### OpenAI Codex 集成

```python
from sra_agent.adapters import get_adapter

adapter = get_adapter("codex")
recs = adapter.recommend("帮我写个Python脚本")

# 获取 Function Calling 格式
functions = adapter.to_openai_tool_format(recs)
```

---

## ⚙️ 配置

配置文件位置：`~/.sra/config.json`

### 默认配置

```json
{
    "skills_dir": "/root/.hermes/skills",
    "data_dir": "/root/.sra/data",
    "socket_path": "/root/.sra/srad.sock",
    "http_port": 8532,
    "auto_refresh_interval": 3600,
    "enable_http": true,
    "enable_unix_socket": true,
    "log_level": "INFO",
    "max_connections": 10,
    "watch_skills_dir": true
}
```

### 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `skills_dir` | string | `~/.hermes/skills` | 技能目录路径（必填） |
| `data_dir` | string | `~/.sra/data` | 数据持久化目录 |
| `socket_path` | string | `~/.sra/srad.sock` | Unix Socket 路径 |
| `http_port` | int | `8532` | HTTP API 端口 |
| `auto_refresh_interval` | int | `3600` | 自动刷新间隔（秒） |
| `enable_http` | bool | `true` | 启用 HTTP API |
| `enable_unix_socket` | bool | `true` | 启用 Unix Socket |
| `log_level` | string | `INFO` | 日志级别 |
| `max_connections` | int | `10` | 最大并发连接数 |
| `watch_skills_dir` | bool | `true` | 监听技能目录变更 |

### 通过 CLI 修改配置

```bash
# 查看配置
sra config show

# 修改端口
sra config set http_port 8532

# 修改技能目录
sra config set skills_dir /path/to/skills

# 重置为默认值
sra config reset
```

---

## 📊 基准测试

| 指标 | 值 |
|------|-----|
| 扫描 268 个技能 | ~50ms |
| 守护进程内存占用 | ~8MB |
| HTTP API 延迟 | ~5ms (overhead) |
| 技能识别率（有 trigger） | 90.6% |
| 总体技能识别率 | 86.6% |
| 常见查询通过率 | 67.5% |
| 通过测试数 | 38/38 ✅ |
| 代码覆盖率 | 86.6% |

---

## ❓ 常见问题

### 守护进程无法启动？

```bash
# 检查是否端口被占用
lsof -i :8532

# 检查日志
cat ~/.sra/srad.log

# 前台调试运行
sra attach
```

### skills_dir 不存在？

```bash
# 创建技能目录
mkdir -p ~/.hermes/skills

# 或在配置中指定已有目录
sra config set skills_dir /your/skills/path
```

### 推荐结果为空？

1. 确保技能目录不为空：`ls ~/.hermes/skills`
2. 手动刷新索引：`sra refresh`
3. 检查覆盖率：`sra coverage`
4. 使用更具体的查询词

### 国内服务器访问 GitHub 慢？

```bash
# 配置 git 代理
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

---

## 🛠️ 开发

### 设置开发环境

```bash
git clone https://github.com/JackSmith111977/Hermes-Skill-View.git
cd Hermes-Skill-View
pip install -e ".[dev]"
```

### 运行测试

```bash
# 全部测试
pytest tests/ -v

# 覆盖率和基准测试
pytest tests/test_coverage.py -v
pytest tests/test_benchmark.py -v

# 快速验证
pytest tests/ -q
```

### 覆盖率要求

| 指标 | 要求 |
|------|------|
| 有 trigger 的 skill 识别率 | ≥ 85% |
| 所有 skill 综合识别率 | ≥ 50% |
| 常见用户查询通过率 | ≥ 60% |
| 整体测试通过率 | 100% |

### 项目结构

```
sra-agent/
├── skill_advisor/           # 核心源码
│   ├── __init__.py          # 包入口，导出 SkillAdvisor / SRaDDaemon / get_adapter
│   ├── advisor.py           # 技能推荐引擎主类 SkillAdvisor
│   ├── cli.py               # CLI 命令行入口（sra 命令）
│   ├── indexer.py           # 技能目录索引器 SkillIndexer
│   ├── matcher.py           # 四维匹配引擎 SkillMatcher
│   ├── memory.py            # 场景记忆持久化 SceneMemory
│   ├── synonyms.py          # 中英文同义词映射表（30+ 大类）
│   ├── adapters/            # 多 Agent 适配器
│   │   └── __init__.py      # Hermes / Claude / Codex / Generic 适配器
│   ├── runtime/             # 守护进程
│   │   └── daemon.py        # SRA Daemon（Socket + HTTP + 自动刷新）
│   ├── utils/               # 工具函数
│   └── scripts/             # 辅助脚本
├── tests/                   # 测试
│   ├── test_matcher.py      # 匹配引擎测试
│   ├── test_indexer.py      # 索引器测试
│   ├── test_coverage.py     # 覆盖率测试
│   └── test_benchmark.py    # 基准测试
├── scripts/                 # 部署脚本
│   └── install.sh           # 一键安装脚本
├── docs/                    # 文档
│   ├── DESIGN.md            # 设计文档
│   └── INTEGRATION.md       # 集成指南
├── data/                    # 运行时数据（gitignore）
├── pyproject.toml           # 项目元数据
├── setup.py                 # 安装配置
├── LICENSE                  # MIT 许可证
├── CONTRIBUTING.md          # 贡献指南
└── README.md                # 本文件
```

---

## 🤝 贡献

欢迎 PR！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

请确保：
1. 新增测试覆盖
2. 通过所有现有测试（38/38）
3. 匹配引擎改动需更新基准测试数据
4. 新增同义词时确保中英文都有映射

---

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

---

## 🌟 相关项目

- [Hermes Agent](https://github.com/Hermes/hermes-agent) — 全能 AI 助手框架
- [Anthropic Claude Skills](https://docs.anthropic.com/claude/docs/skills) — Claude 技能系统
