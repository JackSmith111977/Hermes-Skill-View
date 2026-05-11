"""SRA 运行时配置管理 — 路径常量 + 配置加载/保存 + Schema 校验"""

import json
import logging
import os

logger = logging.getLogger("sra.config")

# ── 路径常量 ─────────────────────────────────
SRA_HOME = os.path.expanduser("~/.sra")
PID_FILE = os.path.join(SRA_HOME, "srad.pid")
LOCK_FILE = os.path.join(SRA_HOME, "srad.lock")
SOCKET_FILE = os.path.join(SRA_HOME, "srad.sock")
LOG_FILE = os.path.join(SRA_HOME, "srad.log")
STATUS_FILE = os.path.join(SRA_HOME, "srad.status.json")
CONFIG_FILE = os.path.join(SRA_HOME, "config.json")
CONFIG_SCHEMA = os.path.join(SRA_HOME, "config.schema.json")

# 默认配置
DEFAULT_CONFIG = {
    "skills_dir": os.path.expanduser("~/.hermes/skills"),
    "data_dir": os.path.join(SRA_HOME, "data"),
    "socket_path": SOCKET_FILE,
    "http_port": 8536,
    "auto_refresh_interval": 3600,
    "enable_http": True,
    "enable_unix_socket": True,
    "log_level": "INFO",
    "max_connections": 10,
    "watch_skills_dir": True,
}


def ensure_sra_home() -> None:
    """确保 SRA 家目录存在"""
    os.makedirs(SRA_HOME, exist_ok=True)
    os.makedirs(os.path.join(SRA_HOME, "data"), exist_ok=True)
    os.makedirs(os.path.join(SRA_HOME, "logs"), exist_ok=True)


def _load_schema() -> dict | None:
    """加载配置 Schema，失败时返回 None（不阻断启动）"""
    if not os.path.exists(CONFIG_SCHEMA):
        return None
    try:
        with open(CONFIG_SCHEMA) as f:
            return json.load(f)
    except Exception as e:
        logger.warning("配置 Schema 加载失败: %s", e)
        return None


def validate_config(config: dict, schema: dict | None = None) -> list[str]:
    """校验配置合法性，返回违规字段列表（非阻断）"""
    if schema is None:
        schema = _load_schema()
    if schema is None:
        return []  # 无 Schema 时不校验

    errors: list[str] = []
    schema_props = schema.get("properties", {})
    allowed_fields = set(schema_props.keys())

    # 检查未知字段
    for key in config:
        if key not in allowed_fields:
            errors.append(f"未知配置字段: '{key}'")

    # 检查已知字段的值类型
    for key, prop in schema_props.items():
        if key not in config:
            continue  # 用默认值，不报错
        expected_type = prop.get("type")
        val = config[key]
        if expected_type == "integer" and not isinstance(val, int):
            errors.append(f"字段 '{key}' 应为整数，当前为 {type(val).__name__}")
        elif expected_type == "boolean" and not isinstance(val, bool):
            errors.append(f"字段 '{key}' 应为布尔值，当前为 {type(val).__name__}")
        elif expected_type == "string" and not isinstance(val, str):
            errors.append(f"字段 '{key}' 应为字符串，当前为 {type(val).__name__}")
        elif expected_type == "object" and not isinstance(val, dict):
            errors.append(f"字段 '{key}' 应为对象，当前为 {type(val).__name__}")

        # 检查 enum 约束
        enum_vals = prop.get("enum")
        if enum_vals is not None and val not in enum_vals:
            errors.append(f"字段 '{key}' 值 '{val}' 不在允许范围内: {enum_vals}")

        # 检查 minimum/maximum
        if expected_type == "integer" and isinstance(val, int):
            min_val = prop.get("minimum")
            max_val = prop.get("maximum")
            if min_val is not None and val < min_val:
                errors.append(f"字段 '{key}' 值 {val} 小于最小值 {min_val}")
            if max_val is not None and val > max_val:
                errors.append(f"字段 '{key}' 值 {val} 大于最大值 {max_val}")

        # 递归检查嵌套对象
        if expected_type == "object" and isinstance(val, dict):
            nested_props = prop.get("properties", {})
            nested_additional = prop.get("additionalProperties", True)
            if not nested_additional:
                for nk in val:
                    if nk not in nested_props:
                        errors.append(f"字段 '{key}.{nk}' 为未知子字段")

    return errors


def load_config() -> dict:
    """加载配置，启动时自动校验 Schema 合法性"""
    ensure_sra_home()
    config: dict = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                user_config = json.load(f)
            merged = {**DEFAULT_CONFIG, **user_config}
            config = merged
        except Exception as e:
            logger.warning("配置文件加载失败: %s", e)
            config = dict(DEFAULT_CONFIG)
    else:
        config = dict(DEFAULT_CONFIG)

    # Schema 校验（非阻断，仅警告）
    schema = _load_schema()
    if schema is not None:
        errors = validate_config(config, schema)
        for err in errors:
            logger.warning("配置校验: %s", err)

    # 环境变量覆盖（SRA_HTTP_PORT → http_port）
    env_prefix = "SRA_"
    env_type_map = {
        "http_port": int,
        "auto_refresh_interval": int,
        "max_connections": int,
        "enable_http": lambda v: v.lower() == "true",
        "enable_unix_socket": lambda v: v.lower() == "true",
        "watch_skills_dir": lambda v: v.lower() == "true",
    }
    for key in list(DEFAULT_CONFIG.keys()):
        env_key = f"{env_prefix}{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            try:
                converter = env_type_map.get(key)
                if converter:
                    config[key] = converter(env_val)
                else:
                    config[key] = env_val
                logger.debug("环境变量 %s=%s 已覆盖配置 %s", env_key, env_val, key)
            except (ValueError, TypeError) as e:
                logger.warning("环境变量 %s 解析失败: %s (值: %s)", env_key, e, env_val)

    return config


def save_config(config: dict) -> None:
    """保存配置"""
    ensure_sra_home()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
