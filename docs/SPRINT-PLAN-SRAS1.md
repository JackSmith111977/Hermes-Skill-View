# Sprint Plan: SRA P0 质量提升

## Sprint 信息
- **Sprint 名称**: SRAS1-P0-QUALITY
- **开始日期**: 2026-05-04
- **分支**: `feat/design-philosophy-overhaul` → 每个 Story 开子分支
- **验证策略**: 每个 Story 完成前后做对照测试，数据证明改进效果

## Story 拆解

### Story 1: 修复同义词映射粒度 + 中文匹配
**分支**: `sra-s1-synonyms-match`
**改动文件**: synonyms.py (≈10行), indexer.py (≈6行), matcher.py (≈5行)
**预期收益**: 
- ✅ 消除"设计数据库→PDF排版"的误匹配
- ✅ 覆盖率从 86.9% 提升到 90%+

**测试方法**:
```
改进前: sra recommend "设计数据库" → Top1: pdf-layout (错误)
改进后: sra recommend "设计数据库" → Top1: 数据库相关 skill (正确)
```

### Story 2: match_text 加入 body_keywords
**分支**: `sra-s1-body-keywords`
**改动文件**: indexer.py (1行)
**预期收益**: 未识别 36 个技能中的一部分被覆盖

**测试方法**:
```
改进前: sra recommend "AI Agent 框架" → 未覆盖某些特定技能
改进后: sra recommend "AI Agent 框架" → 更多精确匹配
```

### Story 3: watch_skills_dir 文件监听
**分支**: `sra-s1-file-watch`
**改动文件**: daemon.py (≈50行)
**预期收益**: 新增 SKILL.md 后 30 秒内被感知（而不是 3600 秒）

**测试方法**:
```
改进前: 创建 skill → 等 3600 秒
改进后: 创建 skill → 30 秒内 SRA 自动刷新索引
```

### Story 4: 为 36 个未识别技能补 trigger
**分支**: `sra-s1-coverage-fix`
**改动文件**: 外部技能文件（不是 SRA 代码本身）
**预期收益**: 覆盖率从 86.9% 提升到 95%+

**测试方法**:
```
改进前: sra coverage → 86.9%
改进后: sra coverage → 95%+
```

## 迭代顺序

```
Sprint SRAS1-P0-QUALITY
├── Story 1: Synonyms + Match Fix (最高优先: 直接影响推荐质量)
│   └── 完成后 → 对照测试 → PR 请求
├── Story 2: body_keywords (低优先级, 但改动极小)
│   └── 完成后 → 对照测试 → PR 请求
├── Story 3: File Watch (独立, 不依赖任何其他 Story)
│   └── 完成后 → 对照测试 → PR 请求
└── Story 4: Skill Coverage (需要 Story 1+2 完成后效果最大化)
    └── 完成后 → 对照测试 → PR 请求
```

## 验证框架

每个 Story 必须完成：
1. **改进前测试**: 有问题的场景 → 记录行为
2. **实施修复**: 修改代码
3. **回归测试**: 运行 `pytest tests/` 确保没有退化
4. **改进后测试**: 同一场景 → 记录行为
5. **对比汇报**: 改进前 vs 改进后
6. **提交 + PR**: 带着测试证据
