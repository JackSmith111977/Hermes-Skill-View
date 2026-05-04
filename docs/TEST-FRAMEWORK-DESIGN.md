# SRA 测试框架设计 — 基于 Cranfield 范式的 skill 推荐评估

> 研究来源: TREC 评测体系、Cranfield 实验、ACL IR 评估框架
> 适配场景: 超多skill (279个) 的推荐引擎效果评估

---

## 一、为什么要用 Cranfield 范式？

### 当前测试的问题

| 问题 | 表现 | 后果 |
|------|------|------|
| **只测 4 个场景** | "设计数据库", "画架构图"等 | 无法代表 279 个skill的真实分布 |
| **无 ground truth** | "应该推荐什么"纯靠人工判断 | 评估主观，不能自动化 |
| **无量化指标** | "改进前 52.8 vs 改进后 51.0" | 看不出整体是变好还是变差 |
| **无难度分层** | 简单和复杂场景混在一起 | 无法确认"哪个环节出了问题" |

### Cranfield 范式给我们的答案

Cranfield 范式（1960s 至今，TREC 沿用）由三部分组成：
1. **文档集 (Corpus)** → 279 个 SKILL.md
2. **查询集 (Topics/Queries)** → 精心设计的测试查询（按难度分层）
3. **相关性判断 (Relevance Judgments / Qrels)** → 每个查询应该推荐哪些 skill

有了这三样，就能做**量化、可复现、自动化**的评估。

---

## 二、SRA 测试集设计

### 2.1 文档集 (Corpus)

已经是现成的——279 个 SKILL.md。但需要确保：
- 每个 skill 的 name、description、triggers 是可索引的
- SRA 的 coverage 分析可以看到哪些 skill "不可见"

### 2.2 查询集 — 按难度分层

借鉴 Meta AI 的研究结论：**评估数据集若偏向简单查询，会高估 25-30% 的生产质量。**

所以查询必须分层：

| 层级 | 难度 | 定义 | 数量建议 | 示例 |
|------|------|------|---------|------|
| 🟢 **L1 精确匹配** | 简单 | skill 名称直接包含查询词 | 30 个 | "pptx" → pptx-guide |
| 🟡 **L2 同义映射** | 中等 | 需要同义词桥接的中文查询 | 30 个 | "幻灯片" → pptx-guide |
| 🔴 **L3 语义理解** | 困难 | 自然语言任务描述，需跨技能 | 20 个 | "帮我把设计稿做成能演示的PPT" |
| 🟣 **L4 多跳推理** | 极难 | 需要多个 skill 组合的任务 | 10 个 | "每天自动爬取新闻生成PDF报告" |
| ⚫ **L5 边缘/噪声** | 验证 | 无关查询不应推荐任何 skill | 10 个 | "今天天气怎么样" |

**总查询量**：100 个（参考 TREC 每轮 50 个 topic，我们翻倍以覆盖更多技能）

### 2.3 相关性判断 (Qrels) — 从 skill 的 Triggers 自动生成

这是关键洞察：**不需要人工标注！skill 的 trigger 字段就是天然的 ground truth！**

```
对于每个 test_query，将其与所有 279 个 skill 的 trigger 列表比对：
- 如果 test_query 命中某个 skill 的 trigger → 该 skill 与该 query 相关 (relevance=1)
- 否则 → 不相关 (relevance=0)
```

但 trigger 不是完美的——有些 skill trigger 写得太少。所以需要**补充策略**：

```
对于每个 test_query:
  1. 精确 trigger 匹配 → 相关 (relevance=2)
  2. 同义词扩展后 trigger 匹配 → 相关 (relevance=1)
  3. name 或 category 命中 → 弱相关 (relevance=0.5)
  4. 以上都不命中 → 不相关 (relevance=0)
```

### 2.4 评估指标

借鉴 TREC 评测体系和信息检索最佳实践，选用 4 个核心指标：

| 指标 | 缩写 | 衡量什么 | 为什么选它 |
|------|------|---------|-----------|
| **召回率@K** | Recall@5 | "正确的 skill 被推荐的比例" | SRA 的核心是"不要漏掉该推荐的" |
| **平均倒数排名** | MRR | "第一个正确结果的位置" | SRA 的核心是"顶部的推荐必须精准" |
| **归一化折损累计增益** | NDCG@5 | "推荐的排序质量" | 考虑多级相关性(精确/同义/弱) |
| **未经请求推荐率** | Spurious@5 | "推荐了根本不相关的 skill 的比例" | 防止退化——宁可少推荐，不推荐错的 |

**权重设计**：
```
Score = Recall@5 × 0.30 + MRR × 0.35 + NDCG@5 × 0.25 + (1 - Spurious@5) × 0.10
```

### 2.5 分难度加权

不同难度层级的重要性不同：
```
总得分 = L1得分 × 0.20 + L2得分 × 0.35 + L3得分 × 0.30 + L4得分 × 0.10 + L5得分 × 0.05
```

这个权重反映：**同义映射和语义理解是最关键的改进方向**。

---

## 三、实现方案

### 3.1 SRA-eval 工具

```bash
# 一条命令跑完整评估
python3 scripts/sra-eval.py

# 输出示例:
# ╔════════════════════════════════════════════╗
# ║  SRA 推荐质量评估报告                      ║
# ╠════════════════════════════════════════════╣
# ║ 总得分: 73.2/100                          ║
# ║ - Recall@5:     0.68                      ║
# ║ - MRR:          0.72                      ║
# ║ - NDCG@5:       0.65                      ║
# ║ - Spurious@5:   0.12 (越低越好)           ║
# ╠════════════════════════════════════════════╣
# ║ 按难度分层:                                ║
# ║ L1 精确匹配:   92.5 ✅                    ║
# ║ L2 同义映射:   68.3 ⚠️                    ║
# ║ L3 语义理解:   45.1 ❌                     ║
# ║ L4 多跳推理:   22.0 ❌                     ║
# ║ L5 噪声抑制:   95.0 ✅                     ║
# ╚════════════════════════════════════════════╝
```

### 3.2 自动生成 Qrels

核心函数伪代码：

```python
def generate_qrels(skills):
    """
    从 279 个 SKILL.md 的 triggers 和 metadata 自动生成相关性判断。
    无需人工标注。

    策略：
    1. 对每个 test_query，提取其关键词
    2. 对每个 skill，检查其 triggers 是否命中这些关键词
    3. name 和 category 也参与匹配，但权重降一级
    4. 输出标准 TREC qrel 格式: query_id 0 skill_id relevance
    """
    qrels = {}
    for qid, query in test_queries.items():
        query_kws = extract_keywords(query)
        query_expanded = expand_with_synonyms(query_kws)

        rels = []
        for sid, skill in enumerate(skills):
            relevance = compute_relevance(query_expanded, skill)
            if relevance > 0:
                rels.append((sid, relevance))

        qrels[qid] = rels
    return qrels


def compute_relevance(query_expanded, skill):
    """
    多级相关性判断：
    - 2: 精确 trigger 匹配
    - 1: 同义词扩展后匹配
    - 0.5: name/category 部分命中
    - 0: 不相关
    """
    triggers = [t.lower() for t in skill.get("triggers", [])]
    name = skill.get("name", "").lower()
    category = skill.get("category", "").lower()
    tags = [t.lower() for t in skill.get("tags", [])]

    for word in query_expanded:
        w = word.lower()
        if w in triggers:
            return 2
        if w in name:
            return 1.5
        if w in tags or w in category:
            return 1
        # 部分匹配
        for t in triggers:
            if len(w) >= 3 and (w in t or t in w):
                return 1
    return 0
```

### 3.3 评估脚本设计

```
sra-eval.py 文件结构:
├── load_test_queries()     # 加载 100 个分层测试查询
├── generate_qrels()        # 从 skill triggers 生成 ground truth
├── run_evaluation()        # 对每个查询调 sra recommend，收集结果
├── compute_metrics()       # 计算 Recall/MRR/NDCG/Spurious
├── report()                # 按难度分层报告
└── compare()               # 与上次运行结果对比（改进/退化/不变）
```

### 3.4 测试查询示例

```python
TEST_QUERIES = {
    # L1: 精确匹配 (30个)
    "L1_ppt": {"query": "ppt", "expected_skills": ["pptx-guide"]},
    "L1_pdf": {"query": "pdf", "expected_skills": ["pdf-layout"]},
    "L1_git": {"query": "git", "expected_skills": ["git-advanced-ops"]},
    "L1_feishu": {"query": "飞书", "expected_skills": ["feishu"]},
    "L1_mermaid": {"query": "mermaid", "expected_skills": ["mermaid-guide"]},
    # ... 25个更多

    # L2: 同义映射 (30个)
    "L2_slides": {"query": "幻灯片", "expected_skills": ["pptx-guide"]},
    "L2_database_design": {"query": "设计数据库", "expected_skills": ["(无精确匹配，期望相关领域skill)"]},
    "L2_architecture_diagram": {"query": "画架构图", "expected_skills": ["architecture-diagram"]},
    "L2_code_review": {"query": "审查代码", "expected_skills": ["code-review"]},
    # ... 26个更多

    # L3: 语义理解 (20个)
    "L3_make_ppt": {"query": "帮我把设计稿做成能演示的PPT"},
    "L3_search_news": {"query": "帮我搜索最新的AI行业新闻"},
    # ... 18个更多

    # L4: 多跳推理 (10个)
    "L4_daily_report": {"query": "每天自动爬取新闻生成PDF摘要发飞书"},

    # L5: 噪声检测 (10个)
    "L5_weather": {"query": "今天天气怎么样"},
    "L5_greeting": {"query": "你好"},
}
```

---

## 四、为什么这个设计方案适合 SRA

| 设计决策 | 理由 |
|---------|------|
| **Qrels 自动生成（基于 trigger）** | SRA 的 trigger 字段天然是 ground truth，无需人工标注 |
| **按难度分层** | 可以定位"哪个环节弱"（精确匹配？同义映射？语义？） |
| **4 个核心指标** | Recall/MRR/NDCG/Spurious 覆盖全面且业界标准 |
| **单脚本运行** | `python3 sra-eval.py` 一次出完整报告 |
| **可对比历史** | 每次修改后运行，自动显示"改进/退化/不变" |
| **100 个查询覆盖 279 skill** | 比 4 个手动测试的代表性提高 25 倍 |

---

## 五、与现有测试的关系

```
现有测试 (pytest tests/)
├── test_matcher.py     ✅  保留 — 白盒测试（单个匹配算法的单元测试）
├── test_indexer.py     ✅  保留 — 索引构建测试
├── test_benchmark.py   ✅  保留 — 性能基准
└── test_coverage.py    ⚠️  需要升级 — 用 Qrels 替代简单的"能否被识别"

新增测试工具
└── scripts/sra-eval.py 🆕  新加 — 完整 Cranfield 范式的推荐质量评估
     ├── 100 个分层查询
     ├── 自动 Qrels 生成
     ├── 4 个 IR 核心指标
     └── 难度分层报告
```

---

## 六、参考来源

| 来源 | 核心借鉴 |
|------|---------|
| Cranfield Experiments (Cleverdon 1967) | 测试集三要素：文档/查询/相关性判断 |
| TREC Ad Hoc Track (NIST 1992-1999) | 池化(pooling)方法、MAP/NDCG 指标标准化 |
| Meta AI RAG Evaluation (2024) | 简单查询高估 25-30%，必须分层测试 |
| Weaviate IR Metrics Guide | Recall/MRR/NDCG 的计算实现 |
| Stanford CS276 IR Evaluation | NDCG 多级相关性处理的数学定义 |
| Tweag RAG Evaluation Framework (2024) | 构建 benchmark + 参数空间 + 实验追踪 |
