"""SRA 配置系统测试 — Schema 校验 + 环境变量覆盖 + config validate CLI"""

import json
import os
import sys
import tempfile
from unittest.mock import patch

import pytest

# 确保导入可用
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Fixtures ──────────────────────────────────────────

@pytest.fixture
def mock_sra_home(tmp_path):
    """创建临时 SRA 家目录"""
    home = tmp_path / ".sra"
    home.mkdir()
    data_dir = home / "data"
    data_dir.mkdir()
    logs_dir = home / "logs"
    logs_dir.mkdir()
    return home


@pytest.fixture
def valid_schema() -> dict:
    """标准配置 Schema"""
    return {
        "$schema": "https://json-schema.org/draft-07/schema#",
        "title": "SRA Configuration Schema",
        "type": "object",
        "properties": {
            "http_port": {
                "type": "integer",
                "description": "HTTP API server port",
                "minimum": 1024,
                "maximum": 65535,
                "default": 8536
            },
            "log_level": {
                "type": "string",
                "description": "Logging level",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "default": "INFO"
            },
            "max_connections": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 10
            },
            "enable_http": {
                "type": "boolean",
                "default": True
            },
            "enable_unix_socket": {
                "type": "boolean",
                "default": True
            },
            "watch_skills_dir": {
                "type": "boolean",
                "default": True
            },
            "skills_dir": {
                "type": "string",
                "default": "~/.hermes/skills"
            },
            "data_dir": {
                "type": "string",
                "default": "~/.sra/data"
            },
            "socket_path": {
                "type": "string",
                "default": "~/.sra/srad.sock"
            },
            "auto_refresh_interval": {
                "type": "integer",
                "minimum": 60,
                "default": 3600
            },
            "runtime_force": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "enum": ["basic", "medium", "advanced", "omni"],
                        "default": "medium"
                    },
                    "periodic_interval_rounds": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 5
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }


# ── Schema 校验测试 ────────────────────────────────────

class TestValidateConfig:
    """配置 Schema 校验功能测试"""

    def test_valid_config_passes(self, valid_schema):
        """合法配置应无错误"""
        from skill_advisor.runtime.config import validate_config
        config = {
            "http_port": 8536,
            "log_level": "INFO",
            "max_connections": 10,
            "enable_http": True,
            "enable_unix_socket": True,
        }
        errors = validate_config(config, valid_schema)
        assert len(errors) == 0, f"合法配置不应有错误: {errors}"

    def test_unknown_field_warning(self, valid_schema):
        """未知字段应产生警告"""
        from skill_advisor.runtime.config import validate_config
        config = {"unknown_key": "test_value"}
        errors = validate_config(config, valid_schema)
        assert any("未知配置字段" in e for e in errors), \
            f"应检测到未知字段: {errors}"

    def test_type_mismatch(self, valid_schema):
        """类型不匹配应被检测"""
        from skill_advisor.runtime.config import validate_config
        config = {"http_port": "not_a_number"}
        errors = validate_config(config, valid_schema)
        assert any("应为整数" in e for e in errors), \
            f"应检测到类型错误: {errors}"

    def test_enum_violation(self, valid_schema):
        """枚举值违规应被检测"""
        from skill_advisor.runtime.config import validate_config
        config = {"log_level": "VERBOSE"}
        errors = validate_config(config, valid_schema)
        assert any("不在允许范围内" in e for e in errors), \
            f"应检测到枚举违规: {errors}"

    def test_minimum_violation(self, valid_schema):
        """最小值违规应被检测"""
        from skill_advisor.runtime.config import validate_config
        config = {"http_port": 80}
        errors = validate_config(config, valid_schema)
        assert any("小于最小值" in e for e in errors), \
            f"应检测到最小值违规: {errors}"

    def test_maximum_violation(self, valid_schema):
        """最大值违规应被检测"""
        from skill_advisor.runtime.config import validate_config
        config = {"max_connections": 999}
        errors = validate_config(config, valid_schema)
        assert any("大于最大值" in e for e in errors), \
            f"应检测到最大值违规: {errors}"

    def test_nested_unknown_field(self, valid_schema):
        """嵌套对象中的未知子字段应被检测"""
        from skill_advisor.runtime.config import validate_config
        config = {"runtime_force": {"unknown_sub_field": "test"}}
        errors = validate_config(config, valid_schema)
        assert any("未知子字段" in e for e in errors), \
            f"应检测到嵌套未知字段: {errors}"

    def test_empty_config_passes(self, valid_schema):
        """空配置应无错误（使用默认值）"""
        from skill_advisor.runtime.config import validate_config
        errors = validate_config({}, valid_schema)
        assert len(errors) == 0

    def test_multiple_errors(self, valid_schema):
        """多个错误应同时报告"""
        from skill_advisor.runtime.config import validate_config
        config = {
            "http_port": "string",
            "log_level": "VERBOSE",
            "max_connections": 999,
            "unknown_field": "test",
        }
        errors = validate_config(config, valid_schema)
        assert len(errors) >= 3


# ── 环境变量覆盖测试 ────────────────────────────────────

class TestEnvOverride:
    """环境变量配置覆盖功能测试"""

    def test_env_override_http_port(self):
        """SRA_HTTP_PORT 应覆盖 http_port"""
        from skill_advisor.runtime.config import load_config
        with patch.dict(os.environ, {"SRA_HTTP_PORT": "9999"}, clear=True):
            cfg = load_config()
        # clear=True 会清空所有环境变量，所以需要检查默认值行为
        # 改用更安全的方式
        with patch.dict(os.environ, {"SRA_HTTP_PORT": "9999"}):
            cfg = load_config()
            assert cfg["http_port"] == 9999, \
                f"预期 9999, 实际 {cfg['http_port']}"

    def test_env_override_log_level(self):
        """SRA_LOG_LEVEL 应覆盖 log_level"""
        from skill_advisor.runtime.config import load_config
        with patch.dict(os.environ, {"SRA_LOG_LEVEL": "DEBUG"}):
            cfg = load_config()
            assert cfg["log_level"] == "DEBUG"

    def test_env_override_boolean(self):
        """SRA_ENABLE_HTTP=false 应覆盖 enable_http 为 False"""
        from skill_advisor.runtime.config import load_config
        with patch.dict(os.environ, {"SRA_ENABLE_HTTP": "false"}):
            cfg = load_config()
            assert cfg["enable_http"] is False

    def test_env_override_unknown_key(self):
        """未知环境变量不应影响配置"""
        from skill_advisor.runtime.config import load_config
        with patch.dict(os.environ, {"SRA_SOME_RANDOM_KEY": "test"}):
            cfg = load_config()
            # 不应有 'some_random_key' 键出现
            assert "some_random_key" not in cfg

    def test_env_precedence_over_file(self, mock_sra_home):
        """环境变量优先级高于配置文件"""
        from skill_advisor.runtime import config as cfg_module

        # 保存原始模块级变量以在 finally 中恢复
        orig_home = cfg_module.SRA_HOME
        orig_file = cfg_module.CONFIG_FILE
        orig_schema = cfg_module.CONFIG_SCHEMA

        try:
            # 写入配置文件到临时目录
            cfg_module.SRA_HOME = str(mock_sra_home)
            cfg_module.CONFIG_FILE = str(mock_sra_home / "config.json")
            cfg_module.CONFIG_SCHEMA = str(mock_sra_home / "config.schema.json")

            os.environ["SRA_HOME"] = str(mock_sra_home)
            test_config = {"http_port": 8080}
            with open(cfg_module.CONFIG_FILE, "w") as f:
                json.dump(test_config, f)

            with patch.dict(os.environ, {"SRA_HTTP_PORT": "6666"}):
                result = cfg_module.load_config()
                assert result["http_port"] == 6666, \
                    f"环境变量 6666 应覆盖配置文件的 8080, 实际 {result['http_port']}"
        finally:
            # 恢复原始模块级变量，避免污染后续测试
            cfg_module.SRA_HOME = orig_home
            cfg_module.CONFIG_FILE = orig_file
            cfg_module.CONFIG_SCHEMA = orig_schema


# ── config validate CLI 测试 ────────────────────────────

class TestConfigValidateCLI:
    """sra config validate CLI 命令测试"""

    @patch("skill_advisor.cli.load_config")
    def test_validate_valid_config(self, mock_load_config, capsys, valid_schema):
        """合法配置输出 ✅ 消息"""
        from skill_advisor.cli import cmd_config

        # 准备：创建临时 Schema 文件
        from skill_advisor.runtime import config as cfg_module

        tmp_schema = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(valid_schema, tmp_schema)
        tmp_schema.close()

        original_schema = cfg_module.CONFIG_SCHEMA
        try:
            cfg_module.CONFIG_SCHEMA = tmp_schema.name
            mock_load_config.return_value = {"http_port": 8536}

            cmd_config(["validate"])
            captured = capsys.readouterr()
            assert "配置合法" in captured.out
        finally:
            cfg_module.CONFIG_SCHEMA = original_schema
            os.unlink(tmp_schema.name)

    @patch("skill_advisor.cli.load_config")
    def test_validate_invalid_config(self, mock_load_config, capsys, valid_schema):
        """非法配置输出 ❌ 错误列表"""
        from skill_advisor.cli import cmd_config
        from skill_advisor.runtime import config as cfg_module

        tmp_schema = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(valid_schema, tmp_schema)
        tmp_schema.close()

        original_schema = cfg_module.CONFIG_SCHEMA
        try:
            cfg_module.CONFIG_SCHEMA = tmp_schema.name
            mock_load_config.return_value = {"http_port": "string", "log_level": "VERBOSE", "unknown_key": "x"}

            cmd_config(["validate"])
            captured = capsys.readouterr()
            assert "校验发现" in captured.out
            assert "未知配置字段" in captured.out
        finally:
            cfg_module.CONFIG_SCHEMA = original_schema
            os.unlink(tmp_schema.name)
