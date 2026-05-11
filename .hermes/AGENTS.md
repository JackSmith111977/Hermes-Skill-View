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

4. **📋 SDD Spec 门禁 — 没有批准的 Spec 就不写代码**:
    - **执行门禁检查**:
      ```bash
      # 自动检查当前任务是否需要 Spec
      python3 ~/.hermes/skills/sdd-workflow/scripts/spec-gate.py enforce "<任务描述>"
      if [ $? -ne 0 ]; then
          echo "🛑 SDD 门禁拦截！"
          echo "   1. 创建 Spec: cp docs/STORY-TEMPLATE.md docs/stories/STORY-XXX-NN.md"
          echo "   2. 初始化: python3 ~/.hermes/skills/sdd-workflow/scripts/spec-state.py create \"STORY-XXX-NN\" \"标题\""
          echo "   3. 填充内容后提交审阅"
          exit 1
      fi
      ```

## 🧹 POST-TASK: MANDATORY DOCUMENTATION ALIGNMENT + PRE-COMMIT VERIFICATION

**AFTER** completing any development task (story/sprint/bugfix/feature), **BEFORE** committing code, you **MUST**:

### Phase 0: 测试基础设施检查（写新测试前的强制前序）

**写新测试前，必须执行：**

```bash
# 0.1 扫描已有 fixture 模式
grep -rn "FIXTURES_DIR\|fixtures/" tests/ 2>/dev/null | head -10

# 0.2 检查 fixture 目录是否存在
ls tests/fixtures/ 2>/dev/null || echo "⚠️  无 fixture 目录"

# 0.3 如果 fixture 存在，新测试必须优先使用它
# 禁止直接引用 ~/.hermes/skills —— CI 中没有此目录！
```

**🔴 铁律**: 如果有 `tests/fixtures/` 目录，新测试中**禁止**出现 `~/.hermes/skills`。
违反此规则的测试将被视为「有缺陷的测试 —— CI 不可运行」。

参考 `tests/TEST-DATA-MANIFESTO.md` 了解所有可用 fixture。

### Phase 1: 本地 CI 预演（验证通过后才能提交）

```bash
# 1. 测试基础设施健康检查
python3 -c "
import os
d = 'tests/fixtures/skills'
count = sum(1 for _,_,files in os.walk(d) for f in files if f == 'SKILL.md')
assert count >= 300, f'Fixture 不完整: {count}'
print(f'✅ {count} valid fixture skills')
"

# 2. 扫描新测试是否引用了运行时依赖（这是 P0 违规）
grep -rn "hermes/skills\|~/.hermes" tests/ 2>/dev/null && {
    echo "❌ 测试中禁止引用 ~/.hermes/skills！请用 tests/fixtures/ 替代"
    exit 1
} || echo "✅ 无测试依赖运行时环境"

# 3. Ruff lint — 代码风格
ruff check skill_advisor/ tests/ || exit 1

# 4. 全量测试
python -m pytest tests/ -q --tb=short -o "addopts=" || exit 1

# 5. 版本检查
python -c "from skill_advisor import __version__; print(f'Version: {__version__}')"
```

> ⚠️ **不要等 CI 告诉你失败了**。本地预演能提前发现 95% 的问题。
> CI 实战教训：测试依赖本地环境→skipif 降级、ruff 配置版本兼容、mypy 用 || echo 非阻塞。
> **新增教训**: 必须在写测试前检查已有 fixture（`tests/fixtures/`），不要幻觉文件存在。

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
