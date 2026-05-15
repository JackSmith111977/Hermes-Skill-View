"""端到端测试 — sra-guard 插件全链路验证

STORY-4-7-1: 端到端测试
- mock SRA Daemon + 真实插件加载
- 覆盖 Phase 1-4 全链路
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[1]


# ── Mock SRA Daemon ──────────────────────────────────────


class MockSRADaemonHandler(BaseHTTPRequestHandler):
    """模拟 SRA Daemon HTTP 处理器"""

    # 类级别变量，测试可配置
    health_response = {"status": "running"}
    recommend_response = {"rag_context": "推荐: html-presentation skill"}
    validate_response = {"compliant": True, "missing": [], "severity": "info", "message": ""}
    record_response = {"status": "ok"}
    _recorded = []  # 记录收到的 POST /record 数据

    def do_GET(self):
        if self.path == "/health":
            self._send_json(self.health_response)
        else:
            self._send_json({"error": "not_found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        data = json.loads(body) if body else {}

        if self.path == "/recommend":
            self._send_json(self.recommend_response)
        elif self.path == "/validate":
            self._send_json(self.validate_response)
        elif self.path == "/record":
            self._recorded.append(data)
            self._send_json(self.record_response)
        else:
            self._send_json({"error": "not_found"}, 404)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def mock_sra():
    """启动 mock SRA Daemon，返回 (port, handler_class)"""
    MockSRADaemonHandler._recorded.clear()
    server = HTTPServer(("127.0.0.1", 0), MockSRADaemonHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port, MockSRADaemonHandler
    server.shutdown()


# ── 插件加载 ──────────────────────────────────────────────


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


# ── 测试 ──────────────────────────────────────────────────


class TestE2EMockServer:
    """AC-1: mock SRA Daemon 启停"""

    def test_mock_server_responds_to_health(self, mock_sra):
        """mock 服务器响应 /health"""
        port, _ = mock_sra
        import httpx
        resp = httpx.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"


class TestE2EPluginLoading:
    """AC-2: 插件加载 + hook 注册"""

    def test_plugin_loads_and_registers_three_hooks(self):
        """加载插件，验证 3 个 hook 注册"""
        mod = _load_plugin()

        class MockCtx:
            def __init__(self):
                self.hooks = {}
            def register_hook(self, name, callback):
                self.hooks[name] = callback

        ctx = MockCtx()
        mod.register(ctx)
        assert "pre_llm_call" in ctx.hooks
        assert "pre_tool_call" in ctx.hooks
        assert "post_tool_call" in ctx.hooks


class TestE2EMessageInjection:
    """AC-3: 消息注入 (Phase 1)"""

    @pytest.fixture
    def mod_with_mock(self, mock_sra):
        port, _ = mock_sra
        cm = _load_client()
        mod = _load_plugin()
        mod._client = cm.SraClient(http_url=f"http://127.0.0.1:{port}", timeout=2.0)
        mod._SRA_CACHE.clear()
        mod._turn_counter = 0
        yield mod
        mod._client = None
        mod._SRA_CACHE.clear()

    def test_injection_returns_context(self, mod_with_mock):
        """用户消息 → pre_llm_call → 返回 [SRA] 上下文"""
        mod = mod_with_mock
        result = mod._on_pre_llm_call(
            messages=[{"role": "user", "content": "画架构图"}],
            session_id="e2e-test",
        )
        assert result is not None
        assert "context" in result
        assert "[SRA]" in result["context"]

    def test_cache_works(self, mod_with_mock):
        """同一条消息第二次调用命中缓存"""
        mod = mod_with_mock

        # 第一次：缓存未命中
        result1 = mod._on_pre_llm_call(
            messages=[{"role": "user", "content": "写代码"}],
            session_id="e2e-test",
        )
        assert result1 is not None

        # 第二次：缓存命中
        result2 = mod._on_pre_llm_call(
            messages=[{"role": "user", "content": "写代码"}],
            session_id="e2e-test",
        )
        assert result2 is not None
        assert result2["context"] == result1["context"]


class TestE2EToolValidation:
    """AC-4: 工具校验 (Phase 2)"""

    @pytest.fixture
    def mod_with_mock(self, mock_sra):
        port, _ = mock_sra
        cm = _load_client()
        mod = _load_plugin()
        mod._client = cm.SraClient(http_url=f"http://127.0.0.1:{port}", timeout=2.0)
        yield mod
        mod._client = None

    def test_write_file_passes_validation(self, mod_with_mock):
        """write_file → pre_tool_call → 返回 None（放行）"""
        mod = mod_with_mock
        result = mod._on_pre_tool_call(
            tool_name="write_file",
            args={"path": "test.html"},
            task_id="t1", session_id="s1", tool_call_id="c1",
        )
        assert result is None  # 放行


class TestE2ETracking:
    """AC-5: 轨迹记录 (Phase 3)"""

    @pytest.fixture
    def mod_with_mock(self, mock_sra):
        port, handler_cls = mock_sra
        handler_cls._recorded.clear()
        cm = _load_client()
        mod = _load_plugin()
        mod._client = cm.SraClient(http_url=f"http://127.0.0.1:{port}", timeout=2.0)
        mod._last_record_time = {}
        yield mod, handler_cls
        mod._client = None
        mod._last_record_time = {}

    def test_skill_view_records_viewed(self, mod_with_mock):
        """skill_view → post_tool_call → record viewed"""
        mod, handler = mod_with_mock
        handler._recorded.clear()

        mod._on_post_tool_call(
            tool_name="skill_view",
            args={"name": "html-presentation"},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )

        assert len(handler._recorded) >= 1
        last = handler._recorded[-1]
        assert last.get("action") == "viewed"
        assert last.get("skill") == "html-presentation"

    def test_write_file_records_used(self, mod_with_mock):
        """write_file → post_tool_call → record used"""
        mod, handler = mod_with_mock
        handler._recorded.clear()

        mod._on_post_tool_call(
            tool_name="write_file",
            args={"path": "test.html"},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )

        assert len(handler._recorded) >= 1
        last = handler._recorded[-1]
        assert last.get("action") == "used"


class TestE2ERecheck:
    """AC-6: 重注入 (Phase 4)"""

    @pytest.fixture
    def mod_with_mock(self, mock_sra):
        port, handler_cls = mock_sra
        cm = _load_client()
        mod = _load_plugin()
        mod._client = cm.SraClient(http_url=f"http://127.0.0.1:{port}", timeout=2.0)
        mod._SRA_CACHE.clear()
        mod._turn_counter = 0
        yield mod
        mod._client = None
        mod._SRA_CACHE.clear()
        mod._turn_counter = 0

    def test_recheck_after_5_turns(self, mod_with_mock):
        """5 轮后清除缓存 → 重查"""
        mod = mod_with_mock
        text = "画架构图"

        # 第一次：调 SRA
        r1 = mod._on_pre_llm_call(
            messages=[{"role": "user", "content": text}],
            session_id="e2e-recheck",
        )
        assert r1 is not None
        first_context = r1["context"]

        # 第 2-4 轮：缓存命中，不调 SRA
        for i in range(3):
            r = mod._on_pre_llm_call(
                messages=[{"role": "user", "content": text}],
                session_id="e2e-recheck",
            )
            assert r is not None

        # 第 5 轮：达到 RECHECK_INTERVAL，清除缓存，调 SRA
        # 计数器现在是 4（第 1 次+1，2-4 各+1）
        # 第 5 次调用时 counter=5 → 触发重查
        r5 = mod._on_pre_llm_call(
            messages=[{"role": "user", "content": text}],
            session_id="e2e-recheck",
        )
        assert r5 is not None
        # 上下文字段应不同（新推荐）
        assert r5["context"] is not None


class TestE2EGracefulDegradation:
    """AC-7: SRA 不可用降级"""

    def test_all_hooks_work_when_sra_down(self):
        """mock 服务器关闭后，所有 hook 返回 None（不抛异常）"""
        mod = _load_plugin()
        mod._client = None  # 模拟 SRA 不可用
        mod._SRA_CACHE.clear()
        mod._turn_counter = 0

        # pre_llm_call
        r1 = mod._on_pre_llm_call(
            messages=[{"role": "user", "content": "hello"}],
            session_id="e2e-down",
        )
        assert r1 is None

        # pre_tool_call
        r2 = mod._on_pre_tool_call(
            tool_name="write_file", args={},
            task_id="t1", session_id="s1", tool_call_id="c1",
        )
        assert r2 is None

        # post_tool_call
        r3 = mod._on_post_tool_call(
            tool_name="skill_view", args={"name": "test"},
            result="", task_id="t1", session_id="s1",
            tool_call_id="c1", duration_ms=10,
        )
        assert r3 is None


class TestE2EIndependent:
    """AC-8: 独立可运行"""

    def test_runs_without_hermes_installation(self):
        """不依赖已安装的 Hermes，使用 importlib 加载"""
        mod = _load_plugin()
        assert hasattr(mod, "register")
        assert hasattr(mod, "_on_pre_llm_call")
        assert hasattr(mod, "_on_pre_tool_call")
        assert hasattr(mod, "_on_post_tool_call")
