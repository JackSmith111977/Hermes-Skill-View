"""
SRA 测试基础设施 — 标准化 Fixture 与工具

== 使用规范 ==

1. 所有需要 SkillAdvisor 的测试，优先使用 `advisor_from_fixtures` fixture
2. 所有需要技能目录路径的测试，使用 `skills_fixture_dir` fixture
3. 禁止在测试中直接引用 ~/.hermes/skills —— CI 环境中不存在此目录
4. 如需使用真实 Hermes 技能数据，从 `_all_yamls_json` fixture 加载

== Fixture 层级 ==

Session scope (加载一次，全局复用):
  - skills_fixture_dir        → tests/fixtures/skills/ 路径
  - yaml_fixture_path         → tests/fixtures/skills_yaml/_all_yamls.json 路径
  - all_real_skills_yaml      → 313 条真实 skill 记录（已解析）

Function scope (每次测试独立):
  - advisor_from_fixtures     → 使用 fixture 数据初始化的 SkillAdvisor
  - advisor_with_memory       → 带场景记忆的 SkillAdvisor

== pytest markers (QA 工作流) ==

unit:         单元测试，快速执行 (< 3s)
integration:  集成测试，需多模块配合
slow:         慢速测试 (> 5s)
flaky:        已知不稳定测试（当前: test_serve_forever_in_thread）
smoke:        冒烟测试，版本发布前快速验证
concurrency:  并发安全测试
benchmark:    性能基准测试

== 历史 ==
2026-05-11: 创建 — 解决 test_contract.py 绕过 fixture 直接使用 ~/.hermes/skills 的问题
2026-05-12: 添加 pytest markers 定义 — 对齐 QA 工作流 L0-L4 分类
"""
import json
import os
import sys

import pytest

# 确保包在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def pytest_configure(config):
    """注册 QA 工作流相关的 pytest markers"""
    config.addinivalue_line("markers", "unit: 单元测试，快速执行 (< 3s)")
    config.addinivalue_line("markers", "integration: 集成测试，需多模块配合")
    config.addinivalue_line("markers", "slow: 慢速测试 (> 5s)")
    config.addinivalue_line("markers", "flaky: 已知不稳定测试，失败不阻断CI")
    config.addinivalue_line("markers", "smoke: 冒烟测试，版本发布前验证")
    config.addinivalue_line("markers", "concurrency: 并发安全测试")
    config.addinivalue_line("markers", "benchmark: 性能基准测试")


# ── 常量 ────────────────────────────────────────────────

# ── 常量 ────────────────────────────────────────────────

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "skills")
YAML_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "skills_yaml", "_all_yamls.json")
FIXTURES_EXIST = os.path.isdir(FIXTURES_DIR) and os.path.isfile(YAML_FIXTURE)


# ── session-scoped fixtures ─────────────────────────────

@pytest.fixture(scope="session")
def skills_fixture_dir() -> str:
    """全局 fixture 技能目录路径 (session scope, 只加载一次)"""
    if not os.path.isdir(FIXTURES_DIR):
        pytest.skip(f"技能 fixture 目录不存在: {FIXTURES_DIR}")
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def yaml_fixture_path() -> str:
    """全局 YAML fixture 文件路径"""
    if not os.path.isfile(YAML_FIXTURE):
        pytest.skip(f"YAML fixture 文件不存在: {YAML_FIXTURE}")
    return YAML_FIXTURE


@pytest.fixture(scope="session")
def all_real_skills_yaml():
    """所有真实技能 YAML 数据 (session scope, JSON 加载一次)"""
    if not os.path.isfile(YAML_FIXTURE):
        pytest.skip(f"YAML fixture 文件不存在: {YAML_FIXTURE}")
    with open(YAML_FIXTURE, "r") as f:
        return json.load(f)


# ── function-scoped fixtures ────────────────────────────

@pytest.fixture
def advisor_from_fixtures(skills_fixture_dir, tmp_path):
    """从 fixture 数据创建 SkillAdvisor — CI 独立，每次测试全新实例"""
    from skill_advisor import SkillAdvisor
    advisor = SkillAdvisor(skills_dir=skills_fixture_dir, data_dir=str(tmp_path))
    advisor.refresh_index()
    return advisor


@pytest.fixture
def advisor_with_memory(skills_fixture_dir, tmp_path):
    """带使用记录和场景记忆的 SkillAdvisor"""
    from skill_advisor import SkillAdvisor
    advisor = SkillAdvisor(skills_dir=skills_fixture_dir, data_dir=str(tmp_path))
    advisor.refresh_index()
    # 预填充一些使用记录
    advisor.record_usage("pdf-layout", "生成 PDF", accepted=True)
    advisor.record_usage("feishu", "发送飞书消息", accepted=True)
    advisor.record_usage("architecture-diagram", "画架构图", accepted=True)
    return advisor


# ── 辅助函数 ─────────────────────────────────────────────

def count_fixture_skills() -> int:
    """统计 fixture 目录中的 SKILL.md 数量"""
    if not os.path.isdir(FIXTURES_DIR):
        return 0
    count = 0
    for root, dirs, files in os.walk(FIXTURES_DIR):
        for f in files:
            if f == "SKILL.md":
                count += 1
    return count
