# SRA — Skill Runtime Advisor 设计文档

## 问题

AI Agent（如 Hermes Agent）拥有大量技能（skill），但：
1. **不知道自己有什么** — system prompt 里只有 name + description
2. **不知道何时该用什么** — triggers 写在 YAML 但没暴露给 LLM
3. **没有运行时匹配** — 全凭 LLM 自己做"阅读理解"，经常遗漏
4. **没有场景记忆** — 用过也不记得

## 解决方案：运行时中介层

SRA 在 Agent 的推理循环外插入一个轻量级中介层：

```
[用户输入] → SRA 引擎 → skill 推荐 → Agent 加载并执行
                ↑
            技能索引
            (triggers/name/desc/tags)
                ↑
            场景记忆
            (历史使用模式)
```

## 核心算法

### 四维匹配

```
总得分 = 词法 × 40% + 语义 × 25% + 场景 × 20% + 类别 × 15%
```

### 词法匹配

- Name 精确匹配 (+30)
- Name 部分匹配 (+20)
- Trigger 精确匹配 (+25)
- Tag 匹配 (+15)
- Description 关键词匹配 (+8)
- 同义词桥接 (+25) — 中文→英文双向

### 同义词桥接

这是 SRA 的核心创新。例如：

```
用户输入: "画架构图"
  → 提取中文词: {"画", "架构", "图", "架构图"}
  → 同义词扩展: {"architecture diagram", "architecture", "diagram", ...}
  → 匹配英文 skill "architecture-diagram"
```

## 数据结构

### 技能索引 (skill_full_index.json)

```json
{
  "skills": [{
    "name": "architecture-diagram",
    "triggers": ["architecture diagram", "architecture-diagram"],
    "tags": ["architecture", "diagrams", "SVG"],
    "category": "creative",
    "match_text": "...",
    "full_description": "..."
  }]
}
```

### 场景记忆 (skill_usage_stats.json)

```json
{
  "skills": {
    "architecture-diagram": {
      "total_uses": 15,
      "trigger_phrases": ["帮我画架构图", "画个系统架构"],
      "acceptance_rate": 0.93
    }
  },
  "scene_patterns": [
    {"pattern": "画图", "recommended_skills": ["architecture-diagram"], "hit_count": 5}
  ]
}
```

## 性能目标

- 索引构建：< 5s（268 skills）
- 单次推荐：< 100ms
- 内存：< 20MB

## 扩展性

SRA 设计为可插拔：
- 替换 `synonyms.py` 即可支持其他语言
- 新增匹配维度只需继承 `matcher.py` 的接口
- 场景记忆可替换为数据库后端
