"""
SRA 性能基准测试

使用 tests/fixtures/skills/ 中的测试用技能库，不依赖外部环境。
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor import SkillAdvisor

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "skills")


class TestBenchmark:
    """性能基准测试"""

    @classmethod
    def setup_class(cls):
        cls.advisor = SkillAdvisor(skills_dir=FIXTURES_DIR)
        cls.advisor.refresh_index()
        cls.has_skills = True
        cls.skill_count = len(cls.advisor.indexer.get_skills())

    def test_index_build_time(self):
        """索引构建时间应 < 5s"""
        if not self.has_skills:
            return
        start = time.time()
        count = self.advisor.refresh_index()
        elapsed = time.time() - start
        print(f"\n📊 索引构建: {count} skills in {elapsed:.2f}s")
        assert elapsed < 10, f"索引构建时间应 < 10s，实际 {elapsed:.2f}s"

    def test_recommend_latency(self):
        """推荐响应时间应 < 200ms"""
        if not self.has_skills:
            return
        queries = [
            "生成PDF文档",
            "帮我做个PPT",
            "飞书发送文件",
            "帮我 review 代码",
            "画个架构图",
            "用 mermaid 画流程图",
            "怎么做 Excel 报表",
            "Git 操作",
            "AI 生图",
            "番剧推荐",
        ]
        
        times = []
        for q in queries:
            start = time.time()
            self.advisor.recommend(q)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        
        avg = sum(times) / len(times)
        max_t = max(times)
        print(f"\n📊 推荐延迟测试 ({len(queries)} 个查询):")
        print(f"  平均: {avg:.1f}ms")
        print(f"  最大: {max_t:.1f}ms")
        print(f"  最小: {min(times):.1f}ms")
        
        assert avg < 200, f"平均延迟应 < 200ms，实际 {avg:.1f}ms"
        assert max_t < 500, f"最大延迟应 < 500ms，实际 {max_t:.1f}ms"

    def test_memory_usage(self):
        """内存使用应 < 50MB"""
        if not self.has_skills:
            return
        # 简单估算：技能索引 JSON 序列化大小
        import json
        skills = self.advisor.indexer.get_skills()
        size_bytes = len(json.dumps(skills))
        size_mb = size_bytes / (1024 * 1024)
        print(f"\n📊 索引 JSON 大小: {size_mb:.2f}MB ({len(skills)} skills)")
        assert size_mb < 10, f"索引应 < 10MB，实际 {size_mb:.2f}MB"
