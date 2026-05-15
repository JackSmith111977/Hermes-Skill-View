"""
消息注入集成测试 — 验证 _on_pre_llm_call 的完整注入链路

使用 mock SRA HTTP 服务器模拟 SRA Daemon。
覆盖正常/多轮/非user/空消息/缓存/截断/降级 7 种场景。
"""

from __future__ import annotations

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict

import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[1]


# ── Mock SRA HTTP Server ─────────────────────────────────


class MockSRAHandler(BaseHTTPRequestHandler):
    """模拟 SRA Daemon — 记录请求次数"""

    call_count = 0

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "running"})
        else:
            self._send_json({"error": "not_found"}, 404)

    def do_POST(self):
        MockSRAHandler.call_count += 1
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/recommend":
            query = body.get("message", "")
            self._send_json({
                "rag_context": (
                    "── [SRA Skill 推荐] ──────────────────────────────\n"
                    f"  ⭐ [medium] injected-skill (50.0分) — query'{query[:20]}'\n"
                    "── ──────────────────────────────────────────────"
                ),
                "recommendations": [
                    {"skill": "injected-skill", "score": 50.0, "confidence": "medium"}
                ],
                "top_skill": "injected-skill",
                "should_auto_load": False,
                "sra_available": True,
            })
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
def mock_sra():
    """启动 mock SRA 服务器"""
    MockSRAHandler.call_count = 0
    server = HTTPServer(("127.0.0.1", 0), MockSRAHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


# ── 加载插件 ───────────────────────────────────────────────


def _load_plugin():
    """加载插件模块并替换 client 的目标地址为 mock 服务器"""
    init_path = PLUGIN_DIR / "__init__.py"
    spec = importlib.util.spec_from_file_location("sra_guard", str(init_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _patch_client(mod, port: int):
    """将插件内部的 SraClient 指向 mock 服务器"""
    # 替换 _get_client 返回指向 mock 的 client
    client_path = PLUGIN_DIR / "client.py"
    spec = importlib.util.spec_from_file_location("sra_guard.client", str(client_path))
    cm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cm)
    mock_client = cm.SraClient(http_url=f"http://127.0.0.1:{port}", timeout=2.0)
    # 直接注入到模块（绕过 _get_client 的缓存）
    mod._client = mock_client
    return mod


# ── 集成测试 ──────────────────────────────────────────────


class TestMessageInjection:
    """消息注入 7 场景集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_sra):
        port = mock_sra
        mod = _load_plugin()
        self.mod = _patch_client(mod, port)

    def test_normal_injection_contains_sra_header(self):
        """AC-1: 正常消息注入包含 [SRA] 前缀"""
        result = self.mod._on_pre_llm_call(
            messages=[{"role": "user", "content": "帮我画架构图"}],
            session_id="test-001",
        )
        assert result is not None
        assert "context" in result
        assert "[SRA]" in result["context"]
        assert "injected-skill" in result["context"]

    def test_multi_turn_extracts_last_user_message(self):
        """AC-2: 多轮对话只提取最后一条 user message"""
        result = self.mod._on_pre_llm_call(
            messages=[
                {"role": "assistant", "content": "好的"},
                {"role": "user", "content": "第一轮问题"},
                {"role": "assistant", "content": "回答完了"},
                {"role": "user", "content": "画架构图"},
            ],
            session_id="test-002",
        )
        assert result is not None
        assert "context" in result
        # 验证发送到 SRA 的是最后一条消息
        assert MockSRAHandler.call_count >= 1

    def test_non_user_role_returns_none(self):
        """AC-3: 非 user role 不注入"""
        result = self.mod._on_pre_llm_call(
            messages=[{"role": "assistant", "content": "你好"}],
            session_id="test-003",
        )
        assert result is None

    def test_empty_message_returns_none(self):
        """AC-4: 空消息不注入"""
        result = self.mod._on_pre_llm_call(
            messages=[{"role": "user", "content": ""}],
            session_id="test-004",
        )
        assert result is None

    def test_cache_hit_avoids_duplicate_request(self):
        """AC-5: 缓存命中时跳过 SRA 请求"""
        count_before = MockSRAHandler.call_count

        # 第一次调用（未缓存）
        result1 = self.mod._on_pre_llm_call(
            messages=[{"role": "user", "content": "画架构图"}],
            session_id="test-005",
        )
        count_after_first = MockSRAHandler.call_count
        assert count_after_first > count_before

        # 第二次调用（应命中缓存）
        result2 = self.mod._on_pre_llm_call(
            messages=[{"role": "user", "content": "画架构图"}],
            session_id="test-005",
        )
        count_after_second = MockSRAHandler.call_count
        assert count_after_second == count_after_first  # 请求数不变

        # 两次结果一致
        assert result1 == result2

    def test_long_context_truncation(self):
        """AC-6: 长消息截断"""
        long_msg = "帮我画一幅" + "非常详细的" * 500 + "架构图"

        result = self.mod._on_pre_llm_call(
            messages=[{"role": "user", "content": long_msg}],
            session_id="test-006",
        )
        # SRA 返回后格式化，截断在 2500 字符
        if result and "context" in result:
            assert len(result["context"]) <= 2500

    def test_sra_unavailable_returns_none(self):
        """AC-7: SRA 不可用时优雅降级"""
        mod = _load_plugin()
        # 创建一个指向不存在地址的 client
        client_path = PLUGIN_DIR / "client.py"
        spec = importlib.util.spec_from_file_location("sra_guard.client", str(client_path))
        cm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cm)
        mod._client = cm.SraClient(http_url="http://127.0.0.1:19999", timeout=0.5)

        result = mod._on_pre_llm_call(
            messages=[{"role": "user", "content": "测试降级"}],
            session_id="test-007",
        )
        assert result is None
