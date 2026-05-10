"""CLI 命令测试 — mock socket 请求"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from skill_advisor.cli import (
    cmd_recommend, cmd_stats, cmd_coverage, cmd_compliance,
    cmd_refresh, cmd_record, cmd_config, cmd_version,
    print_help, COMMANDS,
)


# ── 辅助函数 ──

def _run_cmd(cmd_func, args, mock_response=None):
    """运行 CLI 命令, 捕获 stdout"""
    from io import StringIO
    captured = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        if mock_response is not None:
            with patch("skill_advisor.cli._socket_request", return_value=mock_response):
                cmd_func(args)
        else:
            cmd_func(args)
    finally:
        sys.stdout = old_stdout
    return captured.getvalue()


# ── cmd_recommend ──

class TestCmdRecommend:
    def test_with_results(self):
        """有推荐结果时应正常输出"""
        mock_resp = {
            "result": {
                "recommendations": [
                    {"skill": "test-skill", "score": 85.0, "confidence": "high",
                     "description": "A test skill", "reasons": ["match"]},
                ],
                "processing_ms": 10.5,
                "skills_scanned": 50,
            }
        }
        output = _run_cmd(cmd_recommend, ["python", "test"], mock_resp)
        assert "test-skill" in output
        assert "85" in output

    def test_no_results(self):
        """无结果时应提示"""
        mock_resp = {"result": {"recommendations": [], "processing_ms": 5.0}}
        output = _run_cmd(cmd_recommend, ["zzzxxxx"], mock_resp)
        assert "没有" in output or not output == ""

    def test_daemon_not_running(self):
        """daemon 未运行时应提示本地模式"""
        mock_resp = {"error": "SRA Daemon 未运行"}
        output = _run_cmd(cmd_recommend, ["python"], mock_resp)
        assert "未运行" in output or "本地模式" in output


# ── cmd_stats ──

class TestCmdStats:
    def test_with_daemon_stats(self):
        """daemon 统计输出"""
        mock_resp = {
            "stats": {
                "version": "1.2.0",
                "status": "running",
                "skills_count": 100,
                "total_requests": 50,
                "total_recommendations": 30,
                "uptime_seconds": 3600,
            }
        }
        output = _run_cmd(cmd_stats, [], mock_resp)
        assert "running" in output or "运行" in output
        assert "100" in output or "50" in output

    def test_daemon_not_running(self):
        """daemon 未运行时应使用本地模式"""
        mock_resp = {"error": "SRA Daemon 未运行"}
        output = _run_cmd(cmd_stats, [], mock_resp)
        assert "本地模式" in output or "未运行" in output


# ── cmd_coverage ──

class TestCmdCoverage:
    def test_with_coverage(self):
        """覆盖率输出"""
        mock_resp = {
            "result": {
                "total": 100,
                "covered": 80,
                "coverage_rate": 80.0,
                "not_covered": [],
            }
        }
        output = _run_cmd(cmd_coverage, [], mock_resp)
        assert "80" in output
        assert "覆盖率" in output or "coverage" in output.lower()

    def test_with_not_covered(self):
        """有未覆盖技能时列出"""
        mock_resp = {
            "result": {
                "total": 100,
                "covered": 95,
                "coverage_rate": 95.0,
                "not_covered": [
                    {"name": "uncovered-skill", "category": "test"},
                ],
            }
        }
        output = _run_cmd(cmd_coverage, [], mock_resp)
        assert "uncovered-skill" in output


# ── cmd_compliance ──

class TestCmdCompliance:
    def test_with_stats(self):
        """遵循率输出"""
        mock_resp = {
            "compliance": {
                "summary": {
                    "total_views": 10,
                    "total_uses": 8,
                    "total_skips": 2,
                    "overall_compliance_rate": 0.8,
                },
                "per_skill": {
                    "skill-a": {"view_count": 5, "use_count": 4, "skip_count": 1, "compliance_rate": 0.8},
                    "skill-b": {"view_count": 5, "use_count": 4, "skip_count": 1, "compliance_rate": 0.8},
                },
            }
        }
        output = _run_cmd(cmd_compliance, [], mock_resp)
        assert "10" in output  # total_views
        assert "8" in output   # total_uses
        assert "skill-a" in output

    def test_daemon_not_running(self):
        """daemon 未运行时应回退本地模式"""
        mock_resp = {"error": "SRA Daemon 未运行"}
        output = _run_cmd(cmd_compliance, [], mock_resp)
        assert "本地模式" in output or "未运行" in output


# ── cmd_refresh ──

class TestCmdRefresh:
    def test_success(self):
        """刷新成功"""
        mock_resp = {"count": 42}
        output = _run_cmd(cmd_refresh, [], mock_resp)
        assert "42" in output or "refresh" in output.lower()

    def test_daemon_not_running(self):
        """daemon 未运行时应回退本地模式"""
        mock_resp = {"error": "SRA Daemon 未运行"}
        output = _run_cmd(cmd_refresh, [], mock_resp)
        assert "本地模式" in output or "未运行" in output


# ── cmd_record ──

class TestCmdRecord:
    def test_valid_args(self):
        """有效参数"""
        mock_resp = {"status": "ok"}
        output = _run_cmd(cmd_record, ["my-skill", "test query"], mock_resp)
        assert "已记录" in output or "ok" in output.lower()

    def test_invalid_args(self):
        """缺少参数应显示用法"""
        output = _run_cmd(cmd_record, ["my-skill"], None)
        assert "用法" in output

    def test_daemon_not_running(self):
        """daemon 未运行时应回退本地模式"""
        mock_resp = {"error": "SRA Daemon 未运行"}
        output = _run_cmd(cmd_record, ["my-skill", "test query"], mock_resp)
        assert "本地模式" in output or "已记录" in output


# ── cmd_config ──

class TestCmdConfig:
    def test_config_show(self):
        """显示配置"""
        output = _run_cmd(cmd_config, ["show"], None)
        assert "配置" in output or "SRA" in output

    def test_config_set(self):
        """设置配置"""
        output = _run_cmd(cmd_config, ["set", "test_key", "test_value"], None)
        assert "已更新" in output or "test_key" in output

    def test_config_reset(self):
        """重置配置"""
        output = _run_cmd(cmd_config, ["reset"], None)
        assert "已重置" in output or "reset" in output.lower()

    def test_config_unknown(self):
        """未知配置命令"""
        output = _run_cmd(cmd_config, ["invalid"], None)
        assert "未知" in output


# ── cmd_version ──

class TestCmdVersion:
    def test_version_output(self):
        """版本输出"""
        output = _run_cmd(cmd_version, [], None)
        assert "SRA" in output


# ── COMMANDS 注册表 ──

class TestCommandsRegistry:
    def test_required_commands_exist(self):
        """所有必需的命令都已注册"""
        required = [
            "start", "stop", "status", "restart",
            "recommend", "query", "stats", "coverage",
            "compliance", "refresh", "record", "config",
            "version", "help",
        ]
        for cmd in required:
            assert cmd in COMMANDS, f"缺少命令: {cmd}"

    def test_commands_are_callable(self):
        """所有命令都是可调用的"""
        for name, func in COMMANDS.items():
            assert callable(func), f"命令 {name} 不可调用"


# ── print_help ──

class TestPrintHelp:
    def test_help_output(self):
        """帮助信息正常输出"""
        from io import StringIO
        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            print_help()
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        assert "SRA" in output
        assert "start" in output
        assert "compliance" in output
