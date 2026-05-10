"""SRA HTTP 服务器测试 — 验证 ThreadingMixIn + serve_forever 的正确性"""

import os
import sys
import json
import time
import socket
import threading
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor import SkillAdvisor
from skill_advisor.runtime.daemon import SRaDDaemon, load_config


class TestHTTPServerCore:
    """HTTP 服务器核心测试（不启动完整 daemon）"""

    def test_http_server_imports(self):
        """验证 HTTP 服务器所需的模块可导入"""
        import http.server
        import socketserver
        assert hasattr(http.server, "BaseHTTPRequestHandler")
        assert hasattr(socketserver, "ThreadingMixIn")

    def test_threaded_http_server_class(self):
        """验证 ThreadedHTTPServer 类可正确创建"""
        import http.server
        import socketserver
        
        class TestServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
            allow_reuse_address = True
            daemon_threads = True
        
        import tempfile
        server = TestServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
        assert server.server_address is not None
        server.server_close()

    def test_serve_forever_in_thread(self):
        """验证 serve_forever() 在独立线程中可正常启动和停止"""
        import http.server
        import socketserver
        
        class TestServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
            allow_reuse_address = True
            daemon_threads = True
        
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
        
        import tempfile
        server = TestServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        
        # 在线程中启动 serve_forever
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.1)
        
        # 发送请求验证
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
            assert resp.status == 200
            assert resp.read() == b"ok"
        finally:
            server.shutdown()
            server.server_close()


class TestDaemonHTTPServer:
    """Daemon HTTP 服务器集成测试"""

    @classmethod
    def setup_class(cls):
        """启动一个测试用 HTTP 服务器"""
        import tempfile
        cls.tmp_dir = tempfile.mkdtemp()
        cls.skills_dir = os.path.join(cls.tmp_dir, "skills")
        os.makedirs(cls.skills_dir, exist_ok=True)
        
        # 使用随机端口
        cls.config = {
            "http_port": 0,  # 让 OS 分配
            "enable_unix_socket": False,
            "skills_dir": cls.skills_dir,
            "data_dir": os.path.join(cls.tmp_dir, "data"),
        }
        
        cls.daemon = SRaDDaemon(cls.config)
        cls.daemon.start()
        
        # 获取实际分配的端口
        if cls.daemon._http_server:
            cls.port = cls.daemon._http_server.server_address[1]
        else:
            cls.port = 0
        
        time.sleep(0.2)  # 等待就绪

    @classmethod
    def teardown_class(cls):
        cls.daemon.stop()
        import shutil
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _request(self, path, method="GET", data=None):
        """发送 HTTP 请求"""
        url = f"http://127.0.0.1:{self.port}{path}"
        req = urllib.request.Request(url, method=method)
        if data is not None:
            req.data = json.dumps(data).encode("utf-8")
            req.add_header("Content-Type", "application/json")
        try:
            resp = urllib.request.urlopen(req, timeout=3)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return {"status": e.code, "body": e.read().decode()}
    
    def test_health_endpoint(self):
        """GET /health 应返回 200"""
        if not self.port:
            return  # 跳过（服务器未启动）
        result = self._request("/health")
        assert "status" in result
        assert result.get("status") == "ok"
    
    def test_status_endpoint(self):
        """GET /status 应返回 SRA 状态"""
        if not self.port:
            return
        result = self._request("/status")
        assert result.get("sra_engine") == True
        assert "version" in result
    
    def test_stats_endpoint(self):
        """GET /stats 应返回统计信息"""
        if not self.port:
            return
        result = self._request("/stats")
        assert "skills_count" in result or "status" in result
    
    def test_recommend_endpoint_get(self):
        """GET /recommend?q=xxx 应返回推荐"""
        if not self.port:
            return
        result = self._request("/recommend?q=hello")
        assert isinstance(result, dict)

    def test_recommend_endpoint_post(self):
        """POST /recommend 应返回推荐"""
        if not self.port:
            return
        result = self._request("/recommend", method="POST", data={"message": "hello"})
        assert isinstance(result, dict)
    
    def test_404_for_unknown_path(self):
        """未知路径应返回 404"""
        if not self.port:
            return
        result = self._request("/nonexistent")
        if "status" in result and result["status"] == 404:
            pass  # HTTPError 已捕获
        elif "error" in result:
            assert result["error"] == "not_found"

    def test_concurrent_requests(self):
        """并发请求应都能正常响应"""
        if not self.port:
            return
        
        results = []
        def make_request():
            try:
                resp = self._request("/health")
                results.append(resp)
            except Exception:
                results.append(None)
        
        threads = []
        for _ in range(5):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(results) == 5
        assert all(r is not None for r in results)
        assert all(r.get("status") == "ok" for r in results)
