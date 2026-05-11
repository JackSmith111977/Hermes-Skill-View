"""SRA 运行时校验端点 — POST /validate

在 Agent 调用工具前校验是否已加载对应技能。
由 Hermes pre_tool_call hook 调用，返回非阻断性建议。
"""

import logging
from typing import Any, Dict, List, TypedDict

from ..validate_core import validate_tool_call

logger = logging.getLogger("sra.validate")

# 监控的工具白名单
MONITORED_TOOLS = {"write_file", "patch", "terminal", "execute_code"}


class ValidateRequest(TypedDict, total=False):
    tool: str
    args: Dict[str, Any]
    loaded_skills: List[str]
    task_context: str


class ValidateResponse(TypedDict):
    compliant: bool
    missing: List[str]
    severity: str  # "info" | "warning" | "block"
    message: str


def handle_validate(request: Dict[str, Any]) -> Dict[str, Any]:
    """处理 /validate 请求

    Args:
        request: 包含 tool, args, loaded_skills, task_context 的字典
                 _force_level 和 _monitored_tools 由 daemon 自动注入

    Returns:
        ValidateResponse 格式的响应
    """
    tool = request.get("tool", "")
    args = request.get("args", {})
    loaded_skills = request.get("loaded_skills", [])
    request.get("task_context", "")

    # 力度等级感知：如果 pre_tool_call 未激活（basic 级别），直接放行
    force_level = request.get("_force_level", "medium")
    monitored_tools = request.get("_monitored_tools", MONITORED_TOOLS)

    if force_level == "basic":
        # basic 级别：不拦截任何工具调用
        return {
            "compliant": True,
            "missing": [],
            "severity": "info",
            "message": "",
        }

    if not tool:
        return {
            "compliant": True,
            "missing": [],
            "severity": "info",
            "message": "",
        }

    # 根据力度等级决定监控哪些工具
    if monitored_tools == "__all__":
        # advanced/omni: 监控全部工具
        pass  # 不过滤，全部继续
    elif tool not in monitored_tools and isinstance(monitored_tools, (set, list)):
        # medium: 只监控关键工具
        return {
            "compliant": True,
            "missing": [],
            "severity": "info",
            "message": "",
        }
    # monitored_tools 为空（理论上不会到这里，但防御性编码）
    if isinstance(monitored_tools, (set, list)) and not monitored_tools:
        return _compliant()

    try:
        result = validate_tool_call(tool, args, loaded_skills)
        return result
    except Exception as e:
        logger.warning("校验请求处理失败: %s", e)
        return {
            "compliant": True,
            "missing": [],
            "severity": "info",
            "message": "",
        }


def _compliant() -> Dict[str, Any]:
    """返回合规响应"""
    return {
        "compliant": True,
        "missing": [],
        "severity": "info",
        "message": "",
    }
