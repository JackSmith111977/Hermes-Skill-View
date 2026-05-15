"""
缓存测试 — MD5 hash 消息去重
"""

from __future__ import annotations

from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]


def _load_plugin():
    """加载插件模块"""
    import importlib.util
    init_path = PLUGIN_DIR / "__init__.py"
    spec = importlib.util.spec_from_file_location("sra_guard", str(init_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestCache:
    """消息缓存测试"""

    def test_cache_key_uses_md5_prefix(self):
        """AC-3: 缓存 key 使用 MD5 前 12 位"""
        mod = _load_plugin()
        key = mod._cache_key("hello")
        assert isinstance(key, str)
        assert len(key) == 12

    def test_same_message_same_key(self):
        """同一消息产生相同 key"""
        mod = _load_plugin()
        assert mod._cache_key("test") == mod._cache_key("test")

    def test_different_message_different_key(self):
        """不同消息产生不同 key"""
        mod = _load_plugin()
        assert mod._cache_key("A") != mod._cache_key("B")

    def test_cache_set_and_get(self):
        """AC-1, AC-4: 写入后可读取，进程级字典"""
        mod = _load_plugin()
        mod._set_cached("hello", "world")
        assert mod._get_cached("hello") == "world"

    def test_cache_miss_returns_empty(self):
        """未缓存的消息返回空字符串"""
        mod = _load_plugin()
        assert mod._get_cached("not_cached") == ""
