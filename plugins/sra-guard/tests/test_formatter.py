"""
格式化器测试 — format_sra_context() 的各种场景
"""

from __future__ import annotations

from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]


def _load_formatter():
    """加载 formatter 模块"""
    import importlib.util

    path = PLUGIN_DIR / "formatter.py"
    spec = importlib.util.spec_from_file_location("sra_guard.formatter", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SAMPLE_RAG = (
    "── [SRA Skill 推荐] ──────────────────────────────\n"
    "  ⭐ [medium] architecture-diagram (42.5分) — name部分'architecture'\n"
    "     [medium] hermes-ops-tips (40.7分) — trigger'架构图'\n"
    "── ──────────────────────────────────────────────"
)


class TestFormatter:
    """format_sra_context 测试"""

    def _fmt(self):
        return _load_formatter()

    def test_function_exists(self):
        """AC-1: 格式化函数存在"""
        mod = self._fmt()
        assert hasattr(mod, "format_sra_context")
        assert callable(mod.format_sra_context)

    def test_output_starts_with_sra_header(self):
        """AC-2: 输出以 [SRA] 开头"""
        mod = self._fmt()
        result = mod.format_sra_context(SAMPLE_RAG, "architecture-diagram", False)
        assert result.startswith("[SRA] Skill Runtime Advisor 推荐:")

    def test_contains_original_rag_context(self):
        """AC-3: 包含原始 rag_context 内容"""
        mod = self._fmt()
        result = mod.format_sra_context(SAMPLE_RAG, "architecture-diagram", False)
        assert "architecture-diagram" in result
        assert "hermes-ops-tips" in result

    def test_auto_load_appends_skill(self):
        """AC-4: should_auto_load=True 时追加 skill 名称"""
        mod = self._fmt()
        result = mod.format_sra_context(SAMPLE_RAG, "architecture-diagram", True)
        assert "⚡ 建议自动加载" in result
        assert "architecture-diagram" in result

    def test_auto_load_false_no_append(self):
        """should_auto_load=False 时不追加"""
        mod = self._fmt()
        result = mod.format_sra_context(SAMPLE_RAG, "architecture-diagram", False)
        assert "⚡" not in result

    def test_truncates_long_context(self):
        """AC-5: 超过 2500 字符时截断"""
        mod = self._fmt()
        long_rag = "x" * 3000
        result = mod.format_sra_context(long_rag, None, False)
        assert len(result) <= 2500

    def test_empty_rag_returns_empty(self):
        """AC-6: 空 rag_context 返回空字符串"""
        mod = self._fmt()
        assert mod.format_sra_context("", None, False) == ""
        assert mod.format_sra_context("  ", None, False) == ""
        assert mod.format_sra_context(None, None, False) == ""  # type: ignore

    def test_truncation_adds_ellipsis(self):
        """截断时追加省略号"""
        mod = self._fmt()
        long_rag = "y" * 3000
        result = mod.format_sra_context(long_rag, None, False)
        if len(result) == 2500:
            assert result.endswith("...")

    def test_format_matches_proxy_output(self):
        """输出格式与现有 Proxy 输出一致（目测检查）"""
        mod = self._fmt()
        result = mod.format_sra_context(SAMPLE_RAG, "architecture-diagram", True)
        # 输出应包含 SRA header + rag_context + auto_load 提示
        assert "[SRA] Skill Runtime Advisor 推荐:" in result
        assert "architecture-diagram" in result
        assert "⚡" in result
