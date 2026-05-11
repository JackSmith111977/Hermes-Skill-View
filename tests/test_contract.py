"""SRA-003-05 契约机制测试

验证 SkillAdvisor.build_contract() 和 recommend() 返回的 contract 字段。
"""

import pytest

from skill_advisor.advisor import SkillAdvisor


@pytest.fixture
def advisor(tmp_path):
    """创建一个使用临时数据目录的 SkillAdvisor 实例"""
    data_dir = tmp_path / "sra_data"
    data_dir.mkdir()
    # 使用 Hermes 真实技能目录
    import os
    hermes_skills = os.path.expanduser("~/.hermes/skills")
    if os.path.isdir(hermes_skills):
        return SkillAdvisor(skills_dir=hermes_skills, data_dir=str(data_dir))
    return SkillAdvisor(data_dir=str(data_dir))


class TestBuildContract:

    def test_contract_contains_all_keys(self, advisor):
        """验证返回的契约包含所有必要字段"""
        scored = [
            {"skill": "pdf-layout", "category": "documentation", "score": 85.0},
            {"skill": "latex-guide", "category": "documentation", "score": 65.0},
        ]
        contract = advisor.build_contract("生成 PDF 文档", scored)
        assert "task_type" in contract
        assert "required_skills" in contract
        assert "optional_skills" in contract
        assert "confidence" in contract
        assert "summary" in contract

    def test_required_vs_optional_split(self, advisor):
        """验证强推荐(>=80)归入 required，弱推荐(40-80)归入 optional"""
        scored = [
            {"skill": "pdf-layout", "category": "documentation", "score": 85.0},
            {"skill": "latex-guide", "category": "documentation", "score": 55.0},
            {"skill": "markdown-guide", "category": "documentation", "score": 42.0},
            {"skill": "other-skill", "category": "other", "score": 30.0},  # < 40 排除
        ]
        contract = advisor.build_contract("生成 PDF 文档", scored)
        assert "pdf-layout" in contract["required_skills"]
        assert "latex-guide" in contract["optional_skills"]
        assert "markdown-guide" in contract["optional_skills"]
        assert "other-skill" not in contract["required_skills"]
        assert "other-skill" not in contract["optional_skills"]

    def test_empty_scored_list(self, advisor):
        """验证空 scoring 列表返回合理的默认值"""
        contract = advisor.build_contract("随便写点什么", [])
        assert contract["required_skills"] == []
        assert contract["optional_skills"] == []
        assert contract["task_type"] == "general"
        assert contract["confidence"] == "low"

    def test_task_type_from_category(self, advisor):
        """验证 task_type 从最高分技能的 category 推断"""
        scored = [
            {"skill": "pdf-layout", "category": "documentation", "score": 90.0},
            {"skill": "html-guide", "category": "documentation", "score": 50.0},
        ]
        contract = advisor.build_contract("生成报告文档", scored)
        assert contract["task_type"] == "documentation"

    def test_mixed_categories(self, advisor):
        """验证多个 category 时用逗号连接"""
        scored = [
            {"skill": "pdf-layout", "category": "documentation", "score": 90.0},
            {"skill": "git-advanced", "category": "devops", "score": 80.0},
        ]
        contract = advisor.build_contract("写 git 操作文档", scored)
        # 多 category 时用逗号连接
        assert "documentation" in contract["task_type"]
        assert "devops" in contract["task_type"]

    @pytest.mark.parametrize("max_score,expected", [
        (95, "high"),
        (85, "high"),
        (80, "high"),
        (65, "medium"),
        (60, "medium"),
        (45, "low"),
        (30, "low"),
        (0, "low"),
    ])
    def test_confidence_levels(self, advisor, max_score, expected):
        """验证置信度边界值"""
        scored = [
            {"skill": "test-skill", "category": "general", "score": max_score},
        ]
        contract = advisor.build_contract("测试查询", scored)
        assert contract["confidence"] == expected

    def test_summary_format(self, advisor):
        """验证 summary 格式正确"""
        scored = [
            {"skill": "pdf-layout", "category": "documentation", "score": 90.0},
            {"skill": "markdown-guide", "category": "documentation", "score": 50.0},
        ]
        contract = advisor.build_contract("生成报告", scored)
        assert "任务类型" in contract["summary"]
        assert "documentation" in contract["summary"]
        assert "必须加载: pdf-layout" in contract["summary"]
        assert "建议参考: markdown-guide" in contract["summary"]


class TestRecommendWithContract:

    def test_recommend_response_has_contract(self, advisor):
        """验证 recommend() 返回中包含 contract 字段"""
        result = advisor.recommend("写一个 Python 脚本")
        assert "contract" in result
        c = result["contract"]
        assert "task_type" in c
        assert "required_skills" in c
        assert "optional_skills" in c
        assert "confidence" in c

    def test_contract_required_skills_match_recommendations(self, advisor):
        """验证 contract.required_skills 中的技能都在 recommendations 中出现"""
        result = advisor.recommend("用 PDF 生成一份文档")
        contract = result["contract"]
        recs = result["recommendations"]
        rec_names = {r["skill"] for r in recs}
        for req in contract["required_skills"]:
            assert req in rec_names, f"契约中的必需技能 {req} 应在 recommendations 中"

    def test_contract_not_empty_for_relevant_query(self, advisor):
        """验证有意义查询的契约不会全空（仅在有技能数据时验证）"""
        result = advisor.recommend("帮助我写一个 Python 脚本处理数据")
        contract = result["contract"]
        # 检查是否有技能被索引（CI 环境可能没有 Hermes 技能目录）
        has_skills = bool(advisor.indexer.get_skills()) if hasattr(advisor, 'indexer') else True
        if not has_skills:
            pytest.skip("跳过：环境中没有技能数据")
        # 至少 required 或 optional 有一个非空
        has_something = bool(contract["required_skills"]) or bool(contract["optional_skills"])
        # 或 confidence 不为 low
        confidence_ok = contract["confidence"] != "low"
        assert has_something or confidence_ok, (
            f"契约不应全空: {contract}"
        )
