# SRA Sprint 3: 质量收尾 & 分支清理 🧹

> **Sprint 周期**: 2026-05-11
> **目标版本**: v1.4.0 (v1.3.0 release to master + techdebt cleanup)
> **分支策略**: feat/v2.0-enforcement-layer → master fast-forward → v1.4.0-dev
> **当前状态**: feat/v2.0-enforcement-layer 领先 master 33 commits

---

## 一、当前完成度检查 ← 实际剩余工作

| 项目 | 原始分析 | 实际状态 |
|:-----|:---------|:---------|
| 🔴 A-7 线程安全锁 | 待修复 | ✅ 已修复 (SRA-003-18) |
| 🔴 A-8 fork+线程兼容 | 待修复 | ⚠️ 未修复 — commands.py:53 仍用 os.fork() |
| 🔴 D-7 版本号同步 | 8处待修 | ✅ 7处已修，仅 pyproject.toml v1.2.1→v1.3.0 遗漏 |
| 🟡 T-7 dropin+adapters测试 | 待修复 | ✅ 已修复 (test_dropin.py 290行 + test_adapters.py 273行) |
| 🟡 C-9 daemon类型标注 | 33% | ✅ 已修复 84% (SRA-003-19) |
| 🟡 C-7 print→logging | 待修复 | ✅ indexer.py已修，dropin.py print为用户输出(合理的) |
| 🟡 D-2 README命令表 | 缺少命令 | 🟡 upgrade/uninstall/dep-check 确实未列 |
| 🟡 D-3 CHANGELOG一致性 | 不一致 | 🟡 需检查 |
| 🏗️ 分支合并 | master落后33 | ⚠️ 需 fast-forward |

---

## 二、Story 清单

### Story 1: 分支同步 & 版本发布 🏗️

**目标**: 将 feat/v2.0-enforcement-layer 合并到 master，打 v1.3.0 tag，升 v1.4.0-dev

**任务:**
1. 修正 pyproject.toml 版本号 v1.2.1 → v1.3.0
2. 签出 master → fast-forward → push
3. 打 v1.3.0 tag
4. 分支继续开发，版本升为 v1.4.0-dev

### Story 2: os.fork() → multiprocessing spawn (A-8) 🔴

**目标**: 替换 commands.py 中的 os.fork() 为 multiprocessing spawn 模式

**根因**: os.fork() + 线程不兼容 → fork 后只有调用线程存活，其他线程锁状态未定义
**解决方案**: 将 daemon 启动改为 subprocess.Popen 或 multiprocessing.Process

### Story 3: README 命令补全 + 文档同步 (D-2/D-3) 🟡

**目标**: 
- README 命令表补全 upgrade/uninstall/dep-check/force
- CHANGELOG Sprint 状态一致性检查

### Story 4: 文档对齐 + PROJECT-PANORAMA 更新 📐

**目标**: 按 doc-alignment 协议更新 project-report.json 和 PROJECT-PANORAMA.html

---

## 三、执行顺序

```text
Story 1 (分支/版本) ─→ Story 2 (fork修复) ─→ Story 3 (文档) ─→ Story 4 (对齐)
   ↑ 先修版本号         ↑ 核心安全修复        ↑ 用户可见补全      ↑ 最终质量门禁
```

每个 Story 完成时运行测试 (pytest -q) + git commit！
