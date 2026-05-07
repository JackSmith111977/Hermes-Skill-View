# SRA — Skill Runtime Advisor 🎯

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)
[![CLI](https://img.shields.io/badge/CLI-sra-orange)](https://github.com/JackSmith111977/Hermes-Skill-View)

**为 Hermes Agent 解决技能发现痛点的运行时消息前置推理中间件。**  
每次用户消息到达 Agent 之前，先经过 SRA Proxy 语义分析，自动注入最匹配技能（SKILL.md）的 RAG 上下文——让 Agent 永远知道当前任务该用什么能力。

[📖 运行时设计](./RUNTIME.md) · [⚡ 快速安装](#安装) · [🩺 集成指南](./docs/INTEGRATION.md)

---

## 核心能力

| 能力 | 说明 |
|------|------|
| **消息前置推理** | 每次用户消息到达 Agent，自动查询最匹配的技能并注入 RAG 上下文 |
| **语义匹配引擎** | 同义词扩展 + TF-IDF + 共现矩阵混合匹配，不是简单的关键词搜索 |
| **守护进程** | 7x24 后台运行，Unix Socket + HTTP 双协议，自动定时刷新技能索引 |
| **覆盖率分析** | 统计哪些技能能被识别、哪些是盲区，驱动技能库质量改进 |
| **Agent 适配器** | 为 Hermes / Claude / Codex 等 Agent 提供原生格式的输出 |

---

## 安装

**方式一：pip 安装（推荐）**  
```bash
pip install sra-agent
sra version    # 验证安装
```

**方式二：一键脚本（自动配置）**  
```bash
curl -fsSL https://raw.githubusercontent.com/JackSmith111977/Hermes-Skill-View/main/scripts/install.sh | bash
```

**方式三：源码安装**  
```bash
git clone https://github.com/JackSmith111977/Hermes-Skill-View.git
cd Hermes-Skill-View
pip install -e .
```

**方式四：Proxy 模式（消息前置推理）**  
```bash
bash scripts/install.sh --proxy
```

---

## 快速开始

### 1. 启动守护进程
```bash
sra start
# 预期输出: SRA Daemon 运行中...
```

### 2. 查询技能推荐
```bash
sra recommend "画个架构图"
# 预期输出: -> 推荐技能、得分、置信度
```

### 3. 检查状态
```bash
sra status
# 预期输出: 运行状态、技能数量、版本
```

### 4. Proxy 模式（消息前置推理）
```bash
curl -s -X POST http://127.0.0.1:8536/recommend \
  -H "Content-Type: application/json" \
  -d '{"message": "画个架构图"}'
# 预期输出: {"recommendations": [...], "top_skill": "...", ...}
```

---

## 环境检查

安装后运行以下命令确认全部就绪：

```bash
# 自动检测关键组件状态
python3 scripts/check-sra.py
```

预期输出示例：
```
python: ok (3.11.5)
sra cli: ok (sra v1.1.0)
sra daemon: ok (port 8536, 275 skills indexed)
skills dir: ok (~/.hermes/skills, 62 skills)
sra config: ok (~/.sra/config.json)
```

---

## 命令大全

| 命令 | 说明 |
|------|------|
| `sra start` | 启动守护进程 |
| `sra stop` | 停止守护进程 |
| `sra status` | 查看运行状态 |
| `sra restart` | 重启守护进程 |
| `sra attach` | 前台运行（调试用） |
| `sra recommend <输入>` | 查询技能推荐 |
| `sra query <输入>` | 同 recommend |
| `sra coverage` | 分析技能识别覆盖率 |
| `sra stats` | 查看运行统计 |
| `sra refresh` | 刷新技能索引 |
| `sra record <技能> <输入>` | 记录技能使用 |
| `sra config [show\|set\|reset]` | 配置管理 |
| `sra adapters` | 列出支持的 Agent 类型 |
| `sra install <agent>` | 安装到指定 Agent |
| `sra version` | 显示版本 |
| `sra help` | 显示帮助 |

---

## Proxy API（消息前置推理）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/status` | GET | 详细运行状态 |
| `/stats` | GET | 统计信息 |
| `/recommend?q=<查询>` | GET | 技能推荐（GET 方式） |
| `/recommend` | POST | 技能推荐（POST 方式，JSON body） |
| `/record` | POST | 记录技能使用 |
| `/refresh` | POST | 刷新技能索引 |

---

## 设计哲学

SRA 以三个原则指导其作为运行时的设计：

1. **消息优先于工具** — SRA 不是 Agent 主动加载的"技能"，而是 Agent 收到每条消息时**被动触发**的中间件。它不改变 Agent 的行为，只增强 Agent 的上下文。
2. **AI 可观测性优先** — 每个组件必须有状态反馈（ok / warn / error），AI 永远知道"当前状态是什么"和"下一步该怎么做"
3. **渐进式披露** — README（入口）→ RUNTIME.md（运行时设计）→ docs/（详细文档），按需深入

> 📖 完整的运行时设计文档请看 [RUNTIME.md](./RUNTIME.md)

---

## FAQ

**Q: sra 命令找不到？**  
检查 PATH 是否包含 `~/.local/bin`，或运行 `pip install sra-agent` 重试。

**Q: 守护进程启动失败？**  
先运行 `python3 check-sra.py` 诊断环境，针对未通过项修复。

**Q: Proxy 模式不工作？**  
确认搭建模式已安装，守护进程运行中，端口 8536 可用。

---

## 许可证

MIT — 详见 [LICENSE](./LICENSE)
