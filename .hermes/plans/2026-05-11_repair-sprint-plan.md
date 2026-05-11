# SRA-003-18 质量修复 Sprint 计划

> **For Hermes:** 使用 subagent-driven-development 按 Task 逐个实施。
> **目标版本:** SRA v1.2.2

**Goal:** 修复 2026-05-11 审计发现的 8 个 P0/P1 问题（线程安全、版本号、fork 兼容、except:pass、文档漂移）

**范围:** skill_advisor/ 核心模块 + scripts/ 脚本 + README/docs

**前提:** git checkout feat/v2.0-enforcement-layer && git pull

**验证:** pytest tests/ -q (174 passed) + skill_view(name="commit-quality-check")

---

### Task 1: 版本号同步（D1/D3 — 8 处）

**Objective:** 将项目中 8 处过期版本号更新为 v1.2.1

**Files:**
- Modify: `README.md:356-357` — `v1.1.0` → `v1.2.1`, `275 skills` → `313+ skills`
- Modify: `scripts/install.sh:3,185,244,279,566` — `VERSION="v1.1.0"` → `VERSION="v1.2.1"`
- Modify: `scripts/check-sra.py:3,209` — `SRA_VER="1.1.0"` → `SRA_VER="1.2.1"`
- Modify: `ROADMAP.md:4` — `v1.2.0` → `v1.2.1`
- Modify: `CHANGELOG.md [Unreleased]` — pending → completed
- Modify: `README.md` — 补充 `sra upgrade`/`uninstall`/`dep-check` 命令

**Step 1: Patch README.md 版本号**

```bash
# 用 grep 确认位置
grep -n "v1.1.0\|275 skills\|62 skills" README.md
```

**Step 2: Patch scripts/install.sh 版本号**

```bash
grep -n "v1.1.0" scripts/install.sh
```

**Step 3: Patch scripts/check-sra.py 版本号**

```bash
grep -n "1.1.0" scripts/check-sra.py
```

**Step 4: Patch ROADMAP.md header**

**Step 5: Sync CHANGELOG.md Sprint 状态**

**Step 6: 补全 README 命令表** — 添加 upgrade/uninstall/dep-check

**Step 7: 验证**

```bash
grep -rn "v1\.1\.0\|1\.1\.0" --include="*.md" --include="*.py" --include="*.sh" . | grep -v __pycache__ | grep -v .git | grep -v node_modules
# 期望: 0 处残留
```

---

### Task 2: 线程安全锁保护（A7 — SceneMemory + SkillIndexer）

**Objective:** 为 SceneMemory 和 SkillIndexer 添加 threading.RLock 保护，修复 `get_stats()` 无锁读取

**Files:**
- Modify: `skill_advisor/memory.py` — 添加 `self._lock = threading.RLock()`
- Modify: `skill_advisor/indexer.py` — 添加 `self._lock = threading.RLock()`
- Modify: `skill_advisor/runtime/daemon.py` — 修复 `get_stats()` 锁保护

**Step 1: memory.py — 添加锁**

```python
# __init__ 中
self._lock = threading.RLock()

# load() 中
with self._lock:
    ...

# save() 中  
with self._lock:
    ...

# increment_recommendations() 中
with self._lock:
    self._cache[skill_id]["recommendations"] = ...
```

**Step 2: indexer.py — 添加锁**

```python
# __init__ 中
self._lock = threading.RLock()

# build() 中
with self._lock:
    self._skills = index

# get_skills() 中
with self._lock:
    return list(self._skills)  # 返回副本而非引用
```

**Step 3: daemon.py — 修复 get_stats()**

```python
def get_stats(self):
    with self._lock:
        return {
            "running": self.running,
            "stats": dict(self._stats),
            ...
        }
```

**Step 4: 验证**

```python
# 测试: 并发访问不抛异常
pytest tests/test_memory.py tests/test_singleton.py tests/test_daemon.py -v
```

---

### Task 3: 修复 `except: pass`（C1 — 2 处）

**Objective:** 修复 scripts/sra-eval.py 和 scripts/sra-eval-v2.py 中的裸 except

**Files:**
- Modify: `scripts/sra-eval.py:371` — `except:` → `except Exception as e: logger.warning(...)`
- Modify: `scripts/sra-eval-v2.py:113` — `except:` → `except Exception as e: logger.warning(...)`

**Step 1: Patch scripts/sra-eval.py**

`except: pass` → `except Exception as e: logging.warning("SRA eval error: %s", e)`

**Step 2: Patch scripts/sra-eval-v2.py**

同 Step 1

**Step 3: 验证**

```bash
grep -rn "except:" --include="*.py" . | grep -v __pycache__ | grep -v .git | grep -v venv | grep -v build | grep -v tests
# 期望: 0 处裸 except
```

---

### Task 4: daemon.py 线程锁 + fork 兼容（A8）

**Objective:** 减少 fork() 风险，替换为更安全的启动方式

**Files:**
- Modify: `skill_advisor/runtime/daemon.py`

**Step 1: daemon.py — 检查 logging 初始化**

确保 fork 后立即调用 `logging.basicConfig(force=True)`（已验证，行 684 已实现，只需确认）

**Step 2: daemon.py — 添加 fork 安全注释**

在 `os.fork()` 调用前添加注释说明风险

**Step 3: 验证**

```bash
pytest tests/test_daemon.py tests/test_daemon_http.py tests/test_singleton.py -v
```

---

### Task 5: 文档同步 + 提交前检查

**Objective:** 最终验证所有变更的完整性

**Step 1: 全量测试**

```bash
cd ~/projects/sra && python3 -m pytest tests/ -q
# 期望: 174 passed
```

**Step 2: 提交前检查**

```bash
# 加载 skill_view(name="commit-quality-check") 执行
# P0 安全检查 + 文档一致性 + 版本号一致性
```

**Step 3: Git 提交**

```bash
git add -A
git commit -m "fix(SRA-003-18): quality sprint — thread safety, version sync, except pass"
```

**Step 4: 汇报**

向主人汇报修复结果 + 遗留问题
