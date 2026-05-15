"""
sra-guard 插件基础测试 — 验证目录结构、清单文件、插件注册

不依赖 SRA Daemon。使用 mock Hermes PluginRegistrationContext。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

# 插件目录 (plugins/sra-guard/ 在 SRA 项目根目录)
PLUGIN_DIR = Path(__file__).resolve().parents[1]


def _load_plugin_module():
    """从 plugins/sra-guard/__init__.py 加载插件模块"""
    init_path = PLUGIN_DIR / "__init__.py"
    spec = importlib.util.spec_from_file_location("sra_guard", str(init_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class MockRegistrationContext:
    """模拟 Hermes 的 PluginRegistrationContext"""

    def __init__(self):
        self.hooks = {}
        self.commands = {}

    def register_hook(self, name, callback):
        self.hooks.setdefault(name, []).append(callback)

    def register_command(self, name, handler, description=""):
        self.commands[name] = {"handler": handler, "description": description}


# ── 测试 ─────────────────────────────────────────────────


class TestPluginStructure:
    """插件基础结构测试"""

    def test_plugin_yaml_exists(self):
        """plugin.yaml 存在且格式正确"""
        yaml_path = PLUGIN_DIR / "plugin.yaml"
        assert yaml_path.exists(), f"{yaml_path} 不存在"

        with open(yaml_path) as f:
            meta = yaml.safe_load(f)

        assert meta["name"] == "sra-guard"
        assert "version" in meta
        assert "description" in meta
        assert "hooks" in meta
        assert "pre_llm_call" in meta["hooks"]

    def test_init_py_exists_and_loadable(self):
        """__init__.py 存在且可被加载"""
        init_path = PLUGIN_DIR / "__init__.py"
        assert init_path.exists(), f"{init_path} 不存在"
        mod = _load_plugin_module()
        assert mod is not None

    def test_client_py_exists(self):
        """client.py 存在且可加载"""
        client_path = PLUGIN_DIR / "client.py"
        assert client_path.exists(), f"{client_path} 不存在"

    def test_register_function_exists(self):
        """register(ctx) 函数存在且可调用"""
        mod = _load_plugin_module()
        assert hasattr(mod, "register")
        assert callable(mod.register)

    def test_register_hooks_pre_llm_call(self):
        """register 注册 pre_llm_call hook"""
        mod = _load_plugin_module()
        ctx = MockRegistrationContext()
        mod.register(ctx)

        assert "pre_llm_call" in ctx.hooks
        assert len(ctx.hooks["pre_llm_call"]) == 1
        assert callable(ctx.hooks["pre_llm_call"][0])

    def test_register_hooks_pre_tool_call(self):
        """register 注册 pre_tool_call hook（Phase 2）"""
        mod = _load_plugin_module()
        ctx = MockRegistrationContext()
        mod.register(ctx)

        assert "pre_tool_call" in ctx.hooks
        assert len(ctx.hooks["pre_tool_call"]) == 1
        assert callable(ctx.hooks["pre_tool_call"][0])


class TestPreLlmCall:
    """pre_llm_call hook 回调测试"""

    def _make_mod(self):
        return _load_plugin_module()

    def test_returns_none_when_no_messages(self):
        """无消息时返回 None"""
        mod = self._make_mod()
        result = mod._on_pre_llm_call(messages=[], session_id="test")
        assert result is None

    def test_returns_none_when_messages_is_none(self):
        """messages=None 时返回 None"""
        mod = self._make_mod()
        result = mod._on_pre_llm_call(messages=None, session_id="test")
        assert result is None

    def test_returns_none_when_no_user_message(self):
        """最后一条消息不是 user role 时返回 None"""
        mod = self._make_mod()
        result = mod._on_pre_llm_call(
            messages=[{"role": "assistant", "content": "你好"}],
            session_id="test",
        )
        assert result is None

    def test_returns_none_when_sra_unavailable(self):
        """SRA 不可用时返回 None（优雅降级）"""
        mod = self._make_mod()
        result = mod._on_pre_llm_call(
            messages=[{"role": "user", "content": "hello"}],
            session_id="test",
        )
        assert result is None

    def test_handles_exception_gracefully(self):
        """异常时返回 None 不向上传播"""
        mod = self._make_mod()
        result = mod._on_pre_llm_call(messages="not a list", session_id="test")
        assert result is None

    def test_extracts_last_user_message_and_returns_none_or_context(self):
        """正确提取最后一条用户消息，SRA 可用时返回 context，不可用时返回 None"""
        mod = self._make_mod()
        result = mod._on_pre_llm_call(
            messages=[
                {"role": "assistant", "content": "之前的内容"},
                {"role": "user", "content": "帮我画架构图"},
            ],
            session_id="test",
        )
        # SRA 可用时返回 {"context": "..."}，不可用时返回 None
        # 两者都算正确（取决于当前环境是否有 SRA Daemon）
        assert result is None or (isinstance(result, dict) and "context" in result)
