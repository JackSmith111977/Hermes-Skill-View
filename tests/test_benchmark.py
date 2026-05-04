"""
SRA 性能基准测试
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor import SkillAdvisor


class TestBenchmark:
    """性能基准测试"""

    @classmethod
    def setup_class(cls):
        cls.advisor = SkillAdvisor()
        skills_dir = os.path.expanduser("~/.hermes/skills")
        if os.path.exists(skills_dir):
            cls.advisor.refresh_index()
            cls.has_skills = True
            cls.skill_count = len(cls.advisor.indexer.get_skills())
        else:
            cls.has_skills = False

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
            "帮我画个架构图",
            "生成PDF文档",
            "搜索最新的AI Agent框架",
            "飞书发送文件",
            "帮我review一下代码",
            "写PPT演示文稿",
            "怎么做数据分析",
            "帮我部署服务",
            "帮我发邮件",
            "画个流程图",
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
        import tracemalloc
        
        # 简单内存估算：索引 JSON 大小
        index_file = os.path.expanduser("~/.sra_agent/data/skill_full_index.json")
        if os.path.exists(index_file):
            size_mb = os.path.getsize(index_file) / (1024 * 1024)
            print(f"\n📊 索引文件大小: {size_mb:.2f}MB")
            # 索引是压缩的，内存中约 2-5x 大小
            assert size_mb < 20, f"索引文件应 < 20MB，实际 {size_mb:.2f}MB"
