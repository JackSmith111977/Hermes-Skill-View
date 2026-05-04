# EPIC-002: SRA P0 质量提升 — 更新 v2（含前沿算法研究）

> **更新**：根据前沿论文和工业实践的研究，补充匹配算法改进方向
> **研究文档**：`docs/RESEARCH-MATCHING-ALGORITHMS.md`

---

## 新增章节：匹配算法改进路线图（基于前沿研究）

### 核心结论

根据对 Anthropic Contextual Retrieval (2024)、COLING 2025、arXiv 2024-2026、HackerNews 社区共识的深度研究：

**SRA 当前最需要的不是换一个新的匹配算法，而是修复现有算法的细节质量。**

原因：
1. SRA 的查询规模极小（275 个 SKILL.md），不需要向量数据库
2. SRA 的延迟要求极低（<50ms / 条），不允许增加 LLM 级别的计算
3. SRA 的部署环境只能依赖 CPU + 纯 Python 零额外依赖

### 推荐的渐进式改进方案

#### Phase 1: 零依赖修复（当前分支即可完成）

| 子任务 | 文件 | 改动量 | 预期收益 |
|--------|------|--------|---------|
| 修复 synonyms 映射粒度 | synonyms.py ~10行 | 极小 | 解决"设计数据库→PDF排版"错误 |
| match_text 加入 body_keywords | indexer.py 1行 | 极小 | 大幅提升未识别技能的覆盖率 |
| 改进中文 n-gram 拆词去噪声 | indexer.py ~5行 | 极小 | 减少"计数"等噪声词 |
| 给 36 个未识别技能补中文 trigger | 外部技能文件 | 中等 | 覆盖率从 86.9% → 95%+ |
| 修复 watch_skills_dir 文件监听 | daemon.py ~50行 | 小 | P0-1 解决 |

#### Phase 2: 可选 Embedding 增强（中期，非必需）

| 子任务 | 文件 | 改动量 | 预期收益 |
|--------|------|--------|---------|
| 可选加载 bge-small-zh-v1.5 | new `embedder.py` ~100行 | 中 | 语义匹配大幅提升 |
| Hybrid 评分融合（BM25 + Embedding） | 修改 matcher.py ~50行 | 中 | 结合精确匹配和语义匹配 |
| 可选 ONNX 加速 | embedder.py +50行 | 小 | 推理速度 4x 提升 |

**为什么选 bge-small-zh-v1.5**：150MB 模型、512 维向量、CPU 推理 20-30ms、中文 MTEB 排行前列。

**关键设计原则**：Embedding 必须是**可选依赖**——没有它 SRA 也能正常工作（fallback 到纯 BM25）。

#### Phase 3: 远期增强

| 子任务 | 说明 |
|--------|------|
| 反馈闭环 | Agent 使用推荐后自动记录，下次推荐优化权重 |
| Active Learning | 高频低匹配查询自动生成同义词候选人 |
| 多级推荐 | 不仅是 skill 级别，还能推荐 skill 内的具体章节 |

### 权威参考来源

| 来源 | 核心结论 | 适用性 |
|------|---------|--------|
| [Anthropic Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval) | Emb+BM25 降低 failure rate 49% | 核心参考 |
| [Hybrid BM25 Survey](https://www.emergentmind.com/topics/hybrid-bm25-retrieval) | Hybrid > 纯 BM25 > 纯 Embedding | 方向确认 |
| [Local Hybrid RAG (arXiv 2511.10297)](https://arxiv.org/abs/2511.10297) | 最优权重 30% BM25 + 70% Dense | 参数参考 |
| [BGE 中文模型](https://huggingface.co/BAAI/bge-small-zh-v1.5) | 轻量中文 embedding 标杆 | 模型选型 |
| [Anthropic Claude Cookbook](https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide) | 完整 Contextual + Hybrid 实现 | 实现参考 |
| [ACL Survey 2024](https://www.mdpi.com/2078-2489/15/6/332) | 四种匹配方法对比框架 | 评估框架 |
| [HackerNews Discussion](https://news.ycombinator.com/item?id=46080933) | "不要沉迷向量搜索，BM25 很多时候足够好了" | 设计原则 |
