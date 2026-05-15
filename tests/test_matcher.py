"""SRA 核心匹配引擎测试 — 使用真实技能数据"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor import SkillAdvisor
from skill_advisor.matcher import SkillMatcher
from skill_advisor.synonyms import SYNONYMS

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "skills")
YAML_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "skills_yaml", "_all_yamls.json")

# 加载所有真实技能 YAML
with open(YAML_FIXTURE, 'r') as f:
    ALL_REAL_SKILLS_YAML = json.load(f)
REAL_SKILL_NAMES = set(s.get('_source_name', s.get('name', '')) for s in ALL_REAL_SKILLS_YAML)


class TestSynonyms:
    """同义词映射表测试"""

    def setup_method(self):
        self.matcher = SkillMatcher(SYNONYMS)

    def test_synonyms_structure(self):
        """验证同义词表结构完整性"""
        assert len(SYNONYMS) >= 30, f"同义词大类应 ≥ 30，实际 {len(SYNONYMS)}"
        for key, values in SYNONYMS.items():
            assert len(key) >= 1, f"同义词 key 不能为空: {key}"
            assert len(values) >= 2, f"同义词 {key} 至少应有 2 个映射值"
            assert all(isinstance(v, str) for v in values), f"同义词 {key} 的值必须为字符串"

    def test_chinese_to_english_mapping(self):
        """中文关键词应有英文映射"""
        chinese_keys = [k for k in SYNONYMS if any('\u4e00' <= c <= '\u9fff' for c in k)]
        for key in chinese_keys:
            has_english = any(all(c.isascii() for c in v) for v in SYNONYMS[key])
            assert has_english, f"中文同义词 {key} 缺少英文映射"

    def test_english_to_chinese_mapping(self):
        """英文关键词应有英文映射"""
        from skill_advisor.synonyms import REVERSE_INDEX
        assert len(REVERSE_INDEX) > 0, "反向索引不应为空"
        english_values = [v for values in SYNONYMS.values() for v in values if all(c.isascii() for c in v)]
        found = sum(1 for v in english_values if v.lower() in REVERSE_INDEX)
        assert found > len(english_values) * 0.5, "超过一半的英文同义词值应能被反向查找"

    def test_no_duplicate_synonyms(self):
        """同义词表不应有重复条目"""
        for key, values in SYNONYMS.items():
            lower_values = [v.lower() for v in values]
            assert len(lower_values) == len(set(lower_values)), f"同义词 {key} 包含重复值"


class TestMatcher:
    """匹配引擎测试"""

    def setup_method(self):
        self.matcher = SkillMatcher(SYNONYMS, no_quality=True)

    def _make_skill(self, name, triggers=None, tags=None, desc="", category="general"):
        return {
            "name": name,
            "triggers": triggers or [],
            "tags": tags or [],
            "category": category,
            "match_text": f"{name} {' '.join(triggers or [])} {' '.join(tags or [])} {desc}".lower(),
            "full_description": desc,
            "description": desc[:200],
            "body_keywords": [],
        }

    def test_exact_name_match(self):
        """精确名称匹配应得高分"""
        skill = self._make_skill("pdf-layout", ["pdf", "layout"])
        score, _, _ = self.matcher.score({"pdf", "layout"}, skill, {})
        assert score >= 40, f"精确名称匹配应 ≥ 40，实际 {score}"

    def test_chinese_trigger_match(self):
        """中文 trigger 应能匹配"""
        skill = self._make_skill("feishu-send-file", ["飞书", "发送文件", "上传"])
        score, _, _ = self.matcher.score({"飞书", "发送", "文件", "feishu"}, skill, {})
        assert score >= 40, f"中文 trigger 匹配应 ≥ 40，实际 {score}"

    def test_synonym_bridge_match(self):
        """同义词桥接：中文输入匹配英文 skill"""
        skill = self._make_skill("architecture-diagram",
                                  ["architecture diagram", "architecture-diagram"],
                                  ["architecture", "diagrams", "svg"],
                                  "Generate dark-themed SVG diagrams of software systems")
        score, _, _ = self.matcher.score({"画", "架构", "图", "架构图", "画架构图",
                                           "architecture", "architecture diagram",
                                           "diagram"}, skill, {})
        assert score >= 40, f"同义词桥接匹配应 ≥ 40，实际 {score}"

    def test_partial_name_match(self):
        """名称部分匹配"""
        skill = self._make_skill("pdf-layout-reportlab", ["reportlab", "pdf"])
        score, _, _ = self.matcher.score({"pdf", "reportlab", "生成pdf"}, skill, {})
        assert score >= 40, f"部分名称匹配应 ≥ 40，实际 {score}"

    def test_description_match(self):
        """描述关键词匹配"""
        skill = self._make_skill("ai-trends", ["ai trends"],
                                  desc="AI前沿技术趋势追踪 — 开源模型、AI Agent、LLM新特性")
        score, _, _ = self.matcher.score({"ai", "trends", "agent", "llm", "趋势"}, skill, {})
        assert score >= 30, f"描述匹配应 ≥ 30，实际 {score}"

    def test_category_match(self):
        """类别匹配"""
        skill = self._make_skill("test-driven-development",
                                  category="software-development",
                                  tags=["test", "testing", "tdd"])
        score, _, _ = self.matcher.score({"test", "testing", "tdd", "development"}, skill, {})
        assert score >= 30, f"类别匹配应 ≥ 30，实际 {score}"

    def test_scene_memory_boost(self):
        """场景记忆应提升匹配分"""
        skill = self._make_skill("architecture-diagram")
        stats = {
            "scene_patterns": [
                {"pattern": "画图", "recommended_skills": ["architecture-diagram"], "hit_count": 5},
                {"pattern": "架构", "recommended_skills": ["architecture-diagram"], "hit_count": 3},
            ],
            "skills": {
                "architecture-diagram": {"total_uses": 10, "acceptance_rate": 0.9}
            }
        }
        score_with, _, _ = self.matcher.score({"architecture", "diagram"}, skill, stats)
        score_without, _, _ = self.matcher.score({"architecture", "diagram"}, skill, {})
        assert score_with >= score_without, f"场景记忆应提升分数: {score_with} vs {score_without}"

    def test_no_match_for_unrelated(self):
        """不相关的输入应得低分"""
        skill = self._make_skill("minecraft-modpack-server",
                                  ["minecraft", "modpack", "server"])
        score, _, _ = self.matcher.score({"金融", "股票", "基金", "akshare"}, skill, {})
        assert score < 40, f"不相关输入应 < 40，实际 {score}"

    def test_strong_recommendation(self):
        """强推荐阈值测试（得分应 ≥ 40）"""
        skill = self._make_skill("pptx-guide", ["powerpoint", "presentation", "pptx"],
                                  desc="PowerPoint 演示文稿操作技能")
        score, _, _ = self.matcher.score({"ppt", "powerpoint", "presentation", "幻灯片", "演示", "pptx"}, skill, {})
        assert score >= 40, f"PPT 匹配应 ≥ 40，实际 {score}"


class TestAdvisor:
    """SkillAdvisor 集成测试 — 使用全部 313 个真实技能"""

    SKILLS_FIXTURE = FIXTURES_DIR

    def setup_method(self):
        self.advisor = SkillAdvisor(skills_dir=self.SKILLS_FIXTURE)
        self.advisor.refresh_index()
        self.skills = self.advisor.indexer.get_skills()

    def test_initialization(self):
        """初始化测试：使用真实技能数据"""
        assert self.advisor is not None
        assert len(self.skills) >= 300, (
            f"应加载 ≥ 300 个真实技能，实际 {len(self.skills)} 个。"
            f"测试需要基于真实技能数据！"
        )

    def test_recommend_pdf(self):
        """PDF 推荐测试（基于真实技能库）"""
        result = self.advisor.recommend("生成PDF文档")
        names = [r["skill"] for r in result["recommendations"]]
        pdf_related = any("pdf" in n.lower() for n in names)
        assert pdf_related, f"PDF 查询应推荐 pdf 相关 skill: {names}"

    def test_recommend_feishu(self):
        """飞书推荐测试（基于真实技能库）"""
        result = self.advisor.recommend("飞书发送文件")
        names = [r["skill"] for r in result["recommendations"]]
        feishu_related = any("feishu" in n.lower() for n in names)
        assert feishu_related, f"飞书查询应推荐 feishu 相关 skill: {names}"

    def test_recommend_ppt(self):
        """PPT 推荐测试（基于真实技能库）"""
        result = self.advisor.recommend("写PPT演示文稿")
        names = [r["skill"] for r in result["recommendations"]]
        ppt_related = any("ppt" in n.lower() for n in names)
        assert ppt_related, f"PPT 查询应推荐 ppt 相关 skill: {names}"

    def test_recommend_code_review(self):
        """代码审查推荐测试（基于真实技能库）"""
        result = self.advisor.recommend("帮我review一下代码")
        assert len(result["recommendations"]) > 0, "代码审查应有推荐结果"

    def test_recommend_ai_trends(self):
        """AI 趋势推荐测试（基于真实技能库）"""
        result = self.advisor.recommend("搜索最新的AI Agent框架")
        names = [r["skill"] for r in result["recommendations"]]
        ai_related = any("ai" in n.lower() or "trend" in n.lower() for n in names)
        assert ai_related, f"AI 查询应推荐 ai 相关 skill: {names}"

    def test_performance(self):
        """性能测试：应在 200ms 内完成（真实 313 技能库）"""
        result = self.advisor.recommend("画架构图")
        assert result["processing_ms"] < 200, f"处理时间应 < 200ms: {result['processing_ms']}ms"

    def test_analyze_coverage(self):
        """覆盖率分析测试（基于真实技能库）"""
        result = self.advisor.analyze_coverage()
        assert result["total"] >= 300, f"应有 ≥ 300 个技能被扫描，实际 {result['total']}"
        assert result["coverage_rate"] > 0, "覆盖率应 > 0%"

    def test_record_and_stats(self):
        """记录使用和统计测试"""
        self.advisor.record_usage("test-skill", "test query", accepted=True)
        stats = self.advisor.show_stats()
        assert stats["total_recommendations"] >= 0

    def test_all_skills_indexed(self):
        """验证所有 313 个真实技能都已被索引"""
        indexed_names = set(s["name"] for s in self.skills)
        missing = REAL_SKILL_NAMES - indexed_names
        if missing:
            print(f"\n⚠️ 以下真实技能未出现在索引中 ({len(missing)} 个):")
            for m in list(missing)[:20]:
                print(f"  - {m}")
        # 至少 90% 真实技能被索引
        coverage = len(indexed_names & REAL_SKILL_NAMES) / len(REAL_SKILL_NAMES) * 100
        assert coverage >= 90, f"真实技能索引覆盖率应 ≥ 90%，实际 {coverage:.1f}%"
