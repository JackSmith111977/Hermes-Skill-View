# SRA 开发路线图 (Roadmap)

> Skill Runtime Advisor — 让 AI Agent 知道自己有什么能力，以及什么时候该用什么能力。
> 版本: v1.1.0 | 更新: 2026-05-07

---

## ✅ v1.1.0 已完成

- [x] 测试框架重构：从 15 个假 fixtures → 313 个真实技能 YAML 提取
- [x] L0-L4 五级验证体系：pytest → CLI → HTTP → 仿真 → 压力
- [x] 测试门禁：assert skills >= 300 阻止 CI 退化到假数据
- [x] 覆盖率分析：整体 94.9%，有 trigger 技能 99.4%
- [x] 复盘经验沉淀到 skill-eval-cranfield

---

## 🚀 v1.2.0 计划

### 1. 🐛 同义词桥接修复
| 问题 | 影响 | 方案 |
|:-----|:-----|:-----|
| "发飞书消息" → himalaya (59分) | 飞书用户被推荐邮件工具 | 检查 synonyms 中 himalaya 与飞书的交叉干扰路径 |
| "画系统设计图" → NONE (0分) | 系统设计需求完全无匹配 | 新增 "系统设计" ↔ "architecture diagram" 同义词 |
| "用 python 画个折线图" → NONE (0分) | 图表需求无匹配 | 考虑加入 matplotlib/seaborn 映射或新建 chart skill |

**策略**: 先跑基线评估 → 单变量修改 → 重跑 L0-L4 全套验证

### 2. 🌐 HTTP API 完善
| 端点 | 当前状态 | 目标 |
|:-----|:---------|:-----|
| `GET /coverage` | 404 Not Found | 返回覆盖率 JSON |
| `GET /recommend` | 不支持 GET | 支持 GET ?q=xxx 查询 |
| `POST /refresh` | 需要实现 | 手动触发索引刷新 |
| 响应时间 | ~225ms | 优化到 < 100ms（缓存推荐结果） |

### 3. 🧪 CI/CD 增强
- [ ] 添加 pyproject.toml 中的 pytest 配置
- [ ] GitHub Actions 缓存 pytest fixtures 加速 CI
- [ ] 添加代码风格检查 (ruff/formatter)
- [ ] 添加类型检查 (mypy)

### 4. 📊 量化评估体系
- [ ] 实现 Cranfield 范式完整的 Recall/MRR/NDCG 评估脚本
- [ ] 自动化 Qrels 生成（从 triggers 自动推导）
- [ ] 按 L1-L5 难度分层报告
- [ ] 基线对比模式 (`--compare`)

### 5. 📝 文档完善
- [ ] 英文版 README 同步更新
- [ ] API 文档（HTTP 端点参考）
- [ ] 贡献指南 (CONTRIBUTING.md)

---

## 🔮 远期规划

### v2.0 — 多 Agent 适配器生态
- [ ] 标准协议层：统一各 Agent 的 skill 接口
- [ ] Claude Code 适配器完善
- [ ] Codex CLI 适配器
- [ ] OpenCode 适配器
- [ ] 自定义 Agent 适配器 SDK

### v2.x — 智能推荐增强
- [ ] 场景记忆持久化（跨会话）
- [ ] 用户行为学习（基于 accept/reject 反馈）
- [ ] 负反馈学习（明确不推荐的 skill）
- [ ] 组合技能推荐（多 skill 编排）

---

## 📋 当前 Sprint 状态

| 状态 | 任务 | 负责人 |
|:----:|:-----|:-------|
| ✅ | 真实技能提取 + Fixture 改造 | Emma |
| ✅ | 测试门禁 + 覆盖率验证 | Emma |
| ✅ | 复盘沉淀 | Emma |
| ⏳ | 同义词桥接修复 | — |
| ⏳ | HTTP /coverage 端点 | — |
| ⏳ | CI 优化 | — |
