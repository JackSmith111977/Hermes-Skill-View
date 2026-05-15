"""
工具校验测试 — pre_tool_call hook + Force Level 感知

STORY-4-3-1: pre_tool_call → POST /validate 核心链路
STORY-4-3-2: Force Level 感知
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


def _load_client():
    """加载 client 模块"""
    import importlib.util
    client_path = PLUGIN_DIR / "client.py"
    spec = importlib.util.spec_from_file_location("sra_guard.client", str(client_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Force Level Tests (STORY-4-3-2) ─────────────────────


class TestForceLevel:
    """Force Level 感知测试"""

    def _make_mod(self):
        return _load_plugin()

    def test_medium_monitors_key_tools(self):
        """AC-1: medium 级别监控关键工具"""
        mod = self._make_mod()
        for tool in ("write_file", "patch", "terminal", "execute_code"):
            assert mod._should_validate(tool, "medium"), f"{tool} should be monitored"

    def test_medium_ignores_other_tools(self):
        """medium 级别不监控非关键工具"""
        mod = self._make_mod()
        assert not mod._should_validate("web_search", "medium")
        assert not mod._should_validate("read_file", "medium")

    def test_advanced_monitors_all(self):
        """AC-2: advanced 监控全部工具"""
        mod = self._make_mod()
        assert mod._should_validate("anything", "advanced")
        assert mod._should_validate("web_search", "advanced")

    def test_omni_monitors_all(self):
        """omni 监控全部工具"""
        mod = self._make_mod()
        assert mod._should_validate("anything", "omni")

    def test_basic_monitors_none(self):
        """AC-3: basic 级别不监控"""
        mod = self._make_mod()
        assert not mod._should_validate("write_file", "basic")
        assert not mod._should_validate("terminal", "basic")

    def test_default_level_is_medium(self):
        """AC-4: 默认级别为 medium"""
        mod = self._make_mod()
        assert mod.DEFAULT_FORCE_LEVEL == "medium"

    def test_default_uses_medium(self):
        """未指定 force level 时使用 medium 默认值"""
        mod = self._make_mod()
        assert mod._should_validate("write_file")  # medium 监控 write_file
        assert not mod._should_validate("unknown_tool")  # medium 不监控


# ── Pre Tool Call Tests (STORY-4-3-1) ──────────────────


class TestPreToolCall:
    """pre_tool_call hook 回调测试"""

    def _make_mod(self):
        return _load_plugin()

    def test_returns_none_when_tool_not_monitored(self):
        """非监控工具直接放行"""
        mod = self._make_mod()
        result = mod._on_pre_tool_call(
            tool_name="web_search",
            args={},
            task_id="t1", session_id="s1", tool_call_id="c1",
        )
        assert result is None  # 非监控工具直接放行

    def test_returns_none_when_client_unavailable(self):
        """SRA 不可用时放行（优雅降级）"""
        mod = self._make_mod()
        # 确保 client 未初始化（_client = None）
        mod._client = None
        result = mod._on_pre_tool_call(
            tool_name="write_file",
            args={"path": "test.html"},
            task_id="t1", session_id="s1", tool_call_id="c1",
        )
        assert result is None  # 优雅降级

    def test_handles_exception_gracefully(self):
        """异常时放行"""
        mod = self._make_mod()
        # 传入 None 作为 args
        result = mod._on_pre_tool_call(
            tool_name="write_file",
            args=None,
            task_id="t1", session_id="s1", tool_call_id="c1",
        )
        assert result is None

    def test_accepts_valid_signature(self):
        """回调签名匹配 Hermes 规范"""
        mod = self._make_mod()
        # 带所有参数调用
        result = mod._on_pre_tool_call(
            tool_name="write_file",
            args={"path": "test.html"},
            task_id="task-1",
            session_id="session-1",
            tool_call_id="call-1",
            extra_param="ignored",  # 额外的 kwargs
        )
        # client 未初始化，应返回 None（优雅降级）
        assert result is None


# ── 集成测试 (STORY-4-3-3) — 使用 mock SRA 服务器 ─────


class TestValidateIntegration:
    """pre_tool_call 集成测试 — 使用 mock SRA 服务器"""

    @pytest.fixture(scope="class")
    def mock_validate_server(self):
        """启动支持 /validate 端点的 mock SRA 服务器"""
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        validate_responses = iter([])  # 会被覆盖

        class ValidateHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/health":
                    self._send_json({"status": "running"})
                else:
                    self._send_json({"error": "not_found"}, 404)

            def do_POST(self):
                if self.path == "/validate":
                    try:
                        resp = next(validate_responses)
                    except StopIteration:
                        resp = {"compliant": True, "missing": [], "severity": "info", "message": ""}
                    self._send_json(resp)
                else:
                    self._send_json({"error": "not_found"}, 404)

            def _send_json(self, data, status=200):
                body = json.dumps(data).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), ValidateHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield port, validate_responses
        server.shutdown()

    def _make_mock_client(self, port):
        """创建指向 mock 服务器的 client"""
        cm = _load_client()
        return cm.SraClient(http_url=f"http://127.0.0.1:{port}", timeout=2.0)

    def test_compliant_tool_passes(self):
        """AC-1: compliant=True 时放行"""
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        response = {"compliant": True, "missing": [], "severity": "info", "message": ""}

        class CompliantHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                self._send_json(response)

            def _send_json(self, data, status=200):
                body = json.dumps(data).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a): pass

        server = HTTPServer(("127.0.0.1", 0), CompliantHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        mod = _load_plugin()
        mod._client = self._make_mock_client(port)

        result = mod._on_pre_tool_call(
            tool_name="write_file",
            args={"path": "test.html"},
            task_id="t1", session_id="s1", tool_call_id="c1",
        )
        assert result is None  # 放行

        server.shutdown()

    def test_warning_tool_passes(self):
        """AC-2: severity=warning 时不阻断"""
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        response = {
            "compliant": False, "missing": ["html-presentation"],
            "severity": "warning",
            "message": "建议加载 html-presentation skill",
        }

        class WarningHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                self._send_json(response)
            def _send_json(self, data, status=200):
                body = json.dumps(data).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *a): pass

        server = HTTPServer(("127.0.0.1", 0), WarningHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        mod = _load_plugin()
        mod._client = self._make_mock_client(port)

        result = mod._on_pre_tool_call(
            tool_name="write_file",
            args={"path": "test.html"},
            task_id="t1", session_id="s1", tool_call_id="c1",
        )
        assert result is None  # warning 不阻断，放行

        server.shutdown()

    def test_basic_level_skips_validation(self):
        """AC-4: basic 级别不校验"""
        mod = _load_plugin()
        # 即使 client 未初始化，basic 级别也应直接放行
        mod._client = None
        # 模拟 basic 级别：不监控 write_file
        result = mod._on_pre_tool_call(
            tool_name="write_file",
            args={"path": "test.html"},
            task_id="t1", session_id="s1", tool_call_id="c1",
        )
        # write_file 在 medium 下才监控，默认 medium 所以会校验
        # 这里验证 basic 行为通过 _should_validate
        assert not mod._should_validate("write_file", "basic")
