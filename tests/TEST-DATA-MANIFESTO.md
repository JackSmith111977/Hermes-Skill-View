# SRA 测试数据宣言 (Test Data Manifesto)

> **最后更新**: 2026-05-11
> **核心理念**: 所有测试必须基于可提交到 git 的静态 fixture 数据，**不得**依赖运行时环境（如 `~/.hermes/skills`）。

---

## 🗂️ Fixture 总览

| 路径 | 类型 | 数量 | 说明 |
|:-----|:-----|:----:|:-----|
| `tests/fixtures/skills/` | SKILL.md 目录 | 318 个 | 从 Hermes Agent 真实 skill 提取的完整 SKILL.md |
| `tests/fixtures/skills_yaml/` | YAML 原始文件 | 314 个 | 每个 skill 的 YAML frontmatter 单独文件 |
| `tests/fixtures/skills_yaml/_all_yamls.json` | JSON 聚合 | 314 条 | 全部 skill 的结构化数据（含 category/triggers/tags） |

### 数据来源

从 `~/.hermes/skills/` 中所有 **SKILL.md** 文件提取的 **YAML frontmatter**，提取时间: 2026-05 (v1.1.0)。

### 更新策略

当 Hermes Agent 的 skill 库有重大更新时，重新提取：

```bash
# 重新生成 fixture（由项目维护者手动执行）
python3 scripts/extract_fixtures.py
```

---

## 📐 如何使用

### 方式 A: 通过 conftest.py fixture（推荐）

```python
# tests/conftest.py 已提供标准 fixture

def test_my_feature(advisor_from_fixtures):
    """使用 fixture 数据创建 SkillAdvisor"""
    result = advisor_from_fixtures.recommend("生成 PDF")
    assert len(result["recommendations"]) > 0

def test_with_raw_data(all_real_skills_yaml):
    """直接使用原始 YAML 数据"""
    assert len(all_real_skills_yaml) >= 300
```

### 方式 B: 直接引用路径

```python
import os
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "skills")

advisor = SkillAdvisor(skills_dir=FIXTURES_DIR)
```

### 方式 C: 在现有测试中迁移

**之前（有缺陷）**:
```python
@pytest.fixture
def advisor(tmp_path):
    hermes_skills = os.path.expanduser("~/.hermes/skills")
    if os.path.isdir(hermes_skills):
        return SkillAdvisor(skills_dir=hermes_skills, data_dir=str(tmp_path))
    return SkillAdvisor(data_dir=str(tmp_path))  # CI 中无技能数据！
```

**之后（正确）**:
```python
@pytest.fixture
def advisor(advisor_from_fixtures):
    return advisor_from_fixtures
```

---

## 🔴 铁律

| # | 规则 | 违反后果 |
|:-:|:-----|:---------|
| 1 | **禁止在测试中直接引用 `~/.hermes/skills`** | CI 无法运行、测试不完整 |
| 2 | **禁止使用 `pytest.skip()` 作为环境差异的默认方案** | 测试在 CI 中静默消失 |
| 3 | **新测试必须优先使用已有 fixture**，而不是创建新的一次性数据 | 维护成本上升、数据碎片化 |
| 4 | **引用 fixture 前必须验证文件存在性**（用 `read_file` 或 `grep -rl`，不用幻觉） | 假阳性/假阴性测试 |

---

## 🔄 工作流集成

### Pre-flight 检查（AGENTS.md Phase 0）

```bash
# 在写新测试前执行
grep -rn "FIXTURES_DIR\|fixtures/" tests/ 2>/dev/null | head -5
```

如果有 fixture 目录（`tests/fixtures/` 存在），新测试必须优先使用它。

### CI 验证

```yaml
- name: 验证测试 Fixture 完整性
  run: |
    python3 -c "
    import os
    d = 'tests/fixtures/skills'
    count = sum(1 for _,_,files in os.walk(d) for f in files if f == 'SKILL.md')
    assert count >= 300, f'Fixture 不完整: {count}'
    print(f'✅ {count} valid fixture skills')
    "
```

---

## 📝 更新日志

| 日期 | 变更 | 原因 |
|:-----|:-----|:-----|
| 2026-05-11 | 创建 | test_contract.py 绕过 fixture 使用 ~/.hermes/skills → CI 失败 |
