"""SRA-003-06 运行时力度体系测试

验证 ForceLevelManager 的 4 级注入覆盖度控制。
"""

import os
import json
import pytest
from skill_advisor.runtime.force import (
    ForceLevelManager,
    FORCE_LEVELS,
    DEFAULT_LEVEL,
    INJECTION_POINT_LABELS,
)


@pytest.fixture
def temp_config(tmp_path):
    """创建临时配置文件"""
    cfg_path = tmp_path / "config.json"
    cfg = {
        "runtime_force": {
            "level": "medium",
        }
    }
    with open(cfg_path, 'w') as f:
        json.dump(cfg, f)
    return str(cfg_path)


@pytest.fixture
def force_manager(temp_config):
    """创建使用临时配置的 ForceLevelManager"""
    return ForceLevelManager(config_path=temp_config)


class TestForceLevelManagerInit:

    def test_default_level(self):
        """验证默认等级为 medium"""
        fm = ForceLevelManager()
        # 不传 config_path 会尝试 ~/.sra/config.json，如果不存在则用默认
        assert fm.get_level() == DEFAULT_LEVEL

    def test_load_from_config(self, force_manager):
        """验证从配置文件加载等级"""
        assert force_manager.get_level() == "medium"

    def test_load_invalid_level(self, tmp_path):
        """验证无效等级回退到默认"""
        cfg_path = tmp_path / "config.json"
        with open(cfg_path, 'w') as f:
            json.dump({"runtime_force": {"level": "invalid_level"}}, f)
        fm = ForceLevelManager(config_path=str(cfg_path))
        assert fm.get_level() == DEFAULT_LEVEL

    def test_config_file_not_found(self):
        """验证配置文件不存在时使用默认"""
        fm = ForceLevelManager(config_path="/nonexistent/path/config.json")
        assert fm.get_level() == DEFAULT_LEVEL

    def test_get_level_config_all_levels(self, force_manager):
        """验证所有等级都有完整定义"""
        for level_name in FORCE_LEVELS:
            config = FORCE_LEVELS[level_name]
            assert "name" in config
            assert "label" in config
            assert "description" in config
            assert "injection_points" in config
            assert "tier" in config
            assert isinstance(config["injection_points"], set)


class TestForceLevelSet:

    def test_set_valid_level(self, force_manager):
        """验证设置有效等级"""
        assert force_manager.set_level("advanced")
        assert force_manager.get_level() == "advanced"

    def test_set_invalid_level(self, force_manager):
        """验证设置无效等级返回 False"""
        assert not force_manager.set_level("ultra")
        assert force_manager.get_level() == "medium"  # 保持不变

    def test_set_level_is_case_insensitive(self, force_manager):
        """验证大小写不敏感"""
        assert force_manager.set_level("ADVANCED")
        assert force_manager.get_level() == "advanced"

    def test_set_level_persists(self, temp_config, force_manager):
        """验证设置后持久化到文件"""
        force_manager.set_level("omni")
        with open(temp_config) as f:
            cfg = json.load(f)
        assert cfg["runtime_force"]["level"] == "omni"


class TestInjectionPoints:

    @pytest.mark.parametrize("level,point,expected", [
        # basic: 只有 on_user_message
        ("basic", "on_user_message", True),
        ("basic", "pre_tool_call", False),
        ("basic", "post_tool_call", False),
        ("basic", "periodic", False),
        # medium: on_user_message + pre_tool_call
        ("medium", "on_user_message", True),
        ("medium", "pre_tool_call", True),
        ("medium", "post_tool_call", False),
        ("medium", "periodic", False),
        # advanced: on_user_message + pre_tool_call + post_tool_call
        ("advanced", "on_user_message", True),
        ("advanced", "pre_tool_call", True),
        ("advanced", "post_tool_call", True),
        ("advanced", "periodic", False),
        # omni: 全部
        ("omni", "on_user_message", True),
        ("omni", "pre_tool_call", True),
        ("omni", "post_tool_call", True),
        ("omni", "periodic", True),
    ])
    def test_injection_point_active(self, force_manager, level, point, expected):
        """验证各等级下注入点激活状态"""
        force_manager.set_level(level)
        assert force_manager.is_injection_point_active(point) == expected


class TestMonitoredTools:

    def test_basic_no_monitoring(self, force_manager):
        """验证 basic 等级不监控任何工具"""
        force_manager.set_level("basic")
        monitored = force_manager.get_monitored_tools()
        assert monitored == set()

    def test_medium_monitors_key_tools(self, force_manager):
        """验证 medium 等级监控关键工具"""
        force_manager.set_level("medium")
        monitored = force_manager.get_monitored_tools()
        assert "write_file" in monitored
        assert "patch" in monitored
        assert "terminal" in monitored
        assert "execute_code" in monitored
        # 不应监控全部
        assert monitored != "__all__"

    def test_advanced_monitors_all(self, force_manager):
        """验证 advanced 和 omni 监控全部工具"""
        force_manager.set_level("advanced")
        assert force_manager.get_monitored_tools() == "__all__"

    def test_omni_monitors_all(self, force_manager):
        """验证 omni 监控全部工具"""
        force_manager.set_level("omni")
        assert force_manager.get_monitored_tools() == "__all__"

    @pytest.mark.parametrize("level,tool,expected", [
        ("basic", "write_file", False),
        ("basic", "read_file", False),
        ("medium", "write_file", True),
        ("medium", "patch", True),
        ("medium", "terminal", True),
        ("medium", "execute_code", True),
        ("medium", "read_file", False),
        ("medium", "web_search", False),
        ("advanced", "write_file", True),
        ("advanced", "read_file", True),
        ("advanced", "web_search", True),
        ("omni", "write_file", True),
        ("omni", "any_random_tool", True),
    ])
    def test_is_tool_monitored(self, force_manager, level, tool, expected):
        """验证工具监控判断"""
        force_manager.set_level(level)
        assert force_manager.is_tool_monitored(tool) == expected


class TestForceSummary:

    def test_get_summary_has_all_keys(self, force_manager):
        """验证摘要包含所有必要信息"""
        summary = force_manager.get_summary()
        assert "level" in summary
        assert "label" in summary
        assert "description" in summary
        assert "tier" in summary
        assert "active_points" in summary
        assert "monitored_tools" in summary
        assert "periodic" in summary

    def test_list_levels_returns_all(self, force_manager):
        """验证 list_levels 返回 4 个等级"""
        levels = force_manager.list_levels()
        assert len(levels) == 4
        names = {l["name"] for l in levels}
        assert names == {"basic", "medium", "advanced", "omni"}

    def test_list_levels_marks_current(self, force_manager):
        """验证当前等级被标记"""
        force_manager.set_level("advanced")
        levels = force_manager.list_levels()
        current = [l for l in levels if l["is_current"]]
        assert len(current) == 1
        assert current[0]["name"] == "advanced"


class TestPeriodicConfig:

    def test_omni_has_periodic(self, force_manager):
        """验证 omni 等级启用周期性注入"""
        force_manager.set_level("omni")
        assert force_manager.get_level_config()["periodic_injection"]

    def test_other_levels_no_periodic(self, force_manager):
        """验证非 omni 等级不启用周期性注入"""
        for level in ["basic", "medium", "advanced"]:
            force_manager.set_level(level)
            assert not force_manager.get_level_config()["periodic_injection"]

    def test_periodic_interval_default(self, force_manager):
        """验证默认周期间隔"""
        assert force_manager.get_periodic_interval() == 5
