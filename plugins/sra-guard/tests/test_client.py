"""
SraClient 通信模块测试 — 验证 HTTP + Unix Socket 双协议

使用 mock HTTP 服务器模拟 SRA Daemon 的响应。
不依赖真实 SRA Daemon。
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict

import pytest

# 插件目录 (plugins/sra-guard/ 在 SRA 项目根目录)
PLUGIN_DIR = Path(__file__).resolve().parents[1]


# ── Mock SRA HTTP Server ─────────────────────────────────


class MockSRAHandler(BaseHTTPRequestHandler):
    """模拟 SRA Daemon 的 HTTP 端点"""

    responses: Dict[str, Any] = {}
    received_requests = []

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "running", "sra_version": "2.0.3"})
        else:
            self._send_json({"error": "not_found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        self.received_requests.append({"method": "POST", "path": self.path, "body": body})

        if self.path == "/recommend":
            self._send_json({
                "rag_context": "── [SRA Skill 推荐] ───\n  ⭐ [medium] test-skill (50.0分)\n── ──────────────────────",
                "recommendations": [{"skill": "test-skill", "score": 50.0, "confidence": "medium"}],
                "top_skill": "test-skill",
                "should_auto_load": False,
                "sra_available": True,
            })
        elif self.path == "/validate":
            self._send_json({
                "compliant": True,
                "missing": [],
                "severity": "info",
                "message": "",
            })
        elif self.path == "/record":
            self._send_json({"status": "ok"})
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


@pytest.fixture(scope="module")
def mock_sra_server():
    """启动 mock SRA HTTP 服务器，返回 (host, port)"""
    server = HTTPServer(("127.0.0.1", 0), MockSRAHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    MockSRAHandler.received_requests.clear()
    yield ("127.0.0.1", port)
    server.shutdown()


# ── SraClient 加载 ────────────────────────────────────────


def _load_client():
    """从 plugins/sra-guard/client.py 加载 SraClient"""
    import importlib.util
    client_path = PLUGIN_DIR / "client.py"
    assert client_path.exists(), f"{client_path} 不存在"

    spec = importlib.util.spec_from_file_location("sra_guard.client", str(client_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── 测试用例 ────────────────────────────────────────────


class TestSraClient:
    """SraClient 通信模块测试"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_sra_server):
        host, port = mock_sra_server
        client_mod = _load_client()
        self.client = client_mod.SraClient(
            http_url=f"http://{host}:{port}",
            timeout=2.0,
        )

    def test_recommend_returns_rag_context(self):
        """recommend() 返回 rag_context 字符串"""
        ctx = self.client.recommend("帮我画架构图")
        assert isinstance(ctx, str)
        assert "SRA Skill" in ctx
        assert "test-skill" in ctx

    def test_recommend_empty_message(self):
        """空消息返回空字符串"""
        ctx = self.client.recommend("")
        assert ctx == ""

    def test_validate_returns_dict(self):
        """validate() 返回校验结果"""
        result = self.client.validate("write_file", {"path": "test.html"}, loaded_skills=[])
        assert isinstance(result, dict)
        assert "compliant" in result
        assert result["compliant"] is True

    def test_record_returns_true(self):
        """record() 返回 True"""
        success = self.client.record("test-skill", "used")
        assert success is True

    def test_health_returns_true_when_running(self):
        """health() 在 SRA 运行时返回 True"""
        healthy = self.client.health()
        assert healthy is True

    def test_health_returns_false_when_down(self):
        """health() 在 SRA 不可用时返回 False"""
        client_mod = _load_client()
        c = client_mod.SraClient(http_url="http://127.0.0.1:19999", timeout=0.5)
        assert c.health() is False

    def test_timeout_returns_empty(self):
        """超时返回空字符串/False"""
        client_mod = _load_client()
        c = client_mod.SraClient(http_url="http://127.0.0.1:19999", timeout=0.5)
        ctx = c.recommend("test")
        assert ctx == ""

    def test_connection_refused_returns_empty(self):
        """连接被拒返回空字符串"""
        client_mod = _load_client()
        c = client_mod.SraClient(http_url="http://127.0.0.1:19998", timeout=0.5)
        ctx = c.recommend("test")
        assert ctx == ""
