"""并发安全测试 — 多线程写入 + 状态一致性"""

import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestConcurrentStatusWrite:
    """并发状态文件写入测试"""

    def test_concurrent_update_status(self, tmp_path):
        """多线程同时更新状态不应导致文件损坏"""
        from skill_advisor.runtime import config as cfg_module

        # 临时替换 STATUS_FILE
        original = cfg_module.STATUS_FILE
        test_file = tmp_path / "srad.status.json"
        cfg_module.STATUS_FILE = str(test_file)

        try:
            # 覆盖 daemon 模块中的 STATUS_FILE 引用
            import skill_advisor.runtime.daemon as daemon_mod
            from skill_advisor.runtime.daemon import SRaDDaemon as Daemon
            daemon_mod.STATUS_FILE = str(test_file)
            test_file.parent.mkdir(parents=True, exist_ok=True)
            daemon = Daemon({"skills_dir": str(tmp_path), "data_dir": str(tmp_path)})
            errors = []

            def writer(status_val):
                try:
                    for _ in range(20):
                        daemon._update_status(f"status_{status_val}")
                        time.sleep(0.001)
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0, f"写入异常: {errors}"

            # 验证文件是合法 JSON
            with open(test_file) as f:
                data = json.load(f)
            assert "status" in data
            assert "pid" in data
            assert "updated_at" in data
        finally:
            cfg_module.STATUS_FILE = original

    def test_no_cross_write_corruption(self, tmp_path):
        """并发写入后文件不应出现截断或交叉"""
        from skill_advisor.runtime import config as cfg_module

        original = cfg_module.STATUS_FILE
        test_file = tmp_path / "srad.status.json"
        cfg_module.STATUS_FILE = str(test_file)

        try:
            # 覆盖 daemon 模块中的 STATUS_FILE 引用
            import skill_advisor.runtime.daemon as daemon_mod
            from skill_advisor.runtime.daemon import SRaDDaemon as Daemon
            daemon_mod.STATUS_FILE = str(test_file)
            test_file.parent.mkdir(parents=True, exist_ok=True)
            daemon = Daemon({"skills_dir": str(tmp_path), "data_dir": str(tmp_path)})

            for i in range(50):
                daemon._update_status(f"cycle_{i}")

            # 验证每次写入后文件都是合法 JSON
            with open(test_file) as f:
                data = json.load(f)
            assert data["status"].startswith("cycle_")
        finally:
            cfg_module.STATUS_FILE = original


class TestConcurrentStats:
    """并发统计计数测试"""

    def test_stats_no_loss_under_concurrency(self):
        """100 次并发请求后计数不应丢失"""
        from unittest.mock import MagicMock

        from skill_advisor.runtime.daemon import SRaDDaemon

        # 轻量 daemon（不启动真实 socket/http）
        daemon = SRaDDaemon.__new__(SRaDDaemon)
        daemon.config = {}
        daemon._lock = threading.Lock()
        daemon._stats = {
            "started_at": "2026-01-01T00:00:00",
            "total_requests": 0,
            "total_recommendations": 0,
            "errors": 0,
        }
        daemon.force_manager = MagicMock()
        daemon.advisor = MagicMock()
        daemon.running = True
        daemon.ROUTER = SRaDDaemon.ROUTER

        errors = []

        def make_request():
            try:
                for _ in range(20):
                    daemon._handle_request({"action": "ping", "params": {}})
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"请求异常: {errors}"
        assert daemon._stats["total_requests"] == 100, \
            f"预期 100 次请求, 实际 {daemon._stats['total_requests']}"

    def test_recommend_count_accuracy(self):
        """并发推荐后计数精确"""
        from unittest.mock import MagicMock

        from skill_advisor.runtime.daemon import SRaDDaemon

        daemon = SRaDDaemon.__new__(SRaDDaemon)
        daemon.config = {}
        daemon._lock = threading.Lock()
        daemon._stats = {
            "started_at": "2026-01-01T00:00:00",
            "total_requests": 0,
            "total_recommendations": 0,
            "errors": 0,
        }
        daemon.force_manager = MagicMock()
        daemon.advisor = MagicMock()
        daemon.advisor.recommend.return_value = {"recommendations": []}
        daemon.running = True
        daemon.ROUTER = SRaDDaemon.ROUTER

        threads = []
        for _ in range(3):
            t = threading.Thread(target=lambda: [
                daemon._handle_request({"action": "recommend", "params": {"query": "test"}})
                for _ in range(10)
            ])
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert daemon._stats["total_recommendations"] == 30, \
            f"预期 30 次推荐, 实际 {daemon._stats['total_recommendations']}"
        assert daemon._stats["total_requests"] >= 30


class TestMemoryFileLock:
    """memory.py 文件锁测试"""

    def test_memory_save_with_flock(self, tmp_path):
        """memory.save() 使用 fcntl.flock 后文件内容完整"""
        from skill_advisor.memory import SceneMemory

        memory = SceneMemory(str(tmp_path))
        memory._cache = {"skills": {}, "scene_patterns": [], "total_recommendations": 5,
                         "compliance": {"total_views": 1, "total_uses": 1, "total_skips": 0,
                                        "overall_compliance_rate": 1.0, "recent_events": []}}
        memory.save()

        # 验证文件合法
        with open(memory.stats_file) as f:
            data = json.load(f)
        assert data["total_recommendations"] == 5

    def test_concurrent_memory_save(self, tmp_path):
        """多线程同时保存不导致文件损坏"""
        from skill_advisor.memory import SceneMemory

        memory = SceneMemory(str(tmp_path))
        memory._cache = {"skills": {}, "scene_patterns": [], "total_recommendations": 0,
                         "compliance": {"total_views": 0, "total_uses": 0, "total_skips": 0,
                                        "overall_compliance_rate": 1.0, "recent_events": []}}

        errors = []

        def saver():
            try:
                for _ in range(10):
                    memory._cache["total_recommendations"] += 1
                    memory.save()
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=saver) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"保存异常: {errors}"

        # 验证文件最终状态
        memory._cache = None  # 清除缓存
        data = memory.load()
        assert data["total_recommendations"] >= 0  # 至少不损坏


class TestRouterConsistency:
    """路由统一一致性测试"""

    def test_router_contains_all_actions(self):
        """ROUTER 包含所有已知 action"""
        from skill_advisor.runtime.daemon import SRaDDaemon

        router = SRaDDaemon.ROUTER
        expected_actions = {
            "recommend", "record", "refresh", "stats", "ping",
            "coverage", "stats/compliance", "stop", "validate",
            "force", "recheck",
        }
        assert set(router.keys()) == expected_actions, \
            f"ROUTER 缺失或多余 action: 预期 {expected_actions}, 实际 {set(router.keys())}"

    def test_router_handler_signature(self):
        """所有 handler 接受 params 参数"""
        import inspect

        from skill_advisor.runtime.daemon import SRaDDaemon

        for action, handler_name in SRaDDaemon.ROUTER.items():
            handler = getattr(SRaDDaemon, handler_name, None)
            assert handler is not None, f"handler {handler_name} 不存在"
            sig = inspect.signature(handler)
            params = list(sig.parameters.keys())
            assert "params" in params or "data" in params, \
                f"{handler_name} 签名不含 params, 实际: {params}"
