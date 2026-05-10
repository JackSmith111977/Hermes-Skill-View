"""SRaDDaemon 核心单元测试 — 生命周期 + 状态管理 + 请求处理"""

import os
import sys
import json
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor.runtime.daemon import SRaDDaemon, cmd_status, PID_FILE, STATUS_FILE


class TestSRaDDaemonInit:
    """SRaDDaemon 初始化和基本属性测试"""

    def setup_method(self):
        self.data_dir = tempfile.mkdtemp()
        self.skills_dir = tempfile.mkdtemp()
        self.config = {
            "skills_dir": self.skills_dir,
            "data_dir": self.data_dir,
            "http_port": 0,
            "enable_http": False,
            "enable_unix_socket": False,
            "log_level": "DEBUG",
        }
        # 创建一个空技能目录
        os.makedirs(self.skills_dir, exist_ok=True)

    def teardown_method(self):
        shutil.rmtree(self.data_dir, ignore_errors=True)
        shutil.rmtree(self.skills_dir, ignore_errors=True)

    def test_init_with_custom_config(self):
        """自定义配置初始化"""
        daemon = SRaDDaemon(self.config)
        assert daemon.config["data_dir"] == self.data_dir
        assert daemon.config["skills_dir"] == self.skills_dir
        assert daemon.running is False
        assert daemon._stats["total_requests"] == 0

    def test_init_default_config(self):
        """缺省配置初始化"""
        # 用临时 SRA_HOME 避免影响真实环境
        with tempfile.TemporaryDirectory() as sra_home:
            old_home = os.environ.get("SRA_HOME")
            os.environ["SRA_HOME"] = sra_home
            try:
                daemon = SRaDDaemon()
                assert daemon.config["http_port"] == 8536
                assert daemon.config["enable_http"] is True
            finally:
                if old_home:
                    os.environ["SRA_HOME"] = old_home
                else:
                    del os.environ["SRA_HOME"]

    def test_advisor_is_initialized(self):
        """初始化后 advisor 应可用"""
        daemon = SRaDDaemon(self.config)
        assert daemon.advisor is not None
        assert daemon.advisor.data_dir == self.data_dir

    def test_stats_initial_values(self):
        """初始统计值应为 0"""
        daemon = SRaDDaemon(self.config)
        assert daemon._stats["total_requests"] == 0
        assert daemon._stats["total_recommendations"] == 0
        assert daemon._stats["errors"] == 0
        assert daemon._stats["started_at"] is None


class TestSRaDDaemonStats:
    """get_stats 方法测试"""

    def setup_method(self):
        self.data_dir = tempfile.mkdtemp()
        self.skills_dir = tempfile.mkdtemp()
        self.config = {
            "skills_dir": self.skills_dir,
            "data_dir": self.data_dir,
            "http_port": 0,
            "enable_http": False,
            "enable_unix_socket": False,
            "log_level": "DEBUG",
        }
        os.makedirs(self.skills_dir, exist_ok=True)
        self.daemon = SRaDDaemon(self.config)

    def teardown_method(self):
        shutil.rmtree(self.data_dir, ignore_errors=True)
        shutil.rmtree(self.skills_dir, ignore_errors=True)

    def test_get_stats_before_start(self):
        """启动前调用 get_stats 返回正确结构"""
        stats = self.daemon.get_stats()
        assert stats["status"] == "stopped"
        assert stats["total_requests"] == 0
        assert stats["total_recommendations"] == 0
        assert stats["errors"] == 0
        assert stats["uptime_seconds"] == 0
        assert "version" in stats
        assert "skills_count" in stats

    def test_get_stats_after_start(self, monkeypatch):
        """启动后状态应为 running"""
        # 避免真正启动 socket 和 HTTP server
        monkeypatch.setattr(self.daemon, "_run_socket_server", lambda: None)
        monkeypatch.setattr(self.daemon, "_run_http_server", lambda: None)
        monkeypatch.setattr(self.daemon, "_auto_refresh_loop", lambda: None)
        self.daemon.start()
        try:
            stats = self.daemon.get_stats()
            assert stats["status"] == "running"
            assert stats["total_requests"] == 0
        finally:
            self.daemon.stop()

    def test_get_stats_increments_on_recommend(self, monkeypatch):
        """推荐操作应增加统计计数"""
        monkeypatch.setattr(self.daemon, "_run_socket_server", lambda: None)
        monkeypatch.setattr(self.daemon, "_run_http_server", lambda: None)
        monkeypatch.setattr(self.daemon, "_auto_refresh_loop", lambda: None)
        self.daemon.start()
        try:
            with self.daemon._lock:
                self.daemon._stats["total_recommendations"] += 1
            stats = self.daemon.get_stats()
            assert stats["total_recommendations"] >= 1
        finally:
            self.daemon.stop()


class TestSRaDDaemonStatus:
    """_update_status 方法测试"""

    def setup_method(self):
        self.data_dir = tempfile.mkdtemp()
        self.skills_dir = tempfile.mkdtemp()
        self.status_dir = tempfile.mkdtemp()
        self.config = {
            "skills_dir": self.skills_dir,
            "data_dir": self.data_dir,
            "http_port": 0,
            "enable_http": False,
            "enable_unix_socket": False,
            "log_level": "DEBUG",
        }
        os.makedirs(self.skills_dir, exist_ok=True)

    def teardown_method(self):
        shutil.rmtree(self.data_dir, ignore_errors=True)
        shutil.rmtree(self.skills_dir, ignore_errors=True)
        shutil.rmtree(self.status_dir, ignore_errors=True)


class TestSRaDDaemonHandleRequest:
    """_handle_request socket 请求分发测试"""

    def setup_method(self):
        self.data_dir = tempfile.mkdtemp()
        self.skills_dir = tempfile.mkdtemp()
        self.config = {
            "skills_dir": self.skills_dir,
            "data_dir": self.data_dir,
            "http_port": 0,
            "enable_http": False,
            "enable_unix_socket": False,
            "log_level": "DEBUG",
        }
        os.makedirs(self.skills_dir, exist_ok=True)
        self.daemon = SRaDDaemon(self.config)

    def teardown_method(self):
        shutil.rmtree(self.data_dir, ignore_errors=True)
        shutil.rmtree(self.skills_dir, ignore_errors=True)

    def test_ping_action(self):
        """ping 应返回 pong"""
        result = self.daemon._handle_request({"action": "ping"})
        assert result["pong"] is True
        assert result["status"] == "ok"

    def test_unknown_action(self):
        """未知 action 应返回 error"""
        result = self.daemon._handle_request({"action": "nonexistent"})
        assert "error" in result
        assert "unknown action" in result["error"]

    def test_recommend_empty_query(self):
        """空查询应返回错误"""
        result = self.daemon._handle_request({
            "action": "recommend",
            "params": {"query": ""},
        })
        assert "error" in result

    def test_refresh_action(self):
        """refresh 应返回索引数量"""
        result = self.daemon._handle_request({"action": "refresh"})
        assert "count" in result
        assert result["status"] == "ok"

    def test_stats_action(self):
        """stats 应返回统计信息"""
        result = self.daemon._handle_request({"action": "stats"})
        assert "stats" in result

    def test_record_action_with_input(self):
        """record 应正常记录（旧 API）"""
        result = self.daemon._handle_request({
            "action": "record",
            "params": {"skill": "test-skill", "input": "test query", "accepted": True},
        })
        assert result["status"] == "ok"

    def test_record_action_viewed(self):
        """record viewed 应正常工作（新 API）"""
        result = self.daemon._handle_request({
            "action": "record",
            "params": {"skill": "test-skill", "action": "viewed"},
        })
        assert result["status"] == "ok"

    def test_record_action_used(self):
        """record used 应正常工作"""
        result = self.daemon._handle_request({
            "action": "record",
            "params": {"skill": "test-skill", "action": "used"},
        })
        assert result["status"] == "ok"

    def test_record_action_skipped(self):
        """record skipped 应正常工作"""
        result = self.daemon._handle_request({
            "action": "record",
            "params": {"skill": "test-skill", "action": "skipped", "reason": "testing"},
        })
        assert result["status"] == "ok"

    def test_record_action_unknown(self):
        """未知 action type 应返回 error"""
        result = self.daemon._handle_request({
            "action": "record",
            "params": {"skill": "test-skill", "action": "invalid_action"},
        })
        assert "error" in result

    def test_coverage_action(self):
        """coverage 应返回分析结果"""
        result = self.daemon._handle_request({"action": "coverage"})
        assert "result" in result

    def test_stats_compliance_action(self):
        """stats/compliance 应返回遵循率"""
        result = self.daemon._handle_request({"action": "stats/compliance"})
        assert result["status"] == "ok"
        assert "compliance" in result

    def test_validate_action(self):
        """validate 应返回校验结果"""
        result = self.daemon._handle_request({
            "action": "validate",
            "params": {"tool": "write_file", "args": {"path": "test.md"}},
        })
        assert "result" in result

    def test_recheck_action(self):
        """recheck 应返回漂移分析"""
        result = self.daemon._handle_request({
            "action": "recheck",
            "params": {"conversation_summary": "test"},
        })
        assert "recheck" in result

    def test_recheck_action_no_summary(self):
        """recheck 缺省 summary 应返回错误"""
        result = self.daemon._handle_request({
            "action": "recheck",
            "params": {},
        })
        assert "error" in result
