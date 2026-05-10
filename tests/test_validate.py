"""SRA /validate 端点测试 — 工具调用前技能合规校验"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor.runtime.endpoints.validate import handle_validate, MONITORED_TOOLS
from skill_advisor.runtime.validate_core import validate_tool_call


class TestValidateEndpoint:
    """POST /validate 端点逻辑测试"""

    def test_basic_compliant(self):
        """合规的工具调用应返回 compliant=True"""
        result = handle_validate({
            "tool": "write_file",
            "args": {"path": "README.md"},
            "loaded_skills": ["markdown-guide"],
        })
        assert result["compliant"] == True
        assert result["severity"] == "info"

    def test_missing_skill_detected(self):
        """缺少对应 skill 应返回 compliant=False"""
        result = handle_validate({
            "tool": "write_file",
            "args": {"path": "report.pdf"},
            "loaded_skills": [],
        })
        assert result["compliant"] == False
        assert "pdf-layout" in result["missing"]
        assert result["severity"] == "warning"

    def test_no_tool_returns_compliant(self):
        """缺少 tool 字段时返回 compliant"""
        result = handle_validate({
            "args": {"path": "test.md"},
            "loaded_skills": [],
        })
        assert result["compliant"] == True

    def test_unmonitored_tool_returns_compliant(self):
        """不在监控白名单中的工具返回 compliant"""
        result = handle_validate({
            "tool": "web_search",
            "args": {"query": "test"},
            "loaded_skills": [],
        })
        assert result["compliant"] == True

    def test_missing_args_returns_compliant(self):
        """缺少 args 时仍可正常处理"""
        result = handle_validate({
            "tool": "write_file",
            "loaded_skills": ["markdown-guide"],
        })
        assert result["compliant"] == True

    def test_pptx_with_loaded_skill(self):
        """.pptx 且已加载 pptx-guide 时合规"""
        result = handle_validate({
            "tool": "write_file",
            "args": {"path": "slides.pptx"},
            "loaded_skills": ["pptx-guide"],
        })
        assert result["compliant"] == True

    def test_html_without_skill(self):
        """.html 未加载 html-guide 时不合规"""
        result = handle_validate({
            "tool": "write_file",
            "args": {"path": "index.html"},
            "loaded_skills": [],
        })
        assert result["compliant"] == False
        assert "html-guide" in result["missing"]

    def test_terminal_with_script(self):
        """terminal 命令中检测到 .py 文件"""
        result = handle_validate({
            "tool": "terminal",
            "args": {"command": "python3 script.py"},
            "loaded_skills": [],
        })
        # terminal 的校验是 info 级别，不会强制
        assert "severity" in result

    def test_execute_code_always_compliant(self):
        """execute_code 永远合规"""
        result = handle_validate({
            "tool": "execute_code",
            "loaded_skills": [],
        })
        assert result["compliant"] == True

    def test_monitored_tools_list(self):
        """监控白名单应包含关键工具"""
        assert "write_file" in MONITORED_TOOLS
        assert "patch" in MONITORED_TOOLS
        assert "terminal" in MONITORED_TOOLS
        assert "execute_code" in MONITORED_TOOLS

    def test_response_has_all_fields(self):
        """响应应包含所有标准字段"""
        result = handle_validate({
            "tool": "write_file",
            "args": {"path": "test.pdf"},
            "loaded_skills": [],
        })
        assert "compliant" in result
        assert "missing" in result
        assert "severity" in result
        assert "message" in result


class TestValidateCoreDirect:
    """validate_core 直接测试（不经过端点层）"""

    def test_write_file_pdf_no_skill(self):
        """write_file .pdf 无 skill → 不合规"""
        result = validate_tool_call(
            "write_file",
            {"path": "report.pdf"},
            [],
        )
        assert result["compliant"] == False
        assert "pdf-layout" in result["missing"]

    def test_write_file_md_with_skill(self):
        """write_file .md 已加载 markdown-guide → 合规"""
        result = validate_tool_call(
            "write_file",
            {"path": "README.md"},
            ["markdown-guide"],
        )
        assert result["compliant"] == True

    def test_patch_tool_same_as_write(self):
        """patch 工具行为应类似 write_file"""
        result = validate_tool_call(
            "patch",
            {"path": "data.xlsx"},
            [],
        )
        assert result["compliant"] == False
        assert "xlsx-guide" in result["missing"]

    def test_terminal_makefile(self):
        """terminal 中有 Makefile 引用"""
        result = validate_tool_call(
            "terminal",
            {"command": "make -f Makefile"},
            [],
        )
        assert isinstance(result["compliant"], bool)

    def test_file_path_variations(self):
        """不同的 path 参数名都应工作"""
        for key in ("file_path", "filepath", "filename"):
            result = validate_tool_call(
                "write_file",
                {key: "test.md"},
                ["markdown-guide"],
            )
            assert result["compliant"] == True, f"key={key} 失败"

    def test_severity_levels(self):
        """不同场景应有适当的 severity"""
        # 完全合规
        r1 = validate_tool_call("write_file", {"path": "notes.md"}, ["markdown-guide"])
        assert r1["severity"] == "info"

        # 缺少推荐 skill
        r2 = validate_tool_call("write_file", {"path": "slides.pptx"}, [])
        assert r2["severity"] == "warning"

        # unmonitored tool
        r3 = validate_tool_call("web_search", {"query": "test"}, [])
        assert r3["severity"] == "info"
