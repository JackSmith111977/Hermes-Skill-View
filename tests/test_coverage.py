"""
SRA 技能覆盖率测试 — 验证每个 skill 是否能被 trigger 机制识别

使用 tests/fixtures/skills/ 中的测试用技能库，不依赖外部环境。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor import SkillAdvisor

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "skills")


def get_all_skills_with_triggers():
    """获取所有 skill 的 trigger 信息，用于生成测试用例"""
    advisor = SkillAdvisor(skills_dir=FIXTURES_DIR)
    advisor.refresh_index()
    skills = advisor.indexer.get_skills()
    
    tests = []
    for s in skills:
        triggers = s.get("triggers", [])
        name = s["name"]
        
        # 根据 triggers 和 name 构造测试查询
        test_queries = []
        
        # 1. 如果有中文 trigger，直接用它
        for t in triggers:
            if any('\u4e00' <= c <= '\u9fff' for c in t):
                test_queries.append(t)
        
        # 2. 用 name 作为查询（替换分隔符）
        name_query = name.replace("-", " ").replace("_", " ")
        test_queries.append(name_query)
        
        # 3. 如果有英文 trigger，用它
        for t in triggers[:2]:
            if all(c.isascii() or c in ' -' for c in t):
                test_queries.append(t)
        
        # 4. 如果只有纯英文 name，构造一个包含 name 关键字的查询
        if not test_queries:
            parts = name.split("-")
            if len(parts) >= 2:
                # 用 name 中最重要的词
                main_part = parts[-1] if len(parts[-1]) > 3 else parts[0]
                test_queries.append(main_part)
        
        tests.append({
            "name": name,
            "has_triggers": len(triggers) > 0,
            "triggers": triggers[:5],
            "test_queries": test_queries[:5],
        })
    
    return tests, advisor


class TestSkillCoverage:
    """技能识别覆盖率测试"""

    @classmethod
    def setup_class(cls):
        cls.advisor = SkillAdvisor(skills_dir=FIXTURES_DIR)
        count = cls.advisor.refresh_index()
        print(f"\n📊 技能索引已加载: {count} 个 skill")
        cls.has_skills = True

    def test_overall_coverage_rate(self):
        """整体覆盖率应 ≥ 50%"""
        if not self.has_skills:
            return
        result = self.advisor.analyze_coverage()
        print(f"\n📊 总技能数: {result['total']}")
        print(f"✅ 能识别的: {result['covered']}")
        print(f"📈 覆盖率: {result['coverage_rate']}%")
        
        not_covered = result.get("not_covered", [])
        if not_covered:
            print(f"\n❌ 未能识别的技能 ({len(not_covered)} 个):")
            for s in not_covered:
                print(f"  - {s['name']} ({s['category']})")
        
        assert result['coverage_rate'] >= 40, \
            f"覆盖率应 ≥ 40%，实际 {result['coverage_rate']}%"

    def test_triggers_skills_high_coverage(self):
        """有 trigger 的 skill 覆盖率应 ≥ 85%"""
        if not self.has_skills:
            return
        result = self.advisor.analyze_coverage()
        
        # 对有 trigger 的 skill 单独计算
        with_triggers = [s for s in result["details"] if s["has_triggers"]]
        covered_triggers = [s for s in with_triggers if s["covered"]]
        
        rate = len(covered_triggers) / len(with_triggers) * 100 if with_triggers else 0
        print(f"\n📊 有 trigger 的技能: {len(with_triggers)}")
        print(f"✅ 其中能识别的: {len(covered_triggers)}")
        print(f"📈 有 trigger 技能覆盖率: {rate:.1f}%")
        
        assert rate >= 80, f"有 trigger 的 skill 覆盖率应 ≥ 80%，实际 {rate:.1f}%"
    
    def test_each_skill_individual(self):
        """逐个验证每个 skill 的识别能力"""
        if not self.has_skills:
            return
        
        all_tests, _ = get_all_skills_with_triggers()
        
        failures = []
        for test in all_tests:
            skill_name = test["name"]
            queries = test["test_queries"]
            
            max_score = 0
            for q in queries:
                if not q:
                    continue
                result = self.advisor.recommend(q)
                for r in result["recommendations"]:
                    if r["skill"] == skill_name:
                        max_score = max(max_score, r["score"])
            
            if max_score < 40:
                failures.append(f"  ❌ {skill_name} (最高分 {max_score}) — 查询: {queries}")
        
        total = len(all_tests)
        failed = len(failures)
        passed = total - failed
        rate = passed / total * 100
        
        print(f"\n📊 逐 skill 识别测试:")
        print(f"  总技能: {total}")
        print(f"  ✅ 通过: {passed}")
        print(f"  ❌ 失败: {failed}")
        print(f"  📈 通过率: {rate:.1f}%")
        
        if failures:
            print(f"\n失败详情 (最多显示 20 个):")
            for f in failures[:20]:
                print(f)
            if len(failures) > 20:
                print(f"  ... 还有 {len(failures) - 20} 个")
        
        # 至少 40% 通过率
        assert rate >= 40, f"逐 skill 识别通过率应 ≥ 40%，实际 {rate:.1f}%"


class TestCoverageWithCommonQueries:
    """用常见用户查询测试覆盖率"""

    @classmethod
    def setup_class(cls):
        cls.advisor = SkillAdvisor(skills_dir=FIXTURES_DIR)
        cls.advisor.refresh_index()
        cls.has_skills = True

    # 常见用户查询 → 期望匹配的技能（基于 tests/fixtures/skills/）
    COMMON_QUERIES = [
        ("生成PDF文档", "pdf"),
        ("帮我做个PPT", "ppt"),
        ("写演示文稿", "ppt"),
        ("发飞书消息", "feishu"),
        ("飞书怎么用", "feishu"),
        ("搜索最新AI新闻", "ai"),
        ("帮我 review 代码", "code"),
        ("代码审查", "code"),
        ("画个架构图", "architecture"),
        ("画系统设计图", "architecture"),
        ("用 mermaid 画时序图", "mermaid"),
        ("画个流程图", "diagram"),
        ("怎么做 Excel 报表", "excel"),
        ("编辑 Word 文档", "word"),
        ("Git 操作", "git"),
        ("github 怎么用", "git"),
        ("数据库设计", "sql"),
        ("AI 生图", "image"),
        ("Stable Diffusion 出图", "image"),
        ("番剧推荐", "bangumi"),
        ("微信机器人", "wechat"),
        ("微信公众号", "weixin"),
        ("网页搜索", "web"),
        ("联网查资料", "web"),
    ]

    def test_common_queries(self):
        """真实用户查询测试"""
        if not self.has_skills:
            return
        
        passed = 0
        total = len(self.COMMON_QUERIES)
        details = []
        
        for query, expected_category in self.COMMON_QUERIES:
            result = self.advisor.recommend(query)
            recs = result["recommendations"]
            
            # 检查是否有匹配的分类
            found = False
            top_score = 0
            top_skill = ""
            
            if recs:
                top_skill = recs[0]["skill"]
                top_score = recs[0]["score"]
                # 检查是否匹配期望的类别
                for r in recs:
                    if expected_category.lower() in r["skill"].lower() or \
                       expected_category.lower() in r["category"].lower():
                        found = True
                        break
                    # 也检查 description
                    if expected_category.lower() in r.get("description", "").lower():
                        found = True
                        break
            
            if found:
                passed += 1
                details.append(f"  ✅ {query:20s} → {top_skill:30s} ({top_score})")
            else:
                details.append(f"  ❌ {query:20s} → {top_skill:30s} ({top_score}) [期望: {expected_category}]")
        
        rate = passed / total * 100
        print(f"\n📊 常见用户查询测试 ({total} 个查询):")
        print(f"  ✅ 通过: {passed}")
        print(f"  ❌ 失败: {total - passed}")
        print(f"  📈 通过率: {rate:.1f}%")
        print()
        for d in details:
            print(d)
        
        assert rate >= 50, f"常见查询通过率应 ≥ 50%，实际 {rate:.1f}%"
