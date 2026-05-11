"""dropin 模块测试 — systemd drop-in 生命周期管理"""

import os
import json
import tempfile
from unittest.mock import patch, MagicMock, call, mock_open

import pytest

from skill_advisor.runtime.dropin import (
    get_dropin_path,
    get_dropin_dir,
    get_service_path,
    cleanup_dropin,
    create_dropin,
    check_dropin_health,
    print_health_report,
    SYSTEMD_USER_DIR,
    GATEWAY_SERVICE_NAME,
    DROPIN_FILENAME,
)


class TestDropinPaths:
    """路径获取函数测试"""

    def test_get_dropin_path(self):
        """get_dropin_path 应返回正确的完整路径"""
        path = get_dropin_path()
        expected = os.path.join(
            SYSTEMD_USER_DIR,
            f"{GATEWAY_SERVICE_NAME}.d/{DROPIN_FILENAME}"
        )
        assert path == expected

    def test_get_dropin_dir(self):
        """get_dropin_dir 应返回正确的目录路径"""
        path = get_dropin_dir()
        expected = os.path.join(SYSTEMD_USER_DIR, f"{GATEWAY_SERVICE_NAME}.d")
        assert path == expected

    def test_get_service_path(self):
        """get_service_path 应返回正确的 service 路径"""
        path = get_service_path()
        expected = os.path.join(SYSTEMD_USER_DIR, "srad.service")
        assert path == expected

    def test_constants_consistency(self):
        """常量应保持一致"""
        assert "sra-dep.conf" in get_dropin_path()
        assert "hermes-gateway.service" in get_dropin_path()


class TestCleanupDropin:
    """cleanup_dropin 函数测试"""

    @patch("skill_advisor.runtime.dropin.os.unlink")
    @patch("skill_advisor.runtime.dropin.subprocess.run")
    @patch("skill_advisor.runtime.dropin.os.path.exists")
    def test_cleanup_existing_file(self, mock_exists, mock_run, mock_unlink):
        """当 drop-in 文件存在时应删除并执行 daemon-reload"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = cleanup_dropin()

        assert result is True
        mock_unlink.assert_called_once()
        mock_run.assert_called_once_with(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True, text=True, timeout=10
        )

    @patch("skill_advisor.runtime.dropin.os.unlink")
    @patch("skill_advisor.runtime.dropin.subprocess.run")
    @patch("skill_advisor.runtime.dropin.os.path.exists")
    def test_cleanup_not_exists(self, mock_exists, mock_run, mock_unlink):
        """当 drop-in 文件不存在时应返回 False"""
        mock_exists.return_value = False

        result = cleanup_dropin()

        assert result is False
        mock_unlink.assert_not_called()
        mock_run.assert_not_called()

    @patch("skill_advisor.runtime.dropin.os.path.exists")
    def test_cleanup_dry_run(self, mock_exists):
        """dry_run=True 时应只打印不执行"""
        mock_exists.return_value = True

        result = cleanup_dropin(dry_run=True)

        assert result is True
        # dry_run 模式不调用 unlink

    @patch("skill_advisor.runtime.dropin.os.unlink", side_effect=OSError("permission denied"))
    @patch("skill_advisor.runtime.dropin.subprocess.run")
    @patch("skill_advisor.runtime.dropin.os.path.exists")
    def test_cleanup_oserror(self, mock_exists, mock_run, mock_unlink):
        """OSError 时应返回 False 并记录错误"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = cleanup_dropin()

        assert result is False

    @patch("skill_advisor.runtime.dropin.os.unlink")
    @patch("skill_advisor.runtime.dropin.subprocess.run")
    @patch("skill_advisor.runtime.dropin.os.path.exists")
    def test_cleanup_daemon_reload_fail(self, mock_exists, mock_run, mock_unlink):
        """daemon-reload 失败不应阻止清理"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stderr="error")

        result = cleanup_dropin()

        assert result is True  # 删除成功就算成功
        mock_unlink.assert_called_once()


class TestCreateDropin:
    """create_dropin 函数测试"""

    @patch("skill_advisor.runtime.dropin.os.makedirs")
    @patch("skill_advisor.runtime.dropin.open", new_callable=mock_open)
    @patch("skill_advisor.runtime.dropin.get_dropin_dir")
    @patch("skill_advisor.runtime.dropin.get_dropin_path")
    def test_create_default_wants(self, mock_get_path, mock_get_dir, mock_file, mock_makedirs):
        """默认应使用 Wants= 软依赖"""
        mock_get_path.return_value = "/tmp/sra-dep.conf"
        mock_get_dir.return_value = "/tmp/dir"

        result = create_dropin()

        assert result is True
        mock_makedirs.assert_called_once_with("/tmp/dir", exist_ok=True)
        # 验证文件内容包含 Wants=
        handle = mock_file()
        all_writes = "".join(str(c) for c in handle.write.call_args_list)
        assert "Wants=srad.service" in all_writes
        assert "Requires=" not in all_writes

    @patch("skill_advisor.runtime.dropin.os.makedirs")
    @patch("skill_advisor.runtime.dropin.open", new_callable=mock_open)
    @patch("skill_advisor.runtime.dropin.get_dropin_path")
    def test_create_requires(self, mock_get_path, mock_file, mock_makedirs):
        """use_wants=False 时应使用 Requires= 硬依赖"""
        mock_get_path.return_value = "/tmp/sra-dep.conf"

        result = create_dropin(use_wants=False)

        assert result is True
        handle = mock_file()
        all_writes = "".join(str(c) for c in handle.write.call_args_list)
        assert "Requires=srad.service" in all_writes

    @patch("skill_advisor.runtime.dropin.get_dropin_path")
    def test_create_dry_run(self, mock_get_path):
        """dry_run=True 时应只打印不创建"""
        mock_get_path.return_value = "/tmp/sra-dep.conf"
        result = create_dropin(dry_run=True)
        assert result is True

    @patch("skill_advisor.runtime.dropin.open", side_effect=OSError("read-only"))
    @patch("skill_advisor.runtime.dropin.os.makedirs")
    @patch("skill_advisor.runtime.dropin.get_dropin_path")
    @patch("skill_advisor.runtime.dropin.get_dropin_dir")
    def test_create_oserror(self, mock_get_dir, mock_get_path, mock_makedirs, mock_open):
        """OSError 时应返回 False"""
        mock_get_path.return_value = "/tmp/sra-dep.conf"
        mock_get_dir.return_value = "/tmp/dir"

        result = create_dropin()

        assert result is False


class TestCheckDropinHealth:
    """check_dropin_health 函数测试"""

    @patch("skill_advisor.runtime.dropin.os.path.exists")
    @patch("skill_advisor.runtime.dropin.open", new_callable=mock_open, read_data="[Unit]\nWants=srad.service\nAfter=srad.service\n")
    def test_healthy_with_wants(self, mock_file, mock_exists):
        """Wants= 且文件存在时应为健康"""
        mock_exists.side_effect = lambda p: True  # 所有文件都存在

        result = check_dropin_health()

        assert result["exists"] is True
        assert result["uses_wants"] is True
        assert result["healthy"] is True
        assert len(result["issues"]) == 0

    @patch("skill_advisor.runtime.dropin.os.path.exists")
    @patch("skill_advisor.runtime.dropin.open", new_callable=mock_open, read_data="[Unit]\nRequires=srad.service\nAfter=srad.service\n")
    def test_unhealthy_with_requires(self, mock_file, mock_exists):
        """Requires= 应标记为不健康"""
        mock_exists.side_effect = lambda p: True

        result = check_dropin_health()

        assert result["exists"] is True
        assert result["uses_wants"] is False
        assert result["healthy"] is False
        assert len(result["issues"]) == 1
        assert "Requires=" in result["issues"][0]

    @patch("skill_advisor.runtime.dropin.os.path.exists")
    def test_dropin_not_exists(self, mock_exists):
        """drop-in 不存在不算不健康"""
        mock_exists.return_value = False

        result = check_dropin_health()

        assert result["exists"] is False
        assert result["healthy"] is True  # 不存在不算不健康

    @patch("skill_advisor.runtime.dropin.os.path.exists")
    @patch("skill_advisor.runtime.dropin.open", new_callable=mock_open, read_data="[Unit]\nWants=srad.service\n")
    def test_orphan_config(self, mock_file, mock_exists):
        """drop-in 存在但 srad.service 不存在时应标记为孤儿配置"""
        def exists_side_effect(path):
            if "srad.service" in path:
                return False  # service 不存在
            return True
        mock_exists.side_effect = exists_side_effect

        result = check_dropin_health()

        assert result["exists"] is True
        assert result["service_exists"] is False
        assert result["healthy"] is False
        assert "孤儿配置" in result["issues"][0]

    @patch("skill_advisor.runtime.dropin.os.path.exists")
    @patch("skill_advisor.runtime.dropin.open", side_effect=OSError("permission denied"))
    def test_unreadable_dropin(self, mock_file, mock_exists):
        """无法读取 drop-in 文件时应标记为不健康"""
        mock_exists.return_value = True

        result = check_dropin_health()

        assert result["exists"] is True
        assert result["healthy"] is False
        assert "无法读取" in result["issues"][0]


class TestPrintHealthReport:
    """print_health_report 函数测试"""

    def test_not_exists(self, capsys):
        """drop-in 不存在时应打印说明"""
        health = {
            "exists": False,
            "healthy": True,
            "issues": [],
        }
        print_health_report(health)
        captured = capsys.readouterr()
        assert "不存在" in captured.out

    def test_healthy(self, capsys):
        """健康状态应打印 ✅"""
        health = {
            "exists": True,
            "service_exists": True,
            "uses_wants": True,
            "healthy": True,
            "issues": [],
        }
        print_health_report(health)
        captured = capsys.readouterr()
        assert "✅" in captured.out

    def test_unhealthy(self, capsys):
        """不健康状态应打印 ❌"""
        health = {
            "exists": True,
            "service_exists": False,
            "uses_wants": False,
            "healthy": False,
            "issues": ["Requires= 警告", "孤儿配置"],
        }
        print_health_report(health)
        captured = capsys.readouterr()
        assert "❌" in captured.out
        assert "Requires" in captured.out
        assert "孤儿配置" in captured.out
