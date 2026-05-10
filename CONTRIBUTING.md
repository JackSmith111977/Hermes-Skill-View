# SRA — Skill Runtime Advisor 贡献指南

> **版本:** v2.0 | **更新:** 2026-05-10

感谢你对 SRA 的关注！以下是如何参与贡献的完整指南。

---

## 目录

1. [报告 Bug](#报告-bug)
2. [提出新功能](#提出新功能)
3. [提交代码](#提交代码)
4. [编码规范](#编码规范)
5. [测试规范](#测试规范)
6. [文档规范](#文档规范)
7. [Git 规范](#git-规范)
8. [PR 审查流程](#pr-审查流程)

---

## 🐛 报告 Bug

1. 使用 [Bug Report 模板](https://github.com/JackSmith111977/Hermes-Skill-View/issues/new?template=bug_report.md)
2. 提供完整的环境信息（OS、Python 版本、SRA 版本）
3. 附上复现步骤和期望行为
4. 如果涉及 Daemon 运行问题，附上日志文件：`~/.sra/srad.log`

---

## 💡 提出新功能

1. 先搜索 [已有的 Issue/Discussion](https://github.com/JackSmith111977/Hermes-Skill-View/issues) 确认是否已有人提过
2. 使用 [Feature Request 模板](https://github.com/JackSmith111977/Hermes-Skill-View/issues/new?template=feature_request.md)
3. 清晰描述解决的问题和你的方案

---

## 🔧 提交代码

```bash
# 1. Fork 本仓库
# 2. 创建特性分支
git checkout -b feat/my-feature     # 新功能
git checkout -b fix/my-bugfix       # Bug 修复
git checkout -b docs/my-doc-update  # 文档更新

# 3. 按规范提交（见下文 Git 规范）
git commit -m 'feat: add amazing feature'

# 4. 运行测试
python3 -m pytest tests/ -v

# 5. 推送到分支
git push origin feat/my-feature

# 6. 创建 Pull Request
```

---

## 📐 编码规范

### 命名约定

| 类型 | 规范 | 示例 |
|:---|:---|:---|
| 模块/包 | `snake_case` | `skill_advisor`, `runtime` |
| 类 | `PascalCase` | `SkillAdvisor`, `SkillMatcher` |
| 函数/方法 | `snake_case` | `recommend()`, `extract_keywords()` |
| 私有方法 | `_snake_case` 前缀 | `_handle_request()`, `_match_lexical()` |
| 常量 | `UPPER_SNAKE_CASE` | `THRESHOLD_STRONG`, `PID_FILE` |
| 变量 | `snake_case` | `skill_name`, `input_words` |
| 类型变量 | `PascalCase` | `SkillDict = Dict[str, Any]` |

### 类型标注

**所有公开函数必须包含完整的类型标注：**

```python
# ✅ 正确
def recommend(self, query: str, top_k: int = 3) -> Dict[str, Any]:
    ...

# ❌ 错误
def recommend(self, query, top_k=3):
    ...
```

**复杂返回值使用 `TypedDict`：**

```python
from typing import TypedDict

class Recommendation(TypedDict):
    skill: str
    score: float
    confidence: str
    reasons: List[str]
```

### 异常处理

```python
# ✅ 正确：区分异常类型，保留日志
try:
    result = risky_operation()
except FileNotFoundError:
    logger.debug("文件不存在，跳过")
    return default_value
except YAMLError as e:
    logger.error("YAML 解析失败: %s", e)
    raise  # 关键路径向上传播

# ❌ 禁止：静默吞噬所有异常
try:
    result = risky_operation()
except:
    pass
```

### 魔法数字

```python
# ❌ 禁止：硬编码分值
score += 30  # 这是什么？

# ✅ 正确：命名常量
class MatchWeight:
    NAME_EXACT = 30
    TRIGGER_HIT = 25
    TAG_HIT = 15

score += MatchWeight.NAME_EXACT
```

### 日志规范

```python
# 不同级别对应不同场景
logger.debug("输入关键词: %s", input_words)     # 调试信息
logger.info("索引重建完成: %d 个 skill", count)  # 正常流程节点
logger.warning("配置项 %s 无效，使用默认值", key)  # 可恢复的问题
logger.error("端口 %d 绑定失败: %s", port, e)     # 不可恢复的错误
```

### Docstring 规范

```python
def score(self, input_words: Set[str], skill: Dict, stats: Dict) -> Tuple[float, Dict, List[str]]:
    """对单个 skill 进行四维评分
    
    Args:
        input_words: 用户输入的关键词集合
        skill: 技能数据字典
        stats: 场景记忆统计数据
        
    Returns:
        (total_score, details_dict, reasons_list)
            total_score: 0-100 的综合评分
            details: 各维度得分明细
            reasons: 匹配原因（用于展示）
            
    Raises:
        ValueError: 当 input_words 为空时
    """
```

---

## 🧪 测试规范

### 测试类型

| 类型 | 文件命名 | 说明 | 执行频率 |
|:---|:---|:---|:---:|
| 单元测试 | `test_<module>.py` | 测试单个函数/类 | 每次提交 |
| 集成测试 | `test_api_integration.py` | 测试 HTTP/Socket API | 每次提交 |
| 覆盖率测试 | `test_coverage.py` | 测试技能识别率 | 每次发布 |
| 基准测试 | `test_benchmark.py` | 性能基准 | 每次发布 |

### 测试覆盖要求

| 层级 | 要求 | 截止 |
|:---|:---|:---:|
| matcher.py | ≥ 90% | v2.0 |
| indexer.py | ≥ 85% | v2.0 |
| advisor.py | ≥ 70% | v2.0 |
| memory.py | ≥ 70% | v2.0 |
| daemon.py | ≥ 60% | v2.0 (SRA-003-14) |
| cli.py | ≥ 50% | v2.0 (SRA-003-14) |

### 测试方法

```python
# 使用 pytest
# 使用 tmp_path fixture 避免污染真实环境
# 使用 monkeypatch 模拟外部依赖

def test_recommend_pdf(self, tmp_path, monkeypatch):
    """PDF 查询应推荐 pdf 相关 skill"""
    advisor = SkillAdvisor(skills_dir=str(tmp_path))
    # 创建测试 skill
    create_test_skill(tmp_path, "pdf-layout", ["pdf", "layout"])
    advisor.refresh_index()
    
    result = advisor.recommend("生成PDF文档")
    names = [r["skill"] for r in result["recommendations"]]
    assert any("pdf" in n.lower() for n in names)
```

### 测试命名

```python
# 格式：test_<场景>_<期望行为>
def test_empty_directory_returns_zero(): ...
def test_chinese_trigger_should_match(): ...
def test_unrelated_query_should_get_low_score(): ...
```

---

## 📖 文档规范

### 文件体系

| 文件 | 用途 | 必须存在？ |
|:---|:---|:---:|
| `README.md` | 项目概要、快速开始 | ✅ |
| `docs/ARCHITECTURE.md` | 架构标准 | ✅ |
| `docs/API-REFERENCE.md` | API 参考 | ✅ |
| `docs/VERSIONING.md` | 版本规约 | ✅ |
| `CHANGELOG.md` | 版本日志 | ✅ |
| `CONTRIBUTING.md` | 贡献指南 | ✅ |

### 文档更新规则

1. **代码改了必须同步文档** — 新增端点时更新 `API-REFERENCE.md`
2. **架构变了必须更新 ARCHITECTURE.md** — 模块拆分/合并时
3. **每个 PR 必须关联文档变更** — 无文档变更的 PR 会被要求补充

---

## 🔄 Git 规范

### 提交信息格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

<body>
```

| Type | 用途 | 示例 |
|:---|:---|:---|
| `feat` | 新功能 | `feat(matcher): 增加场景记忆权重因子` |
| `fix` | Bug 修复 | `fix(daemon): 修复 HTTP 端口重复绑定时崩溃` |
| `refactor` | 重构 | `refactor(matcher): 魔法数字提取为命名常量` |
| `test` | 测试 | `test(daemon): 增加 cmd_start 单元测试` |
| `docs` | 文档 | `docs: 更新 API-REFERENCE.md 推荐端点` |
| `chore` | 杂项 | `chore: 更新依赖版本` |

### 分支命名

| 前缀 | 用途 |
|:---|:---|
| `feat/` | 新功能 |
| `fix/` | Bug 修复 |
| `docs/` | 文档 |
| `refactor/` | 重构 |
| `test/` | 测试 |

---

## ✅ PR 审查流程

### 审查清单

**提交前自查：**
- [ ] 代码遵循编码规范（命名、类型标注、异常处理）
- [ ] 无魔法数字硬编码
- [ ] 无 `except: pass`
- [ ] 新增功能有完整类型标注
- [ ] **已加载 commit-quality-check 并执行完整检查** ← 必做！
- [ ] 测试覆盖率不低于修改前
- [ ] 新功能有对应测试
- [ ] 文档同步更新
- [ ] CHANGELOG.md 有对应条目
- [ ] 提交信息符合 Conventional Commits

**审查者检查：**
- [ ] 代码逻辑正确性
- [ ] 边界条件和异常分支处理
- [ ] 向后兼容性
- [ ] 性能影响
- [ ] 测试覆盖率
- [ ] 文档完整性

---

## 🤝 行为准则

请保持友好、尊重、包容的交流氛围。

---

**感谢你为 SRA 做的贡献！❤️**
