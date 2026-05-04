# EPIC-002: SRA P0 质量提升 — 索引实时性与匹配精度的根因分析与修复

> **BMAD Epic**: SRA v1.2.0 版本质量提升
> **创建日期**: 2026-05-04
> **分析者**: Emma (小喵)
> **状态**: analysis

---

## 🎯 问题总览

| ID | 问题 | 严重程度 | 影响范围 |
|----|------|---------|---------|
| P0-1 | **watch_skills_dir 文件监听未生效** | 🔴 P0 | 新加 SKILL.md 最多等 1 小时才被感知 |
| P0-2 | **中文长文本匹配精度不足** | 🔴 P0 | 36 个技能未识别 + 错误推荐 |

---

## 📋 P0-1: watch_skills_dir 文件监听未生效

### 现象

```
添加新 skill → SRA 不感知 → 需要 POST /refresh 或等 1h 定时刷新
```

### 根因分析（代码深度追踪）

#### 定位 1：`daemon.py` 中 `_auto_refresh_loop` 的定时机制

```python
# daemon.py L385-L396
def _auto_refresh_loop(self):
    interval = self.config.get("auto_refresh_interval", 3600)  # ← 3600秒 = 1小时
    while self.running:
        time.sleep(interval)  # ← 纯时间等待，不是文件监听
```

**根因 1a**: 定时刷新是`time.sleep(3600)`，不是文件系统事件监听。`watch_skills_dir: true` 配置项被读取了，但**没有任何代码实现**文件变更监听。

#### 定位 2：`advisor.py` 中的 refresh_index

```python
# advisor.py L57-L61
def refresh_index(self) -> int:
    count = self.indexer.build()  # ← 每次全量重建索引
    self._index_loaded = True
    return count
```

**根因 1b**: `refresh_index()` 每次都是全量重建（扫描所有 SKILL.md），不是增量更新。当技能库 275 个时，全量重建需要一定时间。

#### 定位 3：`indexer.py` 中 build 的扫描方式

```python
# indexer.py L96
sk_files = glob.glob(os.path.join(self.skills_dir, '**/SKILL.md'), recursive=True)
```

**根因 1c**: 索引构建依赖 `glob`，每次遍历所有子目录。文件监听需要 `watchdog` 或 `inotify` 机制。

#### 根本结论

| 层面 | 问题 |
|------|------|
| **配置层** | `watch_skills_dir: true` 有这个配置项，但没有任何代码消费它 |
| **实现层** | 没有使用 `watchdog`、`inotify`、`pyinotify` 等文件系统监听库 |
| **架构层** | 刷新是全量重建，不是增量更新 |
| **API 层** | `/refresh` 端点存在但只能通过 `POST /refresh` 调用，`/recommend` 端点不触发刷新 |

### 影响范围

1. **用户体验**：新加的 SKILL.md 不能立即被推荐
2. **开发体验**：调试 skill 时需手动 `sra start` 或 `POST /refresh`
3. **运行时可靠性**：依赖 1 小时间隔，有感知延迟

### 修复方案评估

| 方案 | 复杂度 | 依赖 | 推荐 |
|------|--------|------|------|
| A: 用 watchdog 做文件监听 | 中 | 需安装 `watchdog` 包 | ⭐ 长期推荐 |
| B: 纯 Python 轮询（效期戳+文件数量变化检测） | 低 | 无额外依赖 | ⭐ 当前推荐 |
| C: 缩短定时刷新间隔至 60s | 极低 | 无 | 替代方案 |

---

## 📋 P0-2: 中文匹配精度不足

### 现象

```
输入"设计数据库" → Top1 推荐 pdf-layout (52.8分) → 错误！

输入"画架构图" → Top1 architecture-diagram (47.5分) → 正确但分低

36 个技能完全无法被识别（覆盖率 86.9%）
```

### 根因分析（代码深度追踪）

#### 定位 1：`matcher.py` 词法匹配 — _match_lexical

```python
# matcher.py L100-L134
for word in word_list:
    w = word.lower()
    # ... 各种匹配规则
    
    if len(w) >= 2 and w in desc:
        score += 8  # ← 描述匹配得分过低
```

**根因 2a**: 描述匹配（desc）的分值只有 8 分，而同义词分值 25 分。如果同义词映射不准，光靠描述匹配难以拉到高分。

"设计数据库"被推荐为 `pdf-layout` 的原因：

```
"设计数据库" → extract_keywords("设计数据库")
  → 中文拆词："设计", "数据", "数据库", "计数", "计数"
  → 同义词扩展： "设计" → SYNONYMS["计划"] → ["plan", "规划", "方案", "architecture"]
  → 反向匹配： "architecture" → SYNONYMS["架构"] → 命中 pdf-layout 的 name 或 description
  → 获得同义词分 25 + 描述分 8 ≈ 33
  → 加上其他维度 ≈ 52.8
```

**关键问题**："设计"在中文里有多义性（设计（计划）vs 设计（数据库设计）），同义词表把"设计"映射给了"计划/方案/架构"，导致错误匹配。

#### 定位 2：`synonyms.py` 映射粒度

```python
# synonyms.py L47
"计划": ["plan", "planning", "规划", "设计", "方案", "architecture"],
```

**根因 2b**: 同义词映射太宽泛。"计划"包含了"设计"——但"设计数据库"中的"设计"不应该是"计划"。"架构"包含"design"——但"数据库设计"不应该是"architecture design"。

#### 定位 3：`indexer.py` 中文拆词策略

```python
# indexer.py L36-L43
chinese = re.findall(r'[\u4e00-\u9fff]+', text)
for ch in chinese:
    for i in range(len(ch)):
        for j in range(2, min(5, len(ch) - i + 1)):
            words.add(ch[i:i+j].lower())
```

**根因 2c**: 中文拆词策略是暴力 n-gram（2-4 字），没有语义边界。`"设计数据库"` 会被拆成 `"设计"、"计数"、"数据"、"据库"、"设计数"、"计数"、"数据库"`。其中 `"计数"` 完全没有意义，只会增加噪声。

#### 定位 4：未识别 36 个技能的分析

boku 运行覆盖率测试看到 36 个技能未被识别。分析原因：

| 原因分类 | 技能举例 | 数量（预估） |
|---------|---------|------------|
| ❌ 没有中文 trigger/description | obsidian, godmode, bmad-help | ~15 |
| ❌ trigger 太具体/不常用 | bmad-advanced-elicitation | ~8 |
| ❌ 纯英文无中文同义词映射 | bmad-tea, gds-quick-dev | ~8 |
| ❌ 名称与内容不符合中文常见查询 | bmad-testarch-automate | ~5 |

#### 定位 5：`indexer.py` 中 match_text 构建

```python
# indexer.py L132
match_text = f"{name} {description} {' '.join(triggers)} {' '.join(tags)}".lower()
```

**根因 2d**: `match_text` 没有包含 body_keywords。skill 正文中的中文关键词没有被纳入 match_text，导致仅靠 name/description/triggers/tags 这四部分匹配。如果这些部分都是英文，中文输入就无法匹配。

### 影响范围

1. **推荐质量**：用户说"设计数据库"却拿到 PDF 排版，信任度下降
2. **覆盖率**：36/275 = 13.1% 的技能对中文用户"不可见"
3. **Agent 体验**：Agent 依赖 SRA 做 skill 发现，错误的推荐导致 Agent 用错工具

### 修复方案评估

| 方案 | 复杂度 | 影响 | 推荐 |
|------|--------|------|------|
| A: 修复同义词映射粒度（拆分模糊映射） | 低 | 直接改善 | ⭐ P0 必做 |
| B: 给未识别的 36 个 skill 补充中文描述和 trigger | 中 | 覆盖全部 | ⭐ P0 必做（部分可脚本化） |
| C: 改进中文拆词策略（去除非语义 n-gram） | 中 | 减少噪声 | 强烈推荐 |
| D: match_text 加入 body_keywords | 低 | 扩大匹配面 | 推荐 |
| E: 加入 TF-IDF 权重（高质量词优先） | 高 | 深远影响 | 远期 |
| F: 边缘案例测试覆盖（中文多义词） | 中 | 质保 | 推荐 |

---

## 🗺️ 修复路线图（Story 层级）

### Story 2-1: 文件监听实现（P0-1）

**工作量估计**: ~2 小时
**核心改动**: `daemon.py`（~50 行新增）

| 子任务 | 复杂度 | 依赖 |
|--------|--------|------|
| 修改 _auto_refresh_loop 为双模式（定时+文件变更检测） | 中 | 无 |
| 添加校验和/文件数量检测实现轮询 | 低 | 无 |
| 新增 `sra refresh` 子命令显式触发刷新 | 低 | 无 |
| 更新 check-sra.py 检测 watch_skills_dir 是否生效 | 低 | check-sra.py |
| 单元测试：文件变更后索引是否刷新 | 中 | pytest |

### Story 2-2: 中文匹配精度（P0-2，部分）

**工作量估计**: ~3 小时
**核心改动**: `synonyms.py`, `matcher.py`, `indexer.py`

| 子任务 | 复杂度 | 依赖 |
|--------|--------|------|
| 修复同义词映射粒度（分离"设计"、"架构"等模糊映射） | 低 | 无 |
| match_text 中加入 body_keywords（L132 行修改） | 低 | indexer.py |
| 改进中文 n-gram 拆词策略（过滤噪声词） | 中 | indexer.py |
| 边缘测试：中英文混合查询 | 中 | test_matcher.py |

### Story 2-3: 未识别 36 个技能覆盖（P0-2，部分）

**工作量估计**: ~2 小时
**核心改动**: 不需要改代码，只需在 skill 仓库补 trigger

| 子任务 | 复杂度 | 依赖 |
|--------|--------|------|
| 扫描 36 个未识别技能，列出每项缺失的原因 | 低 | check-sra.py 的 coverage |
| 编写自动化脚本：批量检查 skills 的中文 trigger/description | 中 | 无 |
| 生成补种建议（自动生成中文 trigger 候选） | 中 | 无 |
| 验证覆盖率是否提升 | 低 | sra coverage |
