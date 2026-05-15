---
story: STORY-4-1-4
title: "创建安装脚本 — 将 sra-guard 插件部署到 Hermes"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-1
epic: EPIC-004
estimated_hours: 0.5
test_data:
  source: tests/fixtures/skills
  ci_independent: true
  pattern_reference: "scripts/install-hermes-integration.sh"
spec_references:
  - EPIC-004.md
  - SPEC-4-1.md
dependencies:
  - STORY-4-1-1
  - STORY-4-1-2
  - STORY-4-1-3
out_of_scope:
  - 修改 `sra install hermes` CLI 命令
  - 实现插件卸载的 Hermes Gateway 依赖清理
  - 跨平台安装支持（macOS/Windows）
---

# STORY-4-1-4: 创建安装脚本

## 用户故事

> As a **SRA 项目部署者**,
> I want **运行一个脚本就能把 sra-guard 插件从 SRA 项目部署到 Hermes**,
> So that **不需要手动复制文件，安装过程可重复、可验证**。

---

## 背景

sra-guard 插件的源码在 SRA 项目中管理（`~/projects/sra/plugins/sra-guard/`），
但 Hermes 从 `~/.hermes/hermes-agent/plugins/` 目录加载插件。
需要一个安装脚本来完成部署。

---

## 验收标准

### AC-1: install 模式复制文件
- [x] 条件: 运行 `bash scripts/install-hermes-plugin.sh install`
- [x] 验证: `ls ~/.hermes/hermes-agent/plugins/sra-guard/`
- [x] 预期: 包含 plugin.yaml, __init__.py, client.py

### AC-2: uninstall 模式删除文件
- [x] 条件: 运行 `bash scripts/install-hermes-plugin.sh uninstall`
- [x] 验证: `ls ~/.hermes/hermes-agent/plugins/sra-guard/` 2>/dev/null
- [x] 预期: 目录不存在

### AC-3: 安装后验证
- [x] 条件: install 完成后
- [x] 验证: 检查目标目录完整性
- [x] 预期: plugin.yaml / __init__.py / client.py 全部存在

### AC-4: 幂等性
- [x] 条件: 连续运行两次 install
- [x] 验证: 检查文件是否重复
- [x] 预期: 第二次安装不产生重复文件，不报错

### AC-5: 安全性
- [x] 条件: install/uninstall 操作
- [x] 验证: 检查 Hermes plugins 目录下其他插件
- [x] 预期: 不影响其他插件（disk-cleanup, memory 等）

---

## 技术要求

- **源目录**: `~/projects/sra/plugins/sra-guard/`
- **目标目录**: `~/.hermes/hermes-agent/plugins/sra-guard/`
- 使用 `cp -r` 复制（非符号链接，避免 SRA 项目删除后插件失效）
- 使用 `rm -rf` 卸载（仅删除 sra-guard 目录）
- 安装前检查目标目录是否已存在（幂等保护）

### install 模式伪代码

```bash
SOURCE="$(cd "$(dirname "$0")/.." && pwd)/plugins/sra-guard"
TARGET="$HOME/.hermes/hermes-agent/plugins/sra-guard"

# 检查源目录完整性
[ -f "$SOURCE/plugin.yaml" ] || { echo "❌ 源目录不完整"; exit 1; }

# 创建目标目录（如已存在则先备份？幂等：已存在则跳过）
if [ -d "$TARGET" ]; then
    echo "ℹ️  sra-guard 插件已安装，跳过"
else
    cp -r "$SOURCE" "$TARGET"
    echo "✅ sra-guard 插件已安装到 $TARGET"
fi
```

---

## 实施计划

### Task 1: 创建安装脚本
- **文件**: `scripts/install-hermes-plugin.sh`
- **操作**: 实现 install/uninstall 子命令
- **验证**: 运行 `bash scripts/install-hermes-plugin.sh install`

### Task 2: 验证安装
- **操作**: install 后检查目标目录
- **验证**: `ls -la ~/.hermes/hermes-agent/plugins/sra-guard/`

### Task 3: 测试幂等性和安全性
- **操作**: 连续安装两次，然后卸载
- **验证**: 第二次安装不报错，卸载后其他插件不受影响

---

## 测试策略

- **Fixture**: 无（脚本测试为手动验证）
- **CI 环境**: 需要 Hermes 环境（当前仅本地验证）

---

## 完成检查清单

- [x] 所有 AC 通过
- [x] install 模式正常复制文件
- [x] uninstall 模式正常删除文件
- [x] 幂等性验证通过
- [x] 对 Hermes 其他插件无影响
