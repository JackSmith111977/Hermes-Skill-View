"""轨迹追踪测试 — post_tool_call hook

STORY-4-4-1: post_tool_call hook 注册 + skill_view → POST /record
STORY-4-4-2: 工具调用记录 + 内部工具过滤
STORY-4-4-3: 集成测试
"""

from __future__ import annotations

from pathlib import Path

import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[1]


def _load_plugin():
    """加载插件模块"""
    import importlib.util
    init_path = PLUGIN_DIR / "__init__.py"
    spec = importlib.util.spec_from_file_location("sra_guard", str(init_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Mock 辅助 ──────────────────────────────────────────────


class MockSraClient:
    """模拟 SraClient，追踪 record() 调用"""

    def __init__(self):
        self.records = []  # [(skill, action), ...]

    def record(self, skill: str, action: str) -> bool:
        self.records.append((skill, action))
        return True


# ── Hook 注册与签名 (STORY-4-4-1) ──────────────────────────


class TestPostToolCallRegistration:
    """post_tool_call hook 注册测试"""

    def _make_mod(self):
        return _load_plugin()

    def test_hook_is_registered(self):
        """AC-1: post_tool_call hook 被注册"""
        mod = self._make_mod()

        class MockCtx:
            def __init__(self):
                self.hooks = {}

            def register_hook(self, name, callback):
                self.hooks[name] = callback

        ctx = MockCtx()
        mod.register(ctx)
        assert "post_tool_call" in ctx.hooks
        assert callable(ctx.hooks["post_tool_call"])

    def test_accepts_full_signature(self):
        """AC-2: 回调签名匹配 Hermes 规范"""
        mod = self._make_mod()
        # 带全部参数调用，不抛异常
        result = mod._on_post_tool_call(
            tool_name="skill_view",
            args={"name": "test-skill"},
            result='{"ok": true}',
            task_id="task-1",
            session_id="session-1",
            tool_call_id="call-1",
            duration_ms=42,
            extra_param="ignored",
        )
        # 即使 client 未初始化，也不应抛异常
        assert result is None


# ── skill_view 记录测试 (STORY-4-4-1) ─────────────────────


class TestSkillViewRecording:
    """skill_view → action='viewed' 测试"""

    def _make_mod(self):
        return _load_plugin()

    @pytest.fixture
    def mod_with_mock(self):
        """返回带 mock client 的模块"""
        mod = self._make_mod()
        mock_client = MockSraClient()
        mod._client = mock_client
        yield mod, mock_client
        mod._client = None

    def test_skill_view_records_viewed(self, mod_with_mock):
        """AC-3: skill_view → action='viewed'"""
        mod, mock = mod_with_mock
        mod._on_post_tool_call(
            tool_name="skill_view",
            args={"name": "html-presentation"},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )
        assert len(mock.records) == 1
        assert mock.records[0] == ("html-presentation", "viewed")

    def test_skills_list_records_viewed(self, mod_with_mock):
        """AC-4: skills_list 也被记录"""
        mod, mock = mod_with_mock
        mod._on_post_tool_call(
            tool_name="skills_list",
            args={},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )
        assert len(mock.records) == 1
        assert mock.records[0] == ("", "viewed")  # 无具体 skill 名称

    def test_silent_when_client_unavailable(self):
        """AC-5: SRA 不可用时静默降级"""
        mod = self._make_mod()
        mod._client = None  # 模拟 client 未初始化
        # 不应抛异常
        result = mod._on_post_tool_call(
            tool_name="skill_view",
            args={"name": "test"},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )
        assert result is None


# ── 工具调用记录测试 (STORY-4-4-2) ────────────────────────


class TestToolUseRecording:
    """工具调用 → action='used' 测试"""

    def _make_mod(self):
        return _load_plugin()

    @pytest.fixture
    def mod_with_mock(self):
        mod = self._make_mod()
        mock_client = MockSraClient()
        mod._client = mock_client
        # 重置去重缓存
        mod._last_record_time = {}
        yield mod, mock_client
        mod._client = None

    def test_write_file_records_used(self, mod_with_mock):
        """AC-1: 非 skill 工具 → action='used'"""
        mod, mock = mod_with_mock
        mod._on_post_tool_call(
            tool_name="write_file",
            args={"path": "test.html"},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )
        assert len(mock.records) == 1
        assert mock.records[0] == ("", "used")

    def test_web_search_records_used(self, mod_with_mock):
        """web_search 也记录为 used"""
        mod, mock = mod_with_mock
        mod._on_post_tool_call(
            tool_name="web_search",
            args={"query": "test"},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )
        assert len(mock.records) == 1
        assert mock.records[0] == ("", "used")

    def test_todo_is_ignored(self, mod_with_mock):
        """AC-3: 内部工具被忽略"""
        mod, mock = mod_with_mock
        mod._on_post_tool_call(
            tool_name="todo",
            args={},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )
        assert len(mock.records) == 0  # 未被调用

    def test_memory_is_ignored(self, mod_with_mock):
        """memory 也被忽略"""
        mod, mock = mod_with_mock
        mod._on_post_tool_call(
            tool_name="memory",
            args={},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )
        assert len(mock.records) == 0

    def test_session_search_is_ignored(self, mod_with_mock):
        """session_search 也被忽略"""
        mod, mock = mod_with_mock
        mod._on_post_tool_call(
            tool_name="session_search",
            args={},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )
        assert len(mock.records) == 0

    def test_exception_does_not_propagate(self):
        """AC-5: 异常不传播"""
        mod = self._make_mod()
        mod._client = None
        # 各种异常情况都不应抛异常
        result = mod._on_post_tool_call(
            tool_name=None,  # 故意传 None
            args=None,
            result=None,
            task_id=None, session_id=None,
            tool_call_id=None, duration_ms=None,
        )
        assert result is None


# ── 集成测试 (STORY-4-4-3) ────────────────────────────────


class TestTrackingIntegration:
    """轨迹追踪集成测试"""

    def _make_mod(self):
        return _load_plugin()

    @pytest.fixture
    def mod_with_mock(self):
        mod = self._make_mod()
        mock_client = MockSraClient()
        mod._client = mock_client
        mod._last_record_time = {}
        yield mod, mock_client
        mod._client = None
        mod._last_record_time = {}

    def test_skill_view_and_tool_used_record_differently(self, mod_with_mock):
        """skill_view → viewed, 常规工具 → used 分类正确"""
        mod, mock = mod_with_mock

        # skill_view 调用
        mod._on_post_tool_call(
            tool_name="skill_view",
            args={"name": "my-skill"},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )

        # write_file 调用
        mod._on_post_tool_call(
            tool_name="write_file",
            args={"path": "f.html"},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c2", duration_ms=20,
        )

        assert len(mock.records) == 2
        assert mock.records[0] == ("my-skill", "viewed")
        assert mock.records[1] == ("", "used")
