# SRA Agent — Skill Runtime Advisor
# 让 AI Agent 知道自己有什么能力，以及什么时候该用什么能力。
# License: MIT

# ⚠️ 版本号由 git tag 驱动，优先从 git 或 importlib 实时获取
# 不要手动修改！版本来源见 pyproject.toml [tool.setuptools_scm]


def _resolve_version() -> str:
    """三层版本解析：
    1. git describe（开发环境 / editable install — 源头活水）
    2. importlib.metadata（pip install 正式安装 — 发行版）
    3. _version.py（生成的 fallback）
    4. 绝望底线
    """
    import os
    import subprocess

    # 从 __file__ 向上找项目根目录（.git 所在处）
    _here = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_here)  # skill_advisor/../

    # 层级 1: git describe（开发环境 + editable install，只要 .git 存在就可靠）
    git_dir = os.path.join(_project_root, ".git")
    if os.path.isdir(git_dir) or os.path.isfile(git_dir):
        try:
            tag = subprocess.check_output(
                ["git", "describe", "--tags", "--dirty=.dirty", "--always"],
                cwd=_project_root,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).decode().strip().lstrip("v")
            # 如果是精确 tag 匹配（无 dev/post 后缀），直接返回
            if "-" not in tag:
                return tag
            # 有距离信息: "2.1.0-1-g5c513fe" → 保留开发标识
            return tag
        except Exception:
            pass

    # 层级 2: importlib.metadata（pip install 官方安装）
    try:
        from importlib.metadata import version as _v
        return _v("sra-agent")
    except Exception:
        pass

    # 层级 3: _version.py（如果存在）
    try:
        from ._version import version as _v
        if _v:
            return _v
    except Exception:
        pass

    return "0.0.0-dev"


__version__ = _resolve_version()

__author__ = "Emma (SRA Team), Kei"

# 模块级导入放在版本定义之后（避免循环引用 — daemon.py 会 import __version__）
# ruff: noqa: E402
from .adapters import get_adapter, list_adapters  # noqa: E402
from .advisor import SkillAdvisor  # noqa: E402
from .runtime.daemon import SRaDDaemon  # noqa: E402

__all__ = [
    "SkillAdvisor",
    "SRaDDaemon",
    "get_adapter",
    "list_adapters",
]
