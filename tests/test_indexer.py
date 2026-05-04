"""
SRA 索引构建测试
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor.indexer import SkillIndexer
from skill_advisor.synonyms import SYNONYMS


class TestIndexer:
    """索引构建器测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = tempfile.mkdtemp()
        self.indexer = SkillIndexer(self.temp_dir, self.data_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def _create_skill(self, name, triggers=None, desc="Test description"):
        """创建测试 skill"""
        skill_dir = os.path.join(self.temp_dir, name)
        os.makedirs(skill_dir, exist_ok=True)
        
        trigger_yaml = ""
        if triggers:
            trigger_yaml = "triggers:\n" + "\n".join(f"  - {t}" for t in triggers)
        
        content = f"""---
name: {name}
description: "{desc}"
version: 1.0.0
{trigger_yaml}
---

# {name}

{desc}
"""
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write(content)

    def test_empty_directory(self):
        """空目录应返回 0 个 skill"""
        count = self.indexer.build()
        assert count == 0, f"空目录应返回 0，实际 {count}"

    def test_single_skill(self):
        """单个 skill 应被正确索引"""
        self._create_skill("test-skill", ["test", "skill"])
        count = self.indexer.build()
        assert count == 1, f"应索引 1 个 skill，实际 {count}"
        
        skills = self.indexer.get_skills()
        assert skills[0]["name"] == "test-skill"
        assert "test" in skills[0]["triggers"]
        assert "skill" in skills[0]["triggers"]

    def test_multiple_skills(self):
        """多个 skill 应全部被索引"""
        skills_data = [
            ("pdf-layout", ["pdf", "layout"]),
            ("ppt-guide", ["ppt", "powerpoint"]),
            ("feishu-send", ["飞书", "feishu"]),
        ]
        for name, triggers in skills_data:
            self._create_skill(name, triggers)
        
        count = self.indexer.build()
        assert count == 3, f"应索引 3 个 skill，实际 {count}"

    def test_keyword_extraction_chinese(self):
        """中文关键词提取"""
        words = self.indexer.extract_keywords("帮我画个架构图")
        # 应提取出 "架构"、"架构图"、"画" 等相关词
        assert "架构" in words or "架构图" in words, f"应提取中文词: {words}"
        assert len(words) >= 3, f"至少提取 3 个词，实际 {len(words)}"

    def test_keyword_extraction_english(self):
        """英文关键词提取"""
        words = self.indexer.extract_keywords("generate PDF document with weasyprint")
        assert "pdf" in words, f"应提取 'pdf': {words}"
        assert "weasyprint" in words, f"应提取 'weasyprint': {words}"

    def test_keyword_extraction_mixed(self):
        """中英混合关键词提取"""
        words = self.indexer.extract_keywords("帮我 review 一下代码")
        assert "review" in words, f"应提取英文 'review': {words}"
        assert "代码" in words or "一下" in words, f"应提取中文词: {words}"

    def test_synonym_expansion(self):
        """同义词扩展"""
        words = {"架构图"}
        expanded = self.indexer.expand_with_synonyms(words)
        assert "architecture diagram" in expanded or "architecture" in expanded, \
            f"应扩展出英文同义词: {expanded}"

    def test_synonym_expansion_reverse(self):
        """反向同义词查找"""
        words = {"architecture"}
        expanded = self.indexer.expand_with_synonyms(words)
        # architecture 应被反向查到"架构"
        assert any('\u4e00' <= c <= '\u9fff' for c in "".join(expanded)), \
            f"应反向查找出中文同义词: {expanded}"


class TestEmptySkillsDir:
    """无 skill 目录时的行为"""

    def test_no_skills_dir(self):
        """不存在的目录应优雅处理"""
        indexer = SkillIndexer("/nonexistent/path", "/tmp/sra_test_data")
        count = indexer.build()
        assert count == 0
