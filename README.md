# SRA — Skill Runtime Advisor

> **让 AI Agent 知道自己有什么能力，以及什么时候该用什么能力。**

SRA 是一个轻量级的**运行时技能推荐引擎**，解决 AI Agent"不知道自己有什么技能、不知道何时该用什么"的根本问题。它是一个独立于 LLM 推理的**中介层**，通过多维度匹配引擎主动推荐最合适的技能。

## 🎯 核心能力

| 能力 | 说明 |
|------|------|
| 🔍 **实时技能感知** | 扫描技能目录，构建完整索引（含 triggers / tags / description） |
| 🧠 **四维匹配引擎** | 词法 + 语义 + 场景 + 类别，四维加权推荐 |
| 🌐 **中英文互通** | 30+ 大类同义词映射，中文输入匹配英文技能 |
| 📊 **场景记忆** | 记录"什么输入→推荐了什么技能"，持续优化匹配 |
| ⚡ **超低延迟** | ~50ms 扫描 268 个技能，适合嵌入实时推理循环 |

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

## 🚀 快速开始

### 安装

```bash
# pip 安装
pip install sra-agent

# 或从源码
git clone https://github.com/yourname/sra-agent
cd sra-agent
pip install -e .
```

### 基本用法

```python
from sra_agent import SkillAdvisor

# 初始化（自动扫描技能目录）
advisor = SkillAdvisor(skills_dir="~/.hermes/skills")

# 推荐匹配
result = advisor.recommend("帮我画个架构图")
print(result.recommendations)
# → [Skill(name='architecture-diagram', score=47.5, confidence='medium')]

# 记录使用场景（供下次学习）
advisor.record_usage("architecture-diagram", "帮我画个架构图", accepted=True)

# 查看统计
advisor.show_stats()
```

### CLI 使用

```bash
# 推荐匹配
sra --query "帮我画个架构图"

# 刷新索引
sra --refresh

# 查看统计
sra --stats

# 生成增强版技能提示
sra --enhanced-prompt
```

## 📊 基准测试

| 指标 | 值 |
|------|-----|
| 扫描 268 个技能 | ~50ms |
| 内存占用 | ~5MB |
| 首次索引构建 | ~1s |
| 技能识别率（有 trigger 的） | 98% |
| 零 trigger 技能识别率 | 70% |

## 🔌 集成方式

### 作为 Hermes 插件

SRA 设计为 Hermes Agent 的 learning-workflow 前置层：

```
用户输入 → SRA 推荐 → 
├─ 得分 ≥ 80 → 自动加载 skill（跳过 skill_finder）
├─ 得分 ≥ 40 → 弱推荐提示
└─ 得分 < 40 → 回退 skill_finder / learning-workflow
```

### 作为独立服务

```bash
# 启动守护模式
sra --daemon

# 通过 HTTP 查询（后续版本）
curl -X POST http://localhost:8532/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "帮我画个架构图"}'
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 只运行基准测试
pytest tests/test_benchmark.py -v

# 测试特定 skill 识别率
pytest tests/test_skill_coverage.py -v
```

## 📦 项目结构

```
sra-agent/
├── skill_advisor/
│   ├── __init__.py         # 主入口 SkillAdvisor 类
│   ├── advisor.py          # SRA 核心引擎
│   ├── matcher.py          # 四维匹配引擎
│   ├── indexer.py          # 技能索引构建
│   ├── memory.py           # 场景记忆持久化
│   ├── synonyms.py         # 30+ 大类同义词映射
│   └── cli.py              # CLI 入口
├── tests/
│   ├── test_matcher.py     # 匹配引擎测试
│   ├── test_indexer.py     # 索引测试
│   ├── test_synonyms.py    # 同义词测试
│   ├── test_coverage.py    # 技能覆盖率测试
│   └── test_benchmark.py   # 性能基准测试
├── data/
│   └── sample_skills/      # 示例技能目录（测试用）
├── docs/
│   ├── DESIGN.md           # 设计文档
│   └── INTEGRATION.md      # 集成指南
├── setup.py
├── pyproject.toml
├── README.md
├── LICENSE
└── CONTRIBUTING.md
```

## 🤝 贡献

欢迎 PR！请确保：

1. 新增测试覆盖
2. 通过所有现有测试
3. 匹配引擎改动需更新基准测试数据

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

## 🌟 相关项目

- [Hermes Agent](https://github.com/Hermes/hermes-agent) — 全能 AI 助手框架
- [Anthropic Claude Skills](https://docs.anthropic.com/claude/docs/skills) — Claude 技能系统
