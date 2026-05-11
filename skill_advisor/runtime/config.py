"""SRA 运行时配置管理 — 路径常量 + 配置加载/保存"""

import os
import json
import logging

logger = logging.getLogger("sra.config")

# ── 路径常量 ─────────────────────────────────
SRA_HOME = os.path.expanduser("~/.sra")
PID_FILE = os.path.join(SRA_HOME, "srad.pid")
LOCK_FILE = os.path.join(SRA_HOME, "srad.lock")
SOCKET_FILE = os.path.join(SRA_HOME, "srad.sock")
LOG_FILE = os.path.join(SRA_HOME, "srad.log")
STATUS_FILE = os.path.join(SRA_HOME, "srad.status.json")
CONFIG_FILE = os.path.join(SRA_HOME, "config.json")

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


def load_config() -> dict:
    """加载配置"""
    ensure_sra_home()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                user_config = json.load(f)
            merged = {**DEFAULT_CONFIG, **user_config}
            return merged
        except Exception as e:
            logger.warning("配置文件加载失败: %s", e)
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """保存配置"""
    ensure_sra_home()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
