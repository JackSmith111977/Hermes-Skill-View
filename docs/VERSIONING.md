# SRA 技术版本规约

> **版本:** v1.1 | **更新:** 2026-05-11

---

## 1. 版本策略

### 1.1 语义化版本 (SemVer)

本项目严格遵循 [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH
  ↑      ↑      ↑
  │      │      └── 向后兼容的 bug 修复
  │      └───────── 向后兼容的新功能
  └──────────────── 不兼容的 API 变更
```

**当前版本**: `1.4.0`（从 git tag 自动推导）

### 1.2 版本声明位置

| 位置 | 用途 | 同步方式 |
|:---|:---|:---:|
| `pyproject.toml` | pip 包元数据 | 构建时由 `scripts/set_version.py` 自动替换 |
| `skill_advisor/_version.py` | 运行时版本导出 | CI 构建时自动生成 |
| `skill_advisor/__init__.py` | 运行时适配 | 通过 `from ._version import version` 自动读取 |
| `CHANGELOG.md` | 版本变更日志 | 每次发布时手动更新 |

> **⚠️ v1.4.0 变更**：版本号不再手动写在 `__init__.py` 中，而是在 CI 发布流程中从 git tag 自动推导。

### 1.3 版本分支策略

```
main          ─── v1.1.0 ─── v1.2.0 ─── v1.2.1 ─── v1.3.0 ──▶
                   │            │           │           │
feat/             feat/       feat/       fix/        feat/
v1.1-enhance    v1.2-quality  hotfix-xx   v2.0-enforcement
```

| 分支 | 用途 | 合并目标 |
|:---|:---|:---:|
| `main` | 稳定发布版 | — |
| `feat/*` | 功能开发 | `main` |
| `fix/*` | Bug 修复 | `main` |
| `docs/*` | 文档更新 | `main` |

### 1.4 发布标签

**必须使用附注标签（annotated tag）：**

```bash
git tag -a v1.4.0 -m "Release v1.4.0 — 版本说明"
git push origin v1.4.0
```

标签格式：`v{MAJOR}.{MINOR}.{PATCH}`

> **⚠️ 不要使用轻量标签（`git tag v1.4.0`）**：
> - 轻量标签在 CI 中可能被 `setuptools-scm` 忽略
> - 历史版本 `v1.2.1`、`v1.3.0` 均为附注标签

### 1.5 发布流程（CI 自动化）

推送 tag 后，GitHub Actions 自动执行 `release.yml` 工作流：

```
你: git tag -a v1.4.0 -m "..."
    git push origin v1.4.0
                    ↓
GitHub Actions (release.yml):
  1. Set version from tag
     → 从 GITHUB_REF_NAME 提取版本号 (v1.4.0 → 1.4.0)
     → 写入 skill_advisor/_version.py
     → 设置 SETUPTOOLS_SCM_PRETEND_VERSION 环境变量
  2. 运行测试 (pytest)
  3. 构建 wheel + sdist
     → scripts/set_version.py 替换 pyproject.toml 为静态版本
  4. 发布到 PyPI (Trusted Publishing)
  5. 创建 GitHub Release
```

**为什么不用 `setuptools-scm` 自动检测 tag？**
- CI 环境中 `git describe`（默认，不包含 `--tags`）有时无法正确识别附注标签
- `SETUPTOOLS_SCM_PRETEND_VERSION` 在 `python -m build` 的隔离环境中可能不被继承
- 改为显式从 `GITHUB_REF_NAME` 提取版本号 + 写 `_version.py` + 替换 `pyproject.toml`，三保险确保版本正确

---

## 2. Python 版本策略

### 2.1 支持的版本

| Python 版本 | 状态 | 说明 |
|:---:|:---:|:---|
| 3.8 | ✅ 兼容 | 最低要求（`pyproject.toml` 中 `requires-python = ">=3.8"`） |
| 3.9 | ✅ 兼容 | |
| 3.10 | ✅ 兼容 | |
| 3.11 | ✅ 兼容 | 当前开发环境 |
| 3.12 | ✅ 兼容 | |
| 3.13+ | ⚠️ 未测试 | 预计兼容，待验证 |

### 2.2 Python 版本特性使用规范

| 特性 | 最低版本 | 允许使用？ |
|:---|:---:|:---:|
| f-string | 3.6 | ✅ |
| typing 模块 | 3.5 | ✅ |
| dataclasses | 3.7 | ✅ |
| match/case | 3.10 | ❌（兼容 3.8/3.9） |
| `zoneinfo` | 3.9 | ❌（兼容 3.8） |
| `StrEnum` | 3.11 | ❌（兼容 3.8/3.9/3.10） |
| `Self` type | 3.11 | ❌ |

---

## 3. 依赖管理

### 3.1 核心依赖

| 包 | 最低版本 | 用途 | 可替代？ |
|:---|:---:|:---|:---:|
| `pyyaml` | ≥5.1 | YAML frontmatter 解析 | ❌ 核心功能 |
| `python` | ≥3.8 | 运行环境 | ❌ |

### 3.2 开发依赖

| 包 | 最低版本 | 用途 |
|:---|:---:|:---|
| `pytest` | ≥7.0 | 测试框架 |
| `pytest-benchmark` | ≥4.0 | 性能基准测试 |

### 3.3 可选依赖

| 包 | 用途 | 安装方式 |
|:---|:---|:---|
| 无（当前无可选依赖） | | |

### 3.4 依赖管理铁律

| 规则 | 说明 |
|:---|:---|
| 🔴 禁止使用 `pip freeze > requirements.txt` | 直接依赖 vs 传递依赖混淆 |
| 🟡 新增依赖必须更新 `pyproject.toml` | 核心依赖放 `dependencies`，开发依赖放 `[project.optional-dependencies] dev` |
| 🟢 尽量使用标准库 | 减少外部依赖，降低维护成本 |
| 🟡 避免 `latest` / `*` 版本声明 | 明确最低版本号 |

---

## 4. 工具链版本

| 工具 | 版本 | 用途 |
|:---|:---|:---|
| `pytest` | ≥7.0 | 测试框架 |
| `ruff` | — | 代码风格检查（替代 flake8） |
| `mypy` | ≥1.0（推荐） | 类型检查 |
| `git` | ≥2.0 | 版本控制 |
| `python` | ≥3.8 | 运行环境 |

---

## 5. 兼容性策略

### 5.1 API 兼容性

| 变更类型 | 兼容要求 | 示例 |
|:---|:---|:---|
| 新增功能 | 向后兼容 | 新增 `POST /validate` 端点 |
| 修改参数 | 新增参数有默认值，旧调用不受影响 | `recommend(query, top_k=3)` → `recommend(query, top_k=3, threshold=40)` |
| 弃用 API | 标记 `@deprecated` + 保留至少一个小版本 | `v1.x` 弃用 → `v1.y` 后移除 |
| 移除 API | 必须在 Major 版本中移除 | `v1.x` → `v2.0` 可移除 |

### 5.2 数据格式兼容性

| 文件 | 兼容策略 |
|:---|:---|
| `skill_full_index.json` | 每次重建全量覆盖，不保证向前兼容 |
| `skill_usage_stats.json` | 新增字段必须加默认值，不能破坏旧文件读取 |
| `config.json` | 新增配置项必须合入 `DEFAULT_CONFIG`，旧配置无该项时用默认值 |

### 5.3 HTTP API 版本化

```python
# 当前无 URL 前缀版本化
# 如果需要，使用 Accept header 或 URL 前缀
# Accept: application/vnd.sra.v2+json
# /api/v2/recommend
```

---

## 6. 发布流程

### 6.1 发布检查清单

- [ ] 更新 `CHANGELOG.md`（按 [Keep a Changelog](https://keepachangelog.com/) 格式）
- [ ] 更新文档（README、API-REFERENCE——如有变更）
- [ ] 运行完整测试套件：`python3 -m pytest tests/ -v`
- [ ] **创建附注标签**：`git tag -a v{version} -m "Release v{version} — 版本说明"`
- [ ] **推送 tag**：`git push origin v{version}`
- [ ] CI 自动完成：构建 → 测试 → PyPI 发布 → GitHub Release

### 6.2 版本号速查

| 场景 | 版本变化 | 示例 |
|:---|:---:|:---:|
| Bug 修复 | PATCH +1 | 1.2.0 → 1.2.1 |
| 新增功能（向后兼容） | MINOR +1 | 1.2.1 → 1.3.0 |
| 不兼容变更 | MAJOR +1 | 1.3.0 → 2.0.0 |
| Pre-release | 后缀 | 2.0.0-alpha, 2.0.0-beta.1 |

---

> **本文件定义了 SRA 项目的技术版本基线。所有技术决策和代码变更不应偏离此规约。**
