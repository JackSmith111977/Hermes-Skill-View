# SRA — Skill Runtime Advisor 🎯

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)
[![CLI](https://img.shields.io/badge/CLI-sra-orange)](https://github.com/JackSmith111977/Hermes-Skill-View)

**让 AI Agent 拥有运行时技能推荐能力的轻量级引擎。**  
运行时检测用户意图，自动推荐最匹配的技能文件（SKILL.md），无需开发者手动配置。

[📖 设计详解](#设计哲学) · [⚡ 快速安装](#安装)

---

## 核心能力

| 能力 | 说明 |
|------|------|
| **语义推荐** | 分析用户输入，按语义匹配技能 |
| **Proxy 模式** | 消息前置推理，自动注入 RAG 上下文 |
| **守护进程** | 后台运行，实时更新技能索引 |
| **多 Agent 适配** | Hermes / Claude / Codex / 通用 |
| **覆盖率分析** | 统计技能触发分布，发现知识盲区 |

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
| `sra recommend <输入>` | 查询技能推荐 |
| `sra coverage` | 查看技能覆盖率 |
| `sra stats` | 查看使用统计 |
| `sra version` | 显示版本 |

---

## Proxy API（消息前置推理）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/recommend` | POST | 技能推荐 |
| `/targets` | GET | 列出当前 tab |
| `/stats` | GET | 统计信息 |

---

## 设计哲学

SRA 遵循三个设计原则：

1. **AI 可观测性优先** — 每个组件必须有状态反馈（ok / warn / error），AI 永远知道"当前状态是什么"和"下一步该怎么做"
2. **哲学 + 技术事实** — 不仅告诉 AI "做什么"，更要注意"为什么"，讲清 tradeoff 让 Agent 自己推理
3. **渐进式披露** — README（入口）→ SKILL.md（Agent 世界观）→ docs/（详细文档），AI 按需深入

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
