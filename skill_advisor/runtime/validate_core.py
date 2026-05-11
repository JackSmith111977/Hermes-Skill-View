"""SRA 校验核心逻辑 — 验证工具调用是否已加载对应技能

独立于 HTTP/Socket 层，可被 Hermes plugin 直接调用。
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

from ..skill_map import SkillMapRegistry

logger = logging.getLogger("sra.validate_core")

# 全局 SkillMapRegistry 实例（懒加载）
_skill_map: Optional[SkillMapRegistry] = None


def _get_skill_map() -> SkillMapRegistry:
    """获取全局 SkillMapRegistry 实例"""
    global _skill_map
    if _skill_map is None:
        config_path = os.path.expanduser("~/.sra/config/skill_map.json")
        _skill_map = SkillMapRegistry(config_path)
    return _skill_map


def validate_tool_call(
    tool: str,
    args: Dict[str, Any],
    loaded_skills: List[str],
) -> Dict[str, Any]:
    """校验工具调用是否合规

    Args:
        tool: 工具名称 (write_file, patch, terminal, execute_code)
        args: 工具参数
        loaded_skills: 已加载的技能名称列表

    Returns:
        {
            "compliant": bool,
            "missing": List[str],
            "severity": "info" | "warning" | "block",
            "message": str
        }
    """
    loaded_skills_lower = [s.lower() for s in loaded_skills]

    if tool in ("write_file", "patch"):
        return _validate_file_tool(args, loaded_skills_lower)
    elif tool == "terminal":
        return _validate_terminal(args, loaded_skills_lower)
    elif tool == "execute_code":
        return _validate_execute_code(args, loaded_skills_lower)
    else:
        return _compliant()


def _validate_file_tool(
    args: Dict[str, Any],
    loaded_skills: List[str],
) -> Dict[str, Any]:
    """校验文件类工具 (write_file, patch)

    从 args 中提取 path/file_path/command 参数，
    通过扩展名查找推荐技能，对比 loaded_skills。
    """
    # 提取文件路径
    file_path = ""
    for key in ("path", "file_path", "filepath", "filename", "command"):
        val = args.get(key, "")
        if val and isinstance(val, str):
            file_path = val
            break

    if not file_path:
        return _compliant()

    # 通过扩展名查找推荐技能
    registry = _get_skill_map()
    recommended = registry.get_skills_for_file(file_path)

    if not recommended:
        return _compliant()

    # 检查是否有推荐技能已加载
    missing = []
    for skill in recommended:
        if skill.lower() not in loaded_skills:
            missing.append(skill)

    if not missing:
        return _compliant()

    return {
        "compliant": False,
        "missing": missing,
        "severity": "warning",
        "message": (
            f"检测到文件类型 `{os.path.splitext(file_path)[1]}`，"
            f"建议加载 skill: {', '.join(missing)}"
        ),
    }


def _validate_terminal(
    args: Dict[str, Any],
    loaded_skills: List[str],
) -> Dict[str, Any]:
    """校验 terminal 调用

    尝试从命令中推断文件类型，但 terminal 太通用，默认放行。
    """
    command = args.get("command", "")
    if not command or not isinstance(command, str):
        return _compliant()

    # 尝试从命令中提取文件名
    # 如 "python3 script.py"、"./run.sh"、"cat README.md"
    files_in_cmd = re.findall(r'(?:^|\s)(?:\./)?([\w.-]+\.[a-z]{1,6})(?:\s|$)', command, re.I)
    if not files_in_cmd:
        return _compliant()

    registry = _get_skill_map()
    all_missing = []

    for fname in files_in_cmd:
        recommended = registry.get_skills_for_file(fname)
        for skill in recommended:
            if skill.lower() not in loaded_skills:
                all_missing.append(skill)

    if not all_missing:
        return _compliant()

    # 去重
    missing = list(dict.fromkeys(all_missing))

    return {
        "compliant": False,
        "missing": missing,
        "severity": "info",  # terminal 的推荐只是 info 级别
        "message": (
            f"命令中检测到文件 `{files_in_cmd[0]}`，"
            f"可考虑加载 skill: {', '.join(missing)}"
        ),
    }


def _validate_execute_code(
    args: Dict[str, Any],
    loaded_skills: List[str],
) -> Dict[str, Any]:
    """校验 execute_code 调用

    execute_code 通常运行 Python 代码，默认放行。
    """
    return _compliant()


def _compliant() -> Dict[str, Any]:
    """返回合规响应"""
    return {
        "compliant": True,
        "missing": [],
        "severity": "info",
        "message": "",
    }
