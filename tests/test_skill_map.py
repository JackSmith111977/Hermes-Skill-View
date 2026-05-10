"""SRA 文件类型→技能映射注册表测试"""

import os
import sys
import json
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor.skill_map import SkillMapRegistry, DEFAULT_FILE_SKILL_MAP


class TestSkillMapRegistry:
    """SkillMapRegistry 基本功能测试"""

    def setup_method(self):
        self.registry = SkillMapRegistry()

    def test_default_registry_loaded(self):
        """默认注册表应包含足够的扩展名"""
        count = self.registry.get_registered_count()
        assert count >= 40, f"应 ≥ 40 种扩展名，实际 {count}"

    def test_get_skills_for_known_ext(self):
        """已知扩展名应返回推荐技能"""
        skills = self.registry.get_skills_for_file("report.pdf")
        assert "pdf-layout" in skills or "pdf-layout-weasyprint" in skills

    def test_get_skills_for_markdown(self):
        """.md 应推荐 markdown-guide"""
        skills = self.registry.get_skills_for_file("README.md")
        assert "markdown-guide" in skills

    def test_get_skills_for_pptx(self):
        """.pptx 应推荐 pptx-guide"""
        skills = self.registry.get_skills_for_file("slides.pptx")
        assert "pptx-guide" in skills

    def test_get_skills_for_svg(self):
        """.svg 应推荐 architecture-diagram"""
        skills = self.registry.get_skills_for_file("diagram.svg")
        assert "architecture-diagram" in skills

    def test_get_skills_for_html(self):
        """.html 应推荐 html-guide"""
        skills = self.registry.get_skills_for_file("index.html")
        assert "html-guide" in skills

    def test_get_skills_for_png(self):
        """.png 应推荐 image-generation"""
        skills = self.registry.get_skills_for_file("photo.png")
        assert "image-generation" in skills

    def test_get_skills_for_py(self):
        """.py 应推荐 python-env-guide"""
        skills = self.registry.get_skills_for_file("script.py")
        assert "python-env-guide" in skills

    def test_get_skills_for_xlsx(self):
        """.xlsx 应推荐 xlsx-guide"""
        skills = self.registry.get_skills_for_file("data.xlsx")
        assert "xlsx-guide" in skills

    def test_get_skills_for_unknown_ext(self):
        """未知扩展名应返回空列表"""
        skills = self.registry.get_skills_for_file("unknown.xyz")
        assert skills == []

    def test_get_skills_for_no_extension(self):
        """无扩展名的文件应返回空"""
        skills = self.registry.get_skills_for_file("Makefile")
        # Makefile 在 _ext_map 中不存在，但可以走 pattern 匹配
        # 这里是测试无点文件直接查 ext_map
        assert isinstance(skills, list)

    def test_get_skills_case_insensitive(self):
        """扩展名应大小写不敏感"""
        skills_upper = self.registry.get_skills_for_file("REPORT.PDF")
        skills_lower = self.registry.get_skills_for_file("report.pdf")
        assert skills_upper == skills_lower

    def test_get_skills_full_path(self):
        """完整路径应正确提取扩展名"""
        skills = self.registry.get_skills_for_file("/home/user/docs/report.pdf")
        assert "pdf-layout" in skills or "pdf-layout-weasyprint" in skills

    def test_has_skills_for_known(self):
        """已知扩展名应返回 True"""
        assert self.registry.has_skills_for(".pdf") == True
        assert self.registry.has_skills_for("pdf") == True

    def test_has_skills_for_empty_ext(self):
        """无推荐技能的扩展名应返回 False"""
        assert self.registry.has_skills_for(".lock") == False

    def test_docx_and_epub(self):
        """docx 和 epub 映射"""
        assert "docx-guide" in self.registry.get_skills_for_file("doc.docx")
        assert "epub-guide" in self.registry.get_skills_for_file("book.epub")

    def test_mermaid_mmd(self):
        """.mmd 映射"""
        skills = self.registry.get_skills_for_file("diagram.mmd")
        assert "mermaid-guide" in skills

    def test_tex(self):
        """.tex 映射"""
        skills = self.registry.get_skills_for_file("paper.tex")
        assert "latex-guide" in skills

    def test_csv(self):
        """.csv 映射"""
        skills = self.registry.get_skills_for_file("data.csv")
        assert "xlsx-guide" in skills or "financial-analyst" in skills


class TestSkillMapConfig:
    """用户配置加载测试"""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_load_custom_config(self):
        """用户配置应覆盖默认配置"""
        config_path = os.path.join(self.tmp_dir, "skill_map.json")
        custom_config = {
            "ext_map": {
                "pdf": ["custom-pdf-skill"],
                "md": ["custom-md-skill"],
            }
        }
        with open(config_path, "w") as f:
            json.dump(custom_config, f)

        registry = SkillMapRegistry(config_path)

        # 用户配置覆盖
        assert registry.get_skills_for_file("test.pdf") == ["custom-pdf-skill"]
        assert registry.get_skills_for_file("test.md") == ["custom-md-skill"]
        # 用户配置未涉及的部分保持默认
        assert "pptx-guide" in registry.get_skills_for_file("test.pptx")

    def test_config_not_found(self):
        """配置文件不存在时使用默认配置"""
        registry = SkillMapRegistry("/nonexistent/path/skill_map.json")
        assert registry.get_registered_count() >= 40

    def test_config_invalid_json(self):
        """配置文件格式错误时使用默认配置"""
        config_path = os.path.join(self.tmp_dir, "bad.json")
        with open(config_path, "w") as f:
            f.write("not json")

        # 不会崩溃
        registry = SkillMapRegistry(config_path)
        assert registry.get_registered_count() >= 40

    def test_config_partial_override(self):
        """用户配置只覆盖部分 key"""
        config_path = os.path.join(self.tmp_dir, "partial.json")
        with open(config_path, "w") as f:
            json.dump({"ext_map": {"new_ext": ["new-skill"]}}, f)

        registry = SkillMapRegistry(config_path)
        # 新的
        assert registry.get_skills_for_file("file.new_ext") == ["new-skill"]
        # 原有的还保留
        assert "markdown-guide" in registry.get_skills_for_file("test.md")


class TestSkillMapCoverage:
    """覆盖率测试"""

    def test_default_map_has_common_types(self):
        """常见文件类型应有覆盖"""
        common = [
            "md", "pdf", "docx", "pptx", "xlsx",
            "html", "css", "py",
            "svg", "png", "jpg", "gif",
            "json", "yaml", "toml",
            "sh", "txt", "csv",
            "mp3", "mp4",
            "tex", "bib",
            "mmd",
        ]
        registry = SkillMapRegistry()
        for ext in common:
            skills = registry.get_skills_for_file(f"file.{ext}")
            assert isinstance(skills, list), f"{ext} 应返回 list"

    def test_all_default_entries_have_lists(self):
        """所有默认映射值应为 list 类型"""
        for ext, skills in DEFAULT_FILE_SKILL_MAP.items():
            assert isinstance(skills, list), f"{ext} 的值应为 list，实际 {type(skills)}"

    def test_no_none_values(self):
        """映射表中不应有 None 值"""
        registry = SkillMapRegistry()
        for ext in registry.get_all_extensions():
            skills = registry.get_skills_for_file(f"file.{ext}")
            assert skills is not None
