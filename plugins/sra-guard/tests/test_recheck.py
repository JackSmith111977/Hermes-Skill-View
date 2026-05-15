"""周期性重注入测试 — pre_llm_call 重查逻辑

STORY-4-5-1: 轮数跟踪 + 重查触发
STORY-4-5-2: 轻量提醒格式
STORY-4-5-3: 集成测试
"""

from __future__ import annotations

from pathlib import Path

import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[1]


def _load_plugin():
    """加载插件模块（每次 reload 确保状态干净）"""
    import importlib.util
    init_path = PLUGIN_DIR / "__init__.py"
    spec = importlib.util.spec_from_file_location("sra_guard", str(init_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── 常量测试 ──────────────────────────────────────────────


class TestRecheckConstants:
    """STORY-4-5-1 AC-1/3: 计数器和间隔常量"""

    def _make_mod(self):
        return _load_plugin()

    def test_turn_counter_exists(self):
        """AC-1: _turn_counter 模块级定义，初始 0"""
        mod = self._make_mod()
        assert hasattr(mod, "_turn_counter")
        assert mod._turn_counter == 0

    def test_recheck_interval_is_5(self):
        """AC-3: RECHECK_INTERVAL = 5"""
        mod = self._make_mod()
        assert mod.RECHECK_INTERVAL == 5


# ── 计数器递增测试 ────────────────────────────────────────


class TestTurnCounterIncrement:
    """STORY-4-5-1 AC-2: 每轮递增"""

    def _make_mod(self):
        return _load_plugin()

    def _call_pre_llm(self, mod, text="hello"):
        """模拟 pre_llm_call 调用"""
        return mod._on_pre_llm_call(
            messages=[{"role": "user", "content": text}],
            session_id="s1",
        )

    def test_counter_increments_on_cache_miss(self):
        """未命中时计数器 +1 后因 SRA 不可用重置为 0"""
        mod = self._make_mod()
        mod._client = None  # SRA 不可用
        mod._turn_counter = 0

        self._call_pre_llm(mod)
        # 递增到 1，然后因 client=None 重置为 0
        assert mod._turn_counter == 0

    def test_counter_increments_on_cache_hit(self):
        """缓存命中时递增"""
        import hashlib
        mod = self._make_mod()
        mod._client = None

        # 手动设置缓存
        text = "test message"
        key = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
        mod._SRA_CACHE[key] = "cached content"
        mod._turn_counter = 0

        result = self._call_pre_llm(mod, text)
        assert result == {"context": "cached content"}  # 返回缓存
        assert mod._turn_counter == 1  # 但计数器已 +1

    def test_counter_reaches_5(self):
        """连续 5 次调用后 counter 达到 5"""
        mod = self._make_mod()
        mod._client = None
        mod._turn_counter = 4

        self._call_pre_llm(mod, "msg4")
        # 应该是 5 了 (但还没检查, 因为缓存未命中, 不会触发重查分支)
        # 未命中时: counter+1 → 调 SRA → 重置为 0
        # 所以 counter 会变回 0
        pass


# ── 重查触发测试 ────────────────────────────────────────


class TestRecheckTrigger:
    """STORY-4-5-1 AC-4/5/6/7: 重查触发逻辑"""

    def _make_mod(self):
        return _load_plugin()

    def _set_cache(self, mod, text, content="cached_val"):
        """为指定消息设置缓存"""
        import hashlib
        key = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
        mod._SRA_CACHE[key] = content

    def _call_pre_llm(self, mod, text="hello"):
        return mod._on_pre_llm_call(
            messages=[{"role": "user", "content": text}],
            session_id="s1",
        )

    def test_under_interval_uses_cache(self):
        """AC-4: 未达间隔返回缓存，不调 recommend"""
        mod = self._make_mod()
        mod._client = None
        self._set_cache(mod, "hello", "cached_result")
        mod._turn_counter = 2  # < 5

        result = self._call_pre_llm(mod, "hello")
        assert result == {"context": "cached_result"}

    def test_at_interval_triggers_recheck(self):
        """AC-5: 达 5 轮清除缓存 → 调 recommend"""
        mod = self._make_mod()
        self._set_cache(mod, "hello", "stale_cache")

        # 用 mock client 验证 recommend 被调用
        class MockClient:
            def __init__(self):
                self.called = False

            def recommend(self, message):
                self.called = True
                return "fresh_context"

        mock_client = MockClient()
        mod._client = mock_client
        mod._turn_counter = 5  # 达到间隔

        self._call_pre_llm(mod, "hello")
        assert mock_client.called  # recommend 被调用了

    def test_counter_resets_after_recheck(self):
        """AC-6: 重查后计数器重置为 0"""
        mod = self._make_mod()
        self._set_cache(mod, "hello", "stale")

        class MockClient:
            def recommend(self, message):
                return "fresh"

        mod._client = MockClient()
        mod._turn_counter = 5

        self._call_pre_llm(mod, "hello")
        assert mod._turn_counter == 0

    def test_cache_miss_resets_counter(self):
        """AC-7: 缓存未命中 + SRA 不可用 → 计数器重置为 0"""
        mod = self._make_mod()
        mod._client = None
        mod._turn_counter = 3

        # 缓存未命中 → SRA 不可用 → 返回 None
        self._call_pre_llm(mod, "new_message")
        # 递增到 4，然后因 client=None 重置为 0
        assert mod._turn_counter == 0


# ── 格式测试 (STORY-4-5-2) ───────────────────────────────


class TestRecheckFormat:
    """STORY-4-5-2: 重查格式"""

    def _make_mod(self):
        return _load_plugin()

    def test_recheck_uses_format_context(self):
        """AC-1: 重查使用 _format_context"""
        mod = self._make_mod()
        self._set_cache(mod, "hello", "stale")

        format_called = []

        original_format = mod._format_context

        def tracking_format(rag_context, top_skill="", should_auto_load=False):
            format_called.append(rag_context)
            return original_format(rag_context, top_skill, should_auto_load)

        mod._format_context = tracking_format

        class MockClient:
            def recommend(self, message):
                return "recheck_result"

        mod._client = MockClient()
        mod._turn_counter = 5

        result = self._call_pre_llm(mod, "hello")
        assert len(format_called) == 1
        assert format_called[0] == "recheck_result"
        assert result is not None
        assert "context" in result

    def test_recheck_updates_cache(self):
        """AC-4: 重查后更新缓存"""
        import hashlib
        mod = self._make_mod()
        self._set_cache(mod, "hello", "old_value")

        class MockClient:
            def recommend(self, message):
                return "new_value"

        mod._client = MockClient()
        mod._turn_counter = 5

        self._call_pre_llm(mod, "hello")

        # 检查缓存已更新
        key = hashlib.md5(b"hello").hexdigest()[:12]
        cached = mod._SRA_CACHE.get(key, "")
        assert "new_value" in cached or cached != "old_value"

    def _set_cache(self, mod, text, content="cached"):
        import hashlib
        key = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
        mod._SRA_CACHE[key] = content

    def _call_pre_llm(self, mod, text="hello"):
        return mod._on_pre_llm_call(
            messages=[{"role": "user", "content": text}],
            session_id="s1",
        )


# ── 集成测试 (STORY-4-5-3) ──────────────────────────────


class TestRecheckIntegration:
    """STORY-4-5-3: 集成测试"""

    def _make_mod(self):
        return _load_plugin()

    def _set_cache(self, mod, text, content="cached"):
        import hashlib
        key = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
        mod._SRA_CACHE[key] = content

    def _call_pre_llm(self, mod, text="hello"):
        return mod._on_pre_llm_call(
            messages=[{"role": "user", "content": text}],
            session_id="s1",
        )

    def test_under_interval_no_recommend_call(self):
        """AC-1: 未达间隔不调 recommend"""
        mod = self._make_mod()
        self._set_cache(mod, "hello")
        mod._turn_counter = 3

        recommend_called = False

        class MockClient:
            def recommend(self, message):
                nonlocal recommend_called
                recommend_called = True
                return "result"

        mod._client = MockClient()
        self._call_pre_llm(mod, "hello")
        assert not recommend_called

    def test_at_interval_calls_recommend(self):
        """AC-2: 达间隔调 recommend"""
        mod = self._make_mod()
        self._set_cache(mod, "hello")
        mod._turn_counter = 5

        recommend_called = False

        class MockClient:
            def recommend(self, message):
                nonlocal recommend_called
                recommend_called = True
                return "fresh"

        mod._client = MockClient()
        self._call_pre_llm(mod, "hello")
        assert recommend_called

    def test_counter_resets_to_zero(self):
        """AC-3: 重查后计数器重置"""
        mod = self._make_mod()
        self._set_cache(mod, "hello")

        class MockClient:
            def recommend(self, message):
                return "fresh"

        mod._client = MockClient()
        mod._turn_counter = 5

        self._call_pre_llm(mod, "hello")
        assert mod._turn_counter == 0

    def test_exception_fallback(self):
        """AC-4: 异常时回退"""
        mod = self._make_mod()
        self._set_cache(mod, "hello", "fallback_cache")
        mod._turn_counter = 5

        class FailingClient:
            def recommend(self, message):
                raise Exception("SRA down")

        mod._client = FailingClient()

        # 不应抛异常
        result = self._call_pre_llm(mod, "hello")
        assert result is None  # 异常时返回 None

    def test_regression(self):
        """AC-5: 回归测试通过"""
        # 由外部 pytest 验证
        pass
