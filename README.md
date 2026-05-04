
<p align="center">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/tests-38%20passed-brightgreen?style=flat-square"/>
  <img src="https://img.shields.io/badge/coverage-86.6%25-yellow?style=flat-square"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square"/>
  <img src="https://img.shields.io/badge/latency-~5ms-orange?style=flat-square"/>
  <img src="https://img.shields.io/badge/memory-~8MB-purple?style=flat-square"/>
</p>

<h1 align="center">🏆 SRA · Skill Runtime Advisor</h1>

<p align="center">
  <b>让 AI Agent 实时感知自己有什么能力，以及什么时候该用什么能力。</b><br>
  一个独立于 LLM 推理的轻量级运行时技能推荐引擎 · 零依赖 · 超低延迟 · 即插即用
</p>

<p align="center">
  <b>
    <a href="#-为什么需要-sra">为什么需要</a> •
    <a href="#-快速开始-10秒">快速开始</a> •
    <a href="#-架构">架构</a> •
    <a href="#-与-hermes-原生集成">Hermes 集成</a> •
    <a href="#-基准测试">基准测试</a>
  </b>
</p>

---

## 🤔 为什么需要 SRA？

AI Agent（如 Hermes、Claude Code、OpenAI Codex）虽然拥有大量 skill，但面临三个致命问题：

| 问题 | 后果 | SRA 的解法 |
|------|------|------------|
| ❌ **不知道自己有哪些 skill** | 用户说"画个架构图"，Agent 却去写 HTML | 🟢 实时扫描 + 索引构建 |
| ❌ **不知道何时该用什么 skill** | 安装的新 skill 从未被使用 | 🟢 四维匹配引擎主动推荐 |
| ❌ **Agent 文档中的规则被忽略** | SOUL.md/AGENTS.md 的规则会被上下文压缩掉 | 🟢 **代码层强制注入，永不丢失** |

> **SRA 是一个"图书管理员"——它清楚地知道书架上每本书在哪里、讲什么内容、适合谁看。**

---

## ⚡ 快速开始（10秒）

```bash
# 1. 安装
pip install --user sra-agent  # 或从源码安装

# 2. 启动守护进程
sra start

# 3. 测试推荐
sra recommend 帮我画个架构图
# → ⭐ architecture-diagram (得分: 90) — 建议自动加载
```

**就是这么简单。** 接下来每次 Agent 收到消息，SRA 都会自动推荐最合适的 skill。

---

## 🏗️ 架构

SRA 采用**分层轻量架构**，总代码量仅 **95KB**，运行内存占用不到 **8MB**：

```
┌─ 用户输入 ─────────────────────────────────────┐
│  "帮我画个架构图"                                │
└────────────────────┬────────────────────────────┘
                     ↓
┌────────────────────┴────────────────────────────┐
│           SRA 四维匹配引擎 (～50ms)               │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌────┐ │
│  │  词法匹配   │  语义匹配   │  场景记忆  │  类别  │ │
│  │ triggers  │  description│  历史记录  │ tags │ │
│  │   40%     │    25%     │   20%    │ 15% │ │
│  └──────────┘  └──────────┘  └────────┘  └────┘ │
│                         ↓                        │
│              综合推荐决策器                        │
│         → architecture-diagram (得分: 90)         │
└────────────────────┬────────────────────────────┘
                     ↓
┌────────────────────┴────────────────────────────┐
│  Agent → skill_view(architecture-diagram) → 执行   │
└──────────────────────────────────────────────────┘
```

### 进程架构

```
┌──────────────────────────────────────────────────┐
│               SRA Daemon (sra start)               │
│                                                    │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │ Unix Socket│  │ HTTP API │  │ Auto Refresher  │  │
│  │  (primary) │  │ (:8536)  │  │  (every 1h)     │  │
│  └─────┬─────┘  └────┬─────┘  └─────────────────┘  │
│        └──────┬──────┘                              │
│               ↓                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │              推荐引擎                          │  │
│  │  Indexer + Matcher + Memory + Synonyms        │  │
│  └──────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
         ↓          ↓            ↓
    ┌────────┐ ┌────────┐ ┌────────────┐
    │ Hermes │ │ Claude │ │ OpenAI     │
    │ Adapter│ │ Adapter│ │ Codex Adpt │
    └────────┘ └────────┘ └────────────┘
```

---

## ✨ 核心能力

<table>
<tr>
  <td width="50%">
    <h3>🔍 实时技能感知</h3>
    <p>自动扫描技能目录，构建完整索引（含 triggers / tags / description），新增 skill 即时发现</p>
  </td>
  <td width="50%">
    <h3>🧠 四维匹配引擎</h3>
    <p>词法(40%) + 语义(25%) + 场景记忆(20%) + 类别(15%) 加权推荐，中英文互通</p>
  </td>
</tr>
<tr>
  <td>
    <h3>🌐 中英文互通</h3>
    <p>30+ 大类同义词映射，"画图"自动匹配 "draw/diagram"，中文输入通吃英文 skill</p>
  </td>
  <td>
    <h3>📊 场景记忆</h3>
    <p>记录"什么输入→推荐了什么 skill"，持续优化匹配，越用越准</p>
  </td>
</tr>
<tr>
  <td>
    <h3>⚡ 超低延迟</h3>
    <p>扫描 268 个 skill 仅 ~50ms，HTTP API 开销 ~5ms，适合嵌入实时推理循环</p>
  </td>
  <td>
    <h3>🔌 多 Agent 支持</h3>
    <p>Hermes、Claude Code、OpenAI Codex、OpenCode、通用 CLI 即插即用</p>
  </td>
</tr>
<tr>
  <td>
    <h3>🏠 守护进程模式</h3>
    <p>后台运行 + HTTP API + Unix Socket + 自动刷新索引，可集成 systemd</p>
  </td>
  <td>
    <h3>🎯 代码层强制注入</h3>
    <p>直接注入 Hermes 消息管道，每轮消息自动触发 SRA，不依赖模型遵循自然语言指令</p>
  </td>
</tr>
</table>

---

## 🚀 安装指南

### 方式一：pip 安装

```bash
pip install --user sra-agent
```

### 方式二：从源码安装（推荐）

```bash
git clone https://github.com/JackSmith111977/Hermes-Skill-View.git
cd Hermes-Skill-View
pip install -e .
```

### 方式三：一键安装脚本

```bash
curl -fsSL https://raw.githubusercontent.com/JackSmith111977/Hermes-Skill-View/main/scripts/install.sh | bash
```

### 安装后验证

```bash
sra version
# → SRA v1.1.0
```

---

## 🎮 CLI 命令大全

### 守护进程管理

| 命令 | 说明 |
|------|------|
| `sra start` | 启动后台守护进程 |
| `sra stop` | 停止守护进程 |
| `sra status` | 查看状态 |
| `sra restart` | 重启 |
| `sra attach` | 前台运行（调试用） |

### 技能推荐

| 命令 | 说明 |
|------|------|
| `sra recommend <查询>` | 推荐匹配 skill |
| `sra record <skill> <输入>` | 记录 skill 使用 |
| `sra refresh` | 刷新技能索引 |
| `sra coverage` | 分析技能识别覆盖率 |

### 一行快速使用

```bash
# 自动识别为 recommend
sra "帮我画个架构图"
# → ⭐ architecture-diagram (得分: 90)
```

---

## 🌐 HTTP API

```bash
# 健康检查
curl http://localhost:8536/health
# → {"status":"ok","sra_version":"1.1.0"}

# 推荐查询
curl -X POST http://localhost:8536/recommend \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我画个架构图"}'

# → 返回格式：
# {
#   "rag_context": "── [SRA Skill 推荐] ──\n  ⭐ architecture-diagram (90分)",
#   "recommendations": [...],
#   "top_skill": "architecture-diagram",
#   "should_auto_load": true,
#   "timing_ms": 12.3,
#   "sra_version": "1.1.0"
# }

# 查看统计
curl http://localhost:8536/stats

# 刷新索引
curl -X POST http://localhost:8536/refresh
```

---

## 🐍 Python SDK

```python
from sra_agent import SkillAdvisor

# 初始化
advisor = SkillAdvisor()

# 查询推荐
results = advisor.recommend("帮我画个架构图")
for r in results["recommendations"][:3]:
    print(f"  {r['skill']} (得分: {r['score']})")
```

### 通过适配器使用

```python
from sra_agent.adapters import get_adapter

# 获取对应 Agent 的适配器
adapter = get_adapter("hermes")  # 或 "claude" / "codex"

# 查询推荐
recs = adapter.recommend("帮我画个架构图")

# 格式化为该 Agent 的提示
print(adapter.format_suggestion(recs))
```

---

## 🧩 与 Hermes 原生集成

**这是 SRA 的独有杀手锏 🎯** — 直接注入 Hermes 的消息管道，**每轮消息自动触发 SRA，代码层强制拦截**，不依赖任何自然语言指令。

```mermaid
flowchart LR
    A[用户消息] --> B[Hermes run_conversation]
    B --> C{自动触发 SRA}
    C --> D[POST :8536/recommend]
    D --> E[SRA 返回推荐]
    E --> F[注入 [SRA] 上下文到消息前]
    F --> G[LLM 感知推荐 → 回复]
```

### 一键安装

```bash
bash scripts/install-hermes-integration.sh
```

### 效果演示

```
你: 帮我画个架构图

[SRA] Skill Runtime Advisor 推荐:
── [SRA Skill 推荐] ──────────────────────────────
  ⭐ [high] architecture-diagram (90.0分) — 
     Generate dark-themed SVG diagrams...
  ⚡ 强推荐自动加载: architecture-diagram
── ──────────────────────────────────────────────

好的喵～boku 来帮你画架构图！
```

> 🔒 **降级保障**：SRA 不可用时完全静默（2 秒超时 + try/except），绝不阻塞消息。

---

## 📊 基准测试

| 指标 | 值 |
|------|-----|
| 扫描 268 个 skill | **~50ms** |
| 守护进程内存占用 | **~8MB** |
| HTTP API 延迟 | **~5ms** |
| 代码总量 | **95KB** |
| 安装依赖 | **零（纯 Python 标准库）** |
| 有 trigger 的 skill 识别率 | **90.6%** |
| 总体识别率 | **86.6%** |
| 测试通过 | **38/38 ✅** |

---

## 🔌 多 Agent 支持

| Agent | 适配器 | 状态 |
|-------|--------|------|
| **Hermes Agent** | `HermesAdapter` | ✅ 原生集成 + 代码层注入 |
| **Claude Code** | `ClaudeCodeAdapter` | ✅ Tool Use 格式 |
| **OpenAI Codex** | `CodexAdapter` | ✅ Function Calling 格式 |
| **OpenCode** | `GenericCLIAdapter` | ✅ CLI 输出 |
| **通用** | `GenericCLIAdapter` | ✅ 纯文本格式 |

---

## ⚙️ 配置

```bash
# 查看配置
sra config show

# 修改监听端口
sra config set http_port 8536

# 修改技能目录
sra config set skills_dir ~/.hermes/skills
```

**环境变量：**

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SRA_PROXY_URL` | `http://127.0.0.1:8536` | SRA Daemon 地址 |
| `SRA_SKILLS_DIR` | `~/.hermes/skills` | 技能目录路径 |
| `SRA_DATA_DIR` | `~/.sra/data` | 数据持久化路径 |

---

## ❓ 常见问题

<details>
<summary><b>Q: SRA 和 skill_view 有什么区别？</b></summary>
<p><code>skill_view</code> 是文件读取器（打开书本看内容），SRA 是推荐引擎（图书管理员推荐哪本书）。两者互补：SRA 告诉你<em>该用什么</em>，<code>skill_view</code> 告诉你<em>怎么用</em>。</p>
</details>

<details>
<summary><b>Q: 守护进程起不来怎么办？</b></summary>

```bash
# 检查日志
cat ~/.sra/srad.log

# 前台调试
sra attach

# 检查端口占用
lsof -i :8536
```
</details>

<details>
<summary><b>Q: 推荐结果为空？</b></summary>
1. 确保技能目录不为空：<code>ls ~/.hermes/skills</code>
2. 手动刷新索引：<code>sra refresh</code>
3. 检查覆盖率：<code>sra coverage</code>
4. 使用更具体的查询词
</details>

<details>
<summary><b>Q: 升级 Hermes 后集成失效？</b></summary>
升级后重新运行：<code>bash scripts/install-hermes-integration.sh</code>
</details>

<details>
<summary><b>Q: 国内服务器访问 GitHub 慢？</b></summary>

```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```
</details>

---

## 🛠️ 开发

```bash
# 设置开发环境
git clone https://github.com/JackSmith111977/Hermes-Skill-View.git
cd Hermes-Skill-View
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v  # 38 个测试全部通过

# 覆盖率
pytest tests/test_coverage.py -v

# 项目结构
```

### 项目结构

```
sra-agent/
├── skill_advisor/           # 核心源码
│   ├── advisor.py           # 技能推荐引擎
│   ├── cli.py               # CLI 入口
│   ├── indexer.py           # 技能索引器
│   ├── matcher.py           # 四维匹配引擎
│   ├── memory.py            # 场景记忆
│   ├── synonyms.py          # 中英文同义词映射
│   ├── adapters/            # 多 Agent 适配器
│   └── runtime/             # 守护进程
├── tests/                   # 测试（38 tests）
├── scripts/                 # 部署脚本
├── patches/                 # Hermes 集成补丁
└── docs/                    # 文档
```

---

## 🤝 贡献

欢迎任何形式的贡献！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)

**贡献方式：**
- 🐛 报告 Bug → [创建 Issue](https://github.com/JackSmith111977/Hermes-Skill-View/issues/new)
- 💡 建议新功能 → 开启 Discussion
- 🔧 提交 PR → Fork + Branch + PR
- 📖 完善文档 → 改进 README 或新增示例

---

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

---

<p align="center">
  <b>如果 SRA 对你有帮助，请给它一个 ⭐ 吧！</b><br>
  <sub>你的 star 是开源项目前进的最大动力 ❤️</sub>
</p>
