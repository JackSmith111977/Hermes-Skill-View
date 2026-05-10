"""SRA 运行时校验端点 — POST /validate

在 Agent 调用工具前校验是否已加载对应技能。
由 Hermes pre_tool_call hook 调用，返回非阻断性建议。
"""

import os
import logging
from typing import Dict, List, Optional, Any, TypedDict

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

    Returns:
        ValidateResponse 格式的响应
    """
    tool = request.get("tool", "")
    args = request.get("args", {})
    loaded_skills = request.get("loaded_skills", [])
    task_context = request.get("task_context", "")

    if not tool:
        return {
            "compliant": True,
            "missing": [],
            "severity": "info",
            "message": "",
        }

    # 只监控白名单中的工具
    if tool not in MONITORED_TOOLS:
        return {
            "compliant": True,
            "missing": [],
            "severity": "info",
            "message": "",
        }

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
