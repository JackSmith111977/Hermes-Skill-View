"""适配器模块测试 — 多 Agent 格式化和工厂函数"""

from unittest.mock import patch

import pytest

from skill_advisor.adapters import (
    ADAPTER_REGISTRY,
    BaseAdapter,
    ClaudeCodeAdapter,
    CodexAdapter,
    GenericCLIAdapter,
    HermesAdapter,
    get_adapter,
    list_adapters,
)

# ── 测试数据 ──────────────────────────────────

SAMPLE_RECS = [
    {
        "skill": "software-development__writing-plans",
        "score": 95.0,
        "confidence": "high",
        "reasons": ["匹配触发器: writing plans", "名称高度匹配"],
        "description": "Use when you have a spec or requirements for a multi-step task",
    },
    {
        "skill": "dogfood__self-review",
        "score": 72.0,
        "confidence": "medium",
        "reasons": ["匹配描述: review"],
        "description": "Self-review checklist for quality assurance",
    },
]

SAMPLE_STATS_RESPONSE = {
    "stats": {
        "version": "1.3.0",
        "status": "running",
        "skills_count": 313,
        "total_requests": 42,
        "config": {"http_port": 8536},
    }
}


# ── 工厂函数测试 ──────────────────────────────


class TestAdapterFactory:
    """get_adapter 和 list_adapters 测试"""

    def test_get_hermes_adapter(self):
        adapter = get_adapter("hermes")
        assert isinstance(adapter, HermesAdapter)

    def test_get_claude_adapter(self):
        adapter = get_adapter("claude")
        assert isinstance(adapter, ClaudeCodeAdapter)

    def test_get_codex_adapter(self):
        adapter = get_adapter("codex")
        assert isinstance(adapter, CodexAdapter)

    def test_get_opencode_adapter(self):
        adapter = get_adapter("opencode")
        assert isinstance(adapter, GenericCLIAdapter)

    def test_get_generic_adapter(self):
        adapter = get_adapter("generic")
        assert isinstance(adapter, GenericCLIAdapter)

    def test_get_unknown_adapter_defaults_to_generic(self):
        adapter = get_adapter("unknown-agent-type")
        assert isinstance(adapter, GenericCLIAdapter)

    def test_get_adapter_case_insensitive(self):
        adapter = get_adapter("Hermes")
        assert isinstance(adapter, HermesAdapter)

    def test_list_adapters(self):
        adapters = list_adapters()
        assert isinstance(adapters, list)
        assert "hermes" in adapters
        assert "claude" in adapters
        assert "codex" in adapters
        assert "opencode" in adapters
        assert "generic" in adapters
        assert len(adapters) == 5

    def test_adapter_registry_completeness(self):
        """ADAPTER_REGISTRY 中的所有适配器都应有对应测试"""
        for name, cls in ADAPTER_REGISTRY.items():
            adapter = get_adapter(name)
            assert isinstance(adapter, cls)


# ── BaseAdapter 测试 ──────────────────────────


class TestBaseAdapter:
    """BaseAdapter 核心功能测试"""

    @patch("skill_advisor.adapters._sra_socket_request")
    def test_recommend_returns_skills(self, mock_request):
        mock_request.return_value = {
            "result": {"recommendations": SAMPLE_RECS}
        }
        adapter = BaseAdapter()
        result = adapter.recommend("test query", top_k=3)
        assert len(result) == 2
        assert result[0]["skill"] == "software-development__writing-plans"

    @patch("skill_advisor.adapters._sra_socket_request")
    def test_recommend_handles_error(self, mock_request):
        mock_request.return_value = {"error": "Daemon not running"}
        adapter = BaseAdapter()
        result = adapter.recommend("test")
        assert result == []

    @patch("skill_advisor.adapters._sra_socket_request")
    def test_ping_returns_true(self, mock_request):
        mock_request.return_value = {"pong": True, "status": "ok"}
        adapter = BaseAdapter()
        assert adapter.ping() is True

    @patch("skill_advisor.adapters._sra_socket_request")
    def test_ping_returns_false(self, mock_request):
        mock_request.return_value = {"pong": False}
        adapter = BaseAdapter()
        assert adapter.ping() is False

    def test_format_suggestion_raises_not_implemented(self):
        adapter = BaseAdapter()
        with pytest.raises(NotImplementedError):
            adapter.format_suggestion(SAMPLE_RECS)


# ── HermesAdapter 测试 ────────────────────────


class TestHermesAdapter:
    """HermesAdapter 格式化测试"""

    def setup_method(self):
        self.adapter = HermesAdapter()

    def test_format_suggestion_empty(self):
        assert self.adapter.format_suggestion([]) == ""

    def test_format_suggestion_high_confidence(self):
        result = self.adapter.format_suggestion(SAMPLE_RECS)
        assert "💡 SRA 技能推荐" in result
        assert "writing-plans" in result
        assert "95.0" in result
        assert "⚡ 建议自动加载" in result

    def test_format_suggestion_with_reasons(self):
        """推荐应包含理由"""
        result = self.adapter.format_suggestion(SAMPLE_RECS)
        assert "匹配触发器" in result
        assert "名称高度匹配" in result

    @patch("skill_advisor.adapters._sra_socket_request")
    def test_to_system_prompt_block(self, mock_request):
        mock_request.return_value = SAMPLE_STATS_RESPONSE
        result = self.adapter.to_system_prompt_block()
        assert "SRA Runtime" in result
        assert "313" in result
        assert "8536" in result

    @patch("skill_advisor.adapters._sra_socket_request")
    def test_to_system_prompt_block_error(self, mock_request):
        mock_request.return_value = {"error": "not running"}
        result = self.adapter.to_system_prompt_block()
        assert result == ""

    @patch("skill_advisor.adapters._sra_socket_request")
    def test_to_proxy_format(self, mock_request):
        mock_request.return_value = {
            "result": {"recommendations": SAMPLE_RECS}
        }
        result = self.adapter.to_proxy_format("test message")
        assert result["sra_available"] is True
        assert result["should_auto_load"] is True  # score 95 >= 80
        assert result["top_skill"] == "software-development__writing-plans"
        assert len(result["recommendations"]) == 2
        assert "[SRA Skill 推荐]" in result["rag_context"]

    @patch("skill_advisor.adapters._sra_socket_request")
    def test_to_proxy_format_error(self, mock_request):
        mock_request.return_value = {"error": "timeout"}
        result = self.adapter.to_proxy_format("test")
        assert result["sra_available"] is False
        assert result["rag_context"] == ""


# ── ClaudeCodeAdapter 测试 ────────────────────


class TestClaudeCodeAdapter:
    """ClaudeCodeAdapter 格式化测试"""

    def setup_method(self):
        self.adapter = ClaudeCodeAdapter()

    def test_format_suggestion_empty(self):
        assert self.adapter.format_suggestion([]) == ""

    def test_format_suggestion_content(self):
        result = self.adapter.format_suggestion(SAMPLE_RECS)
        assert "[SRA Skill Recommendation]" in result
        assert "writing-plans" in result
        assert "Self-review" in result

    def test_to_claude_tool_format(self):
        result = self.adapter.to_claude_tool_format(SAMPLE_RECS)
        assert len(result) == 2
        assert result[0]["name"] == "software-development__writing-plans"
        assert result[0]["input_schema"]["type"] == "object"


# ── CodexAdapter 测试 ─────────────────────────


class TestCodexAdapter:
    """CodexAdapter 格式化测试"""

    def setup_method(self):
        self.adapter = CodexAdapter()

    def test_format_suggestion_empty(self):
        assert self.adapter.format_suggestion([]) == ""

    def test_format_suggestion_content(self):
        result = self.adapter.format_suggestion(SAMPLE_RECS)
        assert "# SRA recommended skills" in result
        assert "writing-plans" in result

    def test_to_openai_tool_format(self):
        result = self.adapter.to_openai_tool_format(SAMPLE_RECS)
        assert len(result) == 2
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "software-development__writing-plans"


# ── GenericCLIAdapter 测试 ────────────────────


class TestGenericCLIAdapter:
    """GenericCLIAdapter 格式化测试"""

    def setup_method(self):
        self.adapter = GenericCLIAdapter()

    def test_format_suggestion_empty(self):
        assert self.adapter.format_suggestion([]) == ""

    def test_format_suggestion_content(self):
        result = self.adapter.format_suggestion(SAMPLE_RECS)
        assert "=== SRA Skill Recommendation ===" in result
        assert "writing-plans" in result
        assert "95.0" in result
        assert "medium" in result

    def test_format_max_three_items(self):
        more_recs = SAMPLE_RECS * 3  # 6 items
        result = self.adapter.format_suggestion(more_recs)
        # Should only show 3
        assert result.count("Score:") == 3
