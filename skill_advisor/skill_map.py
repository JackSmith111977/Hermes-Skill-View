"""
文件类型到技能的映射注册表

提供文件扩展名到推荐技能列表的映射，用于 SRA 校验引擎在
write_file/patch 等工具调用前自动推导需要的技能。
"""

import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("sra.skill_map")

# ── 默认文件类型→技能映射表 ─────────────────────
# 格式：扩展名 → [推荐技能名称列表]
# 扩展名不包含点，全部小写

DEFAULT_FILE_SKILL_MAP: Dict[str, List[str]] = {
    # === 文档 ===
    "md": ["markdown-guide"],
    "pdf": ["pdf-layout", "pdf-layout-weasyprint", "pdf-pro-design"],
    "docx": ["docx-guide"],
    "pptx": ["pptx-guide"],
    "xlsx": ["xlsx-guide"],
    "epub": ["epub-guide"],
    "csv": ["xlsx-guide", "financial-analyst"],
    "tex": ["latex-guide"],
    "rst": ["markdown-guide"],

    # === 网页 / 前端 ===
    "html": ["html-guide", "html-presentation"],
    "css": ["html-guide"],
    "js": ["html-guide"],
    "ts": ["html-guide"],
    "jsx": ["html-guide"],
    "tsx": ["html-guide"],

    # === 代码 ===
    "py": ["python-env-guide", "test-driven-development"],
    "rs": [],
    "go": [],
    "java": [],
    "c": [],
    "cpp": [],
    "h": [],
    "hpp": [],

    # === 配置 ===
    "json": [],
    "yaml": [],
    "yml": [],
    "toml": [],
    "ini": [],
    "cfg": [],
    "conf": [],

    # === 图片 / 设计图 ===
    "svg": ["architecture-diagram", "concept-diagrams"],
    "png": ["image-generation", "pixel-art"],
    "jpg": ["image-generation"],
    "jpeg": ["image-generation"],
    "webp": ["image-generation"],
    "gif": ["gif-search", "meme-creation"],
    "ico": [],

    # === 多媒体 ===
    "mp3": ["songwriting-and-ai-music", "text-to-speech"],
    "wav": ["songwriting-and-ai-music"],
    "flac": [],
    "mp4": ["manim-video", "ascii-video"],
    "mov": [],
    "avi": [],

    # === 数据 / 分析 ===
    "parquet": [],
    "feather": [],
    "pkl": [],
    "pickle": [],
    "h5": [],
    "hdf5": [],

    # === Mermaid / 图表 ===
    "mmd": ["mermaid-guide"],
    "puml": ["mermaid-guide"],
    "drawio": ["architecture-diagram"],
    "excalidraw": ["excalidraw"],

    # === Shell / 脚本 ===
    "sh": [],
    "bash": [],
    "zsh": [],
    "fish": [],
    "bat": [],
    "ps1": [],

    # === Docker / DevOps ===
    "dockerfile": ["docker-management"],
    "compose": ["docker-management"],
    "tf": [],
    "tfstate": [],
    "nginx": [],
    "env": [],
    "gitignore": [],

    # === 文档 / 学术 ===
    "bib": ["latex-guide"],
    "cls": ["latex-guide"],
    "sty": ["latex-guide"],

    # === 其他 ===
    "txt": [],
    "log": [],
    "lock": [],
    "sum": [],
    "checksum": [],
    "sig": [],
    "asc": [],
}

# 综合型映射：支持通配/模糊匹配的常见模式
DEFAULT_PATTERN_MAP: Dict[str, List[str]] = {
    "readme.*": ["markdown-guide"],
    "dockerfile*": ["docker-management"],
    "*.test.py": ["test-driven-development"],
    "*.spec.ts": ["test-driven-development"],
    "Makefile": [],
    "makefile": [],
    "CHANGELOG*": ["markdown-guide"],
    "LICENSE*": [],
    "requirements*.txt": [],
    "Pipfile*": [],
    "pyproject.toml": [],
    "package.json": [],
    "tsconfig.json": [],
    ".gitignore": [],
    ".dockerignore": ["docker-management"],
}


class SkillMapRegistry:
    """文件类型→技能映射注册表"""

    def __init__(self, config_path: Optional[str] = None):
        self._ext_map: Dict[str, List[str]] = {}
        self._pattern_map: Dict[str, List[str]] = {}
        self._config_path = config_path
        self.load()

    def load(self):
        """加载映射配置（用户配置覆盖默认配置）"""
        # 从默认配置开始
        self._ext_map = dict(DEFAULT_FILE_SKILL_MAP)
        self._pattern_map = dict(DEFAULT_PATTERN_MAP)

        # 尝试加载用户配置
        if self._config_path and os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r") as f:
                    user_config = json.load(f)

                # 合并扩展映射（用户配置完全覆盖同名 key）
                user_ext = user_config.get("ext_map", {})
                if isinstance(user_ext, dict):
                    self._ext_map.update(user_ext)

                # 合并模式映射
                user_pattern = user_config.get("pattern_map", {})
                if isinstance(user_pattern, dict):
                    self._pattern_map.update(user_pattern)

                logger.info("技能映射配置已加载: %s", self._config_path)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.warning("技能映射配置加载失败: %s，使用默认配置", e)
        elif self._config_path:
            logger.debug("技能映射配置文件不存在: %s，使用默认配置", self._config_path)

    def get_skills_for_file(self, filepath: str) -> List[str]:
        """根据文件路径返回推荐的技能列表

        Args:
            filepath: 文件路径（可以是完整路径或文件名）

        Returns:
            推荐技能名称列表（可能为空列表）
        """
        filename = os.path.basename(filepath).lower()
        ext = os.path.splitext(filename)[1].lower().lstrip(".")

        # Step 1: 精确扩展名匹配
        if ext and ext in self._ext_map:
            return list(self._ext_map[ext])

        # Step 2: 模式匹配（文件名模式）
        import fnmatch
        for pattern, skills in self._pattern_map.items():
            if fnmatch.fnmatch(filename, pattern.lower()):
                return list(skills)

        # Step 3: 无点文件名（如 Makefile, Dockerfile）
        if not ext and filename in self._ext_map:
            return list(self._ext_map[filename])

        return []

    def get_all_extensions(self) -> List[str]:
        """获取所有已注册的扩展名"""
        return sorted(self._ext_map.keys())

    def get_registered_count(self) -> int:
        """返回注册的扩展名数量"""
        return len(self._ext_map)

    def has_skills_for(self, ext: str) -> bool:
        """检查某个扩展名是否有推荐的技能"""
        ext = ext.lower().lstrip(".")
        return ext in self._ext_map and len(self._ext_map[ext]) > 0
