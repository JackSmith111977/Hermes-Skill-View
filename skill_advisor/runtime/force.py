"""SRA 运行时力度体系 — 注入覆盖度控制

力度不是阻断强度，而是「SRA 在哪些时机注入推荐上下文」。
力度越高，注入点越多、注入频率越高。

所有注入点均为非阻塞（info/warning 级别，无 block）。

层级定义：
  🐣 L1 basic    — 仅用户消息时注入
  🦅 L2 medium   — 消息 + 关键 pre_tool_call（write_file/patch/terminal/execute_code）
  🦖 L3 advanced — 消息 + 全部 pre_tool_call + post_tool_call
  🐉 L4 omni     — 全部 L3 + 周期性重注入
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("sra.force")

# ── 力度层级定义 ──────────────────────────────────────────

FORCE_LEVELS = {
    "basic": {
        "name": "basic",
        "label": "🐣 basic",
        "description": "仅用户消息时注入推荐",
        "injection_points": {"on_user_message"},
        "pre_tool_call_tools": set(),           # 无工具调用拦截
        "post_tool_call": False,
        "periodic_injection": False,
        "tier": 1,
    },
    "medium": {
        "name": "medium",
        "label": "🦅 medium",
        "description": "消息 + 关键工具调用前检查",
        "injection_points": {"on_user_message", "pre_tool_call"},
        "pre_tool_call_tools": {
            "write_file", "patch", "terminal", "execute_code",
        },
        "post_tool_call": False,
        "periodic_injection": False,
        "tier": 2,
    },
    "advanced": {
        "name": "advanced",
        "label": "🦖 advanced",
        "description": "消息 + 全部工具钩子 + 后检",
        "injection_points": {"on_user_message", "pre_tool_call", "post_tool_call"},
        "pre_tool_call_tools": "__all__",        # 全部工具都拦截
        "post_tool_call": True,
        "periodic_injection": False,
        "tier": 3,
    },
    "omni": {
        "name": "omni",
        "label": "🐉 omni",
        "description": "全部 L3 + 周期性重注入防漂移",
        "injection_points": {"on_user_message", "pre_tool_call", "post_tool_call", "periodic"},
        "pre_tool_call_tools": "__all__",
        "post_tool_call": True,
        "periodic_injection": True,
        "tier": 4,
    },
}

# 默认层级
DEFAULT_LEVEL = "medium"

# 注入点描述
INJECTION_POINT_LABELS = {
    "on_user_message": "用户消息注入",
    "pre_tool_call": "工具调用前检查",
    "post_tool_call": "工具调用后核查",
    "periodic": "周期性重注入",
}


class ForceLevelManager:
    """力度等级管理器

    管理 SRA 的运行时力度配置，控制注入点的启停。
    配置存储在 ~/.sra/config.json 中的 runtime_force.level 字段。
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.expanduser("~/.sra/config.json")
        self._current_level: str = DEFAULT_LEVEL
        self._config_cache: Optional[Dict[str, Any]] = None
        self._load_config()

    def _load_config(self) -> None:
        """从配置文件加载力度配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path) as f:
                    cfg = json.load(f)
                self._config_cache = cfg
                level = cfg.get("runtime_force", {}).get("level", DEFAULT_LEVEL)
                if level in FORCE_LEVELS:
                    self._current_level = level
                else:
                    logger.warning(
                        "未知的力度等级 '%s'，使用默认 '%s'",
                        level, DEFAULT_LEVEL,
                    )
                    self._current_level = DEFAULT_LEVEL
            else:
                self._current_level = DEFAULT_LEVEL
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            logger.debug("加载力度配置失败: %s，使用默认等级", e)
            self._current_level = DEFAULT_LEVEL

    def get_level(self) -> str:
        """获取当前力度等级"""
        return self._current_level

    def get_level_config(self) -> Dict[str, Any]:
        """获取当前等级的完整配置"""
        return FORCE_LEVELS.get(self._current_level, FORCE_LEVELS[DEFAULT_LEVEL])

    def set_level(self, level: str) -> bool:
        """设置力度等级并保存到配置文件

        Args:
            level: 等级名称（basic / medium / advanced / omni）

        Returns:
            bool: 是否成功
        """
        level = level.lower()
        if level not in FORCE_LEVELS:
            logger.error("无效的力度等级: '%s'，可选: %s", level, list(FORCE_LEVELS.keys()))
            return False

        self._current_level = level
        self._persist_config()
        logger.info("力度等级已切换为: %s (%s)", level, FORCE_LEVELS[level]["label"])
        return True

    def _persist_config(self) -> None:
        """持久化力度配置到文件"""
        try:
            cfg = {}
            if os.path.exists(self.config_path):
                with open(self.config_path) as f:
                    cfg = json.load(f)

            if "runtime_force" not in cfg:
                cfg["runtime_force"] = {}
            cfg["runtime_force"]["level"] = self._current_level

            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("保存力度配置失败: %s", e)

    def is_injection_point_active(self, point: str) -> bool:
        """检查指定注入点是否在当前等级下激活

        Args:
            point: 注入点名称（on_user_message / pre_tool_call / post_tool_call / periodic）

        Returns:
            bool: 是否激活
        """
        config = self.get_level_config()
        active_points = config.get("injection_points", set())
        return point in active_points

    def is_tool_monitored(self, tool_name: str) -> bool:
        """检查指定工具是否在当前等级下被监控

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否被监控（pre_tool_call 时应该检查）
        """
        config = self.get_level_config()
        monitored = config.get("pre_tool_call_tools", set())

        if monitored == "__all__":
            return True  # advanced/omni 监控全部工具
        return tool_name in monitored

    def get_monitored_tools(self) -> Set[str]:
        """获取当前等级下被监控的工具集合"""
        config = self.get_level_config()
        monitored = config.get("pre_tool_call_tools", set())
        if monitored == "__all__":
            return "__all__"
        return monitored

    def get_periodic_interval(self) -> int:
        """获取周期性注入的间隔轮数（L4 omni 默认 5 轮）"""
        return self._config_cache.get("runtime_force", {}).get("periodic_interval_rounds", 5) \
            if self._config_cache else 5

    def list_levels(self) -> List[Dict[str, Any]]:
        """列出所有可用的力度等级详情"""
        result = []
        for name, cfg in FORCE_LEVELS.items():
            active = cfg["injection_points"]
            result.append({
                "name": name,
                "label": cfg["label"],
                "description": cfg["description"],
                "tier": cfg["tier"],
                "active_injection_points": sorted(active),
                "is_current": name == self._current_level,
            })
        return result

    def get_summary(self) -> Dict[str, Any]:
        """获取当前力度状态的摘要"""
        config = self.get_level_config()
        return {
            "level": self._current_level,
            "label": config["label"],
            "description": config["description"],
            "tier": config["tier"],
            "active_points": sorted(config["injection_points"]),
            "monitored_tools": "__all__" if config["pre_tool_call_tools"] == "__all__"
                              else sorted(config["pre_tool_call_tools"]),
            "periodic": config["periodic_injection"],
            "periodic_interval": self.get_periodic_interval(),
        }
