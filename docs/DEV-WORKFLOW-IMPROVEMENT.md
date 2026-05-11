# SRA 开发工作流改进 — 深度分析与实施方案

> 作者: Emma (小玛)
> 日期: 2026-05-11
> 背景: Sprint 3 开发中暴露的 3 个系统性缺陷

---

## 一、问题 1：版本号迭代流程缺失

### 1.1 具体表现（来自 Sprint 3）

| 问题 | 后果 |
|:-----|:------|
| `pyproject.toml` 版本 `v1.2.1` 但 `__init__.py` 已是 `v1.3.0` | 构建时版本不一致 |
| 发布后手动改 4 处文件 | 遗忘风险高、容易错 |
| `CHANGELOG.md` Story 状态未同步 | 外部贡献者看到错误状态 |
| 没有版本 bump 的自动化工具 | 每次手动执行，无标准流程 |

### 1.2 根因分析

```
直接原因：版本号散落在多文件中手动维护
  ↓
深层原因：没有单一版本数据源（Single Source of Truth）
  ↓
根本原因：工作流中缺少「版本 bump 自动化」步骤，且无门禁检查版本一致性
```

### 1.3 改进方案

**引入 setuptools-scm，从 git tag 自动推导版本：**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=64", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "sra-agent"
dynamic = ["version"]

[tool.setuptools_scm]
version_file = "skill_advisor/_version.py"
```

**好处：**
- 版本 = git tag，永远唯一
- `pip install` 时自动推导（tag 对应正式版，commit 对应 dev 版）
- 删除 `__init__.py` 中的 `__version__`，改从 `_version.py` 导入
- `sra version` 自动显示真实版本

**规范的版本生命周期：**

```text
开发中:      v1.3.1.dev7+gabc123     (7 commits after v1.3.0)
预发布:      v1.4.0a1 / v1.4.0rc1   (alpha / release candidate)
正式发布:    v1.3.0 / v1.4.0         (git tag)
```

---

## 二、问题 2：GitHub Action CI/CD 缺失

### 2.1 具体表现

| 问题 | 后果 |
|:-----|:------|
| 测试全靠 boku 手动 `pytest -q` | 忘记跑测试就推送→可能 break 主分支 |
| 无自动 lint/类型检查 | 代码质量不一致 |
| 无自动发布流水线 | `sra upgrade` 需要手动 build + push |
| 无安全扫描 | 密钥泄露无法被发现 |

### 2.2 根因分析

```
直接原因：项目从 Hermes 内部工具提取时未建立独立 CI
  ↓
深层原因：开发工作流中没有「push/PR 时自动验证」的强制机制
  ↓
根本原因：缺乏「门禁优先」的开发文化 — 先建立防线再开发
```

### 2.3 改进方案

**创建三层 CI/CD 流水线：**

```yaml
# .github/workflows/ci.yml
层 1 — PR 门禁: push+PR → pytest + lint + typecheck
层 2 — 发布前: tag push → build + test + security scan
层 3 — 发布: tag push → PyPI publish + GitHub Release
```

**CI 流水线要点：**
- `pytest` + fixtures（无需 Hermes 环境）
- `ruff` lint + `mypy` type check（逐步引入）
- `pip-audit` 依赖安全扫描
- `actions/attest-build-provenance` 构建背书

---

## 三、问题 3：文档对齐门控覆盖不全

### 3.1 具体表现（Sprint 3 分析误差回溯）

这是最严重的问题。boku 在 Sprint 3 开始时，**信任了静态文档（TECHDEBT-ANALYSIS.md）而非验证代码现实**，导致：

| boku 最初以为 | 实际状态 | 误差原因 |
|:-------------|:---------|:---------|
| `test_dropin.py` 不存在 (T-7) | ✅ 290行已存在 | TECHDEBT-ANALYSIS 未更新 |
| A-7 线程安全未修复 | ✅ SRA-003-18 已修 | 文档快照过时 |
| C-9 类型标注 33% | ✅ SRA-003-19 已修至84% | 文档快照过时 |
| C-7 print→logging 未做 | ✅ indexer.py 已修 | 文档快照过时 |

### 3.2 根因分析

```
直接原因：boku 读取了过时的 TECHDEBT-ANALYSIS 快照
  ↓
深层原因1：没有「先运行 doc-alignment --verify 获取最新状态」的强制步骤
深层原因2：文档没有「last_verified: 2026-05-11」时间戳标记
深层原因3：没有「代码状态 vs 文档断言」的自动化交叉验证
  ↓
根本原因：开发工作流的「分析阶段」缺少一个强制性的 Reality Check 门禁：
  「不要问文档说了什么，去问代码现在是什么状态」
```

### 3.3 改进方案

**引入「P0 铁律」到开发工作流：**

```text
🔴 铁律 0 — Reality Check First
  在任何分析开始前，必须执行：
    1. git log --oneline -30      — 看最近发生了什么
    2. git diff --stat            — 看有啥未推送的
    3. 扫描代码库关键指标         — 实际测试数、文件是否存在
    4. 然后才读文档              — 带着「验证」心态读
```

**文档标记规范：** 每个分析文档末尾加上：
```markdown
---
> **最后验证**: 2026-05-11 | **测试覆盖验证**: 290/290 passed
> **数据来源**: 代码扫描 + pytest --collect-only + git log
```

**doc-alignment 协议升级到 v3.1 — 新增「分析前对齐」阶段：**

```text
Phase 0: 分析前对齐（新增）
  在读取任何文档前执行：
    1. python3 generate-project-report.py --verify
       → 检测版本漂移、测试数量漂移
    2. git log --oneline -30 | head -10
       → 了解最近的代码变更
    3. 交叉验证文档声明 vs 代码实际
       → 文档说「测试有 200」，pytest 实际说「300」
       → 文档说「A-7 未修复」，git log 说「已修复」
    4. 只有验证通过后，才相信文档的内容
```

---

## 四、统一改进方案 — SRA 开发工作流 v4.0

### 4.1 全流程

```text
[Phase 0] 分析前对齐 ← 新增 Reality Check
  ├── run doc-alignment --verify
  ├── git log --oneline -30
  └── 交叉验证文档 vs 代码实际
       ↓ pass
[Phase 1] 版本管理 ← 改进
  ├── setuptools-scm 自动化版本（单源）
  └── 不手动改版本号，只打 git tag
       ↓
[Phase 2] 开发
  ├── 标准路径（development-workflow-index 决策树）
  ├── TDD / 子代理驱动
  └── 每次提交带文档对齐
       ↓
[Phase 3] CI 验证 ← 新增
  ├── GitHub Actions 自动运行
  │   ├── pytest + fixtures
  │   ├── ruff lint
  │   └── mypy type check
  └── PR 门禁（未通过不能合并）
       ↓
[Phase 4] 发布 ← 改进
  ├── git tag → 自动触发 CI/CD
  │   ├── 测试 + 安全扫描
  │   ├── Build wheel
  │   └── PyPI publish
  └── GitHub Release 自动创建
       ↓
[Phase 5] 复盘 ← 新增
  └── 经验沉淀、workflow 改进
```

### 4.2 立即实施清单

| # | 任务 | 负责人 | 估时 |
|:-:|:-----|:------|:----:|
| 1 | pyproject.toml 改为 setuptools-scm 动态版本 | boku | 20min |
| 2 | 创建 `.github/workflows/ci.yml`（pytest + fixtures） | boku | 15min |
| 3 | 创建 `.github/workflows/release.yml`（PyPI + Release） | boku | 15min |
| 4 | doc-alignment 协议 v3.1 — Phase 0 分析前对齐 | boku | 10min |
| 5 | 在 SOUL.md 中加入 P0 铁律「Reality Check First」 | boku | 5min |
| 6 | 更新 AGENTS.md 开发工作流章节 | boku | 10min |

---

## 五、核心教训

| 教训 | 变成的铁律 |
|:-----|:-----------|
| **信任但验证** — 永远用代码现实验证文档声明 | Reality Check First 🔴 |
| **自动化一切手工版本操作** — 手工 = 必然出错 | 版本号只来自 git tag |
| **门禁先行** — 先建立防线再开发 | CI/CD 必须在代码之前 |
| **分析文档要带时间戳** — 无验证时间的文档是可疑的 | 文档标记 last_verified |
| **用 git log 而非文档了解代码** — git 是唯一真实的历史记录 | `git log --oneline` 是第一步 |
