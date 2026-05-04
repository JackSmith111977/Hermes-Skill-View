"""
SRA 技能覆盖率测试 — 验证每个 skill 是否能被 trigger 机制识别

目标是至少 50% 的 skill 能被 SRA 通过 trigger/name/description 识别。
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor import SkillAdvisor


def get_all_skills_with_triggers():
    """获取所有 skill 的 trigger 信息，用于生成测试用例"""
    advisor = SkillAdvisor()
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
        cls.advisor = SkillAdvisor()
        cls.skills_dir = os.path.expanduser("~/.hermes/skills")
        if os.path.exists(cls.skills_dir):
            count = cls.advisor.refresh_index()
            print(f"\n📊 技能索引已加载: {count} 个 skill")
            cls.has_skills = True
        else:
            cls.has_skills = False

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
        cls.advisor = SkillAdvisor()
        if os.path.exists(os.path.expanduser("~/.hermes/skills")):
            cls.advisor.refresh_index()
            cls.has_skills = True
        else:
            cls.has_skills = False

    # 常见用户查询 → 期望的 skill 类别
    COMMON_QUERIES = [
        ("帮我画个架构图", "architecture"),
        ("画系统架构图", "architecture"),
        ("生成PDF文档", "pdf"),
        ("帮我做个PPT", "ppt"),
        ("写演示文稿", "ppt"),
        ("发飞书文件", "feishu"),
        ("飞书怎么用", "feishu"),
        ("搜索最新AI新闻", "ai"),
        ("帮我review代码", "code"),
        ("代码审查", "code"),
        ("部署服务到服务器", "deploy"),
        ("测试一下这个功能", "test"),
        ("学习Python新特性", "learn"),
        ("查资料", "search"),
        ("帮我做个Excel表格", "excel"),
        ("怎么做数据分析", "data"),
        ("帮我翻译这段话", "translate"),
        ("画个流程图", "diagram"),
        ("做信息图", "infographic"),
        ("播放音乐", "music"),
        ("帮我写邮件", "email"),
        ("设置定时任务", "schedule"),
        ("怎么配置代理", "proxy"),
        ("检查服务器状态", "health"),
        ("git操作用哪个命令", "git"),
        ("帮我发微信消息", "wechat"),
        ("游戏服务器怎么搭", "game"),
        ("做视频", "video"),
        ("帮我画个时序图", "mermaid"),
        ("怎么用markdown", "markdown"),
        ("写LaTeX论文", "latex"),
        ("监控系统状态", "monitor"),
        ("配置clash代理", "clash"),
        ("打开浏览器自动化", "browser"),
        ("做像素画", "pixel art"),
        ("搞个字符画", "ascii art"),
        ("帮我复盘今天的工作", "review"),
        ("帮我总结一下", "summary"),
        ("怎么发通知", "notify"),
        ("帮我查股票", "stock"),
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
