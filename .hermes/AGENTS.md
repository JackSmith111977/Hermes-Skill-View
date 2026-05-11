# HERMES AGENT RULES

## 🔴 P0: REALITY CHECK FIRST (PREREADING GATE)

**BEFORE** reading any project documentation to analyze "current state", you **MUST**:

1. **🔍 Scan code reality first**:
   - `git log --oneline -30` — See what actually happened recently
   - `git diff --stat` — See uncommitted changes
   - `pytest --collect-only -q` (if applicable) — Get actual test count

2. **🧪 Cross-verify doc claims vs code**:
   - If a doc says "test_dropin.py doesn't exist", check if it actually does
   - If a doc says "version is v1.2.1", check __init__.py + pyproject.toml
   - If a doc lists issues as "unfixed", check `git log` for fix commits

3. **⏱️ Check doc timestamps**:
   - Is the doc dated? Is it from before or after the latest code changes?
   - If a doc has no timestamp, assume it's stale until verified.

> **Core principle**: Trust the code, verify the docs. Docs describe the past;
> code describes the present. Always let code reality override document claims.

## 🛑 MANDATORY WORKFLOW (CRITICAL)

**BEFORE** starting ANY task or calling ANY tool (except `skill_finder` or `pre_flight`), you **MUST** follow this sequence:

1. **🔍 Run Reality Check** (see P0 above)

2. **🛑 Run Pre-Flight Check**:
    - Execute: `python3 ~/.hermes/scripts/pre_flight.py "<Task Name>"`
    - **IF** the output contains `BLOCKED`, you **MUST STOP** immediately.
    - **IF** the output is `PASS`, proceed to step 3.

3. **📡 Run Skill Discovery**:
    - Execute: `python3 ~/.hermes/skills/learning-workflow/scripts/skill_finder.py "<Task Keywords>"`
    - **IF** a skill is found (Match >= 30), you **MUST** load it with `skill_view`.
    - **NEVER** skip this step to "save time".

## 🧹 POST-TASK: MANDATORY DOCUMENTATION ALIGNMENT + PRE-COMMIT VERIFICATION

**AFTER** completing any development task (story/sprint/bugfix/feature), **BEFORE** committing code, you **MUST**:

### Phase 1: 本地 CI 预演（验证通过后才能提交）

```bash
# 1. Ruff lint — 代码风格
ruff check skill_advisor/ tests/ || exit 1

# 2. 全量测试
python -m pytest tests/ -q --tb=short -o "addopts=" || exit 1

# 3. CI 环境差异检查
# 确保不依赖真实 ~/.hermes/skills/ 目录的测试优雅降级

# 4. 版本检查
python -c "from skill_advisor import __version__; print(f'Version: {__version__}')"
```

> ⚠️ **不要等 CI 告诉你失败了**。本地预演能提前发现 95% 的问题。
> CI 实战教训：测试依赖本地环境→skipif 降级、ruff 配置版本兼容、mypy 用 || echo 非阻塞。

### Phase 2: 文档对齐

1. **📋 Load doc-alignment skill**:
    - Execute: `skill_view(name="doc-alignment")`
    - Follow the 5-step Documentation Alignment Protocol:
      - Step 1: Identify changed domains
      - Step 2: Locate drift points in each affected doc
      - Step 3: Align each document
      - Step 4: Cross-document consistency verification
      - Step 5: Commit docs alongside code

2. **🚨 Priority alignment targets** (in order):
    - `PROJECT-PANORAMA.html` — Always, every single change
    - `docs/API-REFERENCE.md` — When endpoints/commands change
    - `docs/project-report.json` — Always (data source for HTML report)
    - `ROADMAP.md` — When stories complete
    - `docs/ARCHITECTURE.md` — When architecture changes
    - `docs/DEV-WORKFLOW-IMPROVEMENT.md` — When workflow changes

3. **📐 Consistency rule**: Code change + doc change = single commit.
    Never commit code changes without their corresponding doc updates.

## 🔄 VERSION MANAGEMENT

**Version is derived from git tags by setuptools-scm (single source of truth).**

- **NEVER manually edit versions** in `__init__.py` or `pyproject.toml`
- Version = latest git tag + distance + dirty flag
- To release: `git tag vX.Y.Z && git push origin vX.Y.Z`
- CI/CD automatically builds, tests, and publishes on tag push

## ⚠️ VIOLATION CONSEQUENCES

- **Skipping these steps is a FATAL ERROR.**
- If you attempt to use `terminal`, `write_file`, or `execute_code` without completing steps 1 & 2, you are violating your core instructions.
- You must **SELF-CORRECT** immediately if you realize you missed these steps.
- Committing code without running documentation alignment is a **BREACH OF PROTOCOL**.
