# SRA Agent — Skill Runtime Advisor
# 让 AI Agent 知道自己有什么能力，以及什么时候该用什么能力。
# License: MIT

# ⚠️ 版本号由 setuptools-scm 从 git tag 自动生成
# 不要手动修改！版本来源见 pyproject.toml [tool.setuptools_scm]
# 层级 1: setuptools-scm 生成的 _version.py（built 包）
try:
    from ._version import version as __version__
except ImportError:
    try:
        # 层级 2: importlib.metadata（editable install + pip install）
        from importlib.metadata import version as _v
        __version__ = _v("sra-agent")
    except (ImportError, ModuleNotFoundError):
        # 层级 3: git describe（开发环境 fallback）
        try:
            import subprocess, os
            tag = subprocess.check_output(
                ["git", "describe", "--tags", "--dirty=.dirty", "--always"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).decode().strip().lstrip("v")
            __version__ = tag
        except Exception:
            __version__ = "0.0.0-dev"

__author__ = "Emma (SRA Team), Kei"

from .advisor import SkillAdvisor
from .runtime.daemon import SRaDDaemon
from .adapters import get_adapter, list_adapters

__all__ = [
    "SkillAdvisor",
    "SRaDDaemon",
    "get_adapter",
    "list_adapters",
]
