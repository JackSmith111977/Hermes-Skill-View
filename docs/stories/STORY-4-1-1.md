---
story: STORY-4-1-1
title: "创建 sra-guard 插件目录结构 + 清单文件"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-1
epic: EPIC-004
estimated_hours: 0.5
test_data:
  source: tests/fixtures/skills
  ci_independent: true
  pattern_reference: ""
spec_references:
  - EPIC-004.md
  - SPEC-4-1.md
  - ~/.hermes/hermes-agent/hermes_cli/plugins.py
dependencies: []
out_of_scope:
  - 实现 pre_llm_call 的实际注入逻辑（STORY-4-1-2）
  - 实现 SRA Daemon 通信（STORY-4-1-3）
  - 修改 Hermes 核心代码
---

# STORY-4-1-1: 创建 sra-guard 插件目录结构 + 清单文件

## 用户故事

> As a **SRA 系统维护者**,
> I want **创建 sra-guard Hermes 插件的目录结构和清单文件**,
> So that **Hermes 能自动发现和加载 SRA 插件**。

---

## 验收标准

### AC-1: 插件目录存在
- [x] 条件: `~/.hermes/hermes-agent/plugins/sra-guard/` 目录存在
- [x] 验证方式: `ls ~/.hermes/hermes-agent/plugins/sra-guard/`
- [x] 预期结果: 目录存在

### AC-2: manifest.yaml 存在且格式正确
- [x] 条件: `manifest.yaml` 文件存在，包含必填字段
- [x] 验证方式: `python3 -c "import yaml; yaml.safe_load(open('.../manifest.yaml'))"`
- [x] 预期结果: YAML 解析成功，包含 `name: sra-guard`, `version`, `description`, `hooks` 字段

### AC-3: __init__.py 导出 SRAGuardPlugin 类
- [x] 条件: `__init__.py` 存在且导出 `SRAGuardPlugin` 类
- [x] 验证方式: `python3 -c "from plugins.sra_guard import SRAGuardPlugin; print('OK')"`
- [x] 预期结果: 导入成功

### AC-4: Hermes 自动发现插件
- [x] 条件: Hermes 启动后自动加载 sra-guard
- [x] 验证方式: 检查 `list_plugins` 输出包含 sra-guard
- [x] 预期结果: sra-guard 出现在插件列表中

---

## 技术要求

- 遵循 Hermes 插件规范（`hermes_cli/plugins.py` 中定义的 `Plugin` 类接口）
- 清单文件使用 YAML 格式
- `__init__.py` 使用 `from .plugin import SRAGuardPlugin` 模式（将实际实现在独立文件中）
- 不引入任何外部依赖

### manifest.yaml 模板

```yaml
name: sra-guard
version: 0.1.0
description: "SRA Skill Runtime Advisor — 实时技能推荐与工具校验插件"
kind: agent  # agent plugin: 影响 Agent 行为
hooks:
  - pre_llm_call
source: builtin  # 内置插件（随 Hermes 发行）
```

### __init__.py 模板

```python
"""SRA Guard — Hermes 的 SRA 技能运行时守护插件"""

from .plugin import SRAGuardPlugin

__all__ = ["SRAGuardPlugin"]
```

---

## 实施计划

### Task 1: 创建目录结构
- **文件**: `~/.hermes/hermes-agent/plugins/sra-guard/`
- **操作**: 创建目录 `mkdir -p plugins/sra-guard/tests`
- **验证**: `ls -la plugins/sra-guard/`

### Task 2: 创建 manifest.yaml
- **文件**: `~/.hermes/hermes-agent/plugins/sra-guard/manifest.yaml`
- **操作**: 写入插件清单
- **验证**: `python3 -c "import yaml; yaml.safe_load(open('manifest.yaml'))"`

### Task 3: 创建 plugin.py（基础框架）
- **文件**: `~/.hermes/hermes-agent/plugins/sra-guard/plugin.py`
- **操作**: 创建 `SRAGuardPlugin` 类，包含空的 `__init__` 和 `on_pre_llm_call` 方法
- **验证**: `python3 -c "from plugin import SRAGuardPlugin; p=SRAGuardPlugin(); print('OK')"`

### Task 4: 创建 __init__.py
- **文件**: `~/.hermes/hermes-agent/plugins/sra-guard/__init__.py`
- **操作**: 导出 `SRAGuardPlugin`
- **验证**: `python3 -c "from sra_guard import SRAGuardPlugin; print('OK')"`

### Task 5: 验证插件发现
- **操作**: 启动 Hermes（或运行发现测试），确认插件被识别
- **验证**: `hermes_cli.plugins.discover_plugins()` 返回中包含 sra-guard

---

## 测试策略

- **Fixture**: 无特殊 fixture 需求
- **新测试文件**: `tests/test_manifest.py` — 验证 YAML 格式
- **CI 环境**: 完全独立，不依赖 SRA Daemon

---

## 完成检查清单

- [x] 所有 AC 通过
- [x] 目录结构创建完毕
- [x] manifest.yaml 验证通过
- [x] Hermes 插件发现正常工作
- [x] 代码 + 文档同次 commit
